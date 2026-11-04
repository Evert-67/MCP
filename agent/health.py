"""Read-only Linux and Docker host checks for a local CodePug agent.

No privileged actions, no apt update/upgrade, no systemctl start/stop, and no
remote shell. The host agent must be explicitly installed on each host.
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_ALLOWED_STATES = {"running", "degraded", "starting", "stopping", "maintenance", "offline", "unknown"}
_VERSION = re.compile(r"^[a-zA-Z0-9.()+_~:-]{1,64}$")
_ID = re.compile(r"^[a-zA-Z0-9_-]{1,48}$")
_PATH = re.compile(r"^/[a-zA-Z0-9/_?.=&%-]{0,120}$")


def command(*argv: str, timeout: int = 3) -> tuple[bool, str]:
    """Execute only fixed program/arguments supplied in this module."""
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, check=False,
            timeout=timeout, stdin=subprocess.DEVNULL
        )
        return result.returncode == 0, result.stdout[:65_536].strip()
    except (OSError, subprocess.TimeoutExpired, UnicodeError):
        return False, ""


def os_release(path: Path = Path("/etc/os-release")) -> dict:
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    result = {}
    for row in rows:
        if "=" not in row or row.lstrip().startswith("#"):
            continue
        key, value = row.split("=", 1)
        if key in {"ID", "VERSION_ID", "PRETTY_NAME"}:
            result[key] = value.strip().strip('"')[:100]
    return result


def apt_updates() -> dict:
    """Use current APT cache ONLY; never refresh lists or install updates."""
    if not Path("/usr/bin/apt").exists():
        return {"status": "unavailable", "count": None, "security_count": None}
    ok, output = command("apt", "list", "--upgradable", timeout=10)
    if not ok:
        return {"status": "unavailable", "count": None, "security_count": None}
    items = [line for line in output.splitlines()
             if line and not line.lower().startswith("listing")]
    # The mirror/pocket names do not guarantee that all security fixes
    # are fully classified. Treat security count as a lower-bound indicator.
    security = sum("-security" in line.split(" ", 1)[0] for line in items)
    return {"status": "cached", "count": min(len(items), 100_000),
            "security_count": min(security, 100_000)}


def _version(command_args: tuple[str, ...]) -> str | None:
    ok, output = command(*command_args, timeout=4)
    candidate = output.splitlines()[0].strip()[:64] if ok and output else ""
    return candidate if _VERSION.fullmatch(candidate) else None


def host_health() -> dict:
    if platform.system().lower() != "linux":
        return {"linux": {"scan_status": "unsupported"},
                "docker": {"scan_status": "unsupported"}, "app_checks": []}
    distro = os_release()
    ok_system, system = command("systemctl", "is-system-running", timeout=4)
    # systemctl exits nonzero for "degraded"; stdout is still meaningful.
    system = system.strip().lower()
    if system not in _ALLOWED_STATES:
        system = "unknown"
    ok_docker, docker_active = command("systemctl", "is-active", "docker", timeout=4)
    docker_status = docker_active.strip().lower()
    docker_active_bool = True if ok_docker and docker_status == "active" else (
        False if docker_status in {"inactive", "failed"} else None
    )
    packages = apt_updates()
    return {
        "linux": {
            "scan_status": "read_only",
            "distro": str(distro.get("ID", "unknown"))[:32],
            "version": str(distro.get("VERSION_ID", ""))[:32],
            "pretty_name": str(distro.get("PRETTY_NAME", ""))[:100],
            "kernel": platform.release()[:64],
            "system_state": system,
            "reboot_required": Path("/run/reboot-required").exists(),
            "package_cache_status": packages["status"],
            "updates_available": packages["count"],
            "security_updates_lower_bound": packages["security_count"],
        },
        "docker": {
            "scan_status": "read_only",
            "daemon_active": docker_active_bool,
            "server_version": _version(("docker", "version", "--format", "{{.Server.Version}}")),
            "client_version": _version(("docker", "version", "--format", "{{.Client.Version}}")),
            "compose_version": _version(("docker", "compose", "version", "--short")),
            "engine_latest_verified": False,
        },
        "app_checks": [],
    }


def load_local_checks(path: str | None) -> list[dict]:
    """Optional local-only probe manifest, never received from the hub.

    Only explicit loopback HTTP ports/paths; no arbitrary URLs, credentials,
    hostnames, redirects, link-local or metadata service access.
    """
    if not path:
        return []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return []
    if not isinstance(data, list):
        return []
    result = []
    for raw in data[:24]:
        if not isinstance(raw, dict):
            continue
        check_id = raw.get("id")
        title = raw.get("name")
        port = raw.get("port")
        route = raw.get("path", "/")
        if (not isinstance(check_id, str) or not _ID.fullmatch(check_id)
                or not isinstance(title, str) or not 1 <= len(title) <= 80
                or type(port) is not int or not 1 <= port <= 65535
                or not isinstance(route, str) or not _PATH.fullmatch(route)):
            continue
        result.append({"id": check_id, "name": title, "port": port, "path": route})
    return result


class _NoRedirect:
    """Attached by urllib opener, never follow a redirect to another host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_local_http(config: dict) -> dict:
    """HTTP status of configured localhost port. A 200 isn't a deep health test."""
    from urllib.request import build_opener, HTTPRedirectHandler

    class RejectRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    endpoint = "http://127.0.0.1:" + str(config["port"]) + config["path"]
    started = time.monotonic()
    status = "unknown"
    code = None
    try:
        opener = build_opener(RejectRedirect)
        request = Request(endpoint, method="GET",
                          headers={"User-Agent": "CodePugHostProbe/0.7"})
        with opener.open(request, timeout=2.5) as response:
            code = response.status
    except HTTPError as exc:
        code = exc.code
    except (OSError, URLError, TimeoutError, ValueError):
        pass
    if code is not None:
        if 200 <= code < 300:
            status = "reachable"
        elif code in (401, 403):
            status = "auth_required"
        elif code in (500, 502, 503, 504):
            status = "error"
        else:
            status = "review"
    elif code is None:
        status = "unreachable"
    return {
        "id": config["id"], "name": config["name"],
        "status": status, "http_status": code,
        "latency_ms": min(10_000, max(0, int((time.monotonic() - started) * 1000))),
        "source": "loopback-http",
        "note": "Beschikbaarheidstest, geen volledige functionele applicatietest",
    }


def collect_host_health() -> dict:
    result = host_health()
    config = load_local_checks(os.getenv("CODEPUG_HEALTH_CHECKS_FILE"))
    result["app_checks"] = [check_local_http(item) for item in config]
    return result
