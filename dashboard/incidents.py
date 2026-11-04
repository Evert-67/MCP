"""Cross-service incident correlation for CodePug's compact control center.

Signals are grouped by HOST, not assumed to share a root cause. This logic
does no network inspection, no recovery and no autonomous diagnosis.
"""
from __future__ import annotations
import hashlib

VALID = {"high", "review", "unknown"}


def _incident(host_id: str, code: str, title: str, severity: str,
              evidence: list[str], next_step: str, services: list[str],
              scope: str = "single", hypothesis: str = "") -> dict:
    # Stable IDs for basic incident continuity; no secrets in identifiers.
    digest = hashlib.sha256(f"{host_id}:{code}".encode()).hexdigest()[:14]
    return {
        "id": f"inc-{digest}", "host_id": host_id[:120], "code": code,
        "title": title[:140], "severity": severity if severity in VALID else "unknown",
        "scope": scope, "hypothesis": hypothesis[:360],
        "evidence": [str(e)[:260] for e in evidence[:6]],
        "affected_services": [str(s)[:120] for s in services[:30]],
        "next_step": next_step[:500], "root_cause_confirmed": False,
        "requires_approval": True, "execution_enabled": False,
    }


def build_incidents(state: dict) -> dict:
    """Use each host's measured status, local probes and service health."""
    hosts = state.get("servers") or []
    services = state.get("services") or []
    items = []
    for host in hosts:
        hid = str(host.get("id") or "")
        label = str(host.get("label") or "Onbekende host")[:100]
        own = [s for s in services if s.get("server_id") == hid]
        if not host.get("online"):
            items.append(_incident(
                hid, "host-snapshot-stale", f"{label}: hostmeting ontbreekt",
                "high", ["De host-inventaris is verouderd of ontbreekt."],
                "Controleer eerst scanner, netwerkpad en timestamp op deze host. "
                "Een ontbrekende meting bewijst niet dat Linux offline is.",
                [s.get("name", "") for s in own], scope="host",
                hypothesis="Collector of netwerkpad kan het gedeelde probleem zijn."
            ))
            # Don't multiply stale Docker state into false per-service incidents.
            continue

        measured = host.get("host_health") or {}
        linux = measured.get("linux") or {}
        docker = measured.get("docker") or {}
        probes = measured.get("app_checks") or []
        failed = [p for p in probes if p.get("status") in {"unreachable", "error"}]
        if len(failed) >= 2:
            items.append(_incident(
                hid, "app-probe-cluster",
                f"{label}: meerdere applicaties onbereikbaar",
                "high",
                [f"{len(failed)} lokale app-probes melden een fout of geen HTTP-respons."],
                "Vergelijk hun poorten, DNS/reverse proxy, netwerkbereikbaarheid "
                "vanuit de juiste host en het Docker-netwerk. Controleer pas "
                "daarna individuele app-logs.",
                [p.get("name", "") for p in failed],
                scope="shared-symptom",
                hypothesis="Mogelijke gedeelde afhankelijkheid of netwerkstoring; "
                           "een gezamenlijke oorzaak is nog NIET bewezen."
            ))
        elif len(failed) == 1:
            p = failed[0]
            items.append(_incident(
                hid, "app-probe-" + str(p.get("id", ""))[:48],
                f"{p.get('name', 'Applicatie')}: HTTP-controle afwijkend",
                "high", [f"Lokale HTTP-status: {p.get('status')}."],
                "Controleer of de webapp bereikbaar is vanaf dezelfde netwerkbron "
                "als de foutmelding, inclusief proxy, poort en authenticatie.",
                [p.get("name", "")], scope="single"
            ))
        if linux.get("system_state") == "degraded":
            items.append(_incident(
                hid, "linux-degraded", f"{label}: Linux meldt degraded", "high",
                ["systemctl is-system-running retourneert degraded."],
                "Bekijk systemctl --failed en gerichte journallogs (read-only).",
                [], scope="host"
            ))
        if docker.get("daemon_active") is False:
            items.append(_incident(
                hid, "docker-inactive", f"{label}: Docker-daemon niet actief",
                "high", ["systemd meldt dat Docker niet actief is."],
                "Controleer Docker-units, netwerk en afhankelijkheden; geen blinde herstart.",
                [s.get("name", "") for s in own], scope="platform"
            ))
            # If Docker is down, individual stopped states can be secondary.
        else:
            for s in own:
                name = str(s.get("name") or "Dienst")[:120]
                status = str(s.get("status") or "").lower()
                if "unhealthy" in status:
                    items.append(_incident(
                        hid, "unhealthy-" + name, name + ": Docker unhealthy", "high",
                        [f"Containerstatus: {str(s.get('status', ''))[:180]}"],
                        "Controleer healthcheck, logs en afhankelijke diensten; "
                        "niet zonder diagnose herstarten.", [name]
                    ))
                elif s.get("state") in {"exited", "dead", "created"}:
                    items.append(_incident(
                        hid, "stopped-" + name, name + ": gestopt", "review",
                        [f"Containerstatus: {str(s.get('status', ''))[:180]}"],
                        "Bevestig eerst of deze container bewust uitgeschakeld is. "
                        "Dit is nog geen bewezen storing.", [name]
                    ))
        if linux.get("reboot_required") is True:
            items.append(_incident(
                hid, "reboot-required", label + ": herstart gepland?", "review",
                ["Het hostbestand /run/reboot-required bestaat."],
                "Controleer afhankelijkheden en back-upstatus, plan een onderhoudsvenster.",
                [], scope="host"
            ))
    order = {"high": 0, "review": 1, "unknown": 2}
    items.sort(key=lambda e: (order[e["severity"]], e["host_id"], e["title"]))
    return {
        "read_only": True, "execution_enabled": False,
        "root_causes_verified": False, "incidents": items[:150],
        "summary": {
            "high": sum(i["severity"] == "high" for i in items),
            "review": sum(i["severity"] == "review" for i in items),
            "grouped": sum(i["scope"] in ("host", "platform", "shared-symptom") for i in items),
        },
        "notice": "Groepen zijn vermoedens op basis van meetgegevens, geen bewezen root-cause. "
                  "Bij ontbrekende agentinformatie zijn netwerkconflicten en softwarefouten "
                  "niet volledig te detecteren.",
    }
