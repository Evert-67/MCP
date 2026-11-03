# Security checklist

- Dashboard staat standaard achter loopback, met HTTP Basic via PBKDF2 SHA-256; gebruik TLS of SSH bij bereikbaarheid vanaf andere apparaten.
- Alle muterende dashboardroutes vereisen zowel login als header `X-CodePug-Request: 1`, met origin-controle. Geen wildcard CORS.
- De agent accepteert alleen een individueel token voor POST. Tokens worden eenmalig getoond en gehasht in SQLite. Agent krijgt geen toegang tot web-API voor beleid.
- De container gebruikt UID 10001, read-only filesystem, `no-new-privileges`, `cap_drop: ALL` en slechts één beperkte bindmount voor status.
- Beheer niet te autoriseren op basis van de OpenAI-tunnel alleen. Update-uitvoering moet óók op hostniveau worden afgeschermd.
- Gevoelige bestanden zoals `.env`, API keys, tunnel-sleutels, private screenshots en server-back-ups komen nooit op de publieke GitHub-repo.
- Docker-groepslidmaatschap is root-equivalent: de agent moet lokaal als vertrouwde beheercomponent draaien. De webcontainer krijgt geen Docker-socket.
- `:latest` is ongeschikt voor volledig automatische upgrades, zeker bij persistente data.
- Beperk ingestorapporten tot max. 256 kB en maximaal 500 containers. Rate-limiting bij publieke inzet op reverse proxy noodzakelijk.
- **Niet afgedekt v0.5:** tokenrotatie, UI-multifactor, uitgebreid rollenmodel, harde update-executie, supply-chain verificatie. Niet publiek vrijgeven zonder aanvullende hardening.
- Bij HTTPS achter Nginx Proxy Manager: stel `DASHBOARD_PUBLIC_ORIGIN=https://jouw-domein` in zodat wijzigingsverzoeken van de juiste herkomst worden geaccepteerd.
