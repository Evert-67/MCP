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
