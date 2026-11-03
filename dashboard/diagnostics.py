"""Read-only, minimal diagnostic handoff for a selected service.

No Docker API, logs, passwords, notes or environment variables are accessed here.
A human must explicitly choose to copy the report to a separate AI conversation.
"""
from __future__ import annotations
import re

def one_line(value, limit: int) -> str:
    """Do not allow a host-provided label to smuggle extra report instructions."""
    return re.sub(r"[\\x00-\\x1f\\x7f]+", " ", str(value))[:limit]


def build_diagnosis(service: dict, host: dict) -> dict:
    """Build a bounded incident snapshot from the existing sanitized inventory."""
    name = one_line(service.get("name", ""), 120)
    host_name = one_line(host.get("label", ""), 80)
    status = one_line(service.get("status", "unknown"), 140)
    state = one_line(service.get("state", "unknown"), 50)
    risk = one_line(service.get("risk", "unknown"), 20)
    online = bool(host.get("online"))
    age = host.get("age_seconds")
    unhealthy = "unhealthy" in status.lower()
    running = state == "running" or status.lower().startswith("up ")

    if not online:
        code = "stale"
        summary = "De laatste hostmeting is te oud of de host is niet bereikbaar."
        checks = [
            "Controleer de verbinding en wanneer de scanner voor het laatst draaide.",
            "Bevestig de actuele toestand op de host voordat je acties uitvoert.",
        ]
    elif unhealthy:
        code = "unhealthy"
        summary = "De container draait, maar de healthcheck meldt een probleem."
        checks = [
            "Controleer de Docker-healthcheck en de recente logs via een bevoegde connector.",
            "Controleer afhankelijkheden, schijfruimte en geheugen.",
            "Stel pas een herstart voor nadat de oorzaak en impact zijn beoordeeld.",
        ]
    elif not running:
        code = "stopped"
        summary = "De container draait niet. Het kan ook een bewust uitgeschakelde dienst zijn."
        checks = [
            "Controleer eerst of de dienst bewust is gestopt.",
            "Controleer de exitstatus en recente logs via een bevoegde connector.",
            "Controleer afhankelijkheden en een eventuele back-up vóór herstel.",
        ]
    else:
        code = "running"
        summary = "De container staat als actief gemeld; er is geen bekende healthcheck-fout."
        checks = [
            "Controleer de toepassingsfunctie voordat je concludeert dat alles werkt.",
            "Controleer desgewenst logs en beschikbaarheid via een bevoegde connector.",
        ]

    age_text = f"{int(age)} seconden" if isinstance(age, (int, float)) and 0 <= age <= 10_000_000 else "onbekend"
    report = (
        "Onderzoek deze CodePug-servicestatus. Voer uitsluitend read-only controles uit; "
        "stel herstelacties eerst ter goedkeuring voor.\n\n"
        f"Host: {host_name}\n"
        f"Dienst: {name}\n"
        f"Toestand: {status}\n"
        f"Risicoklasse: {risk}\n"
        f"Host online volgens scanner: {'ja' if online else 'nee'}\n"
        f"Leeftijd laatste meting: {age_text}\n"
        "Beschikbare logs: niet bijgevoegd\n"
        "Back-up en herstelbaarheid: niet geverifieerd\n"
        "Uitvoering: uitgeschakeld\n\n"
        "Geef een waarschijnlijke oorzaak, benoem ontbrekend bewijs en maak een "
        "stapsgewijs onderzoeksplan. Gebruik de bestaande MCP-verbinding alleen "
        "indien beschikbaar en bevoegd; veronderstel geen toegang."
    )
    return {
        "code": code,
        "summary": summary,
        "checks": checks,
        "service": name,
        "host": host_name,
        "status": status,
        "risk": risk,
        "age_seconds": age,
        "logs_included": False,
        "backup_verified": False,
        "execution_enabled": False,
        "handoff": report,
    }
