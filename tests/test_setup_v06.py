"""Regression tests for the v0.6 CLI setup helper."""
import os
import tempfile
import unittest
from pathlib import Path

from scripts.setup_v06 import hash_password, save_hash


class SetupTests(unittest.TestCase):
    def test_hash_is_compatible_and_password_not_stored(self):
        value = hash_password("a memorable passphrase", rounds=100_000)
        self.assertTrue(value.startswith("pbkdf2_sha256$100000$"))
        self.assertNotIn("a memorable passphrase", value)
        self.assertEqual(len(value.split("$")), 4)

    def test_short_password_rejected(self):
        with self.assertRaises(ValueError):
            hash_password("1234567")

    def test_save_does_not_change_other_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text("BIND_IP=127.0.0.1\nDASHBOARD_PASSWORD_HASH=\nDASHBOARD_USER=admin\n", encoding="utf-8")
            self.assertTrue(save_hash(path, "pbkdf2_sha256$100000$abc$def"))
            data = path.read_text()
            self.assertIn("BIND_IP=127.0.0.1", data)
            self.assertIn("DASHBOARD_USER=admin", data)
            self.assertIn("DASHBOARD_PASSWORD_HASH='pbkdf2_sha256$100000$abc$def'", data)
            self.assertFalse(save_hash(path, "replacement"))
            self.assertNotIn("replacement", path.read_text())
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_reset_only_explicitly(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text("DASHBOARD_PASSWORD_HASH='old'\n")
            self.assertTrue(save_hash(path, "new", overwrite=True))
            self.assertIn("DASHBOARD_PASSWORD_HASH='new'", path.read_text())

    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "target"
            target.write_text("DASHBOARD_PASSWORD_HASH=\n")
            shortcut = Path(folder) / ".env"
            try:
                shortcut.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks unavailable")
            with self.assertRaises(ValueError):
                save_hash(shortcut, "some-hash")


if __name__ == "__main__":
    unittest.main()
