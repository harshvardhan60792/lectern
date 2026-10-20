"""Ask the data: plain-English questions turned into SQL by rules.

How it works
1. Clean the question and split it into words.
2. Find what is being asked for (the *intent*): count, average, rate, top, list.
3. Find what it is about (the *subject*): students, enrollments, courses, scores...
4. Find *filters*: a course, a result (passed, withdrew...), a region, a year,
   a score limit ("below 40"), a gender, an age band, an education level.
5. Find a *grouping* ("per course", "by region") and a *limit* ("top 5").
6. Build the SQL from fixed pieces. Typed values only ever travel as
   parameters, never as SQL text, and the pieces can only make a SELECT, so
   there is no way for a question to change or delete data. It also runs on a
   read-only connection with a row limit.

If a question can't be understood, it says so and suggests ones that work.
"""
import re
from dataclasses import dataclass, field
from datetime import timedelta

from services import common
from smart import text as tt

MAX_ROWS = 200
DEFAULT_LIST = 50

EXAMPLES = [
    "How many students withdrew from DDD-2013J?",
    "Pass rate by education level",
    "Average score per course",
    "Top 5 students by score in AAA-2014J",
    "Withdrawal rate by region",
    "How many certificates were issued in 2014?",
    "Students from Scotland with a score below 40",
    "Total clicks by month for BBB-2013J",
    "Average score by age band for women",
    "Number of questions per skill in maths",
    "Courses with the highest completion rate",
    "How many students passed with distinction?",
]


class NotUnderstood(ValueError):
    pass


@dataclass
class Parsed:
    intent: str = "list"            # count | average | rate | top | bottom | total | list
    subject: str | None = None       # students | enrollments | courses | scores | certificates | questions | answers | activity
    metric: str | None = None        # score | clicks | completion | withdrawal | failure | enrollments | accuracy
    rate_kind: str = "completion"
    filters: list[tuple[str, str, object]] = field(default_factory=list)  # (kind, label, value)
    group: str | None = None
    limit: int | None = None
    threshold: tuple[str, float] | None = None   # ("<", 40)
    mentions_withdrawal: bool = False


# Vocabulary ------------------------------------------------------------------

SUBJECT_WORDS = {
    "students": ["student", "students", "learner", "learners", "people", "who"],
    "enrollments": ["enrollment", "enrollments", "enrolment", "enrolments", "registration", "registrations"],
    "courses": ["course", "courses", "class", "classes", "presentations"],
    "certificates": ["certificate", "certificates"],
    "questions": ["question", "questions", "problem", "problems"],
    "answers": ["answer", "answers", "response", "responses", "attempts"],
    "activity": ["click", "clicks", "activity"],
    "scores": ["score", "scores", "mark", "marks", "grade", "grades"],
}
GROUP_WORDS = {
    "course": ["course", "courses", "presentation"],
    "region": ["region", "regions", "area"],
    "education": ["education", "qualification", "qualifications", "education level"],
    "age": ["age", "age band", "age group"],
    "gender": ["gender", "sex"],
    "result": ["result", "results", "outcome", "outcomes", "status", "final result"],
    "month": ["month", "months"],
    "year": ["year", "years"],
    "subject": ["subject", "subjects", "domain"],
    "skill": ["skill", "skills", "module", "modules", "topic", "topics", "assessment", "assessments"],
    "source": ["source", "dataset"],
    "disability": ["disability"],
    "deprivation": ["deprivation", "imd", "imd band"],
}
RESULT_WORDS = [
    (r"\bdistinctions?\b", "result", "Distinction"),
    (r"\b(passed|pass|completed|finished|completers)\b", "status", "completed"),
    (r"\b(failed|fail|failing)\b", "status", "failed"),
    (r"\b(withdrew|withdrawn|withdraw|dropped|drop ?outs?|quit)\b", "status", "withdrawn"),
    (r"\b(active|current|ongoing)\b", "status", "active"),
]
EDUCATION = {
    "no formal": "No Formal quals",
    "lower than a level": "Lower Than A Level",
    "a level": "A Level or Equivalent",
    "he qualification": "HE Qualification",
    "degree": "HE Qualification",
    "post graduate": "Post Graduate Qualification",
    "postgraduate": "Post Graduate Qualification",
}
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
TOPIC_COURSES = {
    "python": ("title", "%Python%"),
    "maths": ("code", "ASSIST-0910"), "math": ("code", "ASSIST-0910"), "mathematics": ("code", "ASSIST-0910"),
    "science": ("code", "SCI-101"),
    "stem": ("subject", "STEM"),
    "social sciences": ("subject", "Social Sciences"),
}
SOURCES = {"open university": "oulad", "assistments": "assistments", "added here": "local", "local": "local"}


def _has(text: str, *phrases: str) -> bool:
    return any(re.search(rf"\b{re.escape(p)}\b", text) for p in phrases)


def parse(question: str, regions: list[str], courses: list[dict]) -> Parsed:
    if ";" in question or re.search(r"\b(drop|delete|truncate|alter)\s+(table|from|database)\b|--", question, re.I):
        raise NotUnderstood("That looks like SQL. Ask in plain English instead; this box only reads data.")
    q = question.lower().strip().rstrip("?.! ")
    q = re.sub(r"[“”\"',;]", " ", q)
    q = re.sub(r"\s+", " ", q)
    if re.match(r"^(please\s+)?(delete|remove|drop|update|insert|change|set|add|create|alter|modify|erase|wipe|truncate)\b", q):
        raise NotUnderstood("This box only reads data. It can't add, change or delete anything.")
    p = Parsed()
    p.mentions_withdrawal = bool(re.search(r"\b(withdraw\w*|dropout|drop out|drop-out)\b", q))

    # Intent ----------------------------------------------------------------
    m = re.search(r"\b(top|best|highest|most|bottom|worst|lowest|least|fewest|first)\s+(\d+)\b", q)
    ranking = re.search(r"\b(top|best|highest|most|bottom|worst|lowest|least|fewest)\b", q)
    if m:
        p.intent = "bottom" if m.group(1) in ("bottom", "worst", "lowest", "least", "fewest") else "top"
        p.limit = int(m.group(2))
    elif ranking and re.search(r"\b(courses?|students?|learners?)\b", q) and not _has(q, "how many", "number of"):
        p.intent = "bottom" if ranking.group(1) in ("bottom", "worst", "lowest", "least", "fewest") else "top"
        p.limit = 10
    elif _has(q, "how many", "number of", "count"):
        p.intent = "count"
    elif re.search(r"\b(completion|pass|passing|success|withdrawal|withdraw|dropout|drop out|drop-out|fail|failure)\s+rates?\b", q) \
            or _has(q, "percentage", "percent", "share", "proportion"):
        p.intent = "rate"
        if re.search(r"\b(withdrawal|withdraw|dropout|drop out|drop-out)\b", q):
            p.rate_kind = "withdrawal"
        elif re.search(r"\b(fail|failure)\s+rate", q):
            p.rate_kind = "failure"
    elif _has(q, "average", "mean", "avg", "typical"):
        p.intent = "average"
    elif _has(q, "total", "sum"):
        p.intent = "total"
    elif _has(q, "highest", "best", "most", "top"):
        p.intent, p.limit = "top", 10
    elif _has(q, "lowest", "worst", "least", "fewest", "bottom"):
        p.intent, p.limit = "bottom", 10

    # Subject and metric ---------------------------------------------------------
    found = {s: min((m.start() for w in ws for m in [re.search(rf"\b{w}\b", q)] if m), default=None)
             for s, ws in SUBJECT_WORDS.items()}
    present = {s: pos for s, pos in found.items() if pos is not None}
    if _has(q, "clicks", "click", "activity"):
        p.metric = "clicks"
    elif _has(q, "score", "scores", "mark", "marks", "grade", "grades"):
        p.metric = "score"
    elif _has(q, "accuracy", "correct"):
        p.metric = "accuracy"
    elif _has(q, "completion rate", "pass rate"):
        p.metric = "completion"
    elif p.intent in ("top", "bottom") and _has(q, "students", "enrollments", "popular", "enrolled"):
        p.metric = "enrollments"

    # The thing being counted or listed is usually the first subject word.
    nouns = [s for s in sorted(present, key=present.get) if s not in ("scores", "activity")]
    if p.intent == "rate":
        p.subject = "enrollments"
    elif p.intent in ("average", "total") and p.metric in ("score", "clicks", "accuracy"):
        p.subject = {"score": "scores", "clicks": "activity", "accuracy": "answers"}[p.metric]
    elif nouns:
        p.subject = nouns[0]
    elif p.metric == "score":
        p.subject = "scores"
    elif p.metric == "clicks":
        p.subject = "activity"
    if p.subject == "students" and p.intent == "average" and p.metric is None:
        p.metric = "score"
        p.subject = "scores"
    if p.subject == "answers" and p.intent == "average":
        p.metric = "accuracy"

    # Grouping --------------------------------------------------------------
    # Lookahead so "per student by result" still finds "by result".
    for g in re.finditer(r"\b(?:per|by|for each|in each|across|each)\s+(?=([a-z ]+))", q):
        tail = g.group(1)
        p.group = next((key for key, words in GROUP_WORDS.items() if any(tail.startswith(w) for w in words)), None)
        if p.group:
            break

    # Filters ----------------------------------------------------------------
    _course_filters(q, p, courses)

    for pattern, kind, value in RESULT_WORDS:
        if re.search(pattern, q) and not re.search(pattern + r"\s+rates?", q):
            if kind == "status" and value == "completed" and p.intent == "rate":
                continue
            if kind == "status" and value == "withdrawn" and p.intent == "rate":
                continue
            p.filters.append((kind, "result", value))
            break

    if _has(q, "women", "female", "females", "woman", "girls"):
        p.filters.append(("gender", "gender", "F"))
    elif _has(q, "men", "male", "males", "man", "boys"):
        p.filters.append(("gender", "gender", "M"))

    for phrase, value in sorted(EDUCATION.items(), key=lambda kv: -len(kv[0])):
        if _has(q, phrase) and p.group != "education":
            p.filters.append(("education", "education", value))
            break

    if _has(q, "with a disability", "with disability", "disabled", "with disabilities"):
        p.filters.append(("disability", "disability", "Y"))
    elif _has(q, "without a disability", "without disability"):
        p.filters.append(("disability", "disability", "N"))

    age_context = _has(q, "age", "aged", "years old", "older", "younger")
    if age_context:
        if re.search(r"\b(under|below|younger than)\s+35\b", q) or "0-35" in q:
            p.filters.append(("age", "age band", "0-35"))
        elif re.search(r"\b35\s*(-|to)\s*55\b", q):
            p.filters.append(("age", "age band", "35-55"))
        elif re.search(r"\b(over|above|older than)\s+55\b", q) or "55+" in q:
            p.filters.append(("age", "age band", "55<="))

    for name in sorted(regions, key=len, reverse=True):
        short = name.lower().replace(" region", "")
        if _has(q, short):
            p.filters.append(("region", "region", name))
            break

    for phrase, value in SOURCES.items():
        if _has(q, phrase):
            p.filters.append(("source", "source", value))
            break

    th = re.search(r"\b(below|under|less than|lower than|above|over|more than|greater than|at least|at most)\s+(\d+(?:\.\d+)?)\s*%?", q)
    if th and not (age_context and th.group(2) in ("35", "55")):
        op = "<" if th.group(1) in ("below", "under", "less than", "lower than") else \
             "<=" if th.group(1) == "at most" else ">=" if th.group(1) == "at least" else ">"
        p.threshold = (op, float(th.group(2)))
        if p.metric is None:
            p.metric = "score"

    _time_filters(q, p)

    if p.subject is None and p.intent == "list" and not p.filters:
        raise NotUnderstood("I couldn't tell what you're asking about.")
    if p.subject is None:
        p.subject = "students"
    return p


def _course_filters(q: str, p: Parsed, courses: list[dict]) -> None:
    m = re.search(r"\b([a-g]{3})[ -]?(20\d\d[bj])\b", q)
    if m:
        p.filters.append(("course_code", "course", f"{m.group(1).upper()}-{m.group(2).upper()}"))
        return
    m = re.search(r"\b(?:module|course)\s+([a-g]{3})\b|\b([a-g])\2\2\b", q)
    if m:
        code = (m.group(1) or m.group(0)).upper()[-3:]
        p.filters.append(("course_prefix", "course", f"{code}-%"))
        return
    for c in courses:
        if re.search(rf"\b{re.escape(c['code'].lower())}\b", q):
            p.filters.append(("course_code", "course", c["code"]))
            return
    for word, (kind, value) in TOPIC_COURSES.items():
        if _has(q, word):
            p.filters.append(({"title": "course_title", "code": "course_code", "subject": "subject"}[kind],
                              "course" if kind != "subject" else "subject", value))
            return
    # Typo-tolerant title match on "in/for <words>".
    m = re.search(r"\b(?:in|for|on|of)\s+([a-z0-9 :\-]{4,60})$", q)
    if m:
        # Compare with full titles and with the part before a colon ("Python programming I").
        names = {}
        for c in courses:
            names[c["title"]] = c["title"]
            names.setdefault(c["title"].split(":")[0].strip(), c["title"])
        hit = tt.best_match(m.group(1).strip(), list(names), cutoff=0.75)
        if hit:
            p.filters.append(("course_title", "course", names[hit]))
            return
    # A misspelt topic word ("pyhton").
    for word in q.split():
        hit = tt.best_match(word, list(TOPIC_COURSES), cutoff=0.8) if len(word) > 4 else None
        if hit:
            kind, value = TOPIC_COURSES[hit]
            p.filters.append(({"title": "course_title", "code": "course_code", "subject": "subject"}[kind],
                              "course" if kind != "subject" else "subject", value))
            return


def _time_filters(q: str, p: Parsed) -> None:
    today = common.today()
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(20\d\d)\b", q)
    if m:
        p.filters.append(("month", "month", f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"))
        return
    m = re.search(r"\b(?:in|during|for|from)\s+(20\d\d)\b", q) or re.search(r"\b(20\d\d)\b(?![bj-])", q)
    if m and not re.search(r"20\d\d[bj]", q):
        p.filters.append(("year", "year", m.group(1)))
        return
    if _has(q, "this month"):
        p.filters.append(("since", "since", today.replace(day=1).isoformat()))
    elif _has(q, "this year"):
        p.filters.append(("since", "since", today.replace(month=1, day=1).isoformat()))
    else:
        m = re.search(r"\b(?:last|past)\s+(\d+)\s+days\b", q)
        if m:
            p.filters.append(("since", "since", (today - timedelta(days=int(m.group(1)))).isoformat()))
        elif _has(q, "today"):
            p.filters.append(("since", "since", today.isoformat()))


# SQL building ----------------------------------------------------------------

# How to reach each table from each subject's main table.
JOINS = {
    "students": {
        "e": ([], "JOIN enrollments e ON e.student_id = s.id"),
        "c": (["e"], "JOIN courses c ON c.id = e.course_id"),
    },
    "enrollments": {
        "s": ([], "JOIN students s ON s.id = e.student_id"),
        "c": ([], "JOIN courses c ON c.id = e.course_id"),
    },
    "courses": {
        "v": ([], "JOIN v_course_stats v ON v.course_id = c.id"),
    },
    "scores": {
        "m": ([], "JOIN modules m ON m.id = mp.module_id"),
        "c": (["m"], "JOIN courses c ON c.id = m.course_id"),
        "s": ([], "JOIN students s ON s.id = mp.student_id"),
        "e": (["m"], "JOIN enrollments e ON e.student_id = mp.student_id AND e.course_id = m.course_id"),
    },
    "certificates": {
        "s": ([], "JOIN students s ON s.id = ct.student_id"),
        "c": ([], "JOIN courses c ON c.id = ct.course_id"),
    },
    "questions": {
        "m": ([], "JOIN modules m ON m.id = q.module_id"),
        "c": (["m"], "JOIN courses c ON c.id = m.course_id"),
    },
    "answers": {
        "q": ([], "JOIN questions q ON q.id = r.question_id"),
        "m": (["q"], "JOIN modules m ON m.id = q.module_id"),
        "c": (["m"], "JOIN courses c ON c.id = m.course_id"),
        "s": ([], "JOIN students s ON s.id = r.student_id"),
    },
    "activity": {
        "s": ([], "JOIN students s ON s.id = a.student_id"),
        "c": ([], "JOIN courses c ON c.id = a.course_id"),
        "e": ([], "JOIN enrollments e ON e.student_id = a.student_id AND e.course_id = a.course_id"),
    },
}
BASE = {
    "students": "students s", "enrollments": "enrollments e", "courses": "courses c",
    "scores": "module_progress mp", "certificates": "certificates ct", "questions": "questions q",
    "answers": "responses r", "activity": "activity_days a",
}
KEY = {
    "students": "s.id", "enrollments": "e.id", "courses": "c.id", "scores": "mp.rowid",
    "certificates": "ct.id", "questions": "q.id", "answers": "r.id", "activity": "a.rowid",
}
DATE = {
    "students": "e.enrolled_on", "enrollments": "e.enrolled_on", "certificates": "ct.issued_on",
    "scores": "mp.completed_on", "answers": "r.answered_at", "activity": "a.day", "courses": "c.starts_on",
    "questions": "q.created_at",
}
GROUP_SQL = {
    "course": ("c.code", "course", "c"), "region": ("s.region", "region", "s"),
    "education": ("s.highest_education", "education", "s"), "age": ("s.age_band", "age band", "s"),
    "gender": ("s.gender", "gender", "s"), "result": ("COALESCE(e.final_result, e.status)", "result", "e"),
    "subject": ("c.subject", "subject", "c"), "skill": ("m.title", "module", "m"),
    "source": ("s.source", "source", "s"), "disability": ("s.disability", "disability", "s"),
    "deprivation": ("s.imd_band", "deprivation band", "s"),
}
FILTER_SQL = {
    "course_code": ("c.code = ?", "c"), "course_prefix": ("c.code LIKE ?", "c"),
    "course_title": ("c.title LIKE ?", "c"), "subject": ("c.subject = ?", "c"),
    "status": ("e.status = ?", "e"), "result": ("e.final_result = ?", "e"),
    "gender": ("s.gender = ?", "s"), "education": ("s.highest_education = ?", "s"),
    "disability": ("s.disability = ?", "s"), "age": ("s.age_band = ?", "s"),
    "region": ("s.region = ?", "s"), "source": ("s.source = ?", "s"),
}


@dataclass
class Built:
    sql: str
    params: list
    explanation: str


class _Query:
    def __init__(self, subject: str):
        self.subject = subject
        self.joins: list[str] = []
        self.where: list[str] = []
        self.params: list = []

    def need(self, alias: str) -> None:
        base_alias = BASE[self.subject].split()[1]
        if alias == base_alias or alias in self.joins:
            return
        spec = JOINS[self.subject].get(alias)
        if spec is None:
            raise NotUnderstood(f"I can't combine {self.subject} with that filter or grouping.")
        for dep in spec[0]:
            self.need(dep)
        if alias not in self.joins:
            self.joins.append(alias)

    def from_sql(self) -> str:
        return " ".join([f"FROM {BASE[self.subject]}"] + [JOINS[self.subject][a][1] for a in self.joins])


def build(p: Parsed) -> Built:
    subject = p.subject
    q = _Query(subject)
    said = []

    if subject == "students" and any(k in ("course_code", "course_prefix", "course_title", "subject", "status", "result")
                                       for k, _, _ in p.filters):
        q.need("e")

    for kind, label, value in p.filters:
        if kind in ("year", "month", "since"):
            col = DATE.get(subject)
            if subject == "students":
                q.need("e")
            if kind == "year":
                q.where.append(f"substr({col}, 1, 4) = ?")
            elif kind == "month":
                q.where.append(f"substr({col}, 1, 7) = ?")
            else:
                q.where.append(f"{col} >= ?")
            q.params.append(value)
            said.append(f"{label} {value}")
            continue
        sql, alias = FILTER_SQL[kind]
        if subject == "courses" and alias in ("s", "e"):
            raise NotUnderstood("Course questions can't be filtered by student details. Try asking about enrollments.")
        q.need(alias)
        q.where.append(sql)
        q.params.append(value)
        shown = value.replace("%", "") if isinstance(value, str) else value
        said.append(f"{label} = {shown}")

    group_expr = group_label = None
    if p.group:
        if p.group in ("month", "year"):
            col = DATE.get(subject)
            if subject == "students":
                q.need("e")
            group_expr = f"substr({col}, 1, {7 if p.group == 'month' else 4})"
            group_label = p.group
        else:
            expr, group_label, alias = GROUP_SQL[p.group]
            if subject == "courses" and alias in ("s", "e"):
                raise NotUnderstood("Try 'rate by …' or 'enrollments by …' for that grouping.")
            q.need(alias)
            group_expr = expr

    where = f"WHERE {' AND '.join(q.where)}" if q.where else ""
    limit = min(p.limit or DEFAULT_LIST, MAX_ROWS)

    def finish(select: str, tail: str = "", order: str = "") -> str:
        parts = [f"SELECT {select}", q.from_sql(), where, tail, order]
        return "\n".join(x for x in parts if x)

    # Rates over enrollments.
    if p.intent == "rate":
        column = {"completion": "completed", "withdrawal": "withdrawn", "failure": "failed"}[p.rate_kind]
        rate = (f"ROUND(100.0 * SUM(e.status = '{column}') / NULLIF(SUM(e.status <> 'active'), 0), 1)")
        name = f"{p.rate_kind}_rate"
        if group_expr:
            sql = finish(f"{group_expr} AS \"{group_label}\", COUNT(*) AS enrollments, {rate} AS {name}",
                         f"GROUP BY {group_expr}", f"ORDER BY {name} DESC")
        else:
            sql = finish(f"COUNT(*) AS enrollments, {rate} AS {name}")
        return Built(sql, q.params, _explain(f"{p.rate_kind} rate of enrollments", said, group_label))

    # Average / total of a measure.
    if p.intent in ("average", "total") or (p.intent in ("top", "bottom") and p.metric in ("score", "clicks", "accuracy")
                                             and subject in ("scores", "activity", "answers")):
        measure, label = _measure(p, subject)
        q_where_threshold(q, p, subject)
        where = f"WHERE {' AND '.join(q.where)}" if q.where else ""
        direction = "ASC" if p.intent == "bottom" else "DESC"
        if group_expr:
            sql = finish(f"{group_expr} AS \"{group_label}\", {measure} AS {label}, COUNT(DISTINCT {_who(subject)}) AS students",
                         f"GROUP BY {group_expr}", f"ORDER BY {label} {direction}\nLIMIT {limit}")
        else:
            sql = finish(f"{measure} AS {label}, COUNT(DISTINCT {_who(subject)}) AS students")
        return Built(sql, q.params, _explain(label.replace("_", " "), said, group_label))

    # Top / bottom students or courses.
    if p.intent in ("top", "bottom"):
        direction = "ASC" if p.intent == "bottom" else "DESC"
        if subject == "courses":
            q.need("v")
            if p.mentions_withdrawal:
                metric, by = "ROUND(100.0 * v.withdrawn / NULLIF(v.enrolled, 0), 1)", "withdrawal rate"
            elif p.metric == "completion":
                metric, by = "v.completion_rate", "completion rate"
            else:
                metric, by = "v.enrolled", "enrollments"
            sql = finish(f"c.code, c.title, v.enrolled, v.completion_rate, {metric} AS ranked_by",
                         "", f"ORDER BY {metric} {direction}\nLIMIT {limit}")
            return Built(sql, q.params, _explain(f"{p.intent} {limit} courses by {by}", said, None))
        if subject in ("students", "enrollments", "scores"):
            return _top_students(p, said, direction, limit)

    # Counts.
    if p.intent == "count":
        if p.threshold and subject in ("students", "scores"):
            return _students_with_threshold(p, said, count=True)
        key = KEY[subject]
        if group_expr:
            sql = finish(f"{group_expr} AS \"{group_label}\", COUNT(DISTINCT {key}) AS {subject}",
                         f"GROUP BY {group_expr}", f"ORDER BY {subject} DESC\nLIMIT {limit}")
        else:
            sql = finish(f"COUNT(DISTINCT {key}) AS {subject}")
        return Built(sql, q.params, _explain(f"count of {subject}", said, group_label))

    # Lists.
    if p.threshold and subject in ("students", "scores"):
        return _students_with_threshold(p, said, count=False)
    columns = {
        "students": "DISTINCT s.display_name AS student, s.region, s.highest_education AS education, s.age_band",
        "enrollments": "s.display_name AS student, c.code AS course, e.status, e.final_result, e.enrolled_on",
        "courses": "c.code, c.title, c.subject, v.enrolled, v.completion_rate",
        "certificates": "ct.code, s.display_name AS student, c.title AS course, ct.issued_on, ct.score",
        "questions": "q.id, COALESCE(q.prompt, 'Problem ' || q.external_id) AS question, m.title AS module",
        "answers": "s.display_name AS student, COALESCE(q.prompt, 'Problem ' || q.external_id) AS question, r.is_correct",
        "scores": "s.display_name AS student, c.code AS course, m.title AS module, mp.best_score",
        "activity": "s.display_name AS student, c.code AS course, a.day, a.clicks",
    }[subject]
    for alias in {"enrollments": ["s", "c"], "courses": ["v"], "certificates": ["s", "c"], "questions": ["m"],
                  "answers": ["q", "m", "s"], "scores": ["m", "c", "s"], "activity": ["s", "c"]}.get(subject, []):
        q.need(alias)
    if group_expr:
        sql = finish(f"{group_expr} AS \"{group_label}\", COUNT(DISTINCT {KEY[subject]}) AS {subject}",
                     f"GROUP BY {group_expr}", f"ORDER BY {subject} DESC\nLIMIT {limit}")
    else:
        sql = finish(columns, "", f"LIMIT {limit}")
    return Built(sql, q.params, _explain(f"list of {subject}", said, group_label))


def _who(subject: str) -> str:
    return {"scores": "mp.student_id", "activity": "a.student_id", "answers": "r.student_id"}.get(subject, "s.id")


def _measure(p: Parsed, subject: str) -> tuple[str, str]:
    if subject == "activity" or p.metric == "clicks":
        if p.intent == "total":
            return "SUM(a.clicks)", "total_clicks"
        return "ROUND(1.0 * SUM(a.clicks) / COUNT(DISTINCT a.student_id), 1)", "clicks_per_student"
    if subject == "answers" or p.metric == "accuracy":
        return "ROUND(100.0 * AVG(r.is_correct), 1)", "percent_correct"
    if subject == "scores":
        return "ROUND(AVG(mp.best_score), 1)", "average_score"
    raise NotUnderstood("I can average scores, clicks or answer accuracy.")


def q_where_threshold(q: _Query, p: Parsed, subject: str) -> None:
    if p.threshold and subject == "scores":
        q.where.append(f"mp.best_score {p.threshold[0]} ?")
        q.params.append(p.threshold[1])


def _top_students(p: Parsed, said: list[str], direction: str, limit: int) -> Built:
    q = _Query("scores")
    q.need("s")
    for kind, label, value in p.filters:
        if kind in FILTER_SQL:
            sql, alias = FILTER_SQL[kind]
            q.need(alias)
            q.where.append(sql)
            q.params.append(value)
    where = f"WHERE {' AND '.join(q.where)}" if q.where else ""
    sql = "\n".join(x for x in [
        "SELECT s.display_name AS student, ROUND(AVG(mp.best_score), 1) AS average_score, COUNT(*) AS scored_modules",
        q.from_sql(), where,
        "GROUP BY s.id\nHAVING COUNT(*) >= 3",
        f"ORDER BY average_score {direction}, scored_modules DESC\nLIMIT {limit}",
    ] if x)
    return Built(sql, q.params, _explain(f"{'top' if direction == 'DESC' else 'bottom'} {limit} students by average score",
                                         said, None) + " (students with at least 3 scored modules)")


def _students_with_threshold(p: Parsed, said: list[str], count: bool) -> Built:
    q = _Query("scores")
    q.need("s")
    for kind, label, value in p.filters:
        if kind in FILTER_SQL:
            sql, alias = FILTER_SQL[kind]
            q.need(alias)
            q.where.append(sql)
            q.params.append(value)
    where = f"WHERE {' AND '.join(q.where)}" if q.where else ""
    op, value = p.threshold
    inner = "\n".join(x for x in [
        "SELECT s.display_name AS student, ROUND(AVG(mp.best_score), 1) AS average_score",
        q.from_sql(), where, f"GROUP BY s.id\nHAVING AVG(mp.best_score) {op} ?",
    ] if x)
    params = q.params + [value]
    said = said + [f"average score {op} {value:g}"]
    if count:
        return Built(f"SELECT COUNT(*) AS students FROM (\n{inner}\n)", params, _explain("count of students", said, None))
    return Built(inner + f"\nORDER BY average_score\nLIMIT {DEFAULT_LIST}", params, _explain("students", said, None))


def _explain(what: str, said: list[str], group: str | None) -> str:
    text = what[0].upper() + what[1:]
    if said:
        text += " where " + ", ".join(said)
    if group:
        text += f", grouped by {group}"
    return text + "."


# Running -----------------------------------------------------------------------

SAFE_START = re.compile(r"^\s*SELECT\b", re.IGNORECASE)
FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM)\b", re.IGNORECASE)


def check_safe(sql: str) -> None:
    """Belt and braces: the builder only makes SELECTs, but check anyway."""
    if not SAFE_START.match(sql) or FORBIDDEN.search(sql) or ";" in sql:
        raise NotUnderstood("Refused: only single read-only SELECT queries are allowed.")


def display_sql(sql: str, params: list) -> str:
    """The SQL with values filled in, for showing (never for running)."""
    out = sql
    for value in params:
        if isinstance(value, str):
            shown = "'" + value.replace("'", "''") + "'"
        elif isinstance(value, float):
            shown = f"{value:g}"
        else:
            shown = str(value)
        out = out.replace("?", shown, 1)
    return out


def ask(question: str, write_conn, read_conn) -> dict:
    """Answer a question. `read_conn` must be a read-only connection."""
    if not question.strip():
        raise NotUnderstood("Type a question first.")
    regions = [r[0] for r in write_conn.execute("SELECT DISTINCT region FROM students WHERE region IS NOT NULL")]
    courses = [dict(r) for r in write_conn.execute("SELECT code, title FROM courses")]
    parsed = parse(question, regions, courses)
    built = build(parsed)
    check_safe(built.sql)
    cur = read_conn.execute(built.sql, built.params)
    columns = [d[0] for d in cur.description]
    rows = [tuple(r) for r in cur.fetchmany(MAX_ROWS)]
    return {
        "question": question,
        "understood": built.explanation,
        "sql": built.sql,
        "params": built.params,
        "shown_sql": display_sql(built.sql, built.params),
        "columns": columns,
        "rows": rows,
    }
