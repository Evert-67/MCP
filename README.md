# CodePug Server Control v0.5

Donker, mobielvriendelijk dashboard voor **Ubuntu/Docker en meerdere homeservers**. Werkt naast de bestaande CodePug Homeserver MCP v0.4 en de OpenAI Secure MCP Tunnel.

> **Status v0.5:** werkende webinterface, risicoprofielen, automatische inventarisatie uit bestaande snapshots, agent-registratie en agent-ingest voor extra servers. **Update-uitvoering is uitgeschakeld.** De bestaande v0.4-update-engine wordt niet automatisch aangeroepen. De uitvoeringsagent, back-upcontrole, rollback en expliciete actieautorisatie volgen pas na afzonderlijke tests.

## Installeren (EB-UBU-HOME)

```bash
# Kies een map BUITEN de bestaande MCP-installatie:
sudo mkdir -p /opt/codepug-control
sudo chown "$USER:$USER" /opt/codepug-control
cd /opt/codepug-control
# Kopieer hier de repo-inhoud via git clone / MobaXterm
cp .env.example .env
python3 scripts/create_password.py
# Plak de gegenereerde HASH-regel in .env (vervang lege regel)
chmod 600 .env
mkdir -p appdata
sudo chown 10001:10001 appdata
sudo chmod 700 appdata
docker compose up -d --build
# Open via SSH-portforward op je laptop:
# ssh -L 8768:127.0.0.1:8768 evert@192.168.2.20
# Ga naar http://127.0.0.1:8768
```

**Let op:** als je de GitHub-repo naar een map clonet, gebruik dan die map in plaats van de voorbeeldmap. De bindmount `/opt/codepug-mcp/data` verwijst bewust naar de bestaande v0.4-snapshots.

### Laptoptoegang

De Compose bindt standaard uitsluitend op `127.0.0.1:8768`. Gebruik een SSH-forward of een TLS-beveiligde proxy. Wil je op het LAN rechtstreeks verbinden, zet `BIND_IP=192.168.2.20` in `.env` en beveilig de netwerktoegang. HTTP Basic mag **niet via onversleuteld internet** lopen.

## Risicolagen

De scanner kent automatisch een **minimumrisico** toe: databases zijn *kritiek*, services met Docker-socket of infrastructuurfuncties minstens *hoog*, `:latest` of persistente data minstens *middel*. Je kunt het niveau alleen **verhogen**, nooit verlagen. De GUI bewaart per-containerinstellingen en notities in SQLite, zonder de Docker-configuratie te veranderen.

- **Laag:** auto-update *als toekomstig beleid* selecteerbaar, maar nog niet uitvoerbaar.
- **Middel:** goedkeuring noodzakelijk.
- **Hoog:** alleen gecontroleerd handmatig na back-up.
- **Kritiek:** nooit automatisch.

Voor daadwerkelijke updates zijn een aparte lokale uitvoeringscomponent, pinning/release checks, een bewezen back-up/restore, health checks, audit trail en per-actie-autorisatie vereist. v0.5 voert **geen** `docker compose pull/up` uit.

## Andere servers koppelen

1. Klik **Server toevoegen** in het dashboard. Noteer het eenmalige agent-token en agent-ID.
2. Installeer `agent/scan.py` op de andere Linux-/Docker-host met Python 3 en Docker CLI. Een Synology met Docker CLI/Container Manager kan ook werken; anders wordt een DSM-API-adapter een later onderdeel.
3. Maak op die host een privé-tokenbestand, bijvoorbeeld `/etc/codepug/agent.token` (mode `0600`), en stel `CODEPUG_HUB_URL`, `CODEPUG_AGENT_ID` en `CODEPUG_TOKEN_FILE` in.
4. Start `python3 agent/scan.py` of maak een systemd-timer van 60–120 seconden. De agent **pusht uitgaand via HTTPS**. Gebruik Tailscale + TLS of een interne veilige reverse proxy.

De agent leest metadata via Docker CLI. **Het account met Docker CLI-rechten is zeer machtig**; geef uitsluitend een vertrouwde, afgeschermde gebruiker toegang. De webcontainer zelf ontvangt **geen** Docker-socket en geen SSH-sleutels.

## GitHub en secrets

Repo: <https://github.com/Evert-67/MCP>. Publiceer uitsluitend code, voorbeeldconfiguraties, migraties en documentatie. Nooit `.env`, API-sleutels, tunnel-tokens, echte serverback-ups of live snapshots committen. De repo is openbaar; review vóór iedere push.

## Indeling

- `dashboard/` FastAPI dashboard, webinterface, risicoanalyse en SQLite-beleid
- `agent/` uitgaande Docker-statusscanner voor extra hosts
- `scripts/` wachtwoord-hashgenerator
- `docs/` architectuur en beveiliging
- `tests/` regressietests

Zie `docs/ARCHITECTURE.md` voor verdere ontwikkeling van de update-uitvoeringsagent.

### Reverse proxy (optioneel)

Gebruik een eigen dashboardhost met geldig HTTPS-certificaat, toegangsrestricties en `DASHBOARD_PUBLIC_ORIGIN=https://jouw-dashboarddomein.nl` in `.env`. Zet de API niet rechtstreeks publiek open: authenticatie en rate-limiting horen ook bij de proxy. De bestaande `homeserver-mcp.codepug.nl`-tunnel en MCP-server blijven ongewijzigd.
