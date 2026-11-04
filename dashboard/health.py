"""Cross-layer, evidence-based host assessment for CodePug.

No shell, Docker socket, mutation runner, remote check or AI call.
An observation is not a confirmed root cause. Unknown stays unknown.
"""
from __future__ import annotations


def item(code: str, severity: str, subject: str, observation: str,
         recommendation: str, source: str) -> dict:
    return {"code": code, "severity": severity, "subject": subject[:120],
            "observation": observation[:250],
            "recommendation": recommendation[:350], "source": source,
            "execution_enabled": False}


def assess_host(host: dict, services: list[dict]) -> dict:
    findings = []
    evidence = host.get("host_health")
    snapshot_online = host.get("online") is True
    linux = (evidence or {}).get("linux") or {}
    docker = (evidence or {}).get("docker") or {}
    app_checks = (evidence or {}).get("app_checks") or []
    if not snapshot_online:
        findings.append(item(
            "host-stale", "high", host.get("label", "Host"),
            "De laatste hostmeting is verouderd of ontbreekt.",
            "Controleer de agent of snapshotcollector en netwerkverbinding. "
            "Een offline melding bewijst niet dat de host is uitgeschakeld.",
            "snapshot"))
    if not evidence:
        findings.append(item(
            "host-evidence-missing", "unknown", host.get("label", "Host"),
            "Deze bron verzamelt nog geen Linux-/Docker-pakket- en applicatiemetingen.",
            "Installeer of activeer op deze host een beperkte read-only CodePug-agent. "
            "Geen automatische herstelactie mogelijk.",
            "collector-coverage"))
    else:
        if linux.get("system_state") == "degraded":
            findings.append(item(
                "linux-degraded", "high", host.get("label", "Host"),
                "systemd meldt degraded; de oorzaak is nog onbekend.",
                "Controleer systemctl --failed en de betrokken unitlogs, read-only.",
                "agent-systemd"))
        if linux.get("system_state") not in ("running", "degraded", "unknown", ""):
            findings.append(item(
                "linux-state", "review", host.get("label", "Host"),
                "systemd-status: " + str(linux.get("system_state")),
                "Bekijk of dit een verwachte onderhoudsstatus is.",
                "agent-systemd"))
        if linux.get("reboot_required") is True:
            findings.append(item(
                "linux-reboot-pending", "review", host.get("label", "Host"),
                "Linux meldt dat een herstart nodig is.",
                "Plan na back-up- en herstelcontrole een onderhoudsvenster; "
                "start de host niet automatisch opnieuw.",
                "agent-reboot"))
        updates = linux.get("updates_available")
        if type(updates) is int and updates > 0:
            findings.append(item(
                "linux-packages", "review", host.get("label", "Host"),
                f"{updates} APT-pakketupdates zichtbaar in de lokale pakketcache.",
                "Controleer security-impact en afhankelijkheden. Eerst back-up, "
                "dan goedgekeurde updates; de pakketcache is niet automatisch vernieuwd.",
                "agent-apt-cache"))
        if docker.get("daemon_active") is False:
            findings.append(item(
                "docker-inactive", "high", host.get("label", "Host"),
                "De lokale Docker-service is niet actief volgens systemd.",
                "Controleer Docker-service en logs; geen blinde herstart.",
                "agent-systemd"))
        if docker.get("apt_package_update_available") is True:
            packages = docker.get("apt_pending_packages") or []
            findings.append(item(
                "docker-package-update", "review", host.get("label", "Host"),
                "APT heeft nieuwere versies in de cache voor: " +
                ", ".join(str(p) for p in packages[:5]),
                "Controleer de Docker-release, back-up, compatibiliteit en "
                "de herstartimpact. APT-cache is mogelijk verouderd.",
                "agent-apt-cache"))
    for check in app_checks:
        status = check.get("status")
        if status in ("error", "unreachable"):
            findings.append(item(
                "app-probe-"+str(check.get("id", ""))[:48], "high",
                check.get("name", "Applicatie"),
                "Geconfigureerde localhost-beschikbaarheidstest: " + status,
                "Controleer vanuit dezelfde host poort, reverse proxy, "
                "authenticatie en applicatielogs. Containerstatus alleen is onvoldoende.",
                "agent-loopback-http"))
        elif status == "auth_required":
            findings.append(item(
                "app-auth-"+str(check.get("id", ""))[:48], "review",
                check.get("name", "Applicatie"),
                "De applicatie reageert met 401/403; bereikbaar maar niet functioneel geverifieerd.",
                "Gebruik later een specifieke beperkte API-integratie met gescheiden secrets.",
                "agent-loopback-http"))
    for svc in services:
        name = str(svc.get("name", "Dienst"))[:120]
        status = str(svc.get("status", ""))
        state = str(svc.get("state", "")).lower()
        if "unhealthy" in status.lower():
            findings.append(item(
                "container-unhealthy", "high", name,
                "Docker meldt unhealthy; proces kan nog draaien.",
                "Bekijk de Docker-healthcheck, toegestane logs en afhankelijke diensten.",
                "docker-inventory"))
        elif state in ("exited", "dead", "created") or "exited" in status.lower():
            findings.append(item(
                "container-stopped", "review", name,
                "Container is gestopt; gewenste toestand is onbekend.",
                "Controleer eerst of de container bewust is uitgezet. "
                "Niet automatisch starten of verwijderen.",
                "docker-inventory"))
        update = svc.get("update") or {}
        if update.get("status") == "candidate":
            findings.append(item(
                "version-candidate", "review", name,
                "Een nieuwer tag- of releasenummer is gevonden, "
                "maar compatibiliteit is niet vastgesteld.",
                "Vergelijk release-notes, image-architectuur, back-up en "
                "geïnstalleerde versie vóór toestemming voor een update.",
                "read-only-release"))
        if update.get("status") == "release_found":
            findings.append(item(
                "release-unverified", "unknown", name,
                "Officiële software-release gevonden, geïnstalleerde versie onbekend.",
                "Controleer de daadwerkelijk draaiende applicatieversie of image-digest; "
                "een :latest-tag bewijst geen updatebehoefte.",
                "read-only-release"))
    high = sum(f["severity"] == "high" for f in findings)
    review = sum(f["severity"] == "review" for f in findings)
    return {
        "id": host.get("id", ""),
        "label": host.get("label", ""),
        "online": snapshot_online,
        "agent_evidence": bool(evidence),
        "linux": linux if evidence else None,
        "docker": docker if evidence else None,
        "app_checks": app_checks,
        "service_count": len(services),
        "app_checks_count": len(app_checks),
        "high_count": high,
        "review_count": review,
        "findings": findings[:80],
        "status": "attention" if high else "review" if review else
                  "partial" if not evidence or not app_checks else "no_issues_detected",
        "fully_verified": False,
    }


def build_health_overview(state: dict) -> dict:
    hosts = state.get("servers") or []
    services = state.get("services") or []
    entries = [
        assess_host(host, [service for service in services
                           if service.get("server_id") == host.get("id")])
        for host in hosts
    ]
    return {
        "read_only": True,
        "execution_enabled": False,
        "diagnosis_complete": False,
        "hosts": entries,
        "summary": {
            "hosts": len(entries),
            "hosts_with_deep_evidence": sum(h["agent_evidence"] for h in entries),
            "app_probes": sum(h["app_checks_count"] for h in entries),
            "high_findings": sum(h["high_count"] for h in entries),
            "review_findings": sum(h["review_count"] for h in entries),
        },
        "notice": (
            "Dit zijn aanwijzingen uit snapshots en lokale read-only checks, "
            "geen bewezen oorzaken. Geen update of herstelactie uitgevoerd. "
            "Back-up en herstelbaarheid zijn niet geverifieerd."
        )
    }
