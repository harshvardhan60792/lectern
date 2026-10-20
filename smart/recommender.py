"""Recommendations.

Courses: two signals, blended.
  - Content similarity: each course becomes a TF-IDF vector of its title,
    description, module titles and lesson text. Cosine similarity says how close
    two courses are in topic (1 = same words, 0 = nothing in common).
  - Collaborative filtering: "students who took X also took Y". A student ×
    course matrix of enrollments gives a course-to-course similarity.
  Final score = 0.6 × content + 0.4 × co-enrollment, weighted by how well the
  student did in the course that triggered it. Courses already taken, closed,
  or with unmet prerequisites are removed. Each result says why.

Materials (OULAD): for each learning material, compare the pass rate of
students who used it with the course's overall pass rate ("lift"). Materials
with high lift that a student skipped are worth pointing out.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

OPEN_SOURCES = ("openstax", "sciq", "local")
CONTENT_WEIGHT, CF_WEIGHT = 0.6, 0.4


def _course_docs(conn) -> tuple[list[int], list[str], dict[int, dict]]:
    courses = {r["id"]: dict(r) for r in conn.execute(
        "SELECT id, code, title, subject, description, source, archived FROM courses")}
    modules: dict[int, list[str]] = {}
    for r in conn.execute("SELECT course_id, title FROM modules ORDER BY position"):
        modules.setdefault(r["course_id"], []).append(r["title"])
    lessons: dict[int, list[str]] = {}
    for r in conn.execute(
            "SELECT m.course_id, substr(l.body, 1, 1500) AS body FROM lessons l JOIN modules m ON m.id = l.module_id"):
        lessons.setdefault(r["course_id"], []).append(r["body"])
    ids = sorted(courses)
    docs = [" ".join([courses[i]["title"], courses[i]["subject"], courses[i]["description"],
                      " ".join(modules.get(i, [])[:60]), " ".join(lessons.get(i, []))]) for i in ids]
    return ids, docs, courses


def _co_enrollment(conn, ids: list[int]) -> np.ndarray:
    index = {cid: i for i, cid in enumerate(ids)}
    pairs = conn.execute("SELECT student_id, course_id FROM enrollments").fetchall()
    if not pairs:
        return np.zeros((len(ids), len(ids)))
    students = {s: i for i, s in enumerate(sorted({p[0] for p in pairs}))}
    matrix = np.zeros((len(students), len(ids)), dtype=np.float32)
    for s, c in pairs:
        matrix[students[s], index[c]] = 1.0
    sim = cosine_similarity(matrix.T)
    np.fill_diagonal(sim, 0.0)
    return sim


def recommend_courses(conn, student_id: int, n: int = 3) -> list[dict]:
    ids, docs, courses = _course_docs(conn)
    index = {cid: i for i, cid in enumerate(ids)}
    content = cosine_similarity(TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(docs))
    np.fill_diagonal(content, 0.0)
    co = _co_enrollment(conn, ids)

    history = conn.execute(
        """SELECT e.course_id, e.status,
                  (SELECT AVG(mp.best_score) FROM module_progress mp JOIN modules m ON m.id = mp.module_id
                   WHERE m.course_id = e.course_id AND mp.student_id = e.student_id) AS score
           FROM enrollments e WHERE e.student_id = ?""",
        (student_id,),
    ).fetchall()
    taken = {h["course_id"] for h in history if h["status"] in ("active", "completed")}
    completed = {h["course_id"] for h in history if h["status"] == "completed"}

    def weight(h) -> float:
        if h["status"] == "completed":
            return 0.5 + 0.5 * ((h["score"] or 70) / 100)
        if h["status"] == "active":
            return 0.7
        return 0.25

    prereqs: dict[int, set[int]] = {}
    for r in conn.execute("SELECT course_id, requires_id FROM prerequisites"):
        prereqs.setdefault(r["course_id"], set()).add(r["requires_id"])

    candidates = [cid for cid in ids
                  if courses[cid]["source"] in OPEN_SOURCES and not courses[cid]["archived"] and cid not in taken]
    results = []
    for cid in candidates:
        missing = prereqs.get(cid, set()) - completed
        best_content = (0.0, None)
        best_co = (0.0, None)
        for h in history:
            w = weight(h)
            c_score = w * content[index[h["course_id"]], index[cid]]
            k_score = w * co[index[h["course_id"]], index[cid]]
            if c_score > best_content[0]:
                best_content = (c_score, h["course_id"])
            if k_score > best_co[0]:
                best_co = (k_score, h["course_id"])
        score = CONTENT_WEIGHT * best_content[0] + CF_WEIGHT * best_co[0]
        if not history:
            reason = "A good place to start." if not prereqs.get(cid) else None
            score = 0.01 if reason else 0.0
        elif CF_WEIGHT * best_co[0] > CONTENT_WEIGHT * best_content[0] and best_co[1]:
            reason = f"Students who took {courses[best_co[1]]['title']} often take this next."
        elif best_content[1]:
            reason = f"Covers related ground to {courses[best_content[1]]['title']}."
        else:
            reason = None
        if missing:
            needs = ", ".join(courses[m]["title"] for m in missing)
            reason = f"Unlocks after {needs}." + (f" {reason}" if reason else "")
            score *= 0.5
        if reason:
            results.append({"course_id": cid, "code": courses[cid]["code"], "title": courses[cid]["title"],
                            "score": round(float(score), 3), "reason": reason, "locked": bool(missing)})
    results.sort(key=lambda r: (r["locked"], -r["score"]))
    return results[:n]


def material_insights(conn, course_id: int, min_users: int = 30, top: int = 15) -> dict:
    """Which learning materials go with passing? (OULAD courses)"""
    base = conn.execute(
        """SELECT COUNT(*) AS n, SUM(status = 'completed') AS passed FROM enrollments
           WHERE course_id = ? AND status <> 'active'""",
        (course_id,),
    ).fetchone()
    if not base["n"]:
        return {"base_rate": None, "materials": []}
    base_rate = base["passed"] / base["n"]
    rows = conn.execute(
        """SELECT m.id, m.external_id, m.activity_type, COUNT(*) AS users,
                  AVG(e.status = 'completed') AS pass_rate, AVG(mu.clicks) AS avg_clicks
           FROM material_use mu
           JOIN materials m   ON m.id = mu.material_id
           JOIN enrollments e ON e.student_id = mu.student_id AND e.course_id = m.course_id
           WHERE m.course_id = ? AND e.status <> 'active'
           GROUP BY m.id HAVING COUNT(*) >= ?""",
        (course_id, min_users),
    ).fetchall()
    materials = [{
        "material_id": r["id"], "label": f"{r['activity_type']} #{r['external_id']}", "type": r["activity_type"],
        "users": r["users"], "share": round(r["users"] / base["n"], 3), "pass_rate": round(r["pass_rate"], 3),
        "lift": round(r["pass_rate"] / base_rate, 2) if base_rate else None, "avg_clicks": round(r["avg_clicks"], 1),
    } for r in rows]
    materials.sort(key=lambda m: -(m["lift"] or 0))
    return {"base_rate": round(base_rate, 3), "materials": materials[:top], "students": base["n"]}
