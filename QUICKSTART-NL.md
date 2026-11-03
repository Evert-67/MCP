# CodePug Server Control v0.5 — snelle installatie

**Status:** v0.5 is een ontwikkelversie op branch `feature/server-control-v0.5`, nog niet samengevoegd met `main`. Het dashboard werkt met monitoring, risicoprofielen, NL/EN en instellingen. **Automatische updates worden niet uitgevoerd.**

## 1. Installeren op Ubuntu

Open via SSH of MobaXterm een terminal op je Ubuntu-host.

```bash
cd /opt
sudo git clone --branch feature/server-control-v0.5 --single-branch https://github.com/Evert-67/MCP.git codepug-control
sudo chown -R "$USER:$USER" /opt/codepug-control
cd /opt/codepug-control
cp .env.example .env
python3 scripts/create_password.py
```

Kies twee keer een sterk wachtwoord van **minstens 14 tekens**. Het script geeft een complete regel met `DASHBOARD_PASSWORD_HASH=...` terug.

## 2. Eénmalige instellingen

Open de configuratie:

```bash
nano .env
```

- **Vervang** `DASHBOARD_PASSWORD_HASH=` door de hele regel die het script zojuist gaf (inclusief aanhalingstekens).
- **Bestaande v0.4-collector?** Zet `HOST_SNAPSHOT_DIR=/opt/codepug-mcp/data` om de status van de lokale host te tonen.
- Behoud `BIND_IP=127.0.0.1`. Dit voorkomt dat de webinterface zomaar vanaf je netwerk bereikbaar is.

Opslaan in nano: **Ctrl+O**, **Enter**, **Ctrl+X**.

## 3. Starten

```bash
cd /opt/codepug-control
chmod 600 .env
mkdir -p appdata
sudo chown 10001:10001 appdata
sudo chmod 700 appdata
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Verwacht: service `codepug-control` is `Up` / `healthy`. Mocht iets niet werken:

```bash
docker logs --tail 60 codepug-control
```

## 4. Vanaf Windows openen

Open **een tweede terminal op je laptop** (PowerShell of MobaXterm) en laat deze SSH-verbinding open:

```powershell
ssh -L 8768:127.0.0.1:8768 evert@192.168.2.20
```

Open vervolgens op je laptop **http://127.0.0.1:8768**.

Log in met `admin` en het wachtwoord dat je bij stap 1 koos.

## 5. Controlelijst

- Dashboard laadt met donkere interface.
- Taalkeuze NL/EN werkt.
- Onder **Servers** verschijnt de lokale host (mits `HOST_SNAPSHOT_DIR` klopt en `status.json` leesbaar is).
- Bij **Diensten** zie je de Docker-containers.
- Bij **Instellingen** kun je scan- en dashboardvoorkeuren aanpassen.

**Zie je geen containers?** Controleer dan of `/opt/codepug-mcp/data/status.json` bestaat en door de containergebruiker (UID 10001) kan worden gelezen. Verander geen rechten van private rapporten of secrets zonder te controleren wat daadwerkelijk nodig is.

## Wat verandert niet?

Dit project draait **naast** je bestaande `codepug-homeserver-mcp` v0.4 op poort 8766. Het dashboard luistert op poort 8768, alleen op localhost. Je bestaande MCP-tunnel en originele `codepug-mcp` blijven ongemoeid. Gebruik geen `docker compose down --remove-orphans` in je bestaande MCP-map.

**Veiligheid:** dit dashboard is voorlopig monitoring/configuratie. De instellingen `auto` zijn voorkeuren voor de toekomstige updater, geen toestemming of mogelijkheid om al updates uit te voeren.
