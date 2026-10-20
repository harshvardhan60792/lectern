"""Database commands.

    python -m db setup      build data/lectern.db from the downloaded datasets (about 5 minutes)
    python -m db stats      row counts per table
    python -m db reset      delete the database file
"""
import sys
import time

from app.config import ROOT, config
from db import connect, init_schema
from db.importers import assistments, openstax, oulad, sciq


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def reset() -> None:
    for suffix in ("", "-wal", "-shm"):
        path = config.db_path.with_name(config.db_path.name + suffix)
        path.unlink(missing_ok=True)
    log(f"Removed {config.db_path}")


def setup() -> None:
    missing = [p for p in ("oulad/studentVle.csv", "assistments/skill_builder_data.csv", "openstax/intro-python.pdf")
               if not (config.raw_dir / p).exists()]
    if missing or not list((config.raw_dir / "sciq").glob("SciQ*")):
        log("Datasets missing in data/raw. See docs/database.md (Part 2) for download links.")
        sys.exit(1)
    if config.db_path.exists():
        log(f"{config.db_path} already exists. Run `python -m db reset` first.")
        sys.exit(1)

    started = time.time()
    conn = connect()
    init_schema(conn)
    openstax.run(conn, config.raw_dir, log)
    sciq.run(conn, config.raw_dir, log)
    assistments.run(conn, config.raw_dir, log)
    oulad.run(conn, config.raw_dir, ROOT / "data" / "stage", log)

    log("Training the at-risk model")
    from smart import risk
    result = risk.train(conn)
    log(f"  accuracy {result['accuracy']:.3f}, precision {result['precision']:.3f}, "
        f"recall {result['recall']:.3f}, ROC AUC {result['roc_auc']:.3f}")

    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('built_at', datetime('now'))")
    conn.execute("ANALYZE")
    conn.close()
    log(f"Done in {time.time() - started:.0f}s")
    stats()


def stats() -> None:
    conn = connect()
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    for t in tables:
        n = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]  # names come from sqlite_master
        print(f"  {t:<18} {n:>12,}")


COMMANDS = {"setup": setup, "stats": stats, "reset": reset}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[cmd]()
