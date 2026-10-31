"""Caminho único do SQLite, independente do diretório de execução."""
import os
from pathlib import Path


def database_path() -> Path:
    configured = os.environ.get("SUPERVISOR_DB_PATH")
    path = Path(configured).expanduser() if configured else Path(__file__).parent / "checkpoints.db"
    if not path.is_absolute():
        raise ValueError("SUPERVISOR_DB_PATH deve ser um caminho absoluto")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
