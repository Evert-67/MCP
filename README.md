# CodePug Server Control v0.5

Donker, mobielvriendelijk **meertalig** dashboard voor verschillende homeservers en meerdere hosts. De centrale webapp draait als Docker-container. Een lokale snapshotbron is optioneel; externe agents sturen zelf hun inventaris via HTTPS. De bestaande CodePug Homeserver MCP v0.4 en OpenAI Secure MCP Tunnel zijn optionele integraties, geen vereisten.

> **Status v0.5:** werkende webinterface, risicoprofielen, automatische inventarisatie uit bestaande snapshots, agent-registratie en agent-ingest voor extra servers. **Update-uitvoering is uitgeschakeld.** De bestaande v0.4-update-engine wordt niet automatisch aangeroepen. De uitvoeringsagent, back-upcontrole, rollback en expliciete actieautorisatie volgen pas na afzonderlijke tests.

## Installeren op iedere Docker-host

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
# ssh -L 8768:127.0.0.1:8768 gebruiker@adres-van-jouw-server
# Ga naar http://127.0.0.1:8768
```

**Let op:** als je de GitHub-repo naar een map clonet, gebruik dan die map in plaats van de voorbeeldmap. Standaard is `HOST_SNAPSHOT_DIR=./host-data`: een lege lokale map; zonder v0.4 kun je de lokale host gewoon aanmelden via de meegeleverde `agent/scan.py`. Heb je al een JSON-collector, zet dan bijvoorbeeld `HOST_SNAPSHOT_DIR=/pad/naar/collector/data` in `.env`. **Geen hardcoded CodePug- of gebruikerspaden.**

### Laptoptoegang

De Compose bindt standaard uitsluitend op `127.0.0.1:8768`. Gebruik een SSH-forward of een TLS-beveiligde proxy. Wil je op het LAN rechtstreeks verbinden, zet `BIND_IP=192.168.1.20` in `.env` en beveilig de netwerktoegang. HTTP Basic mag **niet via onversleuteld internet** lopen.

## Instellingen beheren in de webinterface

De nieuwe pagina **Instellingen / Settings** bevat:
- taalkeuze (Nederlands/Engels; per browser opgeslagen);
- verversinterval van het dashboard (15–300 s);
- grens wanneer een server als offline geldt (3–30 minuten);
- waarschuwingen in het dashboard voor nieuwe offline-statussen en ongezonde containers;
- serveragent-beheer: naam wijzigen, scaninterval aanpassen, toegang intrekken en inventaris verwijderen.

De instellingen voor monitoring staan in de bestaande SQLite-database. Geen aanpassing van de Compose-configuratie nodig voor gewone dashboardvoorkeuren. **De webinterface voert geen Docker-, Ubuntu- of pakketupdates uit.**

### Agent-scaninterval

De oorspronkelijke scanner `python3 agent/scan.py` draait **één keer**: geschikt voor crontab of systemd timers. Die blijven hun eigen interval gebruiken. Om het scaninterval te laten volgen vanuit de webinterface, start de scanner op de gekoppelde server als doorlopend proces:

```bash
python3 agent/scan.py --loop
```

Gebruik daarvoor bij voorkeur een systemd-service met een apart, afgeschermd account. `--loop` vraagt het interval via een token-geauthenticeerd HTTPS-endpoint op en scant tussen 60 en 3600 seconden. Wanneer de hub onbereikbaar is, wacht hij 120 seconden en probeert hij opnieuw. Er wordt **geen commando-uitvoering** aangeboden via dit endpoint.

**Belangrijk:** het scannerproces heeft voor Docker-metadata Docker CLI-rechten nodig; dat is een krachtige bevoegdheid. Gebruik een vertrouwde lokale host en stel de Docker-daemon niet via TCP bloot. Voor lokale v0.4-snapshots geldt de bestaande collector-cron, niet deze instelling.

### Meldingen

Meldingen in v0.5 zijn **alleen tijdelijke waarschuwingen in de geopende webbrowser** wanneer een server of container van gezond naar ongezond/offline verandert. Geen e-mail, push of automatische waarschuwing wanneer niemand het dashboard bekijkt. Die functies vereisen latere, afzonderlijk beveiligde integraties.

### Logo

Het dashboard gebruikt voorlopig een neutraal pictogram. Het oorspronkelijke CodePug-logo (mopshond met bril) wordt pas als merkbestand toegevoegd zodra het bronbestand is bevestigd. Een hertekend logo zou onbedoeld afwijken van het echte merkbeeld.

## Talen / languages

- Het dashboard biedt **Nederlands (nl)** en **Engels (en)** via de taalkeuze rechtsboven.
- De browsertaal bepaalt de eerste selectie (onbekende talen vallen terug op Engels); daarna blijft de keuze lokaal in de browser bewaard. Er worden geen taalvoorkeuren naar de hub gestuurd.
- Vertalingen staan in `dashboard/static/locales/en.json`. Nederlands is de brontaal; ontbrekende vertalingen vallen terug op Nederlands. Een nieuwe taal kan zonder databasewijziging worden toegevoegd via een eigen JSON-catalogus en één extra vermelding in `dashboard/static/i18n.js` en `dashboard/templates/index.html`.
- Server- en dienstnamen, notities en credentials worden niet automatisch vertaald. De API gebruikt nog vaste berichtteksten; verdere API-lokalisatie is vervolgwerk.

## Risicolagen

De scanner kent automatisch een **minimumrisico** toe: databases zijn *kritiek*, services met Docker-socket of infrastructuurfuncties minstens *hoog*, `:latest` of persistente data minstens *middel*. Je kunt het niveau alleen **verhogen**, nooit verlagen. De GUI bewaart per-containerinstellingen en notities in SQLite, zonder de Docker-configuratie te veranderen.

- **Laag:** auto-update *als toekomstig beleid* selecteerbaar, maar nog niet uitvoerbaar.
- **Middel:** goedkeuring noodzakelijk.
- **Hoog:** alleen gecontroleerd handmatig na back-up.
- **Kritiek:** nooit automatisch.

Voor daadwerkelijke updates zijn een aparte lokale uitvoeringscomponent, pinning/release checks, een bewezen back-up/restore, health checks, audit trail en per-actie-autorisatie vereist. v0.5 voert **geen** `docker compose pull/up` uit.

## Platformonafhankelijk ontwerp

De hub gebruikt een gedeeld inventarisatieformaat met hosts, containers, platformnaam en mogelijkheden (`capabilities`). Docker/Linux is de eerste scanner; Docker Desktop-hosts kunnen met de agent beperkte informatie aanleveren. Synology met Docker CLI kan onder voorwaarden werken. **Proxmox, DSM-pakketten, VM's, LXC, Kubernetes en Windows-services vereisen nog eigen adapters** — het dashboard monitort die dus nog niet automatisch.

Voor een nieuwe adapter behouden we dezelfde API-structuur en maken we nieuwe risicoregels en tests. Geen scanner heeft mutatierechten nodig voor de hub; uitvoering is een afzonderlijke toekomstige component.

## Andere servers koppelen

1. Klik **Server toevoegen** in het dashboard. Noteer het eenmalige agent-token en agent-ID.
2. Installeer `agent/scan.py` op een host met Python 3 en Docker CLI. Dit kan ook je **eerste/lokale host** zijn als je geen bestaande snapshotcollector hebt. Voor niet-Docker-systemen maken we later een platformadapter.
3. Maak op die host een privé-tokenbestand, bijvoorbeeld `/etc/codepug/agent.token` (mode `0600`), en stel `CODEPUG_HUB_URL`, `CODEPUG_AGENT_ID` en `CODEPUG_TOKEN_FILE` in.
4. Start `python3 agent/scan.py` of maak een systemd-timer van 60–120 seconden. De agent **pusht uitgaand via HTTPS**. Gebruik Tailscale + TLS of een interne veilige reverse proxy.

De agent scant lokaal zonder vooraf ingevoerde containerlijst en rapporteert alleen inventarisatiegegevens plus platform/capabilities. Hij leest metadata via Docker CLI. **Het account met Docker CLI-rechten is zeer machtig**; geef uitsluitend een vertrouwde, afgeschermde gebruiker toegang. De webcontainer zelf ontvangt **geen** Docker-socket en geen SSH-sleutels.

## Extra talen toevoegen

1. Kopieer `dashboard/static/locales/en.json` naar bijvoorbeeld `dashboard/static/locales/de.json` en vertaal de waarden (niet de Nederlandse sleutels).
2. Voeg `de: 'Deutsch'` toe aan `LANGUAGES` in `dashboard/static/i18n.js`.
3. Voeg `<option value="de">Deutsch</option>` toe onder `#language` in `dashboard/templates/index.html`.
4. Test de mobiele interface, alle dialoogvensters, de risico-uitleg en de fallback voor ontbrekende vertalingen.

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
