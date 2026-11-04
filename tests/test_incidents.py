"""Incident grouping must not invent shared root causes or noisy incidents."""
import unittest

from dashboard.incidents import build_incidents


class IncidentsTests(unittest.TestCase):
    def test_host_snapshot_stale_collapses_children(self):
        state = {
            "servers":[{"id":"h1","label":"Mediarr","online":False}],
            "services":[
                {"server_id":"h1","name":"Sonarr","state":"exited","status":"Exited"},
                {"server_id":"h1","name":"Radarr","state":"exited","status":"Exited"},
            ]
        }
        result=build_incidents(state)
        self.assertEqual(len(result["incidents"]),1)
        self.assertEqual(result["incidents"][0]["scope"],"host")
        self.assertFalse(result["incidents"][0]["root_cause_confirmed"])
        self.assertFalse(result["execution_enabled"])

    def test_cluster_same_host_only_marks_network_hypothesis(self):
        state={
            "servers":[
                {"id":"a","label":"Media","online":True,
                 "host_health":{"app_checks":[
                     {"name":"Sonarr","id":"sonarr","status":"unreachable"},
                     {"name":"Radarr","id":"radarr","status":"error"}]}},
                {"id":"b","label":"Hub","online":True,
                 "host_health":{"app_checks":[
                     {"name":"Prowlarr","id":"prowlarr","status":"unreachable"}]}}
            ],
            "services":[]
        }
        report=build_incidents(state)
        grouped=[i for i in report["incidents"] if i["scope"]=="shared-symptom"]
        self.assertEqual(len(grouped),1)
        self.assertEqual(grouped[0]["host_id"],"a")
        self.assertFalse(grouped[0]["root_cause_confirmed"])
        self.assertIn("niet", grouped[0]["hypothesis"].lower())
        self.assertTrue(all(not i["execution_enabled"] for i in report["incidents"]))

    def test_stopped_is_review_not_outage(self):
        result=build_incidents({
            "servers":[{"id":"h","label":"Host","online":True}],
            "services":[{"server_id":"h","name":"old-test","state":"exited","status":"Exited (0)"}]
        })
        issue=result["incidents"][0]
        self.assertEqual(issue["severity"],"review")
        self.assertIn("bewust",issue["next_step"])
        self.assertFalse(issue["root_cause_confirmed"])

    def test_independent_high_priority(self):
        result=build_incidents({
            "servers":[{"id":"h","label":"Host","online":True,
                        "host_health":{"docker":{"daemon_active":False},
                                       "linux":{"system_state":"degraded"}}}],
            "services":[{"server_id":"h","name":"test","state":"exited","status":"Exited"}]
        })
        codes={x["code"] for x in result["incidents"]}
        self.assertIn("docker-inactive",codes)
        self.assertIn("linux-degraded",codes)
        self.assertNotIn("stopped-test",codes)

if __name__=="__main__":
    unittest.main()
