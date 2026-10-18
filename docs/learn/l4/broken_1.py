"""L4, script 1: list ten students with their email. It crashes. Read the error and fix it."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # lets this file import the project's code

from db import read_only

conn = read_only()
rows = conn.execute("SELECT display_name, emial FROM students WHERE source = 'local' OR email IS NULL LIMIT 10")
for row in rows:
    print(row["display_name"], row["email"])
