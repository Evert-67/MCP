"""Read-only Backup & Recovery planning for CodePug v0.7.

This module deliberately does NOT enumerate host files, run backup tools,
inspect volume contents, verify restores or perform any recovery actions.
A Docker status snapshot is NOT evidence that a backup exists or works.
"""
from __future__ import annotations

from .diagnostics import one_line


def build_recovery_overview(state: dict) -> dict:
    """Return inventory coverage, never inferred backup or redundancy success."""
    hosts = state.get("servers") or []
    services = state.get("services") or []
    entries = []
    for host in hosts:
        server_id = str(host.get("id", ""))[:100]
        related = [s for s in services if s.get("server_id") == server_id]
        entries.append({
            "id": server_id,
            "label": one_line(host.get("label", "Onbekende host"), 80),
            "online": bool(host.get("online")),
            "last_seen_seconds": host.get("age_seconds"),
            "service_count": len(related),
            "critical_services": sum(s.get("risk") == "critical" for s in related),
            "backup_status": "unknown",
            "restore_test_status": "not_tested",
            "redundancy_status": "not_verified",
            "recovery_ready": False,
        })
    return {
        "version": "0.7.0-dev",
        "read_only": True,
        "execution_enabled": False,
        "backup_integrations_enabled": False,
        "backup_count": None,
        "verified_backup_count": None,
        "restore_tests_passed": None,
        "automatic_failover_enabled": False,
        "hosts": entries,
        "notice": (
            "CodePug heeft nog geen back-upbron aangesloten. Back-ups, herstelbaarheid "
            "en redundantie zijn onbekend, niet gezond of gegarandeerd."
        ),
    }


def build_recovery_plan(service: dict, host: dict) -> dict:
    """Give an explicit human review checklist, NOT an executable playbook."""
    name = one_line(service.get("name", ""), 120)
    host_label = one_line(host.get("label", ""), 80)
    status = one_line(service.get("status", "onbekend"), 140)
    risk = one_line(service.get("risk", "onbekend"), 20)
    online = bool(host.get("online"))
    prerequisites = [
        {"id": "inventory", "label": "Actuele toestand en afhankelijkheden controleren",
         "status": "not_verified"},
        {"id": "backup", "label": "Controleer dat er een geschikte back-up bestaat",
         "status": "not_verified"},
        {"id": "restore", "label": "Back-up op aparte omgeving terugzetten en testen",
         "status": "not_verified"},
        {"id": "impact", "label": "Impact, onderhoudsvenster en terugvalplan vastleggen",
         "status": "not_verified"},
        {"id": "approval", "label": "Expliciete goedkeuring van bevoegde beheerder",
         "status": "not_approved"},
    ]
    return {
        "host": host_label,
        "service": name,
        "status": status,
        "risk": risk,
        "host_online": online,
        "report_type": "planning_only",
        "ready_for_recovery": False,
        "backup_verified": False,
        "restore_tested": False,
        "redundancy_verified": False,
        "execution_enabled": False,
        "prerequisites": prerequisites,
        "proposed_steps": [
            "Bepaal eerst of het probleem werkelijk een herstelactie vereist.",
            "Verzamel alleen toegestane logs en controleer actuele systeemstatus.",
            "Identificeer opslagvolumes, databases en gekoppelde afhankelijkheden.",
            "Verifieer back-upbestanden en voer een afzonderlijke restore-test uit.",
            "Beschrijf de exacte herstelactie en mogelijke gevolgen.",
            "Vraag een specifieke, tijdgebonden goedkeuring.",
            "Voer pas later via een afzonderlijk beveiligde herstelagent uit.",
            "Controleer na afloop beschikbaarheid, dataconsistentie en auditlog.",
        ],
        "warning": (
            "Geen back-up, restore-test of redundantie is vastgesteld. "
            "Dit rapport kan geen dienst herstarten, verwijderen of herstellen."
        ),
    }
