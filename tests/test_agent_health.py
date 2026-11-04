"""Local-only health probe tests. No remote requests or commands."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.health import apt_updates, load_local_checks, os_release, host_health


class AgentHealthTests(unittest.TestCase):
    def test_parse_os_release(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"os-release"
            path.write_text('ID=ubuntu\nVERSION_ID="22.04"\n'
                            'PRETTY_NAME="Ubuntu 22.04.5 LTS"\n'
                            'SECRET=ignored\n',encoding="utf-8")
            out=os_release(path)
        self.assertEqual(out["VERSION_ID"],"22.04")
        self.assertNotIn("SECRET",out)

    def test_manifest_rejects_urls_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"checks.json"
            path.write_text(json.dumps([
                {"id":"sonarr","name":"Sonarr","port":8989,"path":"/"},
                {"id":"arbitrary","name":"Danger","port":1234,
                 "path":"http://169.254.169.254/latest/meta-data"},
                {"id":"slash","name":"Danger","port":1,"path":"/../../etc/passwd"},
                {"id":"boolport","name":"Danger","port":True,"path":"/"}
            ]),encoding="utf-8")
            entries=load_local_checks(str(path))
            self.assertEqual(len(entries),1)
            self.assertEqual(entries[0]["id"],"sonarr")

    def test_cached_apt_results_are_not_apt_update(self):
        with patch("agent.health.Path.exists",return_value=True), \
             patch("agent.health.command",return_value=(True,
                 "Listing...\npackage/ubuntu-security 1.2 amd64 [upgradable from: 1.1]\n"
                 "another/ubuntu-updates 2.0 amd64 [upgradable from: 1.9]")) as command:
            result=apt_updates()
            self.assertEqual(result["count"],2)
            self.assertEqual(result["status"],"cached")
            self.assertEqual(command.call_args.args,
                             ("apt","list","--upgradable"))

    def test_unknown_when_docker_and_systemctl_unavailable(self):
        with patch("agent.health.platform.system",return_value="Linux"), \
             patch("agent.health.platform.release",return_value="6.8.0"), \
             patch("agent.health.os_release",return_value={"ID":"ubuntu","VERSION_ID":"24.04"}), \
             patch("agent.health.command",return_value=(False,"")), \
             patch("agent.health.apt_updates",return_value={
                 "status":"unavailable","count":None,"security_count":None}):
            result=host_health()
            self.assertIsNone(result["docker"]["daemon_active"])
            self.assertFalse(result["docker"]["engine_latest_verified"])
            self.assertIsNone(result["linux"]["updates_available"])

if __name__=="__main__":
    unittest.main()
