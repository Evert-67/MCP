# CodePug — Systeemcontrole en beheerassistent (v0.7)

**Status: read-only meetketen, nog geen automatische herstelagent.**

## Vijf controlelagen

1. Host/Linux: OS, kernel, systemd, schijf/geheugen, APT-cache, herstartmelding.
2. Docker: daemon, Engine-, CLI- en Compose-versie, APT-kandidaten en containerstatus.
3. Applicaties: gezondheid, expliciete lokale HTTP-bereikbaarheid, software-releasebron.
4. Analyse: bevindingen, vermoedens, ontbrekend bewijs en onderzoeksvoorstellen.
5. Herstel (later): tijdgebonden toestemming, specifieke allowlist, back-up,
   restore-test, postcheck, audit en rollback.

**Draaiende container ≠ bereikbare app ≠ werkende integratie.**
**Nieuwere release ≠ veilige of verplichte update.**

## Wat daadwerkelijk werkt

De bestaande agent/scan.py verzamelt Docker-metadata. De nieuwe
agent/health.py geeft aanvullend door:

| Check | Methode | Betekenis en beperking |
|---|---|---|
| Linux | /etc/os-release en platform.release | Geïnstalleerde versie, niet automatisch verouderd |
| systemd | systemctl is-system-running | Degraded betekent onderzoeken |
| Herstart | /run/reboot-required | Geen automatische reboot |
| Pakketten | apt list --upgradable | Alleen bestaande APT-cache; geen apt update |
| Docker | systemctl is-active docker | Actieve daemon, niet alle apps geverifieerd |
| Docker-versies | docker version / docker compose version | Geïnstalleerde Engine, CLI, Compose |
| Docker-updates | apt-cache policy van Docker-pakketten | Vergelijk APT-kandidaat; geen laatste upstreamversie bewezen |
| Apps | Optionele expliciete loopback HTTP GET | HTTP-reactie, geen diepgaande functionele test |

Geen Docker-omgevingsvariabelen, volledige logs, API-keys of responseinhouden
worden verzonden. Het dashboard krijgt een gesaneerd rapport. Geen Docker-socket
of algemene host-shell aan de dashboardcontainer.

Het dashboard heeft een nieuwe sectie Systeemcontrole, met kaarten
per host en concrete bevindingen. De endpoint GET /api/health/overview
is ingelogd alleen-lezen. Het dashboard markeert geen host als volledig
geverifieerd op basis van alleen een Docker-containerlijst.

## Tweede server: EB MEDIARR

De rode lampjes op een Homarr-board tonen wat Homarr niet kan bereiken.
Dat is een aanwijzing maar geen bewezen uitval.

Installeer een eigen gekoppelde agent op elke Linux-host waarop diensten
draaien. Daarna kent CodePug het verschil tussen Linux, Docker en lokale
appbereikbaarheid op die host.

Optioneel lokaal agent/checks.json (PAS POORT ZELF AAN):

    [
      {"id":"voorbeeld-app","name":"Voorbeeldapp","port":8080,"path":"/"}
    ]

De agent accepteert alleen expliciet geconfigureerde localhost-poorten.
Zet CODEPUG_HEALTH_CHECKS_FILE op het lokale pad naar die JSON.
Geen ongevraagde netwerk-URL's, redirects of andere hostnamen.
Een HTTP 200 is niet automatisch volledige applicatiegezondheid; HTTP 401
kan betekenen dat de app bereikbaar is maar autorisatie nodig heeft.

Voor Sonarr, Radarr, Plex, Jellyfin en indexers zijn later echte beperkte
API-adapters nodig. Eventuele credentials blijven op de host in een
beschermde secretstore; alleen veilige statusuitkomsten worden gedeeld.

## Eerste handmatige test van een hostagent

1. In CodePug: Servers > Server koppelen. Bewaar agent-ID en eenmalig token.
2. Installeer deze v0.7-bron op de desbetreffende Linux-host.
3. Bewaar het token lokaal met bestandstoegang 0600, niet in een chatbericht
   of shellgeschiedenis.
4. Configureer lokaal CODEPUG_HUB_URL, CODEPUG_AGENT_ID en
   CODEPUG_TOKEN_FILE. Bij externe servers is HTTPS verplicht.
5. Voer python3 agent/scan.py uit om één rapport te verzenden.
6. Bekijk Systeemcontrole. Voor herhaling: python3 agent/scan.py --loop
   als apart, beheerd proces nadat de machtigingen zijn gecontroleerd.

De huidige agent heeft toegang tot Docker CLI nodig. Lidmaatschap
van de Docker-groep is op Linux feitelijk root-equivalent: gebruik dit
alleen op vertrouwde hosts, met een bewuste rechtenafweging. Een beperktere
Docker-observer is nodig voor toekomstige algemene uitrol.

## Wat niet klaar is

- Ondersteuningskalender voor alle Linux-distributies als actuele bron.
- Echte OCI-image-digestcontrole voor GHCR, :latest en andere registries.
- Diepe app-API's voor indexers, API-sleutels, storage, downloadqueues.
- Gewenste toestand per container, inclusief bewust uitgeschakelde diensten.
- Externe uptimebewaker voor een uitgevallen CodePug-hub.
- ChatGPT MCP-tools voor alle hostmetingen en beheerde incidentdossiers.
- Recovery-agent met uitvoerende rechten, backupbewijs, restore-tests,
  scope/expiry/approval, postchecks en rollback.
- Webinstallatiewizard om hosts eenvoudig en veilig te koppelen.

**CodePug v0.7 verandert geen host, installatie of Docker-container.**

## Voorbeeld: Sonarr rood in Homarr

- Controleer eerst de host en wanneer die is gemeten.
- Controleer Docker-daemon en de Sonarr-containerstatus.
- Controleer lokale appbereikbaarheid én of Homarr het juiste adres gebruikt.
- Controleer (na geautoriseerde API-koppeling) indexers, credentials en logs.
- Geef waarschijnlijke oorzaak, ontbrekend bewijs en een voorstel.
- Vraag later expliciet toestemming voor ÉÉN begrensde herstelactie.
- Alleen een afzonderlijke beheeragent mag die actie uitvoeren met
  backup-, audit- en post-checks; deze laatste twee stappen zijn nog gepland.
