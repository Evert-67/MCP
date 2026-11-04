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

Je hoort nu **twee** v0.7-containers te zien: `codepug-control-v07`
en `codepug-version-watcher-v07` (geen eigen webpoort). Dit is expres:
de versiechecker kan doorgaan wanneer je browser gesloten is.

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
7. Ga naar **Instellingen** en schakel **Zoek op de achtergrond naar nieuwe Docker Hub-tags** bewust in. Kies bijvoorbeeld **Elke 24 uur** en klik **Instellingen opslaan**.
8. Open het overzicht: de tegel **Nieuwe versies gevonden** en de kolom **Versiecontrole** worden vanzelf bijgewerkt wanneer de eerste scans klaar zijn.
9. Per dienst blijft **Controleer nieuwere versie** beschikbaar voor een directe handmatige controle.
10. Bij **Homarr** toont CodePug nu een officiële release uit GitHub. Wanneer
    de draaiende versie niet vanuit een hostagent bekend is, staat er
    **Huidige versie onbekend**. Dat is nog géén bevestigde beschikbare update.
    De bestaande v0.4-snapshot levert geen applicatieversie of image-digest.

## Stoppen van uitsluitend v0.7

```bash
cd /opt/codepug-control-v07
docker compose down
```

**Let op:** nooit `docker compose down` in de map van een andere CodePug-versie
en geen productiedata of `/opt/codepug-mcp/data` verwijderen.

Bekijk de achtergrondchecker met `docker compose logs --tail=50 version-watcher`. Geen waarschuwingen over updates? Controleer of de functie in het dashboard is ingeschakeld; veel images met `:latest` of van GHCR zijn nog niet te vergelijken.

Na een nieuwe commit op de v0.7-branch kun je de testinstallatie bijwerken met `cd /opt/codepug-control-v07 && git pull --ff-only && docker compose up -d --build`.

Volledige roadmap: [docs/V07_BACKUP_RECOVERY.md](docs/V07_BACKUP_RECOVERY.md).
