# CodePug Control Center — compacte beheerapp (preview)

> **Testversie:** los van de bestaande v0.5, v0.6 en v0.7. Dit is geen
> complete autonome systeembeheerder: sommige diepgaande metingen,
> ChatGPT-acties, backup-verificatie en hersteluitvoering zijn nog in ontwikkeling.

## Waarom dit anders is

Het startscherm bevat alleen KPI's, enkele prioriteiten en de hosts.
De navigatie opent nu **aparte pagina's**, geen tientallen secties onder
elkaar. De begroeting volgt de **lokale klok van de browser**.

- **Overzicht:** snel zien wat aandacht vraagt.
- **Servers & diensten:** hostkaarten voor Linux/Docker-metingen en een filterbare dienstentabel.
- **Incidenten:** onderzoekt symptomen per host; groepeert ontbrekende hostmetingen
  en meerdere mislukte lokale appchecks om nodeloze meldingen te beperken.
  Een gezamenlijke netwerk- of platformoorzaak is **vermoeden, geen bewijs**.
- **Updates:** bestaande read-only versiechecker en optionele achtergrondcontroles.
- **Backup & Recovery:** eerlijk onbekende back-up-/restorestatus plus conceptplannen.
- **AI-assistent:** gesaneerd diagnoseverslag, opt-in kopiëren naar ChatGPT.
  **Geen ingebouwde AI en geen remote herstelagent.**
- **Instellingen:** monitoring, versiecontrole, weergave en agents afzonderlijk georganiseerd.

## Eerste test op Ubuntu — aparte poort 8771

Gebruik het volgende uitsluitend als de map nog niet bestaat:

```bash
cd /opt
sudo git clone --branch feature/control-center-multipage --single-branch \
  https://github.com/Evert-67/MCP.git codepug-control-console
sudo chown -R "$USER:$USER" /opt/codepug-control-console
cd /opt/codepug-control-console
python3 scripts/setup.py
```

Bestaat de map al? Gebruik dan in plaats van een tweede clone:

```bash
cd /opt/codepug-control-console
git pull --ff-only
```

Zorg dat in de **eigen** `.env` van deze preview staat:

```dotenv
CODEPUG_PROJECT_NAME=codepug-console-preview
CODEPUG_CONTAINER_NAME=codepug-console-preview
DASHBOARD_PORT=8771
BIND_IP=127.0.0.1
HOST_SNAPSHOT_DIR=/opt/codepug-mcp/data
```

Laat de bestaande password-hash ongemoeid. De laatste regel kun je in
de preview-`.env` zetten met:

```bash
sed -i 's|^HOST_SNAPSHOT_DIR=.*|HOST_SNAPSHOT_DIR=/opt/codepug-mcp/data|' .env
```

Start de **preview**, niet je bestaande v0.7:

```bash
mkdir -p appdata
sudo chown 10001:10001 appdata
sudo chmod 700 appdata
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Via een nieuw PowerShell-venster op Windows:

```powershell
ssh -L 8771:127.0.0.1:8771 evert@192.168.2.20
```

Open **http://127.0.0.1:8771** en log in als `admin` met
het wachtwoord dat je voor deze preview hebt gekozen.

De oude lange dashboardpagina is nog te zien via
**http://127.0.0.1:8771/legacy**, maar is niet de standaard.

## Wat is *wel* en *niet* gemeten?

De bestaande v0.4-read-only snapshot toont host-/Dockerinventaris.
Linux-release, systemd en applicatie-healthchecks zijn pas beschikbaar
als er voor de betreffende host een nieuwe, beperkt ingerichte v0.7-agent
is gekoppeld. Een ontbrekende meting is **onbekend**, niet groen.

De incidentengroepering is *heuristisch*. Zij toont mogelijke
gedeelde symptomen, geen bewezen netwerkstoring. Specifieke
Sonarr/Radarr/Indexers-integraties zijn er nog niet.

## Als poort 8771 niet reageert

Controleer eerst **of de preview daadwerkelijk is gestart**:

```bash
cd /opt/codepug-control-console
git pull --ff-only
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl -i http://127.0.0.1:8771/healthz
```

De `/healthz`-endpoint antwoordt op een werkende preview met status 200.
De dashboard-login en applicatiecontrole zijn daarna apart te testen.
De portforward vanuit Windows moet ondertussen openstaan:

```powershell
ssh -L 8771:127.0.0.1:8771 evert@192.168.2.20
```

`docker compose up --build` bouwt twee images. Ze hebben nu
**afzonderlijke image-tags** om gelijktijdige BuildKit-exportconflicten
te vermijden. Als bouwen nog steeds mislukt, gebruik:

```bash
docker compose --progress plain build
```

En bekijk de **volledige foutregels onderaan**, niet alleen de eerste
`ERROR exporting to image`-regel. Een opslag-, permissie- of BuildKit-fout
kan dezelfde bovenste melding geven. Wis geen Docker-volumes, images of
andere containers van de host als algemene herstelmaatregel.

## Veilig stoppen

```bash
cd /opt/codepug-control-console
docker compose down
```

Dit stopt uitsluitend de preview. Het verwijdert je bestaande v0.5,
v0.6, v0.7 en hun gegevens niet.
