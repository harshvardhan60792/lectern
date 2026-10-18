"""L4, script 3: print the average assessment score in course DDD-2013J. It crashes. Read the error and fix it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from db import read_only

conn = read_only()
average = conn.execute(
    """SELECT AVG(mp.best_score)
       FROM module_progress mp
       JOIN modules m ON m.id = mp.module_id
       JOIN courses c ON c.id = m.course_id
       WHERE c.code = ?""",
    ("DDD-2013J",),
).fetchone()[0]
print("Average score: " + round(average, 1) + "%")
