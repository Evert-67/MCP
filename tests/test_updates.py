"""Read-only public registry version checks: never imply installability."""
import unittest
from dashboard.updates import reference, tag_key, check_public_docker_hub


class UpdateCheckTests(unittest.TestCase):
    def test_parser_avoids_non_public_or_ambiguous_refs(self):
        self.assertEqual(reference("redis:7.2"), {"repository":"library/redis","tag":"7.2"})
        self.assertEqual(reference("docker.io/library/postgres:17.2"),
                         {"repository":"library/postgres","tag":"17.2"})
        for image in ("redis:latest","ghcr.io/team/repo:1.2.3",
                      "192.168.2.10:5000/app:1.2.3",
                      "private.local:5000/app:1.2.3",
                      "redis@sha256:"+"a"*64,"registry.example.org/app:1.0"):
            self.assertIsNone(reference(image), image)

    def test_numeric_variants_and_prereleases(self):
        self.assertEqual(tag_key("1.2.3")[0], (1,2,3))
        self.assertEqual(tag_key("v1.2.3-alpine3.22")[0], (1,2,3))
        self.assertIsNone(tag_key("1.2.4-rc1"))
        self.assertIsNone(tag_key("latest"))

    def test_higher_public_tag_candidate_not_authorized_install(self):
        def fetch(repo, page):
            self.assertEqual(repo, "library/redis")
            self.assertEqual(page, 1)
            return {"next": None, "results":[
                {"name":"7.2.4"},{"name":"7.4.2"},{"name":"7.9.0-rc1"},
                {"name":"9.0.0-alpine"},{"name":"7.0.1"}
            ]}
        result=check_public_docker_hub("redis:7.2.4", fetch=fetch)
        self.assertEqual(result["status"],"candidate")
        self.assertEqual(result["candidate_tag"],"7.4.2")
        self.assertFalse(result["execution_enabled"])
        self.assertTrue(result["complete"])

    def test_no_newer_tag_does_not_imply_latest_when_incomplete(self):
        def fetch(repo,page):
            return {"next":"https://hub.docker.com/next", "results":[{"name":"7.2.4"}]}
        result=check_public_docker_hub("redis:7.2.4",fetch=fetch)
        self.assertEqual(result["status"],"incomplete")
        self.assertFalse(result["complete"])
        self.assertEqual(result["checked_pages"],2)

    def test_different_os_variant_not_suggested(self):
        def fetch(repo,page):
            return {"next":None,"results":[
                {"name":"1.3.0-alpine"},{"name":"2.0.0-bookworm"},{"name":"1.4.0"}
            ]}
        result=check_public_docker_hub("nginx:1.2.0-alpine",fetch=fetch)
        self.assertEqual(result["status"],"candidate")
        self.assertEqual(result["candidate_tag"],"1.3.0-alpine")

    def test_unversioned_image_never_triggers_outbound_query(self):
        def no_fetch(*_):
            raise AssertionError("Unsupported image must not make network request")
        result=check_public_docker_hub("ghcr.io/org/private:latest",fetch=no_fetch)
        self.assertEqual(result["status"],"unsupported")
        self.assertFalse(result["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
