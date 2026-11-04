"""Opt-in, read-only Docker Hub release tag checker.

This checks PUBLIC Docker Hub repositories only. It does not inspect running image
digests, architectures, Compose dependencies, release notes, or private registries.
A newer numbered tag is only a candidate to review, NEVER an install decision.
No Docker commands, registry credentials, or update execution are used.
"""
from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_PAGES = 2
TAG_PATTERN = re.compile(
    r"^(?P<v>v?)(?P<major>\d+)"
    r"(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?"
    r"(?P<variant>-(?:alpine|bookworm|bullseye|slim)(?:\d+(?:\.\d+)*)?)?$",
    re.I,
)
REPO_COMPONENT = re.compile(r"^[a-z0-9][a-z0-9._-]{0,119}$")


def reference(image: str) -> dict | None:
    """Parse only plain public Docker Hub references, no user-configured URLs."""
    if not image or len(image) > 240 or "@sha256:" in image:
        return None
    name, sep, tag = image.rpartition(":")
    if not sep or "/" in tag or not tag:
        return None
    parts = name.split("/")
    if parts[0] in {"docker.io", "index.docker.io", "registry-1.docker.io"}:
        parts = parts[1:]
    elif "." in parts[0] or ":" in parts[0] or parts[0] == "localhost":
        return None  # Never query a private registry through an inferred URL.
    if len(parts) == 1:
        namespace, repo = "library", parts[0]
    elif len(parts) == 2:
        namespace, repo = parts
    else:
        return None
    if not REPO_COMPONENT.fullmatch(namespace) or not REPO_COMPONENT.fullmatch(repo):
        return None
    if not TAG_PATTERN.fullmatch(tag):
        return None
    return {"repository": f"{namespace}/{repo}", "tag": tag}


def tag_key(tag: str):
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        return None
    parts = [int(match.group("major")),
             int(match.group("minor") or "0"),
             int(match.group("patch") or "0")]
    # Keep v-prefix and OS-flavor compatible; never equate e.g. alpine to Debian.
    return (tuple(parts), match.group("v").lower(),
            (match.group("variant") or "").lower())


def result_unknown(image: str, reason: str, status: str = "unsupported") -> dict:
    return {"status": status, "current_image": image[:240],
            "current_tag": None, "candidate_tag": None,
            "candidate_image": None, "source": None,
            "checked_pages": 0, "complete": False,
            "note": reason, "execution_enabled": False}


def check_public_docker_hub(image: str, fetch=None) -> dict:
    """Operator-requested best-effort candidate discovery, never a safe-to-update claim."""
    ref = reference(image)
    if ref is None:
        return result_unknown(
            image,
            "Alleen publiek Docker Hub met een vaste numerieke tag wordt ondersteund. "
            "Voor :latest, digest-pins en andere registries ontbreekt een betrouwbare versiecheck."
        )
    current = tag_key(ref["tag"])
    assert current is not None
    if fetch is None:
        fetch = fetch_hub_page
    max_found = (current[0], ref["tag"])
    pages = 0
    complete = False
    repo = ref["repository"]
    try:
        for page in range(1, MAX_PAGES + 1):
            payload = fetch(repo, page)
            if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                return result_unknown(image, "Ongeldig antwoord van Docker Hub.", "check_failed")
            pages = page
            for item in payload["results"][:100]:
                if not isinstance(item, dict):
                    continue
                tag = item.get("name")
                if not isinstance(tag, str) or len(tag) > 80:
                    continue
                candidate = tag_key(tag)
                if candidate is None:
                    continue
                if candidate[1:] != current[1:]:
                    continue  # Keep same flavor and v-prefix.
                if candidate[0] > max_found[0]:
                    max_found = (candidate[0], tag)
            if not payload.get("next"):
                complete = True
                break
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return result_unknown(
            image, "Docker Hub is niet bereikbaar of weigert de versiecheck.", "check_failed"
        )
    if max_found[1] != ref["tag"]:
        status = "candidate"
        note = (
            "Nieuwere numerieke tag gevonden. Geen bewijs dat deze geschikt is voor "
            "jouw architectuur, Compose-configuratie of applicatiedata. Niet automatisch updaten."
        )
    else:
        status = "no_newer_found" if complete else "incomplete"
        note = ("Geen nieuwere compatibele tag gevonden in de gecontroleerde pagina's."
                if complete else "Beperkte tagcontrole; er kunnen nog nieuwere tags bestaan.")
    return {
        "status": status,
        "current_image": image,
        "current_tag": ref["tag"],
        "candidate_tag": max_found[1] if status == "candidate" else None,
        "candidate_image": f"{repo}:{max_found[1]}" if status == "candidate" else None,
        "source": "Docker Hub (publieke tags)",
        "checked_pages": pages,
        "complete": complete,
        "note": note,
        "execution_enabled": False,
    }


def fetch_hub_page(repository: str, page: int) -> dict:
    # Bounded fixed-origin endpoint, never a user-provided network location.
    namespace, repo = repository.split("/")
    if not REPO_COMPONENT.fullmatch(namespace) or not REPO_COMPONENT.fullmatch(repo):
        raise ValueError("Invalid Docker Hub repository")
    if not isinstance(page, int) or not 1 <= page <= MAX_PAGES:
        raise ValueError("Invalid page")
    url = (f"https://hub.docker.com/v2/repositories/{namespace}/{repo}/tags/"
           f"?page_size=100&page={page}")
    req = Request(url, headers={
        "User-Agent": "CodePug-VersionCheck/0.7 (opt-in; read-only)",
        "Accept": "application/json",
    })
    with urlopen(req, timeout=7) as response:
        if response.status != 200:
            raise ValueError("Unexpected registry status")
        # Upper limit prevents excessive JSON ingestion.
        raw = response.read(512_001)
    if len(raw) > 512_000:
        raise ValueError("Registry response too large")
    return json.loads(raw.decode("utf-8"))
