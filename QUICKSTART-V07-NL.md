# CodePug v0.7 — veilige testinstallatie naast v0.5 en v0.6

> **Ontwikkelversie.** Dit is een Backup & Recovery-concept, nog geen werkende back-up- of herstelmotor.
> Houd de bestaande CodePug-instanties op poorten 8768 en 8769 in stand.

## Installeren op Ubuntu

Open een terminal via MobaXterm of SSH:

```bash
cd /opt
sudo git clone --branch feature/server-control-v0.7 --single-branch \
  https://github.com/Evert-67/MCP.git codepug-control-v07
sudo chown -R "$USER:$USER" /opt/codepug-control-v07
cd /opt/codepug-control-v07
python3 scripts/setup.py
```

De setup vraagt om een wachtwoordzin van minstens 12 tekens en slaat zelf de hash in `.env` op.
Er wordt geen bestaande v0.5- of v0.6-configuratie gebruikt of overschreven.

Optioneel: open `nano .env` en stel `HOST_SNAPSHOT_DIR=/opt/codepug-mcp/data` in
als dat daadwerkelijk jouw leesbare v0.4-snapshotmap is. Laat `BIND_IP=127.0.0.1`
en `DASHBOARD_PORT=8770` staan.

```bash
mkdir -p appdata
sudo chown 10001:10001 appdata
sudo chmod 700 appdata
chmod 600 .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

## Openen vanuit Windows

Start in een afzonderlijk PowerShell-venster:

```powershell
ssh -L 8770:127.0.0.1:8770 evert@192.168.2.20
```

Open daarna `http://127.0.0.1:8770` in Chrome. Gebruik gebruikersnaam `admin`
en de gekozen wachtwoordzin.

## Wat kun je testen?

1. De pagina **Backup & Recovery** links in het menu.
2. Het aantal hosts en kritieke diensten (uit de inventaris).
3. De waarschuwing dat back-upstatus en hersteltests nog **onbekend** zijn.
4. **Toon herstelplan** voor een dienst: een checklist zonder uitvoerbare knoppen.
5. De bestaande **AI & Diagnose** en v0.6-functies.
6. Onder **Diensten > Risicobeleid** kan nu ook **Laag** gekozen worden. De harde veiligheidsinschatting verandert daardoor niet.
7. Per dienst: **Controleer nieuwere versie** voor een optionele read-only controle van publieke Docker Hub-images met genummerde tags.

## Stoppen van uitsluitend v0.7

```bash
cd /opt/codepug-control-v07
docker compose down
```

**Let op:** nooit `docker compose down` in de map van een andere CodePug-versie
en geen productiedata of `/opt/codepug-mcp/data` verwijderen.

Na een nieuwe commit op de v0.7-branch kun je de testinstallatie bijwerken met `cd /opt/codepug-control-v07 && git pull --ff-only && docker compose up -d --build`.

Volledige roadmap: [docs/V07_BACKUP_RECOVERY.md](docs/V07_BACKUP_RECOVERY.md).
