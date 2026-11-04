#!/usr/bin/env python3
"""Unprivileged *process* that reads Docker metadata via local Docker CLI then pushes to hub.

Docker group membership is powerful (root-equivalent). Run only on trusted hosts,
under a dedicated account with controlled local permissions. Never expose Docker TCP.
No environment variables, labels values, secret files or container logs are sent.
"""
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, timeout=20)


def scan():
    names = [x for x in docker("ps", "-a", "--format", "{{.Names}}").splitlines() if x]
    if len(names) > 500:
        raise RuntimeError("Te veel containers")
    records = []
    for name in names:
        d = json.loads(docker("inspect", name))[0]
        state = d.get("State", {})
        health = state.get("Health", {}).get("Status")
        state_name = state.get("Status", "unknown")
        labels = d.get("Config", {}).get("Labels") or {}
        mounts = d.get("Mounts") or []
        # Read only OCI image-version metadata already exposed by docker inspect.
        # Never forward arbitrary labels or environment variables.
        software_version = str(labels.get("org.opencontainers.image.version") or "")[:40]
        if not re.fullmatch(r"v?\d{1,3}\.\d{1,3}(?:\.\d{1,4})?", software_version):
            software_version = ""
        records.append({
            "software_version": software_version,
            "name": str(d.get("Name", "")).lstrip("/"),
            "image": d.get("Config", {}).get("Image", ""),
            "status": f"{state_name}{' (unhealthy)' if health == 'unhealthy' else ''}",
            "state": state_name,
            "project": labels.get("com.docker.compose.project", ""),
            "service": labels.get("com.docker.compose.service", ""),
            "docker_socket": any(m.get("Destination") == "/var/run/docker.sock" for m in mounts),
            "persistent": any(m.get("Destination") != "/var/run/docker.sock" for m in mounts),
        })
    memory = {}
    try:
        d = Path('/proc/meminfo').read_text()
        vals = dict((line.split(':')[0],int(line.split(':')[1].strip().split()[0])*1024)
                    for line in d.splitlines() if ':' in line)
        memory = {"total_bytes":vals.get('MemTotal',0),"available_bytes":vals.get('MemAvailable',0)}
    except (OSError, ValueError):
        pass
    try:
        disk = os.statvfs('/')
        disk_root = {"total_bytes":disk.f_blocks*disk.f_frsize,
                     "available_bytes":disk.f_bavail*disk.f_frsize}
    except (AttributeError, OSError):
        # Windows Docker hosts do not provide POSIX statvfs.
        disk_root = {}
    return {"collected_at":datetime.now(timezone.utc).isoformat(),
            "platform":platform.system().lower(),
            "capabilities":["docker-inventory"], "containers":records,
            "memory":memory, "disk_root":disk_root}


def main():
    url = os.environ["CODEPUG_HUB_URL"].rstrip('/')
    sid = os.environ["CODEPUG_AGENT_ID"]
    token = Path(os.environ["CODEPUG_TOKEN_FILE"]).read_text().strip()
    if not url.startswith('https://') and not (url.startswith('http://127.0.0.1:') or url.startswith('http://localhost:')):
        raise ValueError('Gebruik HTTPS naar de hub; onveilig HTTP is alleen op localhost toegestaan')
    req = Request(f"{url}/api/ingest/{sid}",data=json.dumps(scan(),separators=(',',':')).encode(),
                  headers={'content-type':'application/json','authorization':'Bearer '+token},method='POST')
    with urlopen(req,timeout=25) as r:
        print(r.read().decode())


def configured_interval():
    """Fetch only cadence via the agent's own token. No remote shell commands."""
    url = os.environ["CODEPUG_HUB_URL"].rstrip("/")
    if not url.startswith("https://") and not (
        url.startswith("http://127.0.0.1:") or url.startswith("http://localhost:")
    ):
        raise ValueError("HTTPS is required")
    sid = os.environ["CODEPUG_AGENT_ID"]
    token = Path(os.environ["CODEPUG_TOKEN_FILE"]).read_text().strip()
    req = Request(
        f"{url}/api/agent-config/{sid}",
        headers={"Authorization": "Bearer " + token},
    )
    with urlopen(req, timeout=15) as response:
        data = json.load(response)
    return max(60, min(3600, int(data.get("scan_interval", 120))))


if __name__ == '__main__':
    if sys.argv[1:] == ["--loop"]:
        while True:
            try:
                main()
            except Exception as exc:
                print(f"CodePug scan failed: {type(exc).__name__}: {exc}",
                      file=sys.stderr, flush=True)
            try:
                interval = configured_interval()
            except Exception:
                # Fail safe: no busy loop when the hub is unavailable.
                interval = 120
            time.sleep(interval)
    elif not sys.argv[1:]:
        try:
            main()
        except Exception as exc:
            print(f"CodePug scan failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            sys.exit(1)
    else:
        print("Usage: scan.py [--loop]", file=sys.stderr)
        sys.exit(2)
