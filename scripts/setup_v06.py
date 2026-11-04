#!/usr/bin/env python3
"""CodePug password setup: store a password hash without manual copy/paste.

This does NOT provide a web setup wizard or install Docker. Existing .env files
are preserved and never reset unless the operator explicitly passes --reset.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hash_password(password: str, rounds: int = 600_000) -> str:
    if len(password) < 12:
        raise ValueError("Gebruik minimaal 12 tekens; een wachtwoordzin is makkelijker te onthouden.")
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds).hex()
    return "pbkdf2_sha256" + "$" + str(rounds) + "$" + salt.hex() + "$" + digest


def save_hash(env: Path, encoded: str, overwrite: bool = False) -> bool:
    """Replace only the hash key. Do not touch any other installation settings."""
    if env.is_symlink():
        raise ValueError("Weiger symbolische link voor .env")
    if env.exists():
        data = env.read_text(encoding="utf-8")
    else:
        data = (ROOT / ".env.example").read_text(encoding="utf-8")
    lines = data.splitlines()
    matches = [i for i, line in enumerate(lines) if line.startswith("DASHBOARD_PASSWORD_HASH=")]
    if len(matches) != 1:
        raise ValueError("Verwacht precies één DASHBOARD_PASSWORD_HASH-regel")
    idx = matches[0]
    existing = lines[idx].split("=", 1)[1].strip().strip("'").strip('"')
    if existing and not overwrite:
        return False
    lines[idx] = f"DASHBOARD_PASSWORD_HASH='{encoded}'"
    # Atomic replace, protected mode. Never emit secret to stdout or logs.
    tmp = env.with_name(env.name + ".tmp-" + secrets.token_hex(6))
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, env)
        os.chmod(env, 0o600)
    finally:
        tmp.unlink(missing_ok=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Eerste CodePug configuratie")
    parser.add_argument("--reset", action="store_true", help="bestaand dashboardwachtwoord vervangen")
    args = parser.parse_args()
    env = ROOT / ".env"
    if env.exists() and not args.reset:
        already_set = any(line.startswith("DASHBOARD_PASSWORD_HASH=") and
                          bool(line.split("=", 1)[1].strip())
                          for line in env.read_text(encoding="utf-8").splitlines())
        if already_set:
            print("Er is al een wachtwoord ingesteld. Niets gewijzigd.")
            print("Gebruik --reset uitsluitend als je bewust een nieuw wachtwoord wilt kiezen.")
            return
    print("CodePug configuratie — kies een wachtwoordzin (minimaal 12 tekens).")
    first = getpass.getpass("Nieuw dashboardwachtwoord: ")
    second = getpass.getpass("Herhaal dashboardwachtwoord: ")
    if first != second:
        raise SystemExit("Wachtwoorden komen niet overeen; niets gewijzigd.")
    try:
        saved = save_hash(env, hash_password(first), overwrite=args.reset)
    except ValueError as exc:
        raise SystemExit(str(exc))
    print("Dashboardwachtwoord veilig opgeslagen in .env." if saved else "Bestaand wachtwoord behouden.")


if __name__ == "__main__":
    main()
