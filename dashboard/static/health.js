/* CodePug v0.7: evidence-based Linux + Docker + app health, no actions. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const make = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = String(value);
    return node;
  };
  const dash = value => value === null || value === undefined || value === ""
    ? "Onbekend" : String(value);

  function metric(label, value) {
    const row = make("div", "health-fact");
    row.append(make("span", "", label), make("strong", "", dash(value)));
    return row;
  }

  function renderHost(host) {
    const details = make("details", "health-host");
    details.open = host.high_count > 0 || !host.agent_evidence;
    const summary = make("summary", "health-host-summary");
    const meta = make("div", "health-host-title");
    meta.append(make("strong", "", host.label),
      make("small", "", host.agent_evidence
        ? "Linux + Docker: hostmeting beschikbaar"
        : "Alleen inventaris: uitgebreidere metingen ontbreken"));
    const badge = make("span", "health-pill " +
      (host.high_count ? "high" : host.review_count ? "review" : "unknown"),
      host.high_count ? host.high_count + " urgent te onderzoeken"
        : host.review_count ? host.review_count + " te beoordelen"
        : host.agent_evidence ? "Geen afwijking aangetoond" : "Onvoldoende bewijs");
    summary.append(meta, badge);
    details.append(summary);

    const body = make("div", "health-host-detail");
    const cards = make("div", "health-facts");
    const linux = make("section", "health-fact-card");
    linux.append(make("h3", "", "Linux"));
    if (host.linux && host.linux.scan_status === "read_only") {
      linux.append(
        metric("Versie", host.linux.pretty_name || host.linux.version),
        metric("Kernel", host.linux.kernel),
        metric("Systeemstatus", host.linux.system_state),
        metric("APT-updates (cache)", host.linux.updates_available),
        metric("Herstart noodzakelijk", host.linux.reboot_required === null
          ? "Onbekend" : host.linux.reboot_required ? "Ja" : "Nee")
      );
      linux.append(make("small", "health-caveat",
        "Beschikbare pakketten zijn geteld zonder APT-cache te verversen."));
    } else {
      linux.append(make("p", "health-unknown", "Linux-meting niet aangesloten."));
    }
    const docker = make("section", "health-fact-card");
    docker.append(make("h3", "", "Docker"));
    if (host.docker && host.docker.scan_status === "read_only") {
      docker.append(
        metric("Daemon", host.docker.daemon_active === null
          ? "Onbekend" : host.docker.daemon_active ? "Actief" : "Niet actief"),
        metric("Engine", host.docker.server_version),
        metric("CLI", host.docker.client_version),
        metric("Compose", host.docker.compose_version),
        metric("APT Docker-updates", host.docker.apt_package_update_available === null
          ? "Onbekend" : host.docker.apt_package_update_available
          ? "Nieuwere pakketten beschikbaar" : "Geen nieuwere in pakketcache"),
        metric("Nieuwste upstream-versie?", "Nog niet geverifieerd")
      );
    } else {
      docker.append(make("p", "health-unknown", "Docker-versiecontrole niet aangesloten."));
    }
    cards.append(linux, docker);
    body.append(cards);

    const probes = make("section", "health-probes");
    probes.append(make("h3", "", "Applicaties en bereikbaarheid"));
    if (!host.app_checks?.length) {
      probes.append(make("p", "health-unknown",
        "Geen app-controles gekoppeld. Een draaiende container bewijst niet dat de webapp of API goed werkt."));
    } else {
      host.app_checks.forEach(p => {
        const statusText = ({
          reachable: "HTTP bereikbaar, functie niet getest",
          auth_required: "Reageert: authenticatie vereist",
          error: "Serverfout",
          unreachable: "Niet bereikbaar",
          review: "Status beoordelen",
          unknown: "Onbekend"
        })[p.status] || "Onbekend";
        const row = make("div", "health-probe");
        row.append(make("strong", "", p.name),
          make("span", "", statusText + (p.http_status ? " (" + p.http_status + ")" : "")));
        probes.append(row);
      });
    }
    body.append(probes);

    const findings = make("section", "health-findings");
    findings.append(make("h3", "", "Advies en onderzoeksstappen"));
    if (!host.findings?.length) {
      findings.append(make("p", "health-unknown",
        "Geen afwijking aangetoond in de beschikbare metingen. Dit is geen volledige gezondheidsverklaring."));
    } else {
      host.findings.forEach(finding => {
        const entry = make("div", "health-finding " + finding.severity);
        const title = make("div", "health-finding-title");
        title.append(make("strong", "", finding.subject),
          make("span", "", finding.severity === "high" ? "Onderzoeken"
            : finding.severity === "review" ? "Beoordelen" : "Onbekend"));
        entry.append(title,
          make("p", "", finding.observation),
          make("small", "", finding.recommendation));
        findings.append(entry);
      });
    }
    body.append(findings);
    const disclaimer = make("p", "health-caveat",
      "Read-only rapport. CodePug heeft geen herstel uitgevoerd, geen back-up bevestigd en geen toestemming gevraagd voor een actie.");
    body.append(disclaimer);
    details.append(body);
    return details;
  }

  async function refreshHealth() {
    const out = $("health-host-list");
    try {
      const response = await fetch("/api/health/overview",
        {credentials: "same-origin", cache: "no-store"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      const result = await response.json();
      $("health-hosts").textContent = dash(result.summary?.hosts);
      $("health-agent-coverage").textContent =
        dash(result.summary?.hosts_with_deep_evidence);
      $("health-probes").textContent = dash(result.summary?.app_probes);
      $("health-findings").textContent = dash(result.summary?.high_findings);
      $("health-notice").textContent = result.notice;
      out.replaceChildren();
      for (const host of result.hosts || []) out.append(renderHost(host));
      if (!result.hosts?.length) {
        out.append(make("p", "health-unknown", "Er zijn nog geen hosts aangesloten."));
      }
    } catch (error) {
      $("health-notice").textContent =
        "De systeemcontrole kon niet worden geladen: " + error.message;
    }
  }

  document.addEventListener("codepug-state-loaded", refreshHealth);
})();
