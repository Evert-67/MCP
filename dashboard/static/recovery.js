/* CodePug v0.7 — backup/recovery coverage without claiming backups exist. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const t = s => window.CodePugI18n?.t(s) || s;
  let services = [];
  let updating = false;

  async function getJson(url) {
    const response = await fetch(url, {credentials:"same-origin", cache:"no-store"});
    if (!response.ok) throw new Error("HTTP " + response.status);
    return response.json();
  }

  function hostRow(host) {
    const row = document.createElement("div");
    row.className = "recovery-host";
    const block = document.createElement("div");
    const heading = document.createElement("strong");
    heading.textContent = host.label;
    const detail = document.createElement("small");
    detail.textContent = host.service_count + " " + t("diensten") + " · " +
      host.critical_services + " " + t("kritieke diensten");
    block.append(heading,detail);
    const badge = document.createElement("span");
    badge.className = "recovery-unknown";
    badge.textContent = t("Back-up onbekend");
    row.append(block,badge);
    return row;
  }

  function populateServices(state) {
    services = Array.isArray(state.services) ? state.services : [];
    const select = $("recovery-service");
    const previous = select.value;
    const hosts = Object.fromEntries((state.servers || []).map(h=>[h.id,h.label]));
    select.replaceChildren();
    for (const service of [...services].sort((a,b)=>
        (a.name || "").localeCompare(b.name || ""))) {
      const option = document.createElement("option");
      option.value = service.key;
      option.textContent = (hosts[service.server_id] || service.server_id) +
        " / " + service.name;
      select.append(option);
    }
    if (services.some(s=>s.key===previous)) select.value=previous;
    select.disabled = !services.length;
    $("recovery-plan-button").disabled = !services.length;
  }

  async function update(state) {
    if (updating) return;
    updating=true;
    try {
      populateServices(state);
      const result = await getJson("/api/recovery/overview");
      $("recovery-host-count").textContent = String(result.hosts?.length ?? 0);
      $("recovery-backup-count").textContent = t("Onbekend");
      $("recovery-restore-count").textContent = t("Niet getest");
      $("recovery-warning").textContent = result.notice;
      const parent = $("recovery-host-list");
      parent.replaceChildren();
      if (!result.hosts.length) {
        const empty=document.createElement("p");
        empty.className="helper";
        empty.textContent=t("Geen hosts beschikbaar.");
        parent.append(empty);
      } else {
        result.hosts.forEach(host=>parent.append(hostRow(host)));
      }
    } catch (err) {
      $("recovery-warning").textContent =
        t("Recoveryoverzicht kon niet worden geladen:") + " " + err.message;
    } finally {updating=false;}
  }

  async function plan() {
    const select = $("recovery-service");
    if (!services.some(s=>s.key===select.value)) return;
    const button=$("recovery-plan-button");
    button.disabled=true;
    $("recovery-plan-output").replaceChildren();
    try {
      const report=await getJson("/api/recovery/plan?service_key="+
        encodeURIComponent(select.value));
      const title=document.createElement("h3");
      title.textContent=report.host+" / "+report.service;
      const warning=document.createElement("p");
      warning.className="recovery-warning";
      warning.textContent=report.warning;
      const list=document.createElement("ol");
      list.className="recovery-checklist";
      (report.proposed_steps || []).forEach(step=>{
        const li=document.createElement("li");
        li.textContent=step;
        list.append(li);
      });
      const note=document.createElement("small");
      note.textContent=t("Planning, geen uitvoering. Eerst bewijs, toestemming en hersteltest.");
      $("recovery-plan-output").append(title,warning,list,note);
    } catch (err) {
      const p=document.createElement("p");
      p.className="recovery-warning";
      p.textContent=t("Herstelplan kon niet worden geladen:")+" "+err.message;
      $("recovery-plan-output").append(p);
    } finally {button.disabled=!services.length;}
  }

  $("recovery-plan-button").addEventListener("click",plan);
  document.addEventListener("codepug-state-loaded",event=>update(event.detail));
})();
