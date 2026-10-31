"""Backup consistente, inclusive com WAL ativo; nÃ£o importa grafo ou provedores."""
from contextlib import closing
import argparse
from pathlib import Path
import sqlite3


def backup_database(source: Path, destination: Path) -> None:
    source = source.resolve(strict=True)
    destination = destination.absolute()
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Reserva exclusiva: nunca sobrescrever backup ou banco existente.
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=10)) as original:
            with closing(sqlite3.connect(destination)) as copy:
                original.backup(copy)
                result = copy.execute("PRAGMA integrity_check").fetchall()
                if result != [("ok",)]:
                    raise RuntimeError("Backup nÃ£o passou na verificaÃ§Ã£o de integridade")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    backup_database(args.source, args.destination)
    print("Backup concluÃ­do e integridade verificada.")
