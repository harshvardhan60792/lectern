"""L4: three small scripts that crash on purpose. Read each error and fix it.

Run one at a time from the project folder:
    python docs\\learn\\broken.py 1
    python docs\\learn\\broken.py 2
    python docs\\learn\\broken.py 3
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets this file import the project's code

from db import read_only  # noqa: E402
from services import students  # noqa: E402


def script_1(conn):
    """List ten students with their email."""
    rows = conn.execute("SELECT display_name, emial FROM students WHERE source = 'local' OR email IS NULL LIMIT 10")
    for row in rows:
        print(row["display_name"], row["email"])


def script_2(conn):
    """Search students whose ID contains 1139."""
    rows, total = students.serch(conn, "1139")
    print(f"{total} students found")
    for r in rows[:5]:
        print(r["display_name"], r["region"])


def script_3(conn):
    """Print the average assessment score in course DDD-2013J."""
    average = conn.execute(
        """SELECT AVG(mp.best_score)
           FROM module_progress mp
           JOIN modules m ON m.id = mp.module_id
           JOIN courses c ON c.id = m.course_id
           WHERE c.code = ?""",
        ("DDD-2013J",),
    ).fetchone()[0]
    print("Average score: " + round(average, 1) + "%")


if __name__ == "__main__":
    scripts = {"1": script_1, "2": script_2, "3": script_3}
    choice = sys.argv[1] if len(sys.argv) > 1 else ""
    if choice not in scripts:
        sys.exit("Say which script to run: python docs\\learn\\broken.py 1   (or 2, or 3)")
    scripts[choice](read_only())
