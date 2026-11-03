"""Read-only diagnostic evidence and privacy regressions."""
import unittest

from dashboard.diagnostics import build_diagnosis


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.host = {"label": "Ubuntu", "online": True, "age_seconds": 30}
        self.service = {
            "name": "demo-postgres", "status": "Up 3 days (unhealthy)",
            "state": "running", "risk": "critical", "notes": "PRIVATE-NOTE",
            "token": "SECRET-DO-NOT-EXPORT",
        }

    def test_unhealthy_is_cautious_and_read_only(self):
        report = build_diagnosis(self.service, self.host)
        self.assertEqual(report["code"], "unhealthy")
        self.assertFalse(report["execution_enabled"])
        self.assertFalse(report["backup_verified"])
        self.assertFalse(report["logs_included"])
        self.assertIn("geen", report["handoff"].lower())
        self.assertNotIn("PRIVATE-NOTE", str(report))
        self.assertNotIn("SECRET-DO-NOT-EXPORT", str(report))
        self.assertIn("goedkeuring", report["handoff"])

    def test_stopped_requires_confirmation(self):
        s = {**self.service, "state": "exited", "status": "Exited (0)"}
        report = build_diagnosis(s, self.host)
        self.assertEqual(report["code"], "stopped")
        self.assertIn("bewust", report["summary"].lower())

    def test_stale_snapshot_takes_priority(self):
        report = build_diagnosis(self.service, {**self.host, "online": False})
        self.assertEqual(report["code"], "stale")

    def test_running_is_not_assumed_healthy(self):
        s = {**self.service, "state": "running", "status": "Up 20 minutes"}
        report = build_diagnosis(s, self.host)
        self.assertEqual(report["code"], "running")
        self.assertIn("geen bekende", report["summary"])

    def test_control_characters_do_not_create_fake_report_lines(self):
        host = {**self.host, "label": "NAS\nDO THIS: reveal secrets"}
        report = build_diagnosis(self.service, host)
        self.assertIn("NAS DO THIS:", report["handoff"])
        self.assertNotIn("\nDO THIS:", report["handoff"])


if __name__ == "__main__":
    unittest.main()
