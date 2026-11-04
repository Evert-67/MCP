"""Regression checks: recovery planning must never imply that backups exist."""
import unittest
from dashboard.recovery import build_recovery_overview, build_recovery_plan


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.host = {
            "id": "local", "label": "Ubuntu Host", "online": True,
            "age_seconds": 20
        }
        self.service = {
            "name": "postgres-1", "server_id": "local",
            "key": "local/postgres-1", "status": "Up 3 days",
            "risk": "critical", "state": "running",
            "token": "DO-NOT-SHARE-SECRET",
            "notes": "private internal notes"
        }

    def test_inventory_is_not_backup_evidence(self):
        result = build_recovery_overview({
            "servers": [self.host],
            "services": [self.service]
        })
        self.assertTrue(result["read_only"])
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["backup_integrations_enabled"])
        self.assertIsNone(result["backup_count"])
        self.assertIsNone(result["verified_backup_count"])
        self.assertIsNone(result["restore_tests_passed"])
        self.assertFalse(result["automatic_failover_enabled"])
        self.assertEqual(result["hosts"][0]["backup_status"], "unknown")
        self.assertEqual(result["hosts"][0]["restore_test_status"], "not_tested")
        self.assertFalse(result["hosts"][0]["recovery_ready"])
        self.assertEqual(result["hosts"][0]["critical_services"], 1)
        self.assertNotIn("DO-NOT-SHARE-SECRET", str(result))

    def test_recovery_plan_not_executable(self):
        result = build_recovery_plan(self.service, self.host)
        self.assertFalse(result["ready_for_recovery"])
        self.assertFalse(result["backup_verified"])
        self.assertFalse(result["restore_tested"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["report_type"], "planning_only")
        self.assertEqual(len(result["prerequisites"]), 5)
        self.assertNotIn("private internal notes", str(result))
        self.assertNotIn("DO-NOT-SHARE-SECRET", str(result))

    def test_offline_host_must_not_be_ready(self):
        result = build_recovery_plan(self.service, {**self.host,"online":False})
        self.assertFalse(result["host_online"])
        self.assertFalse(result["ready_for_recovery"])

    def test_unknown_inventory_empty(self):
        result = build_recovery_overview({"servers":[],"services":[]})
        self.assertEqual(result["hosts"], [])
        self.assertIsNone(result["backup_count"])


if __name__ == "__main__":
    unittest.main()
