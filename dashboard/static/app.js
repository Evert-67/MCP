const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const i18n=window.CodePugI18n;
const t=(s,vars)=>i18n.t(s,vars);
const labels={low:'Laag',medium:'Middel',high:'Hoog',critical:'Kritiek',monitor:'Alleen volgen',approve:'Na goedkeuring',auto:'Automatisch (gepland)'};
let model={servers:[],services:[],events:[]};
function popup(title,html){$('modal-title').textContent=title;$('modal-content').innerHTML=html;$('overlay').hidden=false;i18n.translate($('overlay'))}
function close(){ $('overlay').hidden=true }
function toast(text){let t=$('toast');t.textContent=text;t.hidden=false;setTimeout(()=>t.hidden=true,4500)}
async function request(url,options={}){const r=await fetch(url,{credentials:'same-origin',...options});const p=await r.json().catch(()=>({}));if(!r.ok)throw Error(p.detail||`HTTP ${r.status}`);return p}
const running=c=>c.state==='running'||/^up\b/i.test(c.status);
function render(){const s=model.services||[], hosts=model.servers||[];
$('m-servers').textContent=hosts.length;$('m-online').textContent=t('{count} online',{count:hosts.filter(x=>x.online).length});$('m-containers').textContent=s.length;$('nav-count').textContent=s.length;
$('m-running').textContent=t('{count} actief',{count:s.filter(running).length});$('m-stopped').textContent=t('{count} gestopt',{count:s.filter(x=>!running(x)).length});$('m-alerts').textContent=s.filter(x=>!running(x)||/unhealthy/i.test(x.status)).length;
const newest=hosts.filter(x=>x.age_seconds!=null).sort((a,b)=>a.age_seconds-b.age_seconds)[0];$('updated').textContent=newest?t('Laatste meting {seconds}s geleden',{seconds:newest.age_seconds}):'Nog geen metingen';
$('server-list').innerHTML=hosts.length?hosts.map(x=>`<div class="server-card"><div class="server-header"><div class="server-icon"><i class="bi ${x.type==='local'?'bi-pc-display':'bi-hdd-network'}"></i></div><div><strong>${esc(x.label)}</strong><small>${x.type==='local'?'Lokale snapshot':'Externe agent'}</small></div><span class="server-status ${x.online?'':'offline'}">${x.online?'● Online':'● Offline'}</span></div><div class="server-details"><div><span>Containers</span><strong>${x.container_count}</strong></div><div><span>Vrije RAM</span><strong>${x.memory?.available_bytes?(x.memory.available_bytes/1e9).toFixed(1)+' GB':'—'}</strong></div><div><span>Laatste scan</span><strong>${x.age_seconds!=null?x.age_seconds+'s':'—'}</strong></div></div></div>`).join(''):'<div class="loading">Nog geen servers gevonden. Controleer de snapshot of voeg een agent toe.</div>';
const old=$('filter-server').value;$('filter-server').innerHTML='<option value="">Alle servers</option>'+hosts.map(x=>`<option value="${esc(x.id)}">${esc(x.label)}</option>`).join('');$('filter-server').value=hosts.some(x=>x.id===old)?old:'';
$('events').innerHTML=model.events?.length?model.events.map(e=>`<div class="event"><div class="event-icon"><i class="bi bi-pencil-square"></i></div><div><strong>${esc(e.kind)}</strong><small>${esc(e.subject)} · ${esc(e.detail)}</small></div><time>${esc(e.time?.slice(11,16))}</time></div>`).join(''):'<div class="loading">Nog geen wijzigingen geregistreerd</div>';
renderRows();renderSettings();i18n.translate();}
function renderRows(){let filtered=(model.services||[]).filter(x=>(!$('filter-server').value||x.server_id===$('filter-server').value)&&(!$('filter-status').value||($('filter-status').value==='running'?running(x):!running(x)))&&(!$('filter-risk').value||x.risk===$('filter-risk').value)&&[x.name,x.image,x.project].join(' ').toLowerCase().includes($('search').value.toLowerCase()));
$('results-count').textContent=t('{count} resultaten',{count:filtered.length});$('service-rows').innerHTML=filtered.length?filtered.map(c=>`<tr data-key="${esc(c.key)}"><td><div class="service-name">${esc(c.name)}</div><div class="service-image">${esc(c.image)}</div></td><td>${esc(model.servers.find(x=>x.id===c.server_id)?.label||c.server_id)}</td><td><span class="pill ${running(c)?'running':'stopped'}"><span class="risk-mark"></span>${running(c)?t('Actief'):t('Gestopt')}${/unhealthy/i.test(c.status)?' · ongezond':''}</span></td><td><span class="pill ${c.risk}"><span class="risk-mark"></span>${labels[c.risk]}</span></td><td><span class="policy-text">${labels[c.mode]}</span></td><td><button class="edit-btn" title="Beleid bewerken"><i class="bi bi-sliders2"></i></button></td></tr>`).join(''):'<tr><td colspan="6" class="loading">Geen diensten gevonden voor deze filters</td></tr>';
$('service-rows').querySelectorAll('tr[data-key]').forEach(tr=>tr.addEventListener('click',()=>editService(tr.dataset.key)))}
function editService(key){const c=model.services.find(x=>x.key===key);if(!c)return;let reasons=c.risk_reasons?.length?c.risk_reasons.map(x=>`<div>• ${esc(t(x))}</div>`).join(''):'<div>Geen aanvullende risico-indicatoren</div>';
popup(t('Risicobeleid ·')+' '+c.name,`<div class="helper">Host: ${esc(model.servers.find(x=>x.id===c.server_id)?.label||c.server_id)}<br>Minimaal risico: <strong>${labels[c.minimum_risk]}</strong></div><div class="reasons">${reasons}</div><form id="policy-form"><div class="form-row"><label>Risicolaag (nooit lager dan het minimum)</label><select class="form-field" id="risk-value">${['low','medium','high','critical'].map(r=>`<option value="${r}" ${r===c.risk?'selected':''} ${['low','medium','high','critical'].indexOf(r)<['low','medium','high','critical'].indexOf(c.minimum_risk)?'disabled':''}>${labels[r]}</option>`).join('')}</select></div><div class="form-row"><label>Updatebeleid</label><select class="form-field" id="policy-mode"><option value="monitor" ${c.mode==='monitor'?'selected':''}>Alleen volgen</option><option value="approve" ${c.mode==='approve'?'selected':''}>Na goedkeuring</option><option value="auto" ${c.mode==='auto'?'selected':''}>Automatisch (uitsluitend laag risico, uitvoering nog uit)</option></select></div><div class="form-row"><label>Notities</label><textarea class="form-area" id="policy-notes" maxlength="500">${esc(c.notes)}</textarea></div><div class="panel-note"><i class="bi bi-shield-lock"></i> Ook bij 'Automatisch' voert v0.5 geen updates uit. Back-up, healthcheck en uitvoeringsagent moeten eerst worden gevalideerd.</div><div class="modal-buttons"><button type="button" class="secondary-btn" id="cancel">Annuleren</button><button class="primary-btn" type="submit">Beleid opslaan</button></div></form>`);
$('cancel').onclick=close;$('policy-form').onsubmit=async e=>{e.preventDefault();try{await request('/api/policies',{method:'POST',headers:{'content-type':'application/json','x-codepug-request':'1'},body:JSON.stringify({service_key:key,risk_override:$('risk-value').value,mode:$('policy-mode').value,notes:$('policy-notes').value})});close();toast('Risicobeleid opgeslagen');await reload()}catch(err){toast('Niet opgeslagen: '+err.message)}}}
function addServer(){popup('Nieuwe server koppelen',`<p class="helper">Maak een agent aan voor je Synology of een andere Linux-server. Je ontvangt een eenmalig token. De agent verstuurt statusgegevens; er is geen inkomende Docker-API nodig.</p><form id="agent-form"><div class="form-row"><label>Herkenbare servernaam</label><input class="form-field" id="agent-name" placeholder="Bijvoorbeeld: Synology NAS" required minlength="2" maxlength="80"></div><div class="modal-buttons"><button type="button" class="secondary-btn" id="cancel">Annuleren</button><button type="submit" class="primary-btn">Agent aanmaken</button></div></form>`);$('cancel').onclick=close;$('agent-form').onsubmit=async e=>{e.preventDefault();try{const d=await request('/api/agents',{method:'POST',headers:{'content-type':'application/json','x-codepug-request':'1'},body:JSON.stringify({label:$('agent-name').value})});popup('Agent aangemaakt',`<p class="helper">Bewaar dit token veilig: het wordt na het sluiten niet opnieuw getoond. Installeer op de andere server <code>agent/scan.py</code> volgens de README.</p><div class="form-row"><label>Agent-ID</label><div class="token-area">${esc(d.id)}</div></div><div class="form-row"><label>Eenmalig toegangstoken</label><div class="token-area">${esc(d.token)}</div></div><div class="panel-note">De agent gebruikt <code>CODEPUG_HUB_URL</code>, <code>CODEPUG_AGENT_ID</code> en een tokenbestand op de server. Gebruik HTTPS/Tailscale.</div><div class="modal-buttons"><button class="secondary-btn" id="close-created">Sluiten</button></div>`);$('close-created').onclick=()=>{close();reload()}}catch(err){toast(err.message)}}}
async function reload(){
try{
  const previous=model;
  model=await request('/api/state');
  reportNewAlerts(previous,model);
  render();
  scheduleReload();
}catch(err){toast('Dashboard kon niet laden: '+err.message)}
}
$('refresh').onclick=reload;$('add-server').onclick=addServer;$('add-server-2').onclick=addServer;$('close-modal').onclick=close;$('overlay').onclick=e=>{if(e.target.id==='overlay')close()};$('menu').onclick=()=>$('sidebar').classList.toggle('open');for(const id of ['search','filter-server','filter-status','filter-risk'])$(id).addEventListener(id==='search'?'input':'change',renderRows);
reload();

// Re-render generated elements on language changes; static text is translated in place.
document.addEventListener('codepug-language-changed',()=>{render()});


// Dashboard settings do not grant execution privileges or alter Docker configurations.
let refreshHandle=null;
function scheduleReload(){
  if(refreshHandle)clearInterval(refreshHandle);
  const seconds=Math.max(15,Math.min(300,Number(model.settings?.refresh_seconds)||60));
  refreshHandle=setInterval(reload,seconds*1000);
}
function reportNewAlerts(before,after){
  if(!before?.servers?.length || !after.settings?.alerts_enabled)return;
  const oldBad=new Set(before.servers.filter(s=>!s.online).map(s=>'server:'+s.id));
  if(after.settings.notify_unhealthy){
    for(const c of before.services||[])if(/unhealthy/i.test(c.status))oldBad.add('container:'+c.key);
  }
  const firstOffline=after.servers.find(s=>!s.online && !oldBad.has('server:'+s.id));
  const firstUnhealthy=after.settings.notify_unhealthy &&
    (after.services||[]).find(c=>/unhealthy/i.test(c.status) && !oldBad.has('container:'+c.key));
  if(firstOffline)toast(t('Server offline:')+' '+firstOffline.label);
  else if(firstUnhealthy)toast(t('Container ongezond:')+' '+firstUnhealthy.name);
}
function renderSettings(){
  const s=model.settings||{};
  const form=$('settings-form');
  // Do not overwrite settings while the user is editing the form.
  if(form && !form.contains(document.activeElement)){
    $('settings-refresh').value=String(s.refresh_seconds??60);
    $('settings-offline').value=String(s.offline_after_seconds??300);
    $('settings-alerts').checked=s.alerts_enabled!==false;
    $('settings-unhealthy').checked=s.notify_unhealthy!==false;
  }
  $('settings-language').value=i18n.language;
  const a=model.agents||[];
  $('settings-agents').innerHTML=a.length?a.map(agent=>
    `<div class="settings-agent">
      <div><strong>${esc(agent.label)}</strong>
      <small>${esc(agent.id)} · ${esc(agent.scan_interval||120)}s ·
      ${agent.last_seen?esc(agent.last_seen.slice(0,16).replace('T',' ')):t('Nog niet verbonden')}</small></div>
      <div class="agent-actions">
        <button type="button" class="icon-btn" data-agent-edit="${esc(agent.id)}" title="${t('Bewerken')}" aria-label="${t('Bewerken')}"><i class="bi bi-pencil"></i></button>
        <button type="button" class="icon-btn danger-outline" data-agent-delete="${esc(agent.id)}" title="${t('Toegang intrekken')}" aria-label="${t('Toegang intrekken')}"><i class="bi bi-trash"></i></button>
      </div>
    </div>`).join(''):`<div class="loading">${t('Nog geen externe agents gekoppeld')}</div>`;
  $('settings-agents').querySelectorAll('[data-agent-edit]').forEach(b=>
    b.addEventListener('click',()=>editAgent(b.dataset.agentEdit)));
  $('settings-agents').querySelectorAll('[data-agent-delete]').forEach(b=>
    b.addEventListener('click',()=>revokeAgent(b.dataset.agentDelete)));
}
function editAgent(id){
  const agent=(model.agents||[]).find(a=>a.id===id);
  if(!agent)return;
  popup(t('Agent bewerken'),
    `<form id="edit-agent-form">
      <div class="form-row"><label>${t('Servernaam')}</label>
      <input class="form-field" id="edit-agent-name" minlength="2" maxlength="80" required value="${esc(agent.label)}"></div>
      <div class="form-row"><label>${t('Scaninterval')}</label>
      <select class="form-field" id="edit-agent-interval">
      ${[60,120,300,600,900,1800,3600].map(v=>`<option value="${v}" ${v===agent.scan_interval?'selected':''}>${v>=60?v/60:1} ${t('minuten')}</option>`).join('')}
      </select></div>
      <div class="panel-note">${t('Alleen agents gestart met --loop nemen dit interval automatisch over. Cronjobs niet.')}</div>
      <div class="modal-buttons"><button type="button" class="secondary-btn" id="agent-cancel">${t('Annuleren')}</button><button type="submit" class="primary-btn">${t('Opslaan')}</button></div>
    </form>`);
  $('agent-cancel').onclick=close;
  $('edit-agent-form').onsubmit=async event=>{
    event.preventDefault();
    try{
      await request('/api/agents/'+encodeURIComponent(id),{
        method:'PATCH',headers:{'content-type':'application/json','x-codepug-request':'1'},
        body:JSON.stringify({label:$('edit-agent-name').value,scan_interval:Number($('edit-agent-interval').value)})
      });
      close();toast(t('Serverinstellingen opgeslagen'));await reload();
    }catch(error){toast(error.message)}
  };
}
async function revokeAgent(id){
  const agent=(model.agents||[]).find(a=>a.id===id);
  if(!agent)return;
  if(!confirm(t('Agent verwijderen, toegangstoken intrekken en inventaris wissen?')+' '+agent.label))return;
  try{
    await request('/api/agents/'+encodeURIComponent(id),{
      method:'DELETE',headers:{'x-codepug-request':'1'}
    });
    toast(t('Agent verwijderd'));await reload();
  }catch(error){toast(error.message)}
}
$('settings-add-agent').onclick=addServer;
$('settings-language').onchange=event=>i18n.setLanguage(event.target.value);
$('settings-form').onsubmit=async event=>{
  event.preventDefault();
  try{
    await request('/api/settings',{
      method:'POST',headers:{'content-type':'application/json','x-codepug-request':'1'},
      body:JSON.stringify({
        refresh_seconds:Number($('settings-refresh').value),
        offline_after_seconds:Number($('settings-offline').value),
        alerts_enabled:$('settings-alerts').checked,
        notify_unhealthy:$('settings-unhealthy').checked
      })
    });
    toast(t('Instellingen opgeslagen'));await reload();
  }catch(error){toast(error.message)}
};
document.addEventListener('codepug-language-changed',()=>{
  $('settings-language').value=i18n.language;
});
