# CodePug Server Control v0.7 — Backup, Recovery & Redundancy

> **Status: eerste ontwikkelmijlpaal, read-only.** Dit is nog geen back-up- of
> herstelproduct. Alle systemen in productie blijven onaangeroerd. De branche
> is gebaseerd op v0.6, en nog niet samengevoegd met v0.6 of main.

## Uitgangspunt

**Bewaken → Begrijpen → Herstellen.** CodePug beheert meerdere hosts en
geeft ChatGPT via één MCP-gateway straks een gecontroleerde mogelijkheid om
storingen te onderzoeken en, na expliciete autorisatie, een passend en
verifieerbaar herstelproces te laten uitvoeren.

Een prettige webinterface is belangrijk, maar veiligheid gaat vóór automatisering.

## Deze eerste v0.7-mijlpaal bevat daadwerkelijk

- Een extra pagina **Backup & Recovery** in het dashboard.
- Een geauthenticeerd `GET /api/recovery/overview` endpoint dat hosts,
  aantallen diensten en kritieke diensten toont.
- Statussen **Onbekend / Niet getest / Niet geverifieerd** voor alle back-ups,
  restore-tests en redundantie: een containersnapshot bevat daar geen bewijs voor.
- Een `GET /api/recovery/plan?service_key=...` endpoint dat per geselecteerde
  dienst een concept-checklist voor veilig herstel geeft.
- Geen uitvoerende endpoints, Docker-socket, host SSH-sleutels, automatische
  herstelacties, back-upinventarisatie of dataverzending naar AI-providers.
- Unit- en API-tests voor autorisatie, waarheidsgetrouwe statussen en
  het niet uitlekken van beleidsnotities/tokens.

## v0.7 extra — risicoprioriteit en handmatige versiecontrole

In **Diensten > Risicobeleid** kun je nu een eigen risicobeoordeling kiezen,
ook **Laag** wanneer CodePug een belangrijkere dienst herkent. Het dashboard
bewaart tegelijk een **onafhankelijke veiligheidsinschatting**. Een lagere
risicoscore verlaagt nooit de veiligheidsdrempel voor automatische acties.
Deze ontwikkelversie kan sowieso geen updates uitvoeren.

Per dienst vind je **Controleer nieuwere versie**. Dit is een *handmatige*
best-effort tagvergelijking tegen de **publieke Docker Hub API**:

- Alleen Docker Hub-images met een expliciet **numeriek image-tag**
  (bijvoorbeeld `redis:7.2.4`), geen `:latest`, digest-pins,
  GHCR, privéregisties of interne repositories.
- Vergelijkt maximaal **200 tags** van dezelfde repository en imagevariant.
  De uitkomst **Nieuwe tag gevonden** betekent alleen dat het nummer
  nieuwer is, niet dat deze software of image veilig geïnstalleerd kan worden.
- Verschillende architecturen, OS-varianten, API-/databasecompatibiliteit
  en breaking changes worden **niet** gevalideerd; controleer release notes,
  back-ups en herstelbaarheid vóór een echte update.
- Zonder expliciete knopdruk is er geen netwerkvraag aan Docker Hub.
  De gecontroleerde repositorynaam wordt wel naar Docker Hub verstuurd
  zodra je op de knop drukt.
- Het dashboard bewaart de laatste checkstatus, niet de beslissing om te
  updaten. Geen pull, restart, build, deployment of AI-mutatie.
- **Niet gecontroleerd** en **Niet ondersteund** blijven expliciet zichtbaar.
  Als de taglijst niet volledig kon worden doorzocht wordt dat vermeld.

### Softwareversie vs image-tag (correctie na test met Homarr)

De oorspronkelijke Docker Hub tagvergelijker kon `alpine:3.20` onjuist
vergelijken met een datumtag als `20260805`. CodePug vergelijkt die
verschillende nummeringssystemen nu **niet meer**. Oude controle-uitkomsten
worden ongeldig gemaakt en na een nieuwe scan opnieuw beoordeeld.

Er is nu een **eerste applicatie-releaseprovider voor Homarr**:

- Voor `ghcr.io/homarr-labs/homarr:latest` vraagt CodePug, uitsluitend
  na ingeschakelde automatische controle of handmatige klik, de officiële
  GitHub-release van `homarr-labs/homarr` op.
- Is de geïnstalleerde applicatieversie **onbekend**, dan verschijnt
  **Software-release gevonden, huidige versie onbekend**. Het telt niet als
  bevestigde update. Een Docker `:latest`-tag is geen versiebewijs.
- Wanneer een gekoppelde hostagent een geldige OCI-versielabel
  `org.opencontainers.image.version` terugstuurt, kan CodePug de
  geïnstalleerde en nieuwste Homarr-versies vergelijken. Sommige images
  hebben dit label niet.
- Een recente GitHub-release is niet hetzelfde als een al beschikbare,
  compatibele GHCR-image. Geen pull, deploy of restart wordt uitgevoerd.
- De bestaande lokale v0.4 MCP-snapshot bevat alleen image en status;
  CodePug kan daaruit **geen** actuele Homarr-applicatieversie of image-digest
  afleiden. Voor bevestiging van een update moet die bewijslijn nog worden
  uitgebreid met lokale inspectie + registry-digestvergelijking.
- Voor andere `ghcr.io`-images zijn nog geen officiële releaseproviders
  geconfigureerd. CodePug meldt expliciet onbekend of niet ondersteund.

### Achtergrondversiecontrole (nieuwe functionele mijlpaal)

Een **afzonderlijke version-watcher-container** draait onafhankelijk van de browser,
met uitsluitend netwerktoegang naar de publieke Docker Hub API en leestoegang
tot de inventaris. De watcher heeft geen dashboardwachtwoord in zijn omgeving,
geen Docker-socket, geen SSH of shellrechten op de host, en geen open poort.

- Standaard staat de uitgaande achtergrondcontrole **uit**. Zet deze via
  **Instellingen → Automatische versiecontrole** aan om expliciet toestemming
  te geven voor het controleren van publieke Docker Hub-imagenamen.
- Interval: 6, 12, 24, 48 of 168 uur (standaard 24 uur na inschakelen).
  Om scans te spreiden verwerkt de watcher maximaal vier unieke imagenamen
  per minuut; grote omgevingen zijn daarom niet direct volledig bijgewerkt.
- Alleen de actuele inventaris van **online hosts** wordt gebruikt.
  Checks van dezelfde imagenaam worden gedeeld over diensten.
- Checkresultaten en het tijdstip van de laatste check worden in SQLite bewaard.
  Bij een nieuw gevonden kandidaattag volgt een event
  `update-candidate`, zonder duplicaten bij dezelfde versie.
- De hoofdpagina toont **Nieuwe versies gevonden** en de actuele scanstand.
  Het dienstenoverzicht heeft een filter op versiecontrole.
- Dit is een **tagwaarschuwing, geen beveiligings- of compatibiliteitsadvies**.
  De check kan niet aantonen dat een update veilig, geschikt of verplicht is.
- Bij `:latest`, image-digests, GHCR en andere registries is de status
  (voorlopig) **Niet ondersteund**. Reeds uitgevoerde scans worden niet
  ongevraagd naar externe AI-servers verstuurd.

**Wat nog ontbreekt:** een echte herstelagent, back-upverificatie,
beschikbaarheidsbewaking buiten de snapshotcollector, alerts buiten
het geopende dashboard, en ondersteuning voor GHCR/digest-vergelijking.

Toekomstig: adapters voor **GHCR**, private registries,
same-tag digest updates en architectuur-/compatibiliteitscontrole. Een
nieuwe beschikbare versie is nooit automatisch een verplichte update.

## Roadmap voor v0.7

### R1 — Back-upinventaris via adapters

Adapters voor bestaande back-upsystemen zoals restic, Borg, kopieën van
Compose-configuraties, database-dumps en ondersteunde NAS-/hypervisorback-ups.
Elke adapter levert gestructureerd bewijs met timestamp, bron, doel en
verificatiemethode. **Een bestand dat bestaat is niet automatisch een
gevalideerde back-up.** Secretbestanden en inhoud worden nooit gelogd.

### R2 — Onafhankelijke hersteltests

Herstellen naar een geïsoleerde testomgeving, met checks op
dataconsistentie en werkende applicatiefunctionaliteit. Resultaat
wordt per back-up als bewijs bewaard.

### R3 — Veilige herstelagent en goedkeuring

De agent krijgt een minimale, expliciete allowlist van acties (geen
algemene shelltool). Per herstelactie: host/service-ID, bevoegdheid,
maximale geldigheidsduur, backup-evidence, bevestiging, auditlog, rollback,
timeout en health checks. Kritieke databases mogen nooit stilzwijgend
automatisch worden teruggezet.

### R4 — Redundantie en failover

Een tweede onafhankelijke opslaglocatie/host en gecontroleerd
overnameplan voor geselecteerde diensten. Redundantie is niet hetzelfde
als back-up. De centrale CodePug-hub vereist een **externe onafhankelijke**
monitor en herstelroute, anders is de bewaker zelf een single point of failure.

### R5 — ChatGPT als beheerassistent

Een centrale MCP-server met least-privilege scopes per host en service.
Onderzoeken is standaard read-only. Uitvoerende workflows vragen
actiespecifieke toestemming en altijd server-side beleidscontrole;
een AI-model krijgt geen onbeperkte Docker- of shelltoegang.
Ingebouwde chat is optioneel en vereist aparte AI-provider/configuratie.

### R6 — Volwassen beheerervaring

Licht/donker, echte CodePug-merkbestanden, eigen pagina's voor diensten en
instellingen, eenvoudige installatiewizard, storingsdossiers en
duidelijke taalmogelijkheden.

## Bewust nog niet aanwezig

- Geen werkelijk gedetecteerde back-ups of back-upschema's.
- Geen restore-/redundantietesten.
- Geen herstel- of restartknop en geen automatische update-runner.
- Geen kant-en-klare Synology/Proxmox-back-upadapter.
- Geen ingebouwde AI-chat of zelfstandige AI-agent.

De pagina mag nooit groen **'Beschermd'** tonen zonder bewijs.

## Ontwikkelinstallatie

Zie `QUICKSTART-V07-NL.md`. Standaard is poort **8770** op localhost,
apart van v0.5 (8768) en v0.6 (8769). **Niet installeren in de bestaande
mappen** en bestaande databases/back-ups nooit overschrijven.
