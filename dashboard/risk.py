"""Risk classification: explicit policy cannot lower built-in hard safety floors."""
from __future__ import annotations

LEVELS = ("low", "medium", "high", "critical")
CRITICAL_TOKENS = ("mariadb", "mysql", "postgres", "database", "mongo", "vault", "redis", "valkey")
HIGH_TOKENS = ("immich", "pihole", "portainer", "codepug", "traefik", "nginx", "caddy", "ollama", "supertokens")


def classify(container: dict) -> dict:
    name = str(container.get("name") or container.get("Names") or "").lower()
    image = str(container.get("image") or container.get("Image") or "").lower()
    status = str(container.get("status") or container.get("Status") or "").lower()
    state = str(container.get("state") or container.get("State") or "").lower()
    socket = bool(container.get("docker_socket"))
    persistent = bool(container.get("persistent"))
    latest = image.endswith(":latest") or ":latest@" in image
    reasons: list[str] = []
    level = 0

    def floor(v: int, reason: str):
        nonlocal level
        level = max(level, v)
        reasons.append(reason)

    if latest:
        floor(1, "Mutabele image-tag :latest")
    if persistent:
        floor(1, "Persistente opslag gekoppeld")
    if "unhealthy" in status:
        floor(2, "Healthcheck meldt unhealthy")
    if socket:
        floor(2, "Toegang tot Docker-socket")
    if any(token in name or token in image for token in HIGH_TOKENS):
        floor(2, "Belangrijke infrastructuurdienst")
    if any(token in name or token in image for token in CRITICAL_TOKENS):
        floor(3, "Database of gevoelig opslagonderdeel")
    if "exited" in state or "exited" in status:
        reasons.append("Container is gestopt")
    return {"minimum": LEVELS[level], "reasons": reasons}


def effective_risk(minimum: str, requested: str | None) -> str:
    requested = requested if requested in LEVELS else minimum
    return LEVELS[max(LEVELS.index(minimum), LEVELS.index(requested))]


def permitted_mode(mode: str, minimum: str) -> bool:
    # v0.5 is monitoring/configuration only: 'auto' records intent, no executor.
    if mode not in ("monitor", "approve", "auto"):
        return False
    return not (mode == "auto" and minimum != "low")
