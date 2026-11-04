/* CodePug multipage console — one task per screen, progressive enhancement. */
const PAGES = {
  overview:"Overzicht", servers:"Servers & diensten", incidents:"Incidenten",
  updates:"Updates", recovery:"Backup & Recovery",
  assistant:"AI-assistent", settings:"Instellingen"
};
const page = location.pathname.split("/").filter(Boolean)[1] || "overview";
const root = document.getElementById("cp-content");
let state = {servers:[],services:[],agents:[],settings:{}};
let incidentsCache = null;
let busy = false;

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for(const [key,value] of Object.entries(attrs||{})) {
    if(value===null || value===undefined) continue;
    if(key==="class") node.className=value;
    else if(key==="text") node.textContent=String(value);
    else if(key==="value") node.value=value;
    else if(key==="checked") node.checked=!!value;
    else if(key==="disabled") node.disabled=!!value;
    else if(key.startsWith("on") && typeof value==="function")
      node.addEventListener(key.slice(2),value);
    else node.setAttribute(key,String(value));
  }
  for(const child of children.flat(Infinity)) {
    if(child===null || child===undefined || child===false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}
const text=(content,cls="")=>el("p",{class:cls,text:content});
const small=s=>el("small",{class:"cp-small",text:s});
const link=(to,label)=>el("a",{class:"cp-button subtle",href:to,text:label});
const btn=(label,click,cls="subtle")=>el("button",{type:"button",class:"cp-button "+cls,onclick:click,text:label});
const pill=(label,kind="")=>el("span",{class:"cp-pill "+kind,text:label});
const card=(title,...content)=>el("section",{class:"cp-card"},el("h2",{text:title}),...content);
const head=(title,description,action)=>el("div",{class:"cp-page-head"},
  el("div",{},el("h1",{text:title}),text(description,"cp-muted")),action||null);
const list=(...children)=>el("div",{class:"cp-list"},...children);
const note=(message,kind="")=>el("div",{class:"cp-note "+kind,text:message});
const formatTime=value=>{
  if(!value)return "Nog geen meting";
  const d=new Date(value);
  return Number.isNaN(d.getTime()) ? "Onbekend" :
    d.toLocaleString("nl-NL",{dateStyle:"short",timeStyle:"short"});
};
const serviceRunning=s=>s.state==="running" || /^up\b/i.test(s.status||"");
const serviceUnhealthy=s=>/unhealthy/i.test(s.status||"");
const serviceLabel=s=>serviceUnhealthy(s)?"Ongezond":serviceRunning(s)?"Draait":"Gestopt / onbekend";
const serviceKind=s=>serviceUnhealthy(s)?"bad":serviceRunning(s)?"good":"warn";
const versionLabel=s=>{
  const u=s.update||{};
  if(u.status==="candidate")return "Nieuwere tag/release gevonden";
  if(u.status==="release_found")return "Officiële release gevonden, huidige versie onbekend";
  if(u.status==="no_newer_found")return "Geen nieuwere tag gevonden in onderzochte bron";
  if(u.status==="unsupported")return "Niet ondersteund";
  if(u.status==="check_failed")return "Controle mislukt";
  if(u.status==="incomplete")return "Controle onvolledig";
  return "Niet gecontroleerd";
};
const chosen=(obj,keys)=>keys.reduce((acc,k)=>acc&&acc[k],obj);
const names={};
function hostName(id) {
  return names[id] || id || "Onbekende host";
}
function stat(label,value,detail) {
  return el("section",{class:"cp-card"},
    small(label),el("div",{class:"cp-stat",text:value}),small(detail));
}
async function getJSON(path,options={}) {
  const r=await fetch(path,{credentials:"same-origin",cache:"no-store",...options});
  const body=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(body.detail||"HTTP "+r.status);
  return body;
}
async function postJSON(path,obj) {
  return getJSON(path,{method:"POST",
    headers:{"content-type":"application/json","x-codepug-request":"1"},
    body:JSON.stringify(obj)});
}
function addNotice(container,message,kind="warn") {
  container.prepend(note(message,kind));
}
function greet() {
  // Browser timezone (the user viewing the page), not the server's UTC clock.
  const hour=new Date().getHours();
  return hour<6?"Goedenacht":hour<12?"Goedemorgen":
         hour<18?"Goedemiddag":"Goedenavond";
}
function hostStatus(h) {
  return h.online ? pill("Meting actueel","good") : pill("Meting ontbreekt","warn");
}
function row(label,description,right) {
  return el("div",{class:"cp-list-item"},
    el("div",{},el("strong",{text:label}),small(description)),right||null);
}
function summaryIncidents(result) {
  return {
    high:result?.summary?.high||0,
    review:result?.summary?.review||0,
    grouped:result?.summary?.grouped||0,
    items:result?.incidents||[]
  };
}
async function incidents() {
  incidentsCache=await getJSON("/api/incidents");
  const count=summaryIncidents(incidentsCache).high;
  const badge=document.getElementById("cp-incidents-count");
  badge.hidden=count===0;
  badge.textContent=count;
  return incidentsCache;
}
function renderOverview(inc) {
  const findings=summaryIncidents(inc);
  const active=state.services.filter(serviceRunning).length;
  const updates=state.services.filter(s=>s.update?.status==="candidate").length;
  const greeting=greet()+", beheerder";
  const wrap=el("div",{},
    head(greeting,"Alles wat vandaag aandacht vraagt, zonder ruis.",
      link("/console/incidents","Bekijk incidenten")),
    el("div",{class:"cp-grid"},
      stat("Servers",state.servers.length,state.servers.filter(h=>h.online).length+" met actuele meting"),
      stat("Docker-diensten",state.services.length,active+" actief volgens containerstatus"),
      stat("Onderzoek nodig",findings.high,findings.grouped+" mogelijk gedeelde signalen"),
      stat("Versie-kandidaten",updates,"Niet automatisch installeren")
    ),
    el("div",{class:"cp-section-head"},el("h2",{text:"Prioriteiten"}),
      link("/console/incidents","Alle incidenten")));
  if(findings.items.length) {
    wrap.append(list(...findings.items.slice(0,4).map(item=>
      row(item.title,item.hypothesis||item.evidence[0]||"Nader onderzoek nodig",
          pill(item.severity==="high"?"Onderzoeken":"Beoordelen",
               item.severity==="high"?"bad":"warn")))));
  } else {
    wrap.append(card("Geen bekende incidenten in beschikbare gegevens",
      text("Dit betekent niet dat alle diensten functioneel zijn gecontroleerd. "
       +"Controleer de meetdekking van iedere server.","cp-muted")));
  }
  wrap.append(el("div",{class:"cp-section-head"},el("h2",{text:"Servers"}),
    link("/console/servers","Open serverbeheer")));
  wrap.append(el("div",{class:"cp-grid three"},...state.servers.map(h=>
    card(h.label,small(h.platform||h.type||"Platform onbekend"),
      text((h.container_count??0)+" diensten geregistreerd","cp-muted"),
      hostStatus(h)))));
  wrap.append(note("CodePug observeert voorlopig uitsluitend. De analyse kan netwerk- "
   +"of platformproblemen vermoeden, maar stelt nooit zonder aanvullend bewijs een hoofdoorzaak vast."));
  return wrap;
}
function renderServers() {
  const hostSelect=el("select",{class:"cp-select","aria-label":"Filter op server"},
    el("option",{value:"",text:"Alle servers"}),
    ...state.servers.map(h=>el("option",{value:h.id,text:h.label})));
  const search=el("input",{class:"cp-input",placeholder:"Zoek dienst of image...",
    "aria-label":"Zoek diensten"});
  const body=el("tbody",{});
  function paint() {
    const q=search.value.toLowerCase().trim();
    const services=state.services.filter(s=>
      (!hostSelect.value||s.server_id===hostSelect.value)&&
      [s.name,s.image,s.status].some(v=>String(v||"").toLowerCase().includes(q)));
    body.replaceChildren(...services.map(s=>
      el("tr",{},el("td",{},el("strong",{text:s.name}),
                   small(s.image||"Geen image-id")),
        el("td",{text:hostName(s.server_id)}),
        el("td",{},pill(serviceLabel(s),serviceKind(s))),
        el("td",{},pill({low:"Laag",medium:"Middel",high:"Hoog",critical:"Kritiek"}[s.risk]||"Onbekend")),
        el("td",{text:versionLabel(s)}),
        el("td",{},el("a",{href:"/console/assistant?service="+encodeURIComponent(s.key),
                           text:"Onderzoeken"})))));
    if(!services.length)
      body.append(el("tr",{},el("td",{colspan:"6",class:"cp-empty",text:"Geen diensten gevonden"})));
  }
  hostSelect.addEventListener("change",paint);
  search.addEventListener("input",paint);
  const wrapper=el("div",{},head("Servers & diensten",
      "Per host Linux, Docker en software. Een draaiend proces is niet altijd een gezonde app."),
    el("div",{class:"cp-grid three"},...state.servers.map(h=>
      card(h.label,hostStatus(h),
        text("Platform: "+(h.platform||"Onbekend"),"cp-muted"),
        small("Laatste meting: "+formatTime(h.collected_at)),
        small("Diensten: "+(h.container_count??0)),
        link("/console/incidents","Bekijk afwijkingen")))),
    el("div",{class:"cp-section-head"},el("h2",{text:"Dienstenoverzicht"})),
    el("div",{class:"cp-actions-inline cp-filterbar"},search,hostSelect),
    el("div",{class:"cp-table-wrap"},
      el("table",{class:"cp-table"},
        el("thead",{},el("tr",{},
          ...["Dienst","Host","Docker","Risico","Versiecontrole","Diagnose"].map(s=>
            el("th",{text:s})))),
        body)));
  paint();
  return wrapper;
}
function renderIncidents(payload) {
  const sorted=summaryIncidents(payload);
  const filters=el("select",{class:"cp-select","aria-label":"Incidentfilter"},
    el("option",{value:"all",text:"Alle aandachtspunten"}),
    el("option",{value:"high",text:"Onderzoeken"}),
    el("option",{value:"review",text:"Beoordelen"}),
    el("option",{value:"group",text:"Gedeeld probleem vermoed"}));
  const results=el("div",{class:"cp-list"});
  function paint() {
    results.replaceChildren();
    const shown=sorted.items.filter(i=>filters.value==="all"||
      filters.value===i.severity||
      filters.value==="group"&&["host","platform","shared-symptom"].includes(i.scope));
    for(const item of shown) {
      const detail=el("details",{class:"cp-detail"});
      detail.append(el("summary",{},
        item.title+" — "+(item.severity==="high"?"Onderzoeken":"Beoordelen")),
        el("div",{class:"cp-stack"},
          item.hypothesis?note(item.hypothesis,"warn"):null,
          el("div",{},el("strong",{text:"Wat weten we?"}),
            ...item.evidence.map(x=>text(x,"cp-muted"))),
          el("div",{},el("strong",{text:"Vervolgcontrole"}),text(item.next_step)),
          item.affected_services?.length?
            small("Betrokken diensten: "+item.affected_services.join(", ")):null,
          note("Mogelijke oorzaak, geen vastgestelde root cause. Uitvoering is geblokkeerd.")
        ));
      results.append(detail);
    }
    if(!shown.length)results.append(card("Geen incidenten in dit filter",
      text("Let op: zonder voldoende meetgegevens kunnen incidenten onzichtbaar blijven.","cp-muted")));
  }
  filters.addEventListener("change",paint);
  paint();
  return el("div",{},
    head("Incidenten","Eén probleem tegelijk, met aandacht voor gedeelde oorzaken en netwerkafhankelijkheden."),
    el("div",{class:"cp-grid three"},
      stat("Onderzoeken",sorted.high,"Signalen die aandacht vragen"),
      stat("Beoordelen",sorted.review,"Kan bewust uitgeschakeld zijn"),
      stat("Gedeelde signalen",sorted.grouped,"Geen bewezen netwerkoorzaak")),
    el("div",{class:"cp-section-head"},el("h2",{text:"Onderzoeksdossier"}),filters),
    note(payload.notice||"Zonder hostagent zijn netwerk-, DNS- en applicatiefouten beperkt zichtbaar."),
    results);
}
function renderUpdates() {
  const results=el("div",{class:"cp-list"});
  const feedback=el("div",{});
  function paint() {
    results.replaceChildren(...state.services.map(s=>{
      const u=s.update||{};
      const action=btn("Versie controleren",async()=>{
        action.disabled=true;
        feedback.replaceChildren(note("Versiecontrole uitgevoerd op verzoek. Er worden geen updates geïnstalleerd."));
        try {
          const result=await postJSON("/api/updates/check",{service_key:s.key});
          s.update={...result,checked_at:new Date().toISOString()};
          paint();
        } catch(error) { feedback.replaceChildren(note("Versiecontrole mislukt: "+error.message,"bad")); }
        finally { action.disabled=false; }
      });
      return row(s.name+" · "+hostName(s.server_id),
        (s.image||"Image onbekend")+" · "+versionLabel(s)+
        (u.checked_at?" · "+formatTime(u.checked_at):""),action);
    }));
  }
  paint();
  const candidates=state.services.filter(s=>s.update?.status==="candidate").length;
  const unknown=state.services.filter(s=>s.update?.status==="release_found").length;
  return el("div",{},head("Updates","Beschikbare versies en bewijs: vergelijken is niet hetzelfde als veilig updaten."),
    el("div",{class:"cp-grid three"},
      stat("Kandidaten",candidates,"Versieverschil nog niet op compatibiliteit getoetst"),
      stat("Versie onbekend",unknown,"Officiële release gevonden, geïnstalleerde versie niet bewezen"),
      stat("Automatische scan",state.settings?.auto_version_checks?"Aan":"Uit",
           "Alleen expliciet ondersteunde bronnen")),
    el("div",{class:"cp-section-head"},el("h2",{text:"Diensten"}),
      link("/console/settings","Scaninstellingen")),
    feedback,results,
    note("Een nieuwere tag of release is geen beveiligingsadvies. "
      +"Er zijn geen automatische downloads, Docker pulls of herstarts.","warn"));
}
async function renderRecovery() {
  const data=await getJSON("/api/recovery/overview");
  const selector=el("select",{class:"cp-select","aria-label":"Kies een dienst"},
    ...state.services.map(s=>el("option",{value:s.key,
        text:hostName(s.server_id)+" / "+s.name})));
  const output=el("div",{});
  const action=btn("Maak herstelplan (alleen lezen)",async()=>{
    if(!selector.value)return;
    action.disabled=true;
    try {
      const plan=await getJSON("/api/recovery/plan?service_key="+encodeURIComponent(selector.value));
      output.replaceChildren(
        card(plan.service+" · herstelvoorbereiding",
          note(plan.warning||"Back-up en herstel niet geverifieerd.","warn"),
          el("ol",{},...plan.proposed_steps.map(step=>el("li",{text:step}))),
          small("Dit is een checklist; uitvoeren is niet mogelijk.")));
    }catch(err){output.replaceChildren(note("Kan plan niet laden: "+err.message,"bad"))}
    finally{action.disabled=false}
  });
  action.disabled=state.services.length===0;
  return el("div",{},head("Backup & Recovery",
      "Eerst zekerheid over back-ups en herstelbaarheid. Nooit gokken met productiedata."),
    el("div",{class:"cp-grid three"},
      stat("Hosts",data.hosts.length,"Inventaris beschikbaar"),
      stat("Back-upstatus","Onbekend","Geen backup-integratie aangesloten"),
      stat("Restore-tests","Niet getest","Geen herstelbewijs")),
    el("div",{class:"cp-section-head"},el("h2",{text:"Herstelgereedheid per host"})),
    list(...data.hosts.map(h=>
      row(h.label,h.service_count+" diensten · back-up niet geverifieerd",
        pill("Niet geverifieerd","warn")))),
    el("div",{class:"cp-section-head"},el("h2",{text:"Herstelplan voorbereiden"})),
    card("Kies de betreffende dienst",
      el("div",{class:"cp-field"},el("label",{text:"Dienst"}),selector),
      action,output),
    note("Er bestaat nog geen uitvoerende herstelagent. Geen back-up, restore, "
      +"failover of rollback wordt door dit scherm uitgevoerd."));
}
async function renderAssistant() {
  const select=el("select",{class:"cp-select","aria-label":"Dienst voor diagnose"},
    ...state.services.map(s=>el("option",{value:s.key,
      text:hostName(s.server_id)+" / "+s.name})));
  const query=new URLSearchParams(location.search).get("service");
  if(query&&state.services.some(s=>s.key===query))select.value=query;
  const consent=el("input",{type:"checkbox",id:"cp-diagnose-consent"});
  const output=el("div",{});
  const copy=btn("Kopieer rapport",async()=>{}, "subtle");
  copy.disabled=true;
  let report="";
  copy.addEventListener("click",async()=>{
    if(!consent.checked||!report)return;
    try { await navigator.clipboard.writeText(report); }
    catch {
      output.append(note("Automatisch kopiëren werkt niet. Selecteer de rapporttekst handmatig."));
    }
  });
  const show=btn("Maak read-only diagnose",async()=>{
    if(!select.value)return;
    show.disabled=true;copy.disabled=true;report="";
    try {
      const data=await getJSON("/api/diagnostics?service_key="+encodeURIComponent(select.value));
      report=data.handoff||"";
      output.replaceChildren(
        card("Voorlopige analyse",text(data.summary||"Geen samenvatting"),
          el("strong",{text:"Nader controleren"}),
          el("ol",{},...(data.checks||[]).map(c=>el("li",{text:c}))),
          note("Deze rapportage is niet automatisch naar ChatGPT gestuurd.")),
        el("pre",{class:"cp-pre",text:report}));
      copy.disabled=!consent.checked;
    } catch(err){output.replaceChildren(note("Diagnose mislukt: "+err.message,"bad"))}
    finally{show.disabled=false}
  });
  show.disabled=state.services.length===0;
  consent.addEventListener("change",()=>{copy.disabled=!consent.checked||!report});
  return el("div",{},head("AI-beheerassistent",
      "Samen onderzoeken: bewijs verzamelen, oorzaak verifiëren, daarna pas een actievoorstel."),
    el("div",{class:"cp-grid two"},
      card("Onderzoek één dienst",
        el("div",{class:"cp-field"},el("label",{text:"Dienst"}),select),
        show,
        el("div",{class:"cp-divider"}),
        el("label",{class:"cp-actions-inline"},consent,
          "Ik geef toestemming om dit gesaneerde rapport zelf met ChatGPT te delen."),
        el("div",{class:"cp-actions-inline"},copy,
          el("a",{class:"cp-button subtle",href:"https://chatgpt.com/",
            target:"_blank",rel:"noopener noreferrer",text:"Open ChatGPT"}))),
      card("Bevoegdheden",pill("Alleen lezen","warn"),
        text("De AI-assistent is nog geen ingebouwde chat met uitvoeringsrechten.",
             "cp-muted"),
        text("ChatGPT kan diagnoses bespreken en adviezen geven. "
          +"Een losse herstelagent met actiegebonden toestemming, rollback en audit "
          +"moet nog worden gebouwd.","cp-muted"))),
    el("div",{class:"cp-section"},output));
}
function settingField(label,id,options,current) {
  return el("div",{class:"cp-field"},
    el("label",{for:id,text:label}),
    el("select",{id,class:"cp-select"},
      ...options.map(([value,name])=>el("option",
        {value:String(value),text:name,selected:String(value)===String(current)?"selected":null}))));
}
function renderSettings() {
  const s=state.settings||{};
  const feedback=el("div",{});
  const refresh=settingField("Dashboard verversen","cp-refresh-setting",
    [[15,"15 seconden"],[30,"30 seconden"],[60,"1 minuut"],[120,"2 minuten"],[300,"5 minuten"]],
    s.refresh_seconds??60);
  const offline=settingField("Server als offline markeren na","cp-offline-setting",
    [[180,"3 minuten"],[300,"5 minuten"],[600,"10 minuten"],[900,"15 minuten"],[1800,"30 minuten"]],
    s.offline_after_seconds??300);
  const alerts=el("input",{type:"checkbox",checked:s.alerts_enabled!==false});
  const unhealthy=el("input",{type:"checkbox",checked:s.notify_unhealthy!==false});
  const enabled=el("input",{type:"checkbox",checked:s.auto_version_checks===true});
  const interval=settingField("Automatische versiecontrole","cp-version-interval",
    [[6,"Elke 6 uur"],[12,"Elke 12 uur"],[24,"Elke 24 uur"],
     [48,"Elke 2 dagen"],[168,"Elke week"]],s.version_check_interval_hours??24);
  const form=el("form",{class:"cp-stack"},
    el("div",{class:"cp-grid two"},
      card("Monitoring",refresh,offline,
        el("label",{class:"cp-actions-inline"},alerts,"Waarschuwingen tonen"),
        el("label",{class:"cp-actions-inline"},unhealthy,"Ongezonde containers melden")),
      card("Update- en versiebeleid",
        el("label",{class:"cp-actions-inline"},enabled,
          "Versietags op de achtergrond controleren"),interval,
        small("Opt-in: ondersteunde openbare imagenamen worden bij een registry opgezocht. "
          +"Software wordt nooit automatisch geïnstalleerd."))),
    card("Weergave",small("De licht/donker-keuze rechtsboven geldt alleen voor deze browser.")),
    el("div",{class:"cp-actions-inline"},
      el("button",{type:"submit",class:"cp-button",text:"Instellingen opslaan"})));
  form.addEventListener("submit",async e=>{
    e.preventDefault();
    const button=form.querySelector('[type="submit"]');button.disabled=true;
    try {
      const newSettings={
        refresh_seconds:Number(refresh.querySelector("select").value),
        offline_after_seconds:Number(offline.querySelector("select").value),
        alerts_enabled:alerts.checked,notify_unhealthy:unhealthy.checked,
        auto_version_checks:enabled.checked,
        version_check_interval_hours:Number(interval.querySelector("select").value)
      };
      const result=await postJSON("/api/settings",newSettings);
      state.settings=result.settings;
      feedback.replaceChildren(note("Instellingen opgeslagen."));
    }catch(err){feedback.replaceChildren(note("Niet opgeslagen: "+err.message,"bad"))}
    finally{button.disabled=false}
  });
  const agentName=el("input",{class:"cp-input",placeholder:"Bijvoorbeeld: Mediaserver",
    maxlength:"80",minlength:"2",required:"required","aria-label":"Naam nieuwe agent"});
  const tokenBlock=el("div",{});
  const addForm=el("form",{class:"cp-actions-inline"},agentName,
    el("button",{type:"submit",class:"cp-button",text:"Agent registreren"}));
  addForm.addEventListener("submit",async e=>{
    e.preventDefault();
    try {
      const created=await postJSON("/api/agents",{label:agentName.value.trim()});
      tokenBlock.replaceChildren(
        note("Bewaar dit token direct en uitsluitend op de juiste host. "
             +"Het wordt hier maar één keer getoond. Geef het nooit aan ChatGPT."),
        el("div",{class:"cp-field"},el("label",{text:"Agent-ID"}),
          el("input",{class:"cp-input",readonly:"readonly",value:created.id})),
        el("div",{class:"cp-field"},el("label",{text:"Eenmalig registratietoken"}),
          el("input",{class:"cp-input",readonly:"readonly",value:created.token})));
      agentName.value="";
      const current=await getJSON("/api/state");
      state.agents=current.agents||[];
      agents.replaceChildren(...agentRows());
    }catch(err){tokenBlock.replaceChildren(note("Kan agent niet registreren: "+err.message,"bad"))}
  });
  const agentRows=()=>state.agents.length?state.agents.map(a=>
    row(a.label,a.id+" · laatste meting "+formatTime(a.last_seen)+
      " · interval "+(a.scan_interval||120)+" sec.",
      pill(a.last_seen?"Geregistreerd":"Nog niet verbonden",
        a.last_seen?"good":"warn"))):[note("Nog geen externe agents gekoppeld.")];
  const agents=list(...agentRows());
  return el("div",{},head("Instellingen",
      "Gescheiden onderdelen voor monitoring, versiecontroles en hostkoppelingen."),
    feedback,form,
    el("div",{class:"cp-section-head"},el("h2",{text:"Hosts & agents"})),
    card("Bestaande agents",agents,
      el("div",{class:"cp-divider"}),
      el("h3",{text:"Nieuwe agent koppelen"}),addForm,tokenBlock,
      small("Registratie alleen maakt nog geen verbinding. "
        +"Een hostagent heeft een beveiligde uitgaande verbinding nodig.")));
}
async function show() {
  if(busy)return;
  busy=true;
  try {
    state=await getJSON("/api/state");
    Object.keys(names).forEach(k=>delete names[k]);
    state.servers.forEach(h=>names[h.id]=h.label);
    document.getElementById("cp-version").textContent=state.version||"test";
    document.getElementById("cp-updated").textContent="Vernieuwd "+new Date().toLocaleTimeString("nl-NL",{hour:"2-digit",minute:"2-digit"});
    const pages={
      overview:async()=>renderOverview(await incidents()),
      servers:async()=>renderServers(),
      incidents:async()=>renderIncidents(await incidents()),
      updates:async()=>renderUpdates(),
      recovery:renderRecovery,
      assistant:renderAssistant,
      settings:async()=>renderSettings()
    };
    const body=await pages[page]();
    root.replaceChildren(body);
  }catch(err) {
    root.replaceChildren(
      head("Gegevens niet beschikbaar","De servercontrole kan niet worden geladen."),
      note("Probeer opnieuw of controleer de verbinding. Details: "+err.message,"bad"));
  } finally {busy=false}
}
function theme(mode) {
  document.documentElement.dataset.theme=mode;
  try {localStorage.setItem("codepug-console-theme",mode)}catch{}
}
try {theme(localStorage.getItem("codepug-console-theme")||"dark")}
catch {theme("dark")}
document.getElementById("cp-theme").addEventListener("click",()=>{
  theme(document.documentElement.dataset.theme==="light"?"dark":"light");
});
document.getElementById("cp-refresh").addEventListener("click",show);
document.getElementById("cp-section").textContent=PAGES[page]||"Overzicht";
document.querySelectorAll("#cp-menu a[data-page]").forEach(a=>{
  if(a.dataset.page===page)a.setAttribute("aria-current","page");
});
show();
// Avoid clobbering forms or in-progress investigations with interval refresh.
if(!["settings","assistant","recovery"].includes(page))
  setInterval(()=>{if(!document.hidden)show()},60000);
