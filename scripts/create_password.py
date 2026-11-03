#!/usr/bin/env python3
"""Generate a PBKDF2 password hash for the dashboard, never store plaintext."""
import getpass
import hashlib
import secrets
p=getpass.getpass('Kies dashboard-wachtwoord: ')
q=getpass.getpass('Herhaal wachtwoord: ')
if p!=q or len(p)<14:
    raise SystemExit('Wachtwoorden komen niet overeen, of minder dan 14 tekens')
rounds=600000
salt=secrets.token_bytes(24)
h=hashlib.pbkdf2_hmac('sha256',p.encode(),salt,rounds)
print("DASHBOARD_PASSWORD_HASH='pbkdf2_sha256$%s$%s$%s'"%(rounds,salt.hex(),h.hex()))
