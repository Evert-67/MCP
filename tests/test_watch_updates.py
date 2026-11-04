"""Background version scans must be opt-in, bounded and non-executable."""
import unittest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from dashboard.watch_updates import due_images, run_cycle


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 4, 20, 0, tzinfo=timezone.utc)
        self.hosts = [{"id":"local","online":True},{"id":"offline","online":False}]
        self.services = [
            {"server_id":"local", "key":"local/redis", "image":"redis:7.2.4"},
            {"server_id":"local", "key":"local/redis-2", "image":"redis:7.2.4"},
            {"server_id":"offline", "key":"offline/postgres", "image":"postgres:17.2"},
        ]
        self.state = {"servers":self.hosts,"services":self.services}

    def test_disabled_never_fetches_state_or_registry(self):
        with patch("dashboard.watch_updates.get_settings",
                   return_value={"auto_version_checks":False}), \
             patch("dashboard.watch_updates.all_update_checks") as checks:
            def fail():
                raise AssertionError("No scan should run before opt in")
            result = run_cycle(get_state=fail, checker=fail, now=self.now)
            self.assertEqual(result, {"enabled":False,"checked":0,"candidates":0})
            checks.assert_not_called()

    def test_due_entries_grouped_and_persisted(self):
        saved=[]
        calls=[]
        def check(image):
            calls.append(image)
            return {"status":"candidate","candidate_tag":"7.4.2","execution_enabled":False}
        with patch("dashboard.watch_updates.get_settings",return_value={
                "auto_version_checks":True,"version_check_interval_hours":24}), \
             patch("dashboard.watch_updates.all_update_checks",return_value={}), \
             patch("dashboard.watch_updates.save_update_check",
                   side_effect=lambda *args: saved.append(args)):
            result=run_cycle(get_state=lambda:self.state,checker=check,now=self.now)
        self.assertEqual(calls, ["redis:7.2.4"])
        self.assertEqual([item[0] for item in saved], ["local/redis","local/redis-2"])
        self.assertEqual(result["checked"],2)
        self.assertEqual(result["candidates"],2)

    def test_backoff_until_expiry(self):
        checks={
            "local/redis":{"image_ref":"redis:7.2.4",
                           "checked_at":(self.now-timedelta(hours=10)).isoformat(),
                           "payload":json.dumps({"checker_rev":2,"current_software_version":None})},
            "local/redis-2":{"image_ref":"redis:7.2.4",
                             "checked_at":(self.now-timedelta(hours=10)).isoformat(),
                           "payload":json.dumps({"checker_rev":2,"current_software_version":None})}
        }
        with patch("dashboard.watch_updates.get_settings",return_value={
                "auto_version_checks":True,"version_check_interval_hours":24}), \
             patch("dashboard.watch_updates.all_update_checks",return_value=checks):
            calls=[]
            result=run_cycle(get_state=lambda:self.state,
                checker=lambda image:calls.append(image),now=self.now)
        self.assertEqual(calls,[])
        self.assertEqual(result["checked"],0)

    def test_legacy_version_checks_are_invalidated(self):
        checks={"local/redis":{"image_ref":"redis:7.2.4",
                                "checked_at":self.now.isoformat(),
                                "payload":json.dumps({"status":"candidate",
                                                      "candidate_tag":"20260805"})}}
        due=due_images(self.services,checks,24,self.now)
        self.assertIn("redis:7.2.4",due)

    def test_installed_version_groups_are_distinct(self):
        services=[
            {"key":"local/a","image":"ghcr.io/homarr-labs/homarr:latest",
             "software_version":"v2.9.0"},
            {"key":"local/b","image":"ghcr.io/homarr-labs/homarr:latest",
             "software_version":"v2.10.1"},
        ]
        due=due_images(services,{},24,self.now)
        self.assertEqual(len(due),2)

    def test_changed_image_immediately_becomes_due(self):
        checks={"local/redis":{"image_ref":"redis:7.0.1",
                               "checked_at":self.now.isoformat()}}
        due=due_images(self.services,checks,24,self.now,limit=1)
        self.assertEqual(list(due),["redis:7.2.4"])
        self.assertEqual(len(due["redis:7.2.4"]),2)

    def test_large_host_inventory_bounded(self):
        services=[{"key":f"local/{idx}","image":f"redis:{idx}.0"}
                  for idx in range(200)]
        due=due_images(services,{},24,self.now,limit=4)
        self.assertEqual(len(due),4)


if __name__=="__main__":
    unittest.main()
