"""Portability and localization regression checks (no running Docker required)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PortabilityTests(unittest.TestCase):
    def test_generic_deployment(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        app = (ROOT / "dashboard/app.py").read_text(encoding="utf-8")
        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("HOST_SNAPSHOT_DIR", compose)
        self.assertIn("HOST_SNAPSHOT_DIR=./host-data", env)
        self.assertNotIn("/opt/codepug-mcp/data:/host-snapshot", compose)
        self.assertNotIn("EB-UBU-HOME", app)

    def test_language_catalog_and_switcher(self):
        page = (ROOT / "dashboard/templates/index.html").read_text(encoding="utf-8")
        i18n = (ROOT / "dashboard/static/i18n.js").read_text(encoding="utf-8")
        english = json.loads((ROOT / "dashboard/static/locales/en.json").read_text(encoding="utf-8"))
        self.assertIn('id="language"', page)
        self.assertIn('value="nl"', page)
        self.assertIn('value="en"', page)
        self.assertIn("/static/i18n.js", page)
        self.assertIn("navigator.language", i18n)
        self.assertIn("localStorage", i18n)
        for key in ("Overzicht", "Risicobeleid", "Dienstenoverzicht",
                    "Server toevoegen", "Automatische updates", "Veilige testmodus actief"):
            self.assertTrue(english.get(key), f"Missing English translation for {key}")

    def test_agent_declares_capabilities(self):
        agent = (ROOT / "agent/scan.py").read_text(encoding="utf-8")
        self.assertIn('"capabilities":["docker-inventory"]', agent)
        self.assertIn("except (AttributeError, OSError):", agent)


if __name__ == "__main__":
    unittest.main()
