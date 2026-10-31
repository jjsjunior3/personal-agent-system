from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backup_database import backup_database
from database import database_path
from memory.decision_log import init_decision_log, log_decision, count_consecutive_approvals
from memory.rules_store import init_rules_store, set_auto_approve, is_auto_approved


class PersistenceTests(unittest.TestCase):
    def test_backup_with_open_wal_and_reopen(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            source = Path(folder) / "nested" / "state.db"
            target = Path(folder) / "backup.db"
            with patch.dict(os.environ, {"SUPERVISOR_DB_PATH": str(source)}):
                init_decision_log()
                init_rules_store()
                log_decision("ficticio", True)
                set_auto_approve("ficticio", True)
                with closing(sqlite3.connect(source)) as writer:
                    writer.execute("PRAGMA wal_autocheckpoint=0")
                    writer.execute("CREATE TABLE fake_checkpoint (state TEXT)")
                    writer.execute("INSERT INTO fake_checkpoint VALUES ('aguardando aprovacao')")
                    writer.commit()
                    self.assertTrue(Path(str(source) + "-wal").exists())
                    backup_database(source, target)
                with self.assertRaises(FileExistsError):
                    backup_database(source, target)
            with patch.dict(os.environ, {"SUPERVISOR_DB_PATH": str(target)}):
                self.assertEqual(count_consecutive_approvals("ficticio"), 1)
                self.assertTrue(is_auto_approved("ficticio"))
                with closing(sqlite3.connect(target)) as restored:
                    self.assertEqual(restored.execute("SELECT state FROM fake_checkpoint").fetchone()[0], "aguardando aprovacao")

    def test_missing_source_is_not_created(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            source = Path(folder) / "missing.db"
            target = Path(folder) / "backup.db"
            with self.assertRaises(FileNotFoundError):
                backup_database(source, target)
            self.assertFalse(source.exists())
            self.assertFalse(target.exists())

    def test_path_validation_and_default(self):
        with patch.dict(os.environ, {"SUPERVISOR_DB_PATH": "relative.db"}):
            with self.assertRaises(ValueError):
                database_path()
        with patch.dict(os.environ):
            os.environ.pop("SUPERVISOR_DB_PATH", None)
            self.assertTrue(database_path().is_absolute())


if __name__ == "__main__":
    unittest.main()
