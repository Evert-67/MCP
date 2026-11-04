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
            "note": reason, "execution_enabled": False, "checker_rev": 2}


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
                # CalVer/date tags (e.g. 20260805) are NOT semantic
                # successor versions to Alpine 3.20. Never compare schemes.
                current_major, candidate_major = current[0][0], candidate[0][0]
                if (current_major >= 1000) != (candidate_major >= 1000):
                    continue
                if (current_major >= 1000 and candidate_major >= 1000 and
                        len(ref["tag"].lstrip("v").split(".")[0]) !=
                        len(tag.lstrip("v").split(".")[0])):
                    continue
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
        "checker_rev": 2,
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


# Application releases: only sources explicitly mapped to a known image.
# Never infer arbitrary GitHub URLs from a container or image name.
KNOWN_SOFTWARE_RELEASES = {
    "ghcr.io/homarr-labs/homarr": "homarr-labs/homarr",
}
RELEASE_TAG = re.compile(r"^v?(\d{1,3})\.(\d{1,3})(?:\.(\d{1,4}))?$", re.I)


def release_version(value: str | None) -> tuple[int, int, int] | None:
    match = RELEASE_TAG.fullmatch(str(value or ""))
    return (tuple(map(int, match.groups(default="0"))) if match else None)


def fetch_github_latest_release(repository: str) -> dict:
    """Anonymous GitHub Releases API for explicit allowlisted repositories."""
    if repository not in KNOWN_SOFTWARE_RELEASES.values():
        raise ValueError("Not an approved release source")
    req = Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={
            "User-Agent": "CodePug-SoftwareReleaseCheck/0.7",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    with urlopen(req, timeout=8) as response:
        if response.status != 200:
            raise ValueError("GitHub release unavailable")
        raw = response.read(128_001)
        if len(raw) > 128_000:
            raise ValueError("GitHub release too large")
    return json.loads(raw.decode("utf-8"))


def check_known_software_release(image: str, installed_version: str | None = None,
                                 fetch=None) -> dict:
    """Discover a release, never claim update unless installed version is known."""
    name, separator, tag = image.rpartition(":")
    repository = KNOWN_SOFTWARE_RELEASES.get(name) if separator else None
    if not repository:
        return result_unknown(image, "Geen bekende officiële software-releasebron")
    fetch = fetch or fetch_github_latest_release
    try:
        payload = fetch(repository)
        release = str(payload.get("tag_name") or "")[:60]
        latest = release_version(release)
        if latest is None:
            return result_unknown(image, "Onverwacht versienummer van officiële bron.",
                                  "check_failed")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError,
            TypeError, AttributeError, json.JSONDecodeError):
        return result_unknown(image, "Officiële GitHub-releases konden niet worden geladen.",
                              "check_failed")
    installed = release_version(installed_version)
    if installed is None:
        status = "release_found"
        note = ("Officiële release " + release + " gevonden. De exacte draaiende softwareversie "
                "is niet bekend; updatebehoefte NIET bevestigd. "
                "Een :latest-tag of oude containerleeftijd is geen versiebewijs.")
    elif latest > installed:
        status = "candidate"
        note = ("Software-release " + release + " is nieuwer dan de "
                "door de host gerapporteerde versie " + str(installed_version) +
                ". Controleer compatibiliteit, imagebeschikbaarheid en backup vóór updaten.")
    else:
        status = "no_newer_found"
        note = ("De officiële release is niet nieuwer dan de door de host "
                "gerapporteerde applicatieversie.")
    return {
        "status": status,
        "current_image": image[:240],
        "current_tag": tag,
        "current_software_version": str(installed_version) if installed else None,
        "latest_release": release,
        "candidate_tag": release if status == "candidate" else None,
        "candidate_image": None,  # Release != proven published OCI image.
        "source": "GitHub Releases (officieel)",
        "release_url": f"https://github.com/{repository}/releases/tag/{release}",
        "checked_pages": 1,
        "complete": True,
        "checker_rev": 2,
        "execution_enabled": False,
        "note": note,
    }


def check_image_update(image: str, installed_version: str | None = None) -> dict:
    """Select a safe read-only provider for this exact image."""
    name, sep, tag = image.rpartition(":")
    if sep and name in KNOWN_SOFTWARE_RELEASES:
        return check_known_software_release(image, installed_version)
    return check_public_docker_hub(image)
