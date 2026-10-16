function validateH4(data){if(data?.format!=='wurfbild-handball4all'||data.version!==1||!/^\d+$/.test(data.organization)||!/^\d+$/.test(data.league)||!/^\d+$/.test(data.season)||!Array.isArray(data.games)||data.games.length>2000||![20,25,30].includes(data.halfMinutes))throw Error('Keine gültige Handball4all-Importdatei.');for(const g of data.games){if(!g||!/^\d+$/.test(g.externalId)||typeof g.home!=='string'||typeof g.away!=='string'||!g.home||!g.away||g.home===g.away||!/^\d{4}-\d{2}-\d{2}$/.test(g.date)||!g.rosters||!['home','away'].every(s=>Array.isArray(g.rosters[s])&&g.rosters[s].every(p=>typeof p.number==='string'&&/^\d{1,2}$/.test(p.number)&&typeof p.name==='string'))||!Array.isArray(g.officialGoals)||g.officialGoals.length>1000)throw Error('Ungültige Mannschafts- oder Spieldaten.');if(g.officialScore!==null&&(!Array.isArray(g.officialScore)||g.officialScore.length!==2||g.officialScore.some(n=>!Number.isInteger(n)||n<0||n>300)))throw Error('Ungültiger Spielstand.');let score=[0,0];for(const e of g.officialGoals){if(!['home','away'].includes(e.side)||typeof e.player!=='string'||!/^\d{1,2}$/.test(e.player)||typeof e.playerName!=='string'||!/^\d{2,3}:[0-5]\d$/.test(e.time))throw Error('Ungültiger Torverlauf.');score[e.side==='home'?0:1]++;if(e.homeScore!==score[0]||e.awayScore!==score[1])throw Error('Der Torverlauf ist nicht konsistent.')}if(g.reportVerified===true&&(!g.officialScore||score.some((n,i)=>n!==g.officialScore[i])))throw Error('Torverlauf und Endstand stimmen nicht überein.')}return data}
function h4Key(d,g){return `h4:${d.organization}:${d.league}:${d.season}:${g.externalId}`}
function importH4Game(d,incoming){const key=h4Key(d,incoming),existing=db.games.find(g=>g.externalKey===key);const matching={};for(const side of ['home','away']){const name=incoming[side];matching[side]=db.teams.find(t=>t.name.toLocaleLowerCase('de')===name.toLocaleLowerCase('de'));const roster=incoming.rosters[side];if(new Set(roster.map(p=>p.number)).size!==roster.length)throw Error('Doppelte Rückennummer im Import.');for(const p of roster){const old=matching[side]?.players.find(x=>x.number===p.number);if(old?.name&&p.name&&old.name.toLocaleLowerCase('de')!==p.name.toLocaleLowerCase('de'))throw Error(`${name}: Nummer ${p.number} ist bereits ${old.name} zugeordnet. Bitte den Kader zuerst prüfen.`)}}for(const side of ['home','away']){let t=matching[side];if(!t){t={id:uid(),name:incoming[side],players:[],color:null};db.teams.push(t);matching[side]=t}for(const p of incoming.rosters[side]){const old=t.players.find(x=>x.number===p.number);if(!old)t.players.push({...p});else if(!old.name)old.name=p.name}t.players.sort((a,b)=>+a.number-+b.number)}const source={provider:'handball4all',organization:d.organization,league:d.league,season:d.season,externalId:incoming.externalId,reportId:incoming.reportId,exportedAt:d.exportedAt};const referenceGoals=incoming.reportVerified?incoming.officialGoals.map(e=>({...e,team:matching[e.side].id})):[];if(existing){existing.referenceGoals=referenceGoals;existing.officialScore=incoming.officialScore;existing.referenceSource=source;existing.reportVerified=incoming.reportVerified;persist();return existing}const g={id:uid(),home:matching.home.id,away:matching.away.id,date:incoming.date,elapsed:0,period:1,halfMinutes:d.halfMinutes,finished:false,shots:[],externalKey:key,referenceSource:source,referenceGoals,officialScore:incoming.officialScore,reportVerified:incoming.reportVerified,keepers:{}};db.games.push(g);persist();return g}
function h4Dialog(){modal(`<div class="eyebrow">Handball4all · Mannschaften & Spiele</div><h2>Liga-Spiel importieren</h2><p class="muted" style="margin:14px 0;line-height:1.6">WURFBILD-Importdatei aus dem Handball4all-Import auswählen. Ein Spiel übernimmt die Mannschaften und verfügbare Kader. Offizielle Tore bleiben getrennte Vergleichsdaten; es werden keine Feld- oder Torsegmente erfunden.</p><input id="h4-file" type="file" accept=".json,application/json" aria-label="Handball4all-Importdatei" style="width:100%"><div id="h4-preview"></div><div class="dialog-actions"><button data-close>Schließen</button></div>`);$('#h4-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>5000000)throw Error('Datei bitte auf 5 MB begrenzen.');const d=validateH4(JSON.parse(await file.text()));$('#h4-preview').innerHTML=`<p class="muted" style="margin:14px 0">Liga ${esc(d.league)} · Saison-ID ${esc(d.season)} · Stand ${esc(d.exportedAt||'unbekannt')}</p><div class="h4-games">${d.games.map((g,i)=>`<button data-h4-game="${i}" class="history-entry"><b>${esc(g.date)} · ${esc(g.home)} – ${esc(g.away)}</b><small>${g.officialScore?g.officialScore.join(':'):'Noch kein Ergebnis'} · ${g.reportVerified?`${g.rosters.home.length+g.rosters.away.length} Spieler · ${g.officialGoals.length} geprüfte Torzeiten`:'Ohne geprüfte Kader/Torzeiten'}${db.games.some(x=>x.externalKey===h4Key(d,g))?' · Bereits vorhanden, Vergleich aktualisieren':''}</small></button>`).join('')}</div>`;document.querySelectorAll('[data-h4-game]').forEach(b=>b.onclick=()=>{try{const g=importH4Game(d,d.games[Number(b.dataset.h4Game)]);$('#dialog').close();selectGame(g.id);toast('Spiel übernommen.')}catch(err){toast(err.message)}})}catch(err){toast(err.message||'Die Datei konnte nicht gelesen werden.')}}}
function referenceDialog(g){const goals=g.referenceGoals||[],manual=g.shots.filter(s=>s.result==='Tor'),used=new Set(),seconds=t=>{const [m,s]=t.split(':').map(Number);return m*60+s};const rows=goals.map(e=>{const candidate=manual.map(s=>({s,diff:Math.abs(seconds(s.time)-seconds(e.time))})).filter(x=>x.s.team===e.team&&x.s.player===e.player&&!used.has(x.s.id)&&x.diff<=10).sort((a,b)=>a.diff-b.diff)[0];if(candidate)used.add(candidate.s.id);return `<tr><td>${esc(e.time)}</td><td>${esc(teamName(e.team))}</td><td>#${esc(e.player)} ${esc(e.playerName)}</td><td>${e.homeScore}:${e.awayScore}</td><td>${candidate?'Ähnlicher Eintrag '+esc(candidate.s.time):'Kein passender Eintrag'}</td></tr>`});modal(`<h2>Abgleich mit Handball4all</h2><div class="notice" style="margin-top:14px">Offiziell: ${g.officialScore?g.officialScore.join(':'):'kein Endstand'} · Erfasst: ${g.shots.filter(s=>s.team===g.home&&s.result==='Tor').length}:${g.shots.filter(s=>s.team===g.away&&s.result==='Tor').length}<br>Zuordnungsvorschläge verwenden Mannschaft, Rückennummer und maximal 10 Sekunden Zeitabweichung. Es werden keine Würfe automatisch geändert.</div>${!g.reportVerified?'<p class="muted">Für dieses Spiel liegen noch keine geprüften Torzeiten vor.</p>':`<p class="muted">${used.size} Zuordnungsvorschläge · ${manual.length-used.size} eigene Tore ohne Zuordnung</p><div class="tablewrap"><table><thead><tr><th>Zeit</th><th>Team</th><th>Werfer</th><th>Stand</th><th>Vergleich</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`}<div class="dialog-actions"><button data-close>Schließen</button></div>`)}
const gamesBeforeH4=gamesView;
gamesView=function(){return gamesBeforeH4().replace('<div class="card">','<div class="row" style="margin-bottom:18px"><button class="primary" id="h4-import">↑ Handball4all-Spiel importieren</button></div><div class="card">').replace(/<button class="primary" data-open="([^"]+)">Spiel öffnen<\/button>/g,(all,id)=>{const g=db.games.find(x=>x.id===id);return all+(g?.referenceSource?`<button data-reference="${id}">Abgleich</button>`:'')})};
const bindBeforeH4=bind;
bind=function(){bindBeforeH4();if($('#h4-import'))$('#h4-import').onclick=h4Dialog;document.querySelectorAll('[data-reference]').forEach(b=>b.onclick=()=>referenceDialog(db.games.find(g=>g.id===b.dataset.reference)))};
render();


function h4IsoDate(v){const m=/^(\d\d)\.(\d\d)\.(\d\d)$/.exec(v||'');if(!m)throw Error('Ungültiges Datum: '+v);return '20'+m[3]+'-'+m[2]+'-'+m[1]}
async function h4Get(url){const r=await fetch(url,{credentials:'same-origin'});if(!r.ok)throw Error('Abruf fehlgeschlagen: '+r.status);return r.json()}
async function h4ImportAll(){
 try{
 const data=await h4Get('/api/handball4all/schedule');
 if(data.league!=='161291'||!data.season||!Array.isArray(data.games))throw Error('Falsche Liga');
 const base={organization:data.organization,league:data.league,season:data.season,halfMinutes:25,exportedAt:new Date().toISOString()};
 let added=0;
 for(const raw of data.games){
 const g={externalId:raw.externalId,reportId:raw.reportId,home:raw.home,away:raw.away,date:h4IsoDate(raw.date),rosters:{home:[],away:[]},officialGoals:[],officialScore:null,reportVerified:false};
 if(db.games.some(x=>x.externalKey===h4Key(base,g)))continue;
 importH4Game(base,g);added++;
 }
 render();toast(added+' Spiele importiert');
 }catch(e){toast(e.message);render()}
}
async function h4FillRoster(id){
 try{
 const g=db.games.find(x=>x.id===id),schedule=await h4Get('/api/handball4all/schedule');
 if(!g?.referenceSource)throw Error('Kein Handball4all-Spiel');
 let added=0;
 for(const teamId of [g.home,g.away]){
 const t=team(teamId);
 const previous=schedule.games.filter(x=>x.reportId&&(x.home===t.name||x.away===t.name)).sort((a,b)=>h4IsoDate(b.date).localeCompare(h4IsoDate(a.date)));
 for(const candidate of previous.slice(0,5)){
 try{
 const report=await h4Get('/api/handball4all/report/'+encodeURIComponent(candidate.reportId)+'/rosters');
 const side=candidate.home===t.name?'home':'away';
 for(const p of report.rosters[side].players){
 const number=String(p.number);
 if(!t.players.some(x=>String(x.number)===number)){t.players.push({number,name:p.name});added++}
 }
 t.players.sort((a,b)=>Number(a.number)-Number(b.number));break;
 }catch(e){console.warn('Bericht übersprungen',candidate.reportId,e)}
 }
 }
 persist();render();toast(added+' Spieler ergänzt; bitte Kader prüfen');
 }catch(e){toast(e.message)}
}
const oldH4GamesView=gamesView;
gamesView=function(){
 return oldH4GamesView().replace('id="h4-import">','id="h4-import">').replace('↑ Handball4all-Spiel importieren</button>','↑ Handball4all-Spiel importieren</button><button id="h4-import-all">Ligaspiele direkt laden</button>').replace(/(<button data-reference="([^"]+)">Abgleich<\/button>)/g, '<button data-h4-roster="$2">Kader laden</button>$1');
};
const oldH4Bind=bind;
bind=function(){
 oldH4Bind();
 if($('#h4-import-all'))$('#h4-import-all').onclick=h4ImportAll;
 document.querySelectorAll('[data-h4-roster]').forEach(b=>b.onclick=()=>h4FillRoster(b.dataset.h4Roster));
};
render();
