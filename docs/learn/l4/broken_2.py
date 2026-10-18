"""L4, script 2: search students whose ID contains 1139. It crashes. Read the error and fix it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from db import read_only
from services import students

conn = read_only()
rows, total = students.serch(conn, "1139")
print(f"{total} students found")
for r in rows[:5]:
    print(r["display_name"], r["region"])
