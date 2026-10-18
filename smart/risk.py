"""At-risk prediction: which students are unlikely to finish a course?

Model: logistic regression (scikit-learn) on seven behaviour features measured
"as of" a given day of the course. Label: the enrollment ended as Withdrawn or
Fail. Trained on real OULAD outcomes.

Honest evaluation: the model is trained on the 2013 presentations and tested on
the 2014 ones, so it is always judged on a later cohort it has never seen, the
way it would be used in practice.

Each prediction comes with reasons: the features that pushed this student's
risk up the most (weight × how unusual their value is).
"""
import json
import math

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.config import config
from db import transaction

FEATURES = [
    "days_since_active",   # days since the last study activity
    "recent_clicks",       # log of activity in the last 14 days
    "active_days",         # number of days with any activity
    "submission_rate",     # assessments handed in / assessments due so far
    "avg_score",           # average score of handed-in assessments
    "late_registration",   # days registered after the start (negative = early)
    "prev_attempts",       # times this course was attempted before
]
# Which way is "worse" for each feature; a reason is only given when the
# student's value really is on the worse side of average.
WORSE_WHEN = {
    "days_since_active": +1, "recent_clicks": -1, "active_days": -1, "submission_rate": -1,
    "avg_score": -1, "late_registration": +1, "prev_attempts": +1,
}
SNAPSHOT_DAYS = (30, 60, 90, 120)
MODEL_FILE = "risk.joblib"
THRESHOLD = 0.5


def _features(conn, day: int, course_ids: list[int] | None = None, include_finished: bool = True) -> list[dict]:
    """One feature row per enrollment that is still running on `day` of its course."""
    course_filter = ""
    params: dict = {"d": day}
    if course_ids:
        course_filter = f"AND c.id IN ({', '.join(str(int(c)) for c in course_ids)})"
    rows = conn.execute(
        f"""
        WITH e AS (
            SELECT e.id AS eid, e.student_id, e.course_id, e.status, e.final_result, e.prev_attempts,
                   COALESCE(c.starts_on, e.enrolled_on) AS start,
                   e.enrolled_on, e.ended_on, c.source
            FROM enrollments e JOIN courses c ON c.id = e.course_id
            WHERE c.source <> 'assistments' {course_filter}
              AND COALESCE(c.starts_on, e.enrolled_on) IS NOT NULL
        ),
        live AS (
            SELECT *, date(start, printf('%+d days', :d)) AS cutoff FROM e
            WHERE NOT (status = 'withdrawn' AND ended_on IS NOT NULL
                       AND ended_on <= date(start, printf('%+d days', :d)))
              AND (enrolled_on IS NULL OR enrolled_on <= date(start, printf('%+d days', :d)))
        ),
        act AS (
            SELECT l.eid,
                   SUM(a.clicks) AS clicks,
                   COUNT(*) AS days,
                   MAX(a.day) AS last_day,
                   SUM(CASE WHEN a.day > date(l.cutoff, '-14 days') THEN a.clicks ELSE 0 END) AS recent
            FROM live l
            JOIN activity_days a ON a.student_id = l.student_id AND a.course_id = l.course_id
            WHERE a.day <= l.cutoff
            GROUP BY l.eid
        ),
        due AS (
            SELECT l.eid, COUNT(m.id) AS n_due
            FROM live l
            JOIN modules m ON m.course_id = l.course_id
            WHERE m.kind = 'assessment' AND m.title <> 'Final exam' AND m.due_day <= :d
            GROUP BY l.eid
        ),
        sub AS (
            SELECT l.eid, COUNT(*) AS n_sub, AVG(mp.best_score) AS avg_score
            FROM live l
            JOIN modules m ON m.course_id = l.course_id
            JOIN module_progress mp ON mp.module_id = m.id AND mp.student_id = l.student_id
            WHERE mp.completed_on <= l.cutoff AND m.title <> 'Final exam'
            GROUP BY l.eid
        )
        SELECT l.eid, l.student_id, l.course_id, l.status, l.final_result, l.prev_attempts, l.source,
               julianday(l.cutoff) - julianday(COALESCE(act.last_day, l.start)) AS days_since_active,
               COALESCE(act.recent, 0) AS recent, COALESCE(act.clicks, 0) AS clicks,
               COALESCE(act.days, 0) AS active_days,
               COALESCE(due.n_due, 0) AS n_due, COALESCE(sub.n_sub, 0) AS n_sub, sub.avg_score,
               COALESCE(julianday(l.enrolled_on) - julianday(l.start), 0) AS late_registration,
               substr((SELECT code FROM courses WHERE id = l.course_id), -5, 4) AS year
        FROM live l
        LEFT JOIN act ON act.eid = l.eid
        LEFT JOIN due ON due.eid = l.eid
        LEFT JOIN sub ON sub.eid = l.eid
        """,
        params,
    ).fetchall()

    out = []
    for r in rows:
        if not include_finished and r["status"] != "active":
            continue
        n_due, n_sub = r["n_due"], r["n_sub"]
        out.append({
            "enrollment_id": r["eid"], "student_id": r["student_id"], "course_id": r["course_id"],
            "status": r["status"], "final_result": r["final_result"], "source": r["source"],
            "year": r["year"], "day": day,
            "n_due": n_due, "n_sub": n_sub, "raw_clicks": r["clicks"], "raw_recent": r["recent"],
            "raw_avg_score": r["avg_score"],
            "days_since_active": max(0.0, r["days_since_active"]),
            "recent_clicks": math.log1p(r["recent"]),
            "active_days": r["active_days"],
            "submission_rate": 1.0 if n_due == 0 else min(1.0, n_sub / n_due),
            "avg_score": r["avg_score"] if r["avg_score"] is not None else 0.0,
            "late_registration": r["late_registration"],
            "prev_attempts": r["prev_attempts"],
        })
    return out


def _matrix(rows: list[dict]) -> np.ndarray:
    return np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)


def _label(row: dict) -> int:
    return int(row["status"] in ("withdrawn", "failed"))


def train(conn) -> dict:
    """Train on 2013 OULAD presentations, test on 2014, save the model and log the run."""
    train_rows, test_rows = [], []
    for day in SNAPSHOT_DAYS:
        for r in _features(conn, day):
            if r["source"] != "oulad" or r["status"] == "active":
                continue
            (train_rows if r["year"] == "2013" else test_rows).append(r)

    X_train, y_train = _matrix(train_rows), np.array([_label(r) for r in train_rows])
    X_test, y_test = _matrix(test_rows), np.array([_label(r) for r in test_rows])

    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= THRESHOLD).astype(int)
    by_day = {}
    for day in SNAPSHOT_DAYS:
        mask = np.array([r["day"] == day for r in test_rows])
        if mask.any():
            by_day[day] = {
                "n": int(mask.sum()),
                "accuracy": round(float(accuracy_score(y_test[mask], pred[mask])), 3),
                "recall": round(float(recall_score(y_test[mask], pred[mask])), 3),
                "precision": round(float(precision_score(y_test[mask], pred[mask])), 3),
            }
    coefs = model[-1].coef_[0]
    result = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision": float(precision_score(y_test, pred)),
        "recall": float(recall_score(y_test, pred)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
        "n_train": len(train_rows),
        "n_test": len(test_rows),
        "details": {
            "split": "train = 2013 presentations, test = 2014 presentations",
            "snapshots": list(SNAPSHOT_DAYS),
            "base_rate_test": round(float(y_test.mean()), 3),
            "by_day": by_day,
            "weights": {f: round(float(c), 3) for f, c in zip(FEATURES, coefs)},
        },
    }

    config.models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES}, config.models_dir / MODEL_FILE)
    global _cached
    _cached = None
    with transaction(conn):
        conn.execute(
            """INSERT INTO model_runs (model, n_train, n_test, accuracy, precision, recall, roc_auc, details)
               VALUES ('at-risk logistic regression', ?, ?, ?, ?, ?, ?, ?)""",
            (result["n_train"], result["n_test"], result["accuracy"], result["precision"],
             result["recall"], result["roc_auc"], json.dumps(result["details"])),
        )
    return result


def latest_run(conn) -> dict | None:
    row = conn.execute("SELECT * FROM model_runs ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    run = dict(row)
    run["details"] = json.loads(run["details"] or "{}")
    return run


_cached = None


def _load():
    global _cached
    if _cached is None:
        path = config.models_dir / MODEL_FILE
        if not path.exists():
            return None
        _cached = joblib.load(path)
    return _cached


def _reasons(row: dict, contributions: dict, z: dict) -> list[tuple[str, str]]:
    text = {
        "days_since_active": lambda: f"No activity for {row['days_since_active']:.0f} days",
        "recent_clicks": lambda: f"Little activity in the last two weeks ({row['raw_recent']} clicks)",
        "active_days": lambda: f"Studied on only {row['active_days']} days so far",
        "submission_rate": lambda: f"Handed in {row['n_sub']} of {row['n_due']} assessments due",
        # With nothing handed in, the submission reason already says it all.
        "avg_score": lambda: (f"Average assessment score {row['raw_avg_score']:.0f}%"
                              if row["raw_avg_score"] is not None else None),
        "late_registration": lambda: f"Registered {row['late_registration']:.0f} days after the start",
        "prev_attempts": lambda: f"Retaking the course ({row['prev_attempts']} earlier attempts)",
    }
    ranked = sorted(contributions.items(), key=lambda kv: -kv[1])
    reasons = [(f, text[f]()) for f, c in ranked if c > 0.3 and z[f] * WORSE_WHEN[f] > 0]
    return [(f, r) for f, r in reasons if r][:3]


def nudge(prediction: dict) -> str:
    """A short, friendly message an instructor could send, built from the top reason."""
    row = prediction["_row"]
    key = prediction["reason_keys"][0] if prediction["reason_keys"] else None
    opening = {
        "days_since_active": f"I noticed you haven't been on the course for {row['days_since_active']:.0f} days.",
        "recent_clicks": "I noticed things have been quieter for you on the course over the last two weeks.",
        "active_days": "I noticed you've only managed a few study sessions so far.",
        "submission_rate": f"I see {row['n_sub']} of the {row['n_due']} assessments due so far have been handed in.",
        "avg_score": "I noticed the last assessments were harder going.",
        "late_registration": "You joined the course a little after it started, so there's catching up to do.",
        "prev_attempts": "I know this isn't your first go at this course.",
    }.get(key, "I wanted to check in on how the course is going.")
    return f"Hi, {opening} Is anything getting in the way? Reply and we can plan the next two weeks together."


def predict(conn, course_id: int, day: int) -> list[dict]:
    """Risk for every student still in the course on `day`, highest first.

    For OULAD courses the real outcome is attached, so the prediction can be
    checked against what actually happened.
    """
    bundle = _load()
    if bundle is None:
        raise RuntimeError("The at-risk model has not been trained yet. Run `python -m db setup`.")
    model = bundle["model"]
    rows = _features(conn, day, [course_id])
    if not rows:
        return []
    X = _matrix(rows)
    proba = model.predict_proba(X)[:, 1]
    scaler, lr = model[0], model[-1]
    z = scaler.transform(X)
    contrib = z * lr.coef_[0]
    names = dict(conn.execute(
        f"SELECT id, display_name FROM students WHERE id IN ({', '.join(str(r['student_id']) for r in rows)})"
    ).fetchall())
    out = []
    for r, p, c, zr in zip(rows, proba, contrib, z):
        reasons = _reasons(r, dict(zip(FEATURES, c)), dict(zip(FEATURES, zr)))
        out.append({
            "student_id": r["student_id"],
            "name": names.get(r["student_id"], str(r["student_id"])),
            "risk": float(p),
            "level": "high" if p >= 0.75 else "medium" if p >= THRESHOLD else "low",
            "reasons": [text for _, text in reasons],
            "reason_keys": [key for key, _ in reasons],
            "outcome": r["final_result"],
            "days_since_active": r["days_since_active"],
            "submitted": f"{r['n_sub']}/{r['n_due']}",
            "_row": r,
        })
    out.sort(key=lambda x: -x["risk"])
    return out


def check_against_outcomes(predictions: list[dict]) -> dict | None:
    """For historical courses: how many flagged students really did not finish?"""
    known = [p for p in predictions if p["outcome"]]
    if not known:
        return None
    flagged = [p for p in known if p["risk"] >= THRESHOLD]
    did_not_finish = [p for p in known if p["outcome"] in ("Withdrawn", "Fail")]
    caught = [p for p in flagged if p["outcome"] in ("Withdrawn", "Fail")]
    return {
        "students": len(known),
        "flagged": len(flagged),
        "flagged_correct": len(caught),
        "did_not_finish": len(did_not_finish),
        "precision": len(caught) / len(flagged) if flagged else None,
        "recall": len(caught) / len(did_not_finish) if did_not_finish else None,
    }
