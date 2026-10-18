"""Import "Introduction to Python Programming" from OpenStax.

Source: Das, U., Lawson, A., Mayfield, C. & Norouzi, N. Introduction to Python
Programming. OpenStax, Rice University, 2024. https://openstax.org/details/books/introduction-python-programming
Licence: CC BY-NC-SA 4.0. Attribution: "Access for free at openstax.org."

The book is split into two courses (chapters 1–7 and 8–15). Each chapter is a
module and each numbered section a lesson. The "Concepts in practice"
questions in the book, with the official answer key, become the quiz bank.
"""
import re
import sqlite3
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from db import transaction
from smart.text import looks_like_python

ATTRIBUTION = ("Content: Introduction to Python Programming, OpenStax (Rice University), "
               "CC BY-NC-SA 4.0. Access for free at openstax.org.")

COURSES = [
    ("PY-101", "Python programming I: foundations", range(1, 8),
     "Statements, expressions, objects, decisions, loops, functions and modules. "
     "Built from chapters 1–7 of the OpenStax textbook."),
    ("PY-102", "Python programming II: data and objects", range(8, 16),
     "Strings, lists, dictionaries, classes, recursion, inheritance, files and an introduction to data science. "
     "Built from chapters 8–15 of the OpenStax textbook. Requires Python I."),
]

FOOTER_PATTERNS = [
    re.compile(r"^Access for free at openstax\.org\.?$"),
    re.compile(r"^\d+\s+\d+\s*[•�]\s.*$"),          # "14     1 • Statements"
    re.compile(r"^\d+\.\d+\s*[•�]\s.*\s\d+$"),      # "15.5 • Data visualization     351"
    re.compile(r"^\d+\s*[•�]\s.*\s\d+$"),           # "1 • Introduction     17"
]
QUESTION = re.compile(r"^(\d+)\s?\.\s+(.*)$")
OPTION = re.compile(r"^([a-e])\.\s+(.*)$")
VIDEO = re.compile(r"\((https?://(?:www\.)?openstax\.org/r/[^\s)]+)\)")
BLOCK_MARKERS = {"CHECKPOINT", "CONCEPTS IN PRACTICE", "TRY IT", "EXPLORING FURTHER", "Learning objectives"}


class Line(str):
    """One line of PDF text, stripped, that remembers where it started.

    `lead` is how far it was indented compared with the page's normal text
    margin (it can be negative). Left and right pages have different margins, so
    measuring from the margin keeps code indentation consistent across a page
    break, which matters for Python.
    """
    lead: int = 0
    qlead: int = 0   # the same, measured from the column the page's answer options start at


def _indent(r: str) -> int:
    return len(r) - len(r.lstrip())


def _clean_lines(text: str) -> list[Line]:
    raw = [r.replace("�", "•").rstrip() for r in text.splitlines()]
    raw = [r for r in raw if r.strip()]
    # The text margin is the indentation most long (prose) lines share.
    leads = Counter(_indent(r) for r in raw if len(r.strip()) > 60)
    margin = leads.most_common(1)[0][0] if leads else 0
    # Code inside a question lines up with the answer options ("a. ...").
    option_leads = Counter(_indent(r) for r in raw if OPTION.match(r.strip()))
    option_col = option_leads.most_common(1)[0][0] if option_leads else margin + 4
    lines = []
    for r in raw:
        content = re.sub(r" {2,}", " ", r.strip())
        if any(p.match(content) for p in FOOTER_PATTERNS):
            continue
        line = Line(content)
        line.lead = _indent(r) - margin
        line.qlead = _indent(r) - option_col
        lines.append(line)
    return lines


def _block(lines: list[Line], attr: str = "lead") -> str:
    """Lines of a code sample, with their indentation relative to each other."""
    base = min(getattr(l, attr) for l in lines)
    return "\n".join(" " * (getattr(l, attr) - base) + l for l in lines)




def _outline(reader: PdfReader):
    chapters = []

    def walk(items, depth=0, chapter=None):
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1, chapters[-1] if chapters else None)
                continue
            page = reader.get_destination_page_number(item)
            if depth == 0:
                m = re.match(r"Chapter (\d+) (.+)", item.title)
                if m:
                    chapters.append({"number": int(m.group(1)), "title": m.group(2), "page": page, "sections": []})
                elif item.title == "Answer Key":
                    chapters.append({"number": None, "title": "Answer Key", "page": page, "sections": []})
                elif item.title == "Index":
                    chapters.append({"number": None, "title": "Index", "page": page, "sections": []})
            elif depth == 1 and chapter is not None:
                m = re.match(r"(\d+\.\d+) (.+)", item.title)
                if m:
                    chapter["sections"].append({"number": m.group(1), "title": m.group(2), "page": page})

    walk(reader.outline)
    return chapters


def _pages_text(reader: PdfReader, start: int, end: int) -> list[Line]:
    lines = []
    for i in range(start, end):
        # Layout mode keeps horizontal positions, so code indentation survives.
        lines.extend(_clean_lines(reader.pages[i].extract_text(extraction_mode="layout") or ""))
    return lines


def _split_sections(lines: list[str], sections: list[dict]) -> dict[str, list[str]]:
    """Cut a chapter's lines at each section heading.

    The chapter outline on the first page lists every heading too, so a heading
    seen again replaces what was collected under it before.
    """
    heads = {f"{s['number']} {s['title']}": s["number"] for s in sections}
    out: dict[str, list[str]] = {}
    current = None
    for line in lines:
        if line in heads:
            current = heads[line]
            out[current] = []
            continue
        if current:
            out[current].append(line)
    return out


def _looks_like_code(line: str) -> bool:
    """Options often wrap onto code lines; headings and prose after a question start
    with a capital letter and contain no code punctuation."""
    return line[:1].islower() or line[:1].isdigit() or line[:1] in "\"'([{#_<>-.:" or any(c in line for c in "=()[]{}")


def _extract_questions(lines: list[str]) -> tuple[list[dict], list[str]]:
    """Pull "Concepts in practice" questions out of a section.

    Returns the questions and the remaining lines (the readable lesson text).
    """
    questions, keep = [], []
    i = 0
    while i < len(lines):
        if lines[i] == "CHECKPOINT":
            i += 2  # the marker and the animation's title; its link line is handled by the caller
            continue
        if lines[i].startswith("Access multimedia content"):
            i += 1
            continue
        if lines[i] != "CONCEPTS IN PRACTICE":
            keep.append(lines[i])
            i += 1
            continue
        i += 2  # skip marker and block title
        current = None
        while i < len(lines):
            line = lines[i]
            if line in BLOCK_MARKERS:
                break
            q = QUESTION.match(line)
            o = OPTION.match(line)
            if q and (current is None or current["options"]):
                current = {"number": int(q.group(1)), "prompt": [q.group(2)], "options": []}
                questions.append(current)
            elif o and current is not None and ord(o.group(1)) - ord("a") == len(current["options"]):
                current["options"].append([o.group(2)])
            elif current is not None and not current["options"]:
                current["prompt"].append(line)
            elif current is not None and current["options"] and _looks_like_code(line) and len(current["options"][-1]) < 4:
                current["options"][-1].append(line)
            else:
                break
            i += 1
    for q in questions:
        first, rest = q["prompt"][0], q["prompt"][1:]
        q["prompt"] = (first + ("\n" + _block(rest, "qlead") if rest else "")).strip()
        q["options"] = [(o[0] + ("\n" + _block(o[1:], "qlead") if len(o) > 1 else "")).strip() for o in q["options"]]
    return questions, keep


def _answer_key(lines: list[str], numbers: set[str]) -> dict[str, dict[int, tuple[str, str]]]:
    key: dict[str, dict[int, tuple[str, str]]] = {}
    current_section, current = None, None
    for line in lines:
        m = re.match(r"^(\d+\.\d+) .+$", line)
        if m and m.group(1) in numbers:
            current_section = m.group(1)
            key[current_section] = {}
            current = None
            continue
        if current_section is None:
            continue
        a = re.match(r"^(\d+)\s?\.\s+([a-e])\.\s*(.*)$", line)
        if a:
            current = [a.group(2), a.group(3)]
            key[current_section][int(a.group(1))] = current
        elif current is not None and not re.match(r"^Chapter \d+$", line):
            current[1] += " " + line
    return {s: {n: (v[0], v[1].strip()) for n, v in items.items()} for s, items in key.items()}


def _to_paragraphs(lines: list[Line]) -> str:
    """Re-flow PDF lines: wrapped prose lines are joined; code samples are kept
    line by line with their indentation. A code block starts at a line that looks
    like Python and continues while lines look like code or are indented deeper
    than where the block started."""
    out: list[str] = []
    code: list[Line] = []
    prose_open = False

    def flush_code():
        nonlocal prose_open
        if code:
            out.append("\n" + _block(code) + "\n")
            code.clear()
            prose_open = False

    for line in lines:
        if looks_like_python(line) or (code and line.lead >= code[0].lead + 2):
            code.append(line)
            continue
        flush_code()
        last = out[-1] if out and prose_open else ""
        wrapped = last and not last.endswith((".", ":", "?", "!")) and (
            (len(last) > 70 and line[:1].islower()) or len(last) > 85)
        if wrapped:
            out[-1] += " " + line
        else:
            out.append(str(line))
            prose_open = True
    flush_code()
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def run(conn: sqlite3.Connection, raw_dir: Path, log=print) -> dict:
    pdf = raw_dir / "openstax" / "intro-python.pdf"
    reader = PdfReader(str(pdf))
    outline = _outline(reader)
    chapters = [c for c in outline if c["number"]]
    answer_start = next(c["page"] for c in outline if c["title"] == "Answer Key")
    index_start = next(c["page"] for c in outline if c["title"] == "Index")

    log("OpenStax: reading answer key")
    all_numbers = {s["number"] for c in chapters for s in c["sections"]}
    answers = _answer_key(_pages_text(reader, answer_start, index_start), all_numbers)

    stats = {"lessons": 0, "questions": 0, "skipped": 0}
    with transaction(conn):
        course_ids = {}
        for code, title, chapter_range, description in COURSES:
            cur = conn.execute(
                """INSERT INTO courses (code, title, subject, description, source, pass_mark, attribution)
                   VALUES (?, ?, 'Computer Science', ?, 'openstax', 60, ?)""",
                (code, title, description, ATTRIBUTION),
            )
            course_ids[code] = cur.lastrowid
            module_pos = 0
            for ch in chapters:
                if ch["number"] not in chapter_range:
                    continue
                log(f"OpenStax: chapter {ch['number']} {ch['title']}")
                end = next((c["page"] for c in outline if c["page"] > ch["page"]), answer_start)
                sections = _split_sections(_pages_text(reader, ch["page"], end), ch["sections"])
                module_pos += 1
                cur = conn.execute(
                    """INSERT INTO modules (course_id, position, title, kind, external_id)
                       VALUES (?, ?, ?, 'chapter', ?)""",
                    (course_ids[code], module_pos, f"{ch['number']}. {ch['title']}", f"ch{ch['number']}"),
                )
                module_id = cur.lastrowid
                lesson_pos = 0
                for sec in ch["sections"]:
                    lines = sections.get(sec["number"])
                    if not lines or sec["title"].lower() == "chapter summary":
                        continue
                    questions, body_lines = _extract_questions(lines)
                    video = next((m.group(1) for l in body_lines for m in [VIDEO.search(l)] if m), None)
                    body_lines = [l for l in body_lines if not VIDEO.search(l) and l != "CHECKPOINT"]
                    lesson_pos += 1
                    conn.execute(
                        """INSERT INTO lessons (module_id, position, title, body, video_url, source_page)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (module_id, lesson_pos, f"{sec['number']} {sec['title']}", _to_paragraphs(body_lines),
                         video, sec["page"] + 1),
                    )
                    stats["lessons"] += 1
                    key = answers.get(sec["number"], {})
                    for q in questions:
                        letter_expl = key.get(q["number"])
                        n_opts = len(q["options"])
                        if (letter_expl is None or n_opts < 2 or len(q["prompt"]) > 700
                                or any(not o or len(o) > 300 for o in q["options"])
                                or ord(letter_expl[0]) - ord("a") >= n_opts):
                            stats["skipped"] += 1
                            continue
                        correct = ord(letter_expl[0]) - ord("a")
                        cur = conn.execute(
                            """INSERT INTO questions (module_id, source, external_id, prompt, explanation)
                               VALUES (?, 'openstax', ?, ?, ?)""",
                            (module_id, f"{sec['number']}-{q['number']}", q["prompt"], letter_expl[1] or None),
                        )
                        conn.executemany(
                            """INSERT INTO question_options (question_id, position, text, is_correct)
                               VALUES (?, ?, ?, ?)""",
                            [(cur.lastrowid, i + 1, text, int(i == correct)) for i, text in enumerate(q["options"])],
                        )
                        stats["questions"] += 1
        conn.execute(
            "INSERT INTO prerequisites (course_id, requires_id) VALUES (?, ?)",
            (course_ids["PY-102"], course_ids["PY-101"]),
        )
    log(f"OpenStax: {stats['lessons']} lessons, {stats['questions']} questions ({stats['skipped']} skipped as unparseable)")
    return stats
