"""CodePug Control Center v0.5: observation and policy editing, no update execution."""
from __future__ import annotations
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .diagnostics import build_diagnosis
from .risk import LEVELS, classify, effective_risk, permitted_mode
from .storage import (init_db, all_agents, all_policies, all_reports, agent_info,
                      new_agent, put_policy, recent_events, save_report,
                      get_settings, put_settings, update_agent, delete_agent)

ROOT = Path(__file__).resolve().parent
HOST_SNAPSHOT = Path(os.getenv("HOST_SNAPSHOT", "/host-snapshot/status.json"))
AUTH_USER = os.getenv("DASHBOARD_USER", "admin")
AUTH_HASH = os.getenv("DASHBOARD_PASSWORD_HASH", "")
PUBLIC_ORIGIN = os.getenv("DASHBOARD_PUBLIC_ORIGIN", "").rstrip("/")
security = HTTPBasic()
app = FastAPI(title="CodePug Server Control", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


def check_password(value: str, encoded: str) -> bool:
    try:
        tag, rounds, salt, digest = encoded.split("$")
        if tag != "pbkdf2_sha256" or not 100_000 <= int(rounds) <= 1_500_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(actual.hex(), digest)
    except (TypeError, ValueError):
        return False


def require_admin(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    if not AUTH_HASH or not (hmac.compare_digest(credentials.username.encode(), AUTH_USER.encode())
                             and check_password(credentials.password, AUTH_HASH)):
        raise HTTPException(401, "Inloggen vereist", headers={"WWW-Authenticate": 'Basic realm="CodePug"'})


def guard_mutation(request: Request):
    # Non-simple header prevents cross-origin form POST; no permissive CORS in app.
    if request.headers.get("x-codepug-request") != "1":
        raise HTTPException(403, "Beveiligde aanvraag vereist")
    origin = request.headers.get("origin")
    if origin and origin != (PUBLIC_ORIGIN or str(request.base_url).rstrip("/")):
        # Reverse proxy deployments should preserve Host + forwarded scheme.
        raise HTTPException(403, "Ongeldige herkomst")


class PolicyIn(BaseModel):
    service_key: str = Field(min_length=3, max_length=240)
    risk_override: str | None = None
    mode: str = "monitor"
    notes: str = Field(default="", max_length=500)


class AgentIn(BaseModel):
    label: str = Field(min_length=2, max_length=80)


class AgentSettingsIn(BaseModel):
    label: str = Field(min_length=2, max_length=80)
    scan_interval: int = Field(ge=60, le=3600)


class DashboardSettingsIn(BaseModel):
    refresh_seconds: int = Field(ge=15, le=300)
    offline_after_seconds: int = Field(ge=120, le=7200)
    alerts_enabled: bool
    notify_unhealthy: bool


def clean_containers(raw):
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw[:500]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("Names") or "")[:120]
        if not name:
            continue
        result.append({
            "name": name,
            "image": str(item.get("image") or item.get("Image") or "")[:240],
            "status": str(item.get("status") or item.get("Status") or "")[:140],
            "state": str(item.get("state") or item.get("State") or "")[:50],
            "project": str(item.get("project") or "")[:90],
            "service": str(item.get("service") or "")[:90],
            "docker_socket": item.get("docker_socket") is True,
            "persistent": item.get("persistent") is True,
        })
    return result


def parse_timestamp(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if d.tzinfo is None:
            raise ValueError("no tz")
        if abs((datetime.now(timezone.utc) - d).total_seconds()) > 3600:
            raise ValueError("out of range")
        return d.isoformat()
    except (ValueError, TypeError):
        raise HTTPException(422, "Ongeldige timestamp")


def build_state():
    agents = all_agents()
    settings = get_settings()
    reports = all_reports()
    policies = all_policies()
    servers, services = [], []
    # Local snapshot from the existing v0.4 MCP collector.
    if HOST_SNAPSHOT.is_file():
        try:
            s = json.loads(HOST_SNAPSHOT.read_text(encoding="utf-8"))
            servers.append({"id":"local", "label":str(s.get("hostname","Local server"))[:80],
                            "type":"local", "collected_at":s.get("collected_at"),
                            "memory":s.get("memory",{}), "disk_root":s.get("disk_root",{}),
                            "platform":str(s.get("platform") or "unknown")[:32],
                            "capabilities":["docker-inventory"]})
            for c in clean_containers(s.get("containers", [])):
                services.append(("local", c))
        except (OSError, ValueError):
            pass
    for a in agents:
        rep = reports.get(a["id"])
        payload = json.loads(rep["payload"]) if rep else {}
        servers.append({"id":a["id"],"label":a["label"],"type":"agent",
                        "collected_at":rep["collected_at"] if rep else None,
                        "memory":payload.get("memory",{}),"disk_root":payload.get("disk_root",{}),
                        "platform":payload.get("platform","unknown"),
                        "capabilities":payload.get("capabilities",[])})
        for c in clean_containers(payload.get("containers", [])):
            services.append((a["id"], c))
    out = []
    now = datetime.now(timezone.utc)
    for server_id, c in services:
        key = f"{server_id}/{c['name']}"
        inherent = classify(c)
        setting = policies.get(key, {})
        risk = effective_risk(inherent["minimum"], setting.get("risk_override"))
        mode = setting.get("mode", "monitor")
        if not permitted_mode(mode, risk):
            mode = "monitor"  # Always fail closed after risk increases.
        out.append({**c, "key":key, "server_id":server_id, "risk":risk,
                    "minimum_risk":inherent["minimum"],"risk_reasons":inherent["reasons"],
                    "mode":mode,"notes":setting.get("notes", "")})
    for s in servers:
        try:
            d = datetime.fromisoformat(str(s.get("collected_at", "")).replace("Z", "+00:00"))
            s["age_seconds"] = max(0, int((now-d).total_seconds()))
        except ValueError:
            s["age_seconds"] = None
        s["online"] = s["age_seconds"] is not None and s["age_seconds"] < settings["offline_after_seconds"]
        s["container_count"] = sum(1 for a in out if a["server_id"] == s["id"])
    return {"version":"0.6.0-dev", "servers":servers, "services":out,
            "settings":settings, "agents":agents,
            "events":recent_events(20), "execution_enabled":False,
            "note":"Updatebeleid wordt opgeslagen; deze versie voert geen updates uit."}


@app.on_event("startup")
def startup():
    if not AUTH_HASH:
        raise RuntimeError("DASHBOARD_PASSWORD_HASH is verplicht; dashboard start niet zonder authenticatie")
    init_db()


@app.get("/")
def home(_: Annotated[None, Depends(require_admin)]):
    return FileResponse(ROOT / "templates" / "index.html")


@app.get("/api/state")
def api_state(_: Annotated[None, Depends(require_admin)]):
    return build_state()


@app.get("/api/diagnostics")
def api_diagnostics(service_key: str = Query(min_length=3, max_length=240),
                    _: Annotated[None, Depends(require_admin)] = None):
    """Read-only evidence summary for a selected visible service.

    No logs or secrets, and never any remote action. A user must approve
    copying the resulting summary into a separate ChatGPT conversation.
    """
    state = build_state()
    item = next((s for s in state["services"] if s["key"] == service_key), None)
    if item is None:
        raise HTTPException(404, "Dienst niet gevonden")
    host = next((h for h in state["servers"] if h["id"] == item["server_id"]), None)
    if host is None:
        raise HTTPException(404, "Host niet gevonden")
    return build_diagnosis(item, host)


@app.post("/api/policies")
def api_policy(form: PolicyIn, request: Request, _: Annotated[None, Depends(require_admin)]):
    guard_mutation(request)
    state = build_state()
    item = next((x for x in state["services"] if x["key"] == form.service_key), None)
    if item is None:
        raise HTTPException(404, "Dienst niet gevonden")
    if form.risk_override not in (None, *LEVELS):
        raise HTTPException(422, "Ongeldig risiconiveau")
    selected = effective_risk(item["minimum_risk"], form.risk_override)
    if not permitted_mode(form.mode, selected):
        raise HTTPException(422, "Automatisch bijwerken alleen voor laag risico; uitvoering bovendien uitgeschakeld")
    put_policy(form.service_key, selected, form.mode, form.notes)
    return {"saved":True, "effective_risk":selected, "execution_enabled":False}


@app.post("/api/agents")
def api_create_agent(form: AgentIn, request: Request, _: Annotated[None, Depends(require_admin)]):
    guard_mutation(request)
    return new_agent(form.label)


@app.post("/api/ingest/{agent_id}")
async def ingest(agent_id: str, request: Request):
    agent = agent_info(agent_id)
    if not agent:
        raise HTTPException(404, "Unknown agent")
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    if not hmac.compare_digest(digest, agent["token_hash"]):
        raise HTTPException(403, "Invalid token")
    body = await request.body()
    if len(body) > 256_000:
        raise HTTPException(413, "Report too large")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(422, "Invalid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(422, "Invalid report")
    collected = parse_timestamp(payload.get("collected_at"))
    report = {"collected_at":collected, "containers":clean_containers(payload.get("containers",[])),
              "memory":payload.get("memory",{}), "disk_root":payload.get("disk_root",{}),
              "platform":str(payload.get("platform") or "unknown")[:32],
              "capabilities":[c for c in payload.get("capabilities",[]) if isinstance(c,str)][:16]
                            if isinstance(payload.get("capabilities",[]),list) else []}
    save_report(agent_id, report)
    return {"ok":True, "received":len(report["containers"])}


@app.get("/healthz")
def health():
    return {"status":"live"}


@app.post("/api/settings")
def api_update_settings(form: DashboardSettingsIn, request: Request,
                        _: Annotated[None, Depends(require_admin)]):
    guard_mutation(request)
    put_settings(form.model_dump())
    return {"saved": True, "settings": get_settings()}


@app.patch("/api/agents/{agent_id}")
def api_update_agent(agent_id: str, form: AgentSettingsIn, request: Request,
                     _: Annotated[None, Depends(require_admin)]):
    guard_mutation(request)
    if not update_agent(agent_id, form.label, form.scan_interval):
        raise HTTPException(404, "Agent not found")
    return {"saved": True}


@app.delete("/api/agents/{agent_id}")
def api_delete_agent(agent_id: str, request: Request,
                     _: Annotated[None, Depends(require_admin)]):
    guard_mutation(request)
    if not delete_agent(agent_id):
        raise HTTPException(404, "Agent not found")
    return {"deleted": True}


@app.get("/api/agent-config/{agent_id}")
def api_agent_config(agent_id: str, request: Request):
    # Only the agent's own token permits access to this safe cadence setting.
    agent = agent_info(agent_id)
    if agent is None:
        raise HTTPException(404, "Unknown agent")
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    if not hmac.compare_digest(digest, agent["token_hash"]):
        raise HTTPException(403, "Invalid agent token")
    return {"scan_interval": max(60, min(3600, int(agent["scan_interval"])))}
