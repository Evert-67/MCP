"""Update candidates are persistent and notification events are de-duplicated."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dashboard import storage


class UpdateStorageTests(unittest.TestCase):
    def test_notify_only_new_candidate_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "control.db"
            with patch.object(storage, "DB_FILE", db_path):
                storage.init_db()
                one = {"status":"candidate","candidate_tag":"7.4.1"}
                storage.save_update_check("local/redis","redis:7.2.0",one)
                storage.save_update_check("local/redis","redis:7.2.0",one)
                self.assertEqual(
                    [e["kind"] for e in storage.recent_events()],
                    ["update-candidate"]
                )
                newer = {"status":"candidate","candidate_tag":"7.4.2"}
                storage.save_update_check("local/redis","redis:7.2.0",newer)
                self.assertEqual(len(storage.recent_events()),2)
                self.assertEqual(
                    json.loads(storage.all_update_checks()["local/redis"]["payload"]),
                    newer
                )

    def test_empty_and_non_candidate_results_do_not_alert(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(storage,"DB_FILE",Path(directory)/"db.sqlite"):
                storage.init_db()
                storage.save_update_check("local/test","test:latest",
                                          {"status":"unsupported"})
                self.assertEqual(storage.recent_events(),[])
