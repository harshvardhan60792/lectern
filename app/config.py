"""Settings, read once from .env (if present) with sensible defaults."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else ROOT / value


@dataclass(frozen=True)
class Config:
    db_path: Path
    raw_dir: Path
    models_dir: Path
    exports_dir: Path


def load() -> Config:
    return Config(
        db_path=_path("LECTERN_DB", "data/lectern.db"),
        raw_dir=_path("LECTERN_RAW", "data/raw"),
        models_dir=ROOT / "data" / "models",
        exports_dir=ROOT / "exports",
    )


config = load()
