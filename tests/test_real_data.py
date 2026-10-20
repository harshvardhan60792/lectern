"""Checks against the real database built by `python -m db setup`.
Skipped when it hasn't been built. Nothing here writes to it."""
import pytest

from app.config import config
from db import connect, read_only
from services import reports
from smart import ask_data, risk

pytestmark = pytest.mark.skipif(not config.db_path.exists(), reason="real database not built")


@pytest.fixture(scope="module")
def real():
    conn, reader = connect(), read_only()
    yield conn, reader
    conn.close()
    reader.close()


def test_datasets_loaded(real):
    conn, _ = real
    counts = dict(conn.execute("SELECT source, COUNT(*) FROM courses GROUP BY source").fetchall())
    assert counts == {"oulad": 22, "assistments": 1, "openstax": 2, "sciq": 6}
    assert conn.execute("SELECT COUNT(*) FROM enrollments e JOIN courses c ON c.id = e.course_id "
                        "WHERE c.source = 'oulad'").fetchone()[0] == 32593


def test_every_example_question_answers(real):
    conn, reader = real
    for question in ask_data.EXAMPLES:
        result = ask_data.ask(question, conn, reader)
        assert result["rows"], question


def test_model_beats_chance_on_unseen_cohort(real):
    run = risk.latest_run(real[0])
    assert run["roc_auc"] > 0.75
    assert "2014" in run["details"]["split"]


def test_predictions_are_ranked_and_explained(real):
    conn, _ = real
    course = conn.execute("SELECT id FROM courses WHERE code = 'DDD-2014J'").fetchone()[0]
    preds = risk.predict(conn, course, 60)
    assert preds == sorted(preds, key=lambda p: -p["risk"])
    assert all(p["reasons"] for p in preds[:20])
    check = risk.check_against_outcomes(preds)
    assert check["precision"] > 0.6


def test_openstax_questions_keep_code_indentation(real):
    prompt = real[0].execute("SELECT prompt FROM questions WHERE prompt LIKE '%x = 256, y = 513%'").fetchone()[0]
    assert "\n  # Body 1\nelif x < y:" in prompt


def test_question_health_on_assistments(real):
    conn, _ = real
    course = conn.execute("SELECT id FROM courses WHERE code = 'ASSIST-0910'").fetchone()[0]
    health = reports.question_health(conn, course)
    assert health["counts"]["Healthy"] > 1000
