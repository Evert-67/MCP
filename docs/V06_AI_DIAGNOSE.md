# CodePug v0.6 — AI & Diagnose (eerste ontwikkelmijlpaal)

> **Status: draft.** v0.6 is NIET actief op de homeserver. De geteste v0.5 blijft staan.
> Geen ingebouwde LLM, geen automatische logboektoegang en geen mutatie-/herstelrechten.

## Wat deze mijlpaal echt doet

1. In de linker navigatie verschijnt **AI & Diagnose**.
2. Kies een van de diensten uit de gecombineerde inventaris van lokale snapshots en gekoppelde hosts.
3. Een nieuwe, geauthenticeerde **GET /api/diagnostics?service_key=...** endpoint geeft een **read-only** rapport.
4. De beheerder ziet status, bekende symptomen, suggesties voor aanvullende controles en de exacte tekst voor ChatGPT.
5. De knop **Kopieer rapport** is pas beschikbaar na expliciete bevestiging.
6. **Open ChatGPT** opent de website zonder gegevens mee te sturen. De gebruiker plakt de tekst zelf in een conversatie. Als een MCP-connector al aan ChatGPT is gekoppeld, kan de assistent via die *afzonderlijke* connector read-only vervolgcontroles doen voor zover zijn rechten dat toestaan.

### Bewuste begrenzingen

- Het report is gebaseerd op **snapshots**; een scan kan verouderd zijn.
- **Geen** Docker-socket of uitvoerende opdrachten vanuit het dashboard.
- **Geen** logboeken, omgevingvariabelen, wachtwoorden, tokens, beleidsnotities of opgeslagen geheimen in het handoff-rapport.
- **Geen** bewering dat een back-up bestaat of terugzetbaar is; `backup_verified=false`.
- Een gestopte container betekent niet automatisch een incident; die kan bewust uit staan.
- De status `running` is geen bewijs dat de applicatie functioneel beschikbaar is.
- Geen data wordt automatisch naar een AI-provider verzonden.

## Architectuur voor de volgende mijlpalen

```text
CodePug Web / API / Incident Store
  ├─ Inventaris & Policy (bestaand)
  ├─ AI & Diagnose: evidence snapshot (nu)
  ├─ MCP Gateway met scopes per host/service (gepland)
  └─ Approval / Audit / Recovery workflow (gepland)
          │
          ├── Linux / Docker scanner (bestaand, read-only)
          ├── Synology DSM adapter (gepland)
          ├── Proxmox API adapter (gepland)
          └── Beperkte local recovery runner (gepland)
                         │
                         └─ Backup verification / rollback / post-checks (gepland)
```

De **MCP gateway** wordt het ene gecontroleerde aanknopingspunt voor ChatGPT. Elke host krijgt alleen-lezen statusrechten als standaard. Een handeling vraagt om afzonderlijke scopes en actie-specifieke toestemming met een vervaltijd, auditspoor, back-up- en health-checkregels. Een LLM krijgt nooit onbeperkte host-shell- of Docker-sockettoegang.

### Doelmatig vervolg voor v0.6

1. **Gebruikerservaring:** echte licht/donkerkeuze, correcte goedgekeurde CodePug-beelden, navigatie per hoofdscherm.
2. **Eenvoudige installatie:** begeleide setup, geen handmatig kopiëren van wachtwoordhashes, beheerderlogin met beter wachtwoordbeleid en passkey-ontwerp.
3. **Hostdetectie:** veilige out-bound agents; adapterinterface voor Synology/Proxmox/andere systemen met capability-advertising.
4. **MCP:** geauthenticeerde read-only status/diagnose-tools voor álle aangemelde hosts; selectieve logtoegang met redactie; host-level scopes.
5. **Herstel:** concept-runbooks, expliciete goedkeuring, back-upcontrole en rollback als voorwaarde voor ingrijpende acties.
6. **Storingsdossier:** tijdlijn met bewijs, diagnose, goedkeuring, acties en post-checks.
7. **Beschikbaarheid:** onafhankelijke externe monitor voor de CodePug hub zelf; scheiding tussen back-up en redundantie.

## Testen zonder productie te veranderen

Deze branch is gebaseerd op `feature/server-control-v0.5` en blijft daar los van.
GitHub Actions controleert Python/JS-syntax en diagnostische unit-/API-tests.
Gebruik bij het testen eerst een eigen testdeploy of een andere poort. **Niet** je werkende v0.5-directory overschrijven.

Voornaamste gebruiksscenario: de `source-supertokens-1` unhealthy-status (voor zover zichtbaar in een actuele snapshot). Deze mijlpaal kan de observatie beschrijven, maar kan zonder bevoegd gelezen logboek geen definitieve oorzaak vaststellen.
