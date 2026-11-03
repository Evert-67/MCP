#!/usr/bin/env python3
"""Unprivileged *process* that reads Docker metadata via local Docker CLI then pushes to hub.

Docker group membership is powerful (root-equivalent). Run only on trusted hosts,
under a dedicated account with controlled local permissions. Never expose Docker TCP.
No environment variables, labels values, secret files or container logs are sent.
"""
import json
import os
import subprocess
import sys
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
        records.append({
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
    disk = os.statvfs('/')
    return {"collected_at":datetime.now(timezone.utc).isoformat(),"containers":records,
            "memory":memory,"disk_root":{"total_bytes":disk.f_blocks*disk.f_frsize,
                                            "available_bytes":disk.f_bavail*disk.f_frsize}}


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

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f"CodePug scan mislukt: {type(e).__name__}: {e}",file=sys.stderr)
        sys.exit(1)
