# CodePug v0.6 — eerste testinstallatie, naast v0.5

> **Ontwikkelversie.** Houd de bestaande v0.5 op poort 8768. Deze versie gebruikt
> **een eigen map, containernaam en poort 8769**. Er worden geen herstelacties uitgevoerd.

## Installeren (Ubuntu, via MobaXterm/SSH)

Kies expliciet een **nieuwe map**:

```bash
cd /opt
sudo git clone --branch feature/server-control-v0.6 --single-branch \
  https://github.com/Evert-67/MCP.git codepug-control-v06
sudo chown -R "$USER:$USER" /opt/codepug-control-v06
cd /opt/codepug-control-v06
python3 scripts/setup_v06.py
```

Kies een wachtwoordzin van minimaal 12 tekens. De configurator slaat de hash
automatisch op in \`.env\`. **Je hoeft geen hash meer te kopiëren.**

### Bestaande snapshots gebruiken (optioneel)

Open \`.env\` alleen als je de collector wilt gebruiken:

```bash
nano .env
```

Pas \`HOST_SNAPSHOT_DIR=./host-data\` aan naar de **daadwerkelijke**
map met je v0.4-\`status.json\` als die beschikbaar is. Dit pad moet vanaf de
host een leesbare map zijn. De originele v0.4 blijft draaien.

Laat \`BIND_IP=127.0.0.1\` en \`DASHBOARD_PORT=8769\` staan.

### Starten

```bash
mkdir -p appdata
sudo chown 10001:10001 appdata
sudo chmod 700 appdata
chmod 600 .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

### Windows laptop: dashboard openen

Open een tweede PowerShell-venster:

```powershell
ssh -L 8769:127.0.0.1:8769 evert@192.168.2.20
```

Vervang gebruiker/IP als ze anders zijn. Ga naar **http://127.0.0.1:8769**.

Inlognaam \`admin\`, wachtwoordzin uit de setup.

### Testen

1. Controleer het dashboard en de bestaande services.
2. Klik op **AI & Diagnose** in de linkernavigatie.
3. Kies een container, bijvoorbeeld een ongezonde dienst.
4. Klik **Diagnose maken** en lees de informatie.
5. Alleen als je dat wilt: vink delen aan, kopieer het rapport en open ChatGPT.
6. Plak het rapport in je bestaande conversatie. Geef *geen* tokens, wachtwoorden of privélogboeken door.

### Terugdraaien van uitsluitend v0.6

```bash
cd /opt/codepug-control-v06
docker compose down
```

De v0.5-container wordt hierdoor niet geraakt. **Gebruik geen**
\`docker compose down\` in de map van je werkende v0.5.

## Wat werkt nog niet?

Er is nog **geen ingebouwde AI-chat, geen nieuwe MCP-gateway, geen automatische
logtoegang en geen herstelagent**. Dit is de eerste read-only diagnosefunctie.
Zie [docs/V06_AI_DIAGNOSE.md](docs/V06_AI_DIAGNOSE.md).

De toekomstig geplande webinstallatiewizard, light/dark thema, originele
CodePug-logo's en extra host-adapters volgen later in v0.6.
