/* CodePug v0.6: explicit, read-only ChatGPT handoff. No automatic data export. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const t = source => window.CodePugI18n?.t(source) || source;
  let services = [];
  let report = null;

  function message(text, error = false) {
    const el = $("diagnose-feedback");
    el.textContent = text;
    el.dataset.error = error ? "true" : "false";
  }

  function reset() {
    report = null;
    $("diagnose-output").textContent = t("Selecteer een dienst en klik op Diagnose maken.");
    $("diagnose-summary").textContent = t("Er is nog geen diagnose gemaakt.");
    $("diagnose-checks").replaceChildren();
    $("diagnose-consent").checked = false;
    $("diagnose-consent").disabled = true;
    $("diagnose-copy").disabled = true;
    $("diagnose-open-chatgpt").disabled = true;
    message("");
  }

  function updateServices(state) {
    const select = $("diagnose-service");
    const prior = select.value;
    services = Array.isArray(state?.services) ? state.services : [];
    const hosts = Object.fromEntries((state?.servers || []).map(h => [h.id, h.label]));
    const ordered = [...services].sort((a,b) => {
      const priority = s => /unhealthy/i.test(s.status || "") ? 0 :
        (s.state !== "running" ? 1 : 2);
      return priority(a) - priority(b) || a.name.localeCompare(b.name);
    });
    select.replaceChildren();
    for (const service of ordered) {
      const option = document.createElement("option");
      option.value = service.key;
      option.textContent = (hosts[service.server_id] || service.server_id) +
        " / " + service.name + (/unhealthy/i.test(service.status) ? " ⚠" : "");
      select.append(option);
    }
    select.disabled = !ordered.length;
    $("diagnose-make").disabled = !ordered.length;
    if (ordered.some(s => s.key === prior)) select.value = prior;
    else reset();
  }

  async function diagnose() {
    const key = $("diagnose-service").value;
    if (!services.some(s => s.key === key)) return;
    reset();
    message(t("Gegevens verzamelen..."));
    $("diagnose-make").disabled = true;
    try {
      const response = await fetch("/api/diagnostics?service_key=" + encodeURIComponent(key),
        {credentials: "same-origin", cache: "no-store"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      report = await response.json();
      $("diagnose-summary").textContent = report.summary;
      const list = $("diagnose-checks");
      for (const check of report.checks || []) {
        const li = document.createElement("li");
        li.textContent = check;
        list.append(li);
      }
      $("diagnose-output").textContent = report.handoff;
      $("diagnose-consent").disabled = false;
      message(t("Controleer de gegevens vóór je ze deelt met ChatGPT."));
    } catch (err) {
      message(t("Diagnose ophalen mislukt:") + " " + err.message, true);
    } finally {
      $("diagnose-make").disabled = !services.length;
    }
  }

  async function copy() {
    if (!report || !$("diagnose-consent").checked) return;
    try {
      await navigator.clipboard.writeText(report.handoff);
      message(t("Rapport gekopieerd. Plak het zelf in een ChatGPT-gesprek."));
    } catch (_) {
      message(t("Kopiëren niet toegestaan in deze browser. Selecteer de tekst handmatig."), true);
    }
  }

  $("diagnose-service").addEventListener("change", reset);
  $("diagnose-make").addEventListener("click", diagnose);
  $("diagnose-consent").addEventListener("change", () => {
    const permitted = Boolean(report && $("diagnose-consent").checked);
    $("diagnose-copy").disabled = !permitted;
    $("diagnose-open-chatgpt").disabled = !permitted;
  });
  $("diagnose-copy").addEventListener("click", copy);
  $("diagnose-open-chatgpt").addEventListener("click", () => {
    if (!report || !$("diagnose-consent").checked) return;
    window.open("https://chatgpt.com/", "_blank", "noopener,noreferrer");
    message(t("ChatGPT geopend. Plak het gekopieerde rapport handmatig."));
  });
  document.addEventListener("codepug-state-loaded", event => updateServices(event.detail));
  document.addEventListener("codepug-language-changed", () => {
    if (!report) reset();
  });
  reset();
})();
