# Architectuur, v0.5 en verder

```
ChatGPT ──OpenAI Secure MCP Tunnel──> bestaande MCP v0.4 (alleen-lezen)
                                     ↑ status/updates snapshots
                                     │
Webbrowser ──TLS/SSH──> Control Center v0.5 (Docker, poort 8768)
                             │          ↑ agent HTTPS push
                             │          ├── Ubuntu / Docker agent
                             │          └── Synology/Linux agent
                             └── SQLite: inventory, policylagen, events

TOEKOMST: lokale update-runner (NIET via willekeurige shell of Docker-socket in webcontainer)
```

## Lifecycle

- Inventarisatie: lokaal uit bestaande `/opt/codepug-mcp/data/status.json`, andere hosts via token-geauthenticeerde POST `/api/ingest/{id}`.
- Agent: alleen containernaam, image, state/health, Compose-project/service, booleans voor docker socket/persistente storage, RAM/schijf; **geen env/labels/volumepaden/logs**.
- Beveiligde beheerlogin met PBKDF2, origin + non-simple custom header voor mutaties, standaard loopback bind.
- Beleid: hard-coded minimum risico; gebruiker kan omhoog, niet omlaag. Auto-voorkeur alleen toegestaan voor laag risico. Voorkeur is **geen uitvoeringstoestemming**.
- Multi-server: iedere host heeft een eigen ingetrokken/roteerbaar te maken token (tokenrotatie v0.6) en push via HTTPS.

## Nog te implementeren voor veilige automatische updates

1. Per-host afzonderlijke update-runner met lokaal beheerde allowlist voor Compose-projectdirectory + service.
2. Verify release metadata/major version/image pin, digest en dependency-/migratiebeleid; bij `:latest` nooit blind updaten.
3. Per-service back-upscript inclusief externe controle op herstelbare data; restore-test minstens éénmaal uitgevoerd.
4. Nieuwe beelden pullen, verschillen tonen, onderhoudsvenster/impact controleren, uitvoering via goedgekeurd eenmalig plan-ID.
5. Host checks, app-specifieke HTTP- en healthchecks, incidentregistratie. Geen automatische DB rollback.
6. Attestation/audit log met initiator en precies uitgevoerde actie; centraal GUI alleen resultaten en status.
7. Aparte MCP-tools `update_scan`, `update_prepare`, `update_apply` na hardening. ChatGPT-toolbeschikbaarheid is niet dezelfde beveiligingsgrens als hostbeleid.

Geen privileges naar de webcontainer. Geen openbare Docker TCP API. Geen `docker.sock:ro` als schijnveiligheid.
