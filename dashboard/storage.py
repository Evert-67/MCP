"""Small SQLite state store. No credentials are ever returned in reads."""
import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_FILE = Path(os.environ.get("CODEPUG_DB", "/appdata/codepug.db"))


def utcnow():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def db():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_FILE, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with db() as c:
        c.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS agents (
          id TEXT PRIMARY KEY, label TEXT NOT NULL, token_hash TEXT NOT NULL,
          created_at TEXT NOT NULL, last_seen TEXT
        );
        CREATE TABLE IF NOT EXISTS reports (
          agent_id TEXT PRIMARY KEY, payload TEXT NOT NULL, collected_at TEXT NOT NULL,
          received_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS policies (
          service_key TEXT PRIMARY KEY, risk_override TEXT, mode TEXT NOT NULL DEFAULT 'monitor',
          notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, kind TEXT NOT NULL,
          subject TEXT NOT NULL, detail TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
          key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """)
        if "scan_interval" not in {r["name"] for r in c.execute("PRAGMA table_info(agents)")}:
            c.execute("ALTER TABLE agents ADD COLUMN scan_interval INTEGER NOT NULL DEFAULT 120")


def event(kind: str, subject: str, detail: str):
    with db() as c:
        c.execute("INSERT INTO events(time,kind,subject,detail) VALUES(?,?,?,?)",
                  (utcnow(), kind[:50], subject[:120], detail[:300]))


def new_agent(label: str):
    sid = secrets.token_hex(12)
    token = secrets.token_urlsafe(40)
    with db() as c:
        c.execute("INSERT INTO agents(id,label,token_hash,created_at,last_seen) VALUES(?,?,?,?,NULL)",
                  (sid, label, hashlib.sha256(token.encode()).hexdigest(), utcnow()))
    event("agent-created", sid, label)
    return {"id": sid, "label": label, "token": token}


def agent_info(sid: str):
    with db() as c:
        row = c.execute("SELECT * FROM agents WHERE id=?", (sid,)).fetchone()
        return dict(row) if row else None


def all_agents():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT id,label,created_at,last_seen,scan_interval FROM agents ORDER BY label")]


def save_report(sid: str, payload: dict):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    now = utcnow()
    with db() as c:
        c.execute("INSERT INTO reports VALUES(?,?,?,?) ON CONFLICT(agent_id) DO UPDATE SET payload=excluded.payload,collected_at=excluded.collected_at,received_at=excluded.received_at",
                  (sid, body, payload["collected_at"], now))
        c.execute("UPDATE agents SET last_seen=? WHERE id=?", (now, sid))


def all_reports():
    with db() as c:
        return {r["agent_id"]: dict(r) for r in c.execute("SELECT * FROM reports")}


def all_policies():
    with db() as c:
        return {r["service_key"]: dict(r) for r in c.execute("SELECT * FROM policies")}


def put_policy(key: str, risk: str | None, mode: str, notes: str):
    with db() as c:
        c.execute("INSERT INTO policies VALUES(?,?,?,?,?) ON CONFLICT(service_key) DO UPDATE SET risk_override=excluded.risk_override,mode=excluded.mode,notes=excluded.notes,updated_at=excluded.updated_at",
                  (key, risk, mode, notes[:500], utcnow()))
    event("policy-edited", key, f"{risk or 'auto'} / {mode}")


def recent_events(limit=25):
    with db() as c:
        return [dict(r) for r in c.execute("SELECT time,kind,subject,detail FROM events ORDER BY id DESC LIMIT ?", (limit,))]


# Presentation and monitoring preferences; never an update-execution grant.
DEFAULT_SETTINGS = {
    "refresh_seconds": 60,
    "offline_after_seconds": 300,
    "alerts_enabled": True,
    "notify_unhealthy": True,
}


def get_settings():
    out = DEFAULT_SETTINGS.copy()
    with db() as c:
        for row in c.execute("SELECT key,value FROM settings"):
            if row["key"] in out:
                try:
                    out[row["key"]] = json.loads(row["value"])
                except (ValueError, TypeError):
                    pass
    return out


def put_settings(values: dict):
    with db() as c:
        for key in DEFAULT_SETTINGS:
            if key in values:
                c.execute(
                    "INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                    (key, json.dumps(values[key]), utcnow()))
    event("settings-edited", "dashboard", "Monitoring preferences changed")


def update_agent(sid: str, label: str, scan_interval: int) -> bool:
    with db() as c:
        changed = c.execute(
            "UPDATE agents SET label=?,scan_interval=? WHERE id=?",
            (label, scan_interval, sid)).rowcount
    if changed:
        event("agent-updated", sid, f"Agent cadence: {scan_interval}s")
    return bool(changed)


def delete_agent(sid: str) -> bool:
    with db() as c:
        found = c.execute("DELETE FROM agents WHERE id=?", (sid,)).rowcount
        if found:
            c.execute("DELETE FROM reports WHERE agent_id=?", (sid,))
            c.execute("DELETE FROM policies WHERE substr(service_key,1,?)=?",
                      (len(sid) + 1, sid + "/"))
    if found:
        event("agent-revoked", sid, "Token revoked; report and policies deleted")
    return bool(found)
