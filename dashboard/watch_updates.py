"""CodePug version watcher: independent, opt-in, read-only background checks.

This process runs WITHOUT an HTTP endpoint, Docker socket, SSH capability,
registry credentials, mutation runner or restart permissions. It only reads
the inventory and performs bounded public Docker Hub requests when enabled.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from .storage import all_update_checks, get_settings, init_db, save_update_check
from .updates import check_public_docker_hub, reference

log = logging.getLogger("codepug.watch_updates")
POLL_SECONDS = 60
MAX_UNIQUE_IMAGES_PER_CYCLE = 4


def parse_time(value: str | None) -> datetime | None:
    try:
        if not value:
            return None
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def due_images(services: list[dict], checks: dict, interval_hours: int,
               now: datetime, limit: int = MAX_UNIQUE_IMAGES_PER_CYCLE) -> dict[str, list[dict]]:
    """Return due, grouped image refs; avoids duplicate HTTP checks per service.

    All service identities are resolved from the sanitized inventory only.
    """
    result = {}
    threshold = now - timedelta(hours=interval_hours)
    for service in services:
        key = service.get("key")
        image = service.get("image")
        if not isinstance(key, str) or not isinstance(image, str):
            continue
        stored = checks.get(key) or {}
        if stored.get("image_ref") == image:
            checked_at = parse_time(stored.get("checked_at"))
            if checked_at and checked_at > threshold:
                continue
        if image in result:
            result[image].append(service)
        elif len(result) < limit:
            result[image] = [service]
    return result


def run_cycle(*, get_state=None, checker=check_public_docker_hub,
              now: datetime | None = None) -> dict:
    """A bounded synchronous pass. No network requests until opted in."""
    settings = get_settings()
    if not settings.get("auto_version_checks", False):
        return {"enabled": False, "checked": 0, "candidates": 0}
    interval = max(6, min(168, int(settings.get("version_check_interval_hours", 24))))
    if get_state is None:
        # Import lazily so unit tests need not initialize FastAPI.
        from .app import build_state
        get_state = build_state
    state = get_state()
    now = now or datetime.now(timezone.utc)
    checks = all_update_checks()
    # A stale/offline inventory is not evidence of what a host currently runs.
    online_hosts = {host["id"] for host in state.get("servers", [])
                    if host.get("online") is True}
    eligible = [service for service in state.get("services", [])
                if service.get("server_id") in online_hosts]
    due = due_images(eligible, checks, interval, now)
    checked = candidates = 0
    for image, services in due.items():
        result = checker(image)
        for service in services:
            save_update_check(service["key"], image, result)
            checked += 1
            candidates += result.get("status") == "candidate"
    return {"enabled": True, "checked": checked, "candidates": candidates}


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    init_db()
    log.info("Watcher started; opt-in required in dashboard settings; no updates executed")
    while True:
        started = time.monotonic()
        try:
            result = run_cycle()
            if result["enabled"] and result["checked"]:
                log.info("Checked %s services; %s candidate tags found",
                         result["checked"], result["candidates"])
        except Exception:
            # No host secrets or service details are added to log exceptions.
            log.error("Version scan failed (%s)", "retry next cycle")
        time.sleep(max(5, POLL_SECONDS - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
