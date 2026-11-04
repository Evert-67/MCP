"""Tests for read-only host findings, absent agent data, and true uncertainty."""
import unittest
from dashboard.health import assess_host, build_health_overview


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.host = {
            "id": "media", "label": "Media server",
            "online": True, "age_seconds": 10,
            "host_health": {
                "linux": {
                    "distro": "ubuntu", "version": "22.04",
                    "system_state": "degraded", "reboot_required": True,
                    "updates_available": 12,
                    "security_updates_lower_bound": 2,
                },
                "docker": {"daemon_active": True,
                           "server_version": "28.0.0",
                           "engine_latest_verified": False},
                "app_checks": [
                    {"id": "sonarr", "name": "Sonarr", "status": "unreachable"},
                    {"id": "jellyfin", "name": "Jellyfin", "status": "auth_required"},
                ]
            }
        }
        self.services = [
            {"server_id":"media","name":"homarr","status":"Up","state":"running",
             "update":{"status":"release_found"}},
            {"server_id":"media","name":"supertokens",
             "status":"Up 3 weeks (unhealthy)","state":"running",
             "update":{"status":"not_checked"}},
            {"server_id":"media","name":"old-nixopus","status":"Exited (1)",
             "state":"exited","update":{"status":"not_checked"}},
        ]

    def test_incident_findings_are_real_but_not_executable(self):
        state = build_health_overview({"servers":[self.host],"services":self.services})
        self.assertTrue(state["read_only"])
        self.assertFalse(state["execution_enabled"])
        self.assertFalse(state["diagnosis_complete"])
        self.assertEqual(state["summary"]["hosts_with_deep_evidence"],1)
        self.assertEqual(state["summary"]["app_probes"],2)
        findings=state["hosts"][0]["findings"]
        codes={i["code"] for i in findings}
        self.assertIn("linux-degraded", codes)
        self.assertIn("linux-reboot-pending", codes)
        self.assertIn("linux-packages", codes)
        self.assertIn("container-unhealthy", codes)
        self.assertIn("container-stopped", codes)
        self.assertIn("app-probe-sonarr", codes)
        self.assertIn("app-auth-jellyfin", codes)
        self.assertIn("release-unverified", codes)
        self.assertFalse(state["hosts"][0]["fully_verified"])
        self.assertTrue(all(not x["execution_enabled"] for x in findings))

    def test_stopped_is_review_not_confirmed_outage(self):
        findings=assess_host(self.host,self.services)["findings"]
        stopped=[i for i in findings if i["code"]=="container-stopped"]
        self.assertEqual(len(stopped),1)
        self.assertEqual(stopped[0]["severity"],"review")
        self.assertIn("gewenste toestand is onbekend",stopped[0]["observation"])

    def test_existing_snapshot_without_agent_is_unknown(self):
        state=build_health_overview({"servers":[{
            "id":"local","label":"EB-UBU-HOME","online":True
        }],"services":[]})
        host=state["hosts"][0]
        self.assertFalse(host["agent_evidence"])
        self.assertIsNone(host["linux"])
        self.assertEqual(host["status"],"partial")
        self.assertIn("host-evidence-missing",
                      [i["code"] for i in host["findings"]])

    def test_offline_snapshot_not_proof_machine_is_dead(self):
        host={**self.host,"online":False}
        result=assess_host(host,[])
        finding=next(i for i in result["findings"] if i["code"]=="host-stale")
        self.assertIn("bewijst niet",finding["recommendation"])

if __name__ == "__main__":
    unittest.main()
