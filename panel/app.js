'use strict';
const root = document.getElementById('nia-control-panel');
const token = document.querySelector('meta[name=nia-token]').content;
let language = localStorage.getItem('nia-language') === 'pl' ? 'pl' : 'en';
let view = 'overview', status = null, draft = null, notice = '', failed = false, pending = false, dirty = false;
const t = (en, pl) => language === 'pl' ? pl : en;
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = value => JSON.parse(JSON.stringify(value));
const promptNames = {
  linia_redakcyjna:['Editorial direction','Linia redakcyjna'], glos_artykulu:['Article voice','Głos artykułów'],
  glos_notki:['Note voice','Głos notek'],glos_komentarza:['Comment voice','Głos komentarzy'],
  kogo_szukamy:['Audience and community','Odbiorcy i społeczność'],okladka:['Cover style','Styl okładek'],oswiadczenie:['Authorship disclosure','Oświadczenie o autorstwie']
};
const roleNames = {write:['Article writing','Pisanie artykułów'],discovery:['Research and search','Research i wyszukiwanie'],
  note:['Notes','Notki'],factcheck:['Fact-checking','Sprawdzanie faktów'],note_tani:['Short Notes','Krótkie notki'],comment:['Comments','Komentarze'],reply:['Replies','Odpowiedzi'],
  scout:['Topic scouting','Wyszukiwanie tematów'],feasibility:['Topic feasibility','Ocena wykonalności tematu'],classify:['Source classification','Klasyfikacja źródeł'],
  synthesis:['Evidence synthesis','Synteza dowodów'],review:['Editorial review','Ocena redakcyjna'],forma:['Article structure','Struktura artykułu'],bank:['Idea bank ranking','Ranking banku pomysłów'],
  naprawa:['Draft repair','Poprawa szkicu'],naprawa_komentarza:['Comment repair','Poprawa komentarza'],aktualne_modele:['Field-status research','Research stanu dziedziny'],
  curiosity:['Short-form research','Research krótkich form'],grafika:['Image instructions','Instrukcje grafiki'],cele:['Community target selection','Wybór celów interakcji'],
  wybor:['Material selection','Wybór materiałów'],bibliotekarz:['Memory curation','Porządkowanie pamięci'],warto_pisac:['Idea evaluation','Ocena pomysłu'],restack:['Restack commentary','Komentarz do restacka'],fedreg:['Regulatory research','Research regulacji']};
const roleLabel = role => roleNames[role] ? t(...roleNames[role]) : role;
const nameModel = id => ({'deepseek-v4-flash':'DeepSeek V4 Flash','deepseek-v4-pro':'DeepSeek V4 Pro','claude-opus-5':'Claude Opus 5','claude-fable-5-1':'Claude Fable 5.1'}[id] || id);
async function api(path, body) {
  const response = await fetch('/api/' + path, {method:body ? 'POST':'GET',headers:{'X-NIA-Token':token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
async function action(task) {
  if(pending) return;
  capture(); pending=true; notice=''; failed=false;
  render();
  try { await task(); status=await api('status'); }
  catch(error){notice=error.message; failed=true;}
  finally{pending=false;render();}
}
const button=(id,en,pl,primary=false,extra='')=>`<button type="button" id="${id}" class="${primary?'primary':'secondary'}" ${pending?'disabled':''} ${extra}>${t(en,pl)}</button>`;
const field=(key,en,pl,kind='text',options={})=>{
  const value=draft?.fields[key] ?? options.default ?? '';
  let data=Array.isArray(value)?value.join('\n'): typeof value==='object'?Object.entries(value).map(([n,v])=>n+' | '+v).join('\n'):value;
  const attr=`data-field="${key}" data-kind="${options.format||kind}" ${options.optional?'data-optional="true"':''}`;
  return `<label>${t(en,pl)}${kind==='textarea'?`<textarea ${attr} rows="${options.rows||3}">${escapeHTML(data)}</textarea>`:`<input ${attr} type="${kind}" value="${escapeHTML(data)}" ${kind==='number'?'min="0" step="'+(options.step||'1')+'"':''}>`}${options.help?`<small>${t(...options.help)}</small>`:''}</label>`;
};
function modelSelect(role) {
  const value=draft.models[role] || status.roles[role];
  const choices=Array.from(new Set([...status.models,value])).filter(Boolean);
  return `<label>${escapeHTML(roleLabel(role))}<select data-model="${escapeHTML(role)}">${choices.map(id=>`<option value="${escapeHTML(id)}" ${id===value?'selected':''}>${escapeHTML(nameModel(id))}</option>`).join('')}</select></label>`;
}
function capture() {
  if(!draft) return;
  root.querySelectorAll('[data-field]').forEach(el=>{
    let value=el.value;
    if(el.dataset.optional && value===''){delete draft.fields[el.dataset.field];return;}
    if(el.dataset.kind==='ints') value=value.split(/[\s,]+/).filter(Boolean).map(Number);
    if(el.dataset.kind==='bool') value=el.checked;
    if(el.dataset.kind==='number') value=el.value===''?null:Number(value);
    if(el.dataset.kind==='lines') value=value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
    if(el.dataset.kind==='map') value=Object.fromEntries(value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean).map(s=>{const i=s.indexOf('|');return i<0?[s,s]:[s.slice(0,i).trim(),s.slice(i+1).trim()];}));
    draft.fields[el.dataset.field]=value;
  });
  root.querySelectorAll('[data-model]').forEach(el=>draft.models[el.dataset.model]=el.value);
  root.querySelectorAll('[data-asset]').forEach(el=>draft.assets[el.dataset.asset]=el.value);
  root.querySelectorAll('[data-prompt]').forEach(el=>draft.prompts[el.dataset.prompt]=el.value);
  root.querySelectorAll('[data-pin]').forEach(el=>draft.pins[el.dataset.pin]=el.value===''?null:Number(el.value));
  const name=root.querySelector('#preset-name');if(name)draft.target=name.value;
  const desc=root.querySelector('#preset-description');if(desc)draft.meta.opis=desc.value;
}
function payload() {
  capture();
  const fields=clone(draft.fields);
  fields['modele.role']={...draft.models};delete fields['modele.role'].obraz;
  // The engine derives article days when only the desired count is supplied.
  if(fields['harmonogram.dni_artykulu']?.length !== fields['wolumeny.artykuly_tygodniowo']) delete fields['harmonogram.dni_artykulu'];
  if(fields['harmonogram.godziny_przebiegow_utc']) fields['wolumeny.przebiegow_dziennie']=fields['harmonogram.godziny_przebiegow_utc'].length;
  return {source:draft.id||undefined,revision:draft.revision,name:draft.target,description:draft.meta.opis,fields,prompts:draft.prompts,assets:draft.assets,pins:draft.pins};
}
function editorBar() {
  return `<div class="editor-toolbar"><label>${t('Preset library','Biblioteka presetów')}<select id="preset-library">${status.presets.map(p=>`<option value="${escapeHTML(p.id)}" ${draft?.id===p.id?'selected':''}>${escapeHTML(p.name)}${p.public?t(' · bundled',' · wzorzec'):t(' · private',' · prywatny')}</option>`).join('')}</select></label>${button('load','Load','Wczytaj')}${button('new','New preset','Nowy preset')}</div>
  ${draft?`<div class="two"><label>${t('Private preset name','Nazwa prywatnego presetu')}<input id="preset-name" value="${escapeHTML(draft.target)}" pattern="[a-z0-9][a-z0-9_-]{0,63}"><small>${t('Lowercase letters, numbers, hyphens or underscores.','Małe litery, cyfry, myślniki i podkreślenia.')}</small></label><label>${t('Description','Opis')}<input id="preset-description" value="${escapeHTML(draft.meta.opis)}"></label></div>`:''}`;
}
function editorFooter() {
  return `<div class="footer"><span>${t('Saving validates the complete preset. Existing private presets receive a backup.','Zapis sprawdza cały preset. Poprzednia wersja prywatnego presetu trafia do kopii zapasowej.')}</span><div class="actions">${button('validate','Validate','Sprawdź')}${button('save','Save preset','Zapisz preset',true)}</div></div>`;
}
function settingsView() {
  const mainRoles=['write','discovery','note','factcheck','note_tani','comment','reply'];
  return `<h1>${t("Set your NIA's rhythm.",'Ustaw rytm swojej NIA.')}</h1><p class="muted">${t('Models, activity and budget in one place.','Modele, aktywność i budżet w jednym miejscu.')}</p>${editorBar()}
  ${draft?`<div class="two"><section><h2>${t('Models by task','Modele do zadań')}</h2>${mainRoles.map(modelSelect).join('')}<details><summary>${t('All other text roles','Pozostałe role tekstowe')}</summary>${Object.keys(status.roles).filter(r=>!mainRoles.includes(r)).map(modelSelect).join('')}</details>
  <label>${t('Fallback writer','Pisarz zapasowy')}<select data-field="modele.zapasowy_pisarz">${['',...status.models].map(id=>`<option value="${escapeHTML(id)}" ${draft.fields['modele.zapasowy_pisarz']===id?'selected':''}>${id?escapeHTML(nameModel(id)):t('Off','Wyłączony')}</option>`).join('')}</select></label>
  <label>${t('Article image','Grafika artykułu')}<select data-field="modele.obraz"><option value="" ${!draft.fields['modele.obraz']?'selected':''}>${t('Off','Wyłączona')}</option><option value="gpt-image-1.5" ${draft.fields['modele.obraz']==='gpt-image-1.5'?'selected':''}>gpt-image-1.5</option></select></label></section>
  <section><h2>${t('Publishing and interactions','Publikacje i interakcje')}</h2>${field('wolumeny.notki_dziennie','Notes per day','Notki dziennie','number')}${field('wolumeny.artykuly_tygodniowo','Articles per week','Artykuły tygodniowo','number')}${field('wolumeny.artykuly_miesiecznie','Articles per month (weekly must be 0)','Artykuły miesięcznie (tygodniowo ustaw 0)','number',{optional:true})}${field('wolumeny.follow_dziennie','Follows per day (blank = monthly range)','Obserwacje dziennie (puste = zakres miesięczny)','number',{optional:true})}${field('wolumeny.subskrypcje_dziennie','Free subscriptions per day (blank = monthly range)','Bezpłatne subskrypcje dziennie (puste = zakres miesięczny)','number',{optional:true})}
  ${[['komentarze','Comments','Komentarze'],['lajki','Likes','Polubienia'],['restacki','Restacks','Restacki'],['follow','Follows per month','Obserwacje miesięcznie'],['subskrypcje','Free subscriptions per month','Bezpłatne subskrypcje miesięcznie']].map(([key,en,pl])=>{const f='wolumeny.'+key+(key==='follow'||key==='subskrypcje'?'_miesiecznie':'_dziennie');const values=draft.fields[f]||[0,0];return `<label>${t(en,pl)}<span class="range"><input type="number" min="0" data-range="${f}" data-index="0" aria-label="${t('Minimum','Minimum')}" value="${values[0]}"><span>–</span><input type="number" min="0" data-range="${f}" data-index="1" aria-label="${t('Maximum','Maksimum')}" value="${values[1]}"></span></label>`;}).join('')}
  <p class="muted small">${t('0 disables an action. Daily ranges are limits, not guaranteed output.','0 wyłącza działanie. Dzienne zakresy to limity, a nie gwarantowana liczba akcji.')}</p>
  <h2>${t('Spending limits · USD','Limity kosztów · USD')}</h2>${field('pieniadze.sufit_przebiegu_usd','Per run','Na przebieg','number',{step:'.01'})}${field('pieniadze.sufit_dzienny_usd','Daily','Dziennie','number',{step:'.01'})}${field('pieniadze.sufit_miesieczny_usd','Monthly','Miesięcznie','number',{step:'.01'})}</section></div>
  <details><summary>${t('Schedule configuration','Konfiguracja harmonogramu')}</summary><p>${t('These settings describe the schedule. This version starts runs manually; it does not install Windows tasks or Linux timers.','Te ustawienia opisują harmonogram. Ta wersja uruchamia przebiegi ręcznie; nie instaluje zadań Windows ani timerów Linux.')}</p>${field('harmonogram.godziny_przebiegow_utc','Daily run times (UTC), one per line','Godziny przebiegów (UTC), po jednej w wierszu','textarea',{format:'lines'})}${field('harmonogram.godzina_artykulu_utc','Article time (UTC)','Godzina artykułu (UTC)')}${field('harmonogram.dni_miesiaca_artykulu','Monthly article days, 1–28, separated by commas','Dni artykułu w miesiącu, 1–28, oddzielone przecinkami','textarea',{format:'ints',optional:true})}</details>${editorFooter()}`:''}`;
}
function presetsView() {
  return `<h1>${t('Build your own preset.','Stwórz własny preset.')}</h1><p class="muted">${t('Topics, sources and voice belong to the preset. Account and API keys belong to your installation.','Temat, źródła i głos należą do presetu. Konto i klucze API należą do Twojej instalacji.')}</p>${editorBar()}${draft?`
  <section><div class="two">${field('temat.nisza','Topic','Temat','textarea')}${field('temat.kat_redakcyjny','Editorial angle','Kąt redakcyjny','textarea')}</div>
  <label>${t('Writing language','Język publikacji')}<select data-field="temat.jezyk"><option value="English" ${draft.fields['temat.jezyk']==='English'?'selected':''}>English</option><option value="Polish" ${draft.fields['temat.jezyk']==='Polish'?'selected':''}>Polski</option></select><small>${t('Interface language is independent. English is the evaluated writing workflow; another language needs suitable examples and review.','Język panelu jest niezależny. Przebieg pisania sprawdzono po angielsku; inny język wymaga odpowiednich przykładów i oceny.')}</small></label>
  <div class="two">${field('temat.znaki_niszy','Topic keywords — one per line','Słowa rozpoznające temat — po jednym w wierszu','textarea',{format:'lines',help:['Each search phrase must contain at least one keyword.','Każda fraza wyszukiwania musi zawierać przynajmniej jedno słowo kluczowe.']})}${field('temat.dziedziny','Editorial lenses — one per line','Obszary tematu — po jednym w wierszu','textarea',{format:'lines',help:['Describe different angles worth researching. Validation checks variety for your Note volume.','Opisz różne obszary warte researchu. Walidacja sprawdza ich liczbę wobec liczby notek.']})}</div></section>
  <details open><summary>${t('Research sources','Źródła researchu')}</summary>${field('zrodla.kanaly_rss','RSS / Atom feeds: name | URL','Kanały RSS / Atom: nazwa | URL','textarea',{format:'map',rows:5,help:['Use a feed URL, not an ordinary home page. Preferred domains below guide web research.','Podaj adres kanału, nie zwykłej strony głównej. Preferowane domeny poniżej kierują researchem.']})}${field('zrodla.kanaly_youtube','YouTube channels: name | channel ID','Kanały YouTube: nazwa | ID kanału','textarea',{format:'map'})}<div class="two">${field('zrodla.domeny_preferowane','Preferred domains','Preferowane domeny','textarea',{format:'lines'})}${field('zrodla.blokowane_hosty','Excluded domains','Wykluczone domeny','textarea',{format:'lines'})}</div>${field('temat.hasla_szukania','Search phrases — at least 15, one per line','Frazy wyszukiwania — co najmniej 15, po jednej w wierszu','textarea',{format:'lines',rows:6})}${field('stan_dziedziny.o_co_pytac','Field-status research question (empty = derive from topic)','Pytanie o stan dziedziny (puste = na podstawie tematu)','textarea')}</details>
  <details><summary>${t('Prompts','Prompty')}</summary>${Object.entries(promptNames).map(([key,label])=>`<label>${t(...label)}<textarea data-prompt="${key}" rows="6">${escapeHTML(draft.prompts[key]||'')}</textarea></label>`).join('')}</details>
  <details><summary>${t('Writing style and examples','Styl i przykłady pisania')}</summary>${field('styl.opis','Style description','Opis stylu','textarea')}<label><input type="checkbox" data-field="osobowosc.wlaczona" data-kind="bool" ${draft.fields['osobowosc.wlaczona']?'checked':''}>${t('Conversational persona: short forms without research or fact-checking','Osobowość: krótkie formy bez researchu i fact-checkingu')}</label>${field('osobowosc.tematy','Persona themes, one per line','Tematy osobowości, po jednym w wierszu','textarea',{format:'lines',optional:true})}<label><input type="checkbox" data-field="osobowosc.przejecie" data-kind="bool" ${draft.fields['osobowosc.przejecie']?'checked':''}>${t('Introduce a new voice replacing this account’s earlier persona','Przedstaw nowy głos zastępujący wcześniejszą osobowość konta')}</label>${[['positive','What good writing looks like','Jak powinien wyglądać dobry tekst'],['negative','What to avoid','Czego unikać'],['corpus','Writing examples (optional)','Przykłady tekstów (opcjonalnie)']].map(([key,en,pl])=>`<label>${t(en,pl)}<textarea rows="7" data-asset="${key}">${escapeHTML(draft.assets[key])}</textarea></label>`).join('')}
  <p class="muted">${t('Separate examples with a blank line. Choose a paragraph index (starting at 0) for each role; selected paragraphs must have 150–900 characters. Leave examples empty to use only the style profiles.','Oddziel przykłady pustą linią. Dla każdej funkcji wybierz indeks akapitu (od 0); wybrane akapity muszą mieć 150–900 znaków. Pozostaw przykłady puste, żeby używać samych profili stylu.')}</p><div class="pins">${['OPENING','CONCRETE_TO_SYSTEM','MECHANISM','COUNTERARGUMENT','ENDING'].map(role=>`<label>${role}<input type="number" min="0" data-pin="${role}" value="${draft.pins[role]??''}"></label>`).join('')}</div></details>
  <details><summary>${t('Other preset fields (JSON)','Pozostałe pola presetu (JSON)')}</summary><p class="muted">${t('Advanced: all fields retained from the loaded preset. Apply changes here before editing other sections.','Zaawansowane: wszystkie pola zachowane z presetu. Zastosuj zmiany tutaj przed edycją innych sekcji.')}</p><textarea id="advanced-fields" rows="12">${escapeHTML(JSON.stringify(draft.fields,null,2))}</textarea>${button('apply-fields','Apply fields','Zastosuj pola')}</details>${editorFooter()}`:''}`;
}
function overviewView() {
  const running=status.job?.running;
  return `<div class="eyebrow">${t('Your publication. Your rules.','Twoja publikacja. Twoje zasady.')}</div><h1>${t('Your NIA workspace.','Twoja redakcja NIA.')}</h1><p class="muted">${t('Local control. Real presets. Visible run results.','Lokalne sterowanie. Prawdziwe presety. Widoczne wyniki przebiegów.')}</p>
  <section><div class="summary"><div><small>${t('Active preset','Aktywny preset')}</small><strong>${escapeHTML(status.active||t('Not selected','Nie wybrano'))}</strong></div><div><small>${t('Data instance','Instancja danych')}</small><strong>${escapeHTML(status.instance||'—')}</strong></div><div><small>${t('Panel job','Praca z panelu')}</small><strong>${running?t('Running','W toku'):t('Idle','Bezczynny')}</strong></div></div>${status.error?`<p class="error">${escapeHTML(status.error)}</p>`:''}</section>
  <section><h2>${t('Activate a saved preset','Aktywuj zapisany preset')}</h2><div class="two"><label>${t('Preset','Preset')}<select id="activate-preset">${status.presets.map(p=>`<option value="${escapeHTML(p.id)}" ${p.id===status.active?'selected':''}>${escapeHTML(p.name)}</option>`).join('')}</select></label><label>${t('Instance ID','ID instancji')}<input id="instance-name" value="${escapeHTML(status.instance||'my-publication')}"><small>${t('Use a new ID for a new topic or account. Existing data is never reassigned.','Nowy temat lub konto wymaga nowego ID. Istniejące dane nie są przejmowane.')}</small></label></div>${button('activate','Activate','Aktywuj',true)}</section>
  <section><h2>${t('Run the bot','Uruchom bota')}</h2><p>${t('Preview checks are free. Draft and publish runs use paid models. Publishing also enables the configured community actions.','Podgląd konfiguracji jest bezpłatny. Tworzenie szkiców i publikowanie korzysta z płatnych modeli. Publikowanie włącza też skonfigurowane działania społecznościowe.')}</p><div class="actions">${button('preview','Configuration preview','Podgląd konfiguracji')}${button('check','Check account and setup','Sprawdź konto i konfigurację')}${button('costs','Cost and memory report','Raport kosztów i pamięci')}</div><div class="two"><label>${t('Workflow','Przebieg')}<select id="workflow"><option value="daily">${t('Daily Notes and community','Dzienne notki i społeczność')}</option><option value="article">${t('Article from the idea bank','Artykuł z banku pomysłów')}</option></select></label><label>${t('Mode','Tryb')}<select id="run-mode"><option value="draft">${t('Create draft — no publishing','Twórz szkic — bez publikacji')}</option><option value="publish">${t('Generate and publish','Generuj i publikuj')}</option></select></label></div>${button('run','Start run','Uruchom przebieg',true,running?'disabled':'')}<p class="small muted">${t('This panel starts manual runs. A closed browser tab does not stop the bot. Scheduling installation is documented separately.','Panel uruchamia przebiegi ręcznie. Zamknięcie karty przeglądarki nie zatrzymuje bota. Instalacja harmonogramu jest opisana osobno.')}</p></section>
  <section><h2>${t('Latest operation','Ostatnia operacja')}</h2><div id="job-status"></div><pre id="job-log" aria-live="off"></pre></section>`;
}
function setupView() {
  return `<h1>${t('Connect your publication.','Podłącz swoją publikację.')}</h1><p class="muted">${t('Account data stays in this installation. Blank API fields keep your existing keys.','Dane konta zostają w tej instalacji. Puste pola API zachowują istniejące klucze.')}</p><section><div class="two"><label>${t('Substack handle (without @)','Uchwyt Substack (bez @)')}<input id="handle" autocomplete="off" value="${escapeHTML(status.account.SUBSTACK_HANDLE)}"></label><label>${t('Publication name','Nazwa publikacji')}<input id="brand" value="${escapeHTML(status.account.NAZWA_MARKI)}"></label></div>${Object.entries(status.keys).map(([key,present])=>`<label>${key} · ${present?t('configured','skonfigurowany'):t('missing','brak')}<input type="password" data-secret="${key}" autocomplete="new-password" value=""></label>`).join('')}${button('account','Save account settings','Zapisz ustawienia konta',true)}</section>
  <section><h2>${t('Browser connection','Połączenie z przeglądarką')}</h2><ol><li>${t('Save account settings and activate your private preset in Overview.','Zapisz konto i aktywuj prywatny preset w zakładce Przegląd.')}</li><li>${t('Open the dedicated Chrome window and sign in to Substack manually.','Otwórz osobne okno Chrome i ręcznie zaloguj się do Substacka.')}</li><li>${t('Verify the account and save the session for the active instance.','Potwierdź konto i zapisz sesję aktywnej instancji.')}</li></ol><div class="actions">${button('login','Open Chrome','Otwórz Chrome')}${button('session','Verify and save session','Sprawdź i zapisz sesję',true)}</div><p class="muted">${t('Saved session file','Zapisany plik sesji')}: ${status.session_saved?t('yes; use verification to check it live','tak; użyj weryfikacji, żeby sprawdzić konto na żywo'):t('not yet','jeszcze nie')}</p></section>`;
}
function renderJob() {
  const el=root.querySelector('#job-status'),log=root.querySelector('#job-log');if(!el)return;
  const job=status?.job;
  el.textContent=job?`${job.action} · ${job.running?t('running','w toku'):t('finished','zakończone')+' · exit '+job.exit_code}`:t('No operation started from this panel session.','W tej sesji panelu nie uruchomiono operacji.');
  log.textContent=job?.log||'';
}
function render() {
  document.documentElement.lang=language;
  if(!status){root.innerHTML='<p>Loading NIA…</p>';return;}
  root.innerHTML=`<header><div class="brand"><b>N</b> NIA <span>${t('Control panel','Panel sterowania')}</span></div><div class="top-actions"><span class="local">${t('Local workspace','Lokalna instalacja')}</span><select id="language" aria-label="${t('Interface language','Język interfejsu')}"><option value="en" ${language==='en'?'selected':''}>English</option><option value="pl" ${language==='pl'?'selected':''}>Polski</option></select></div></header><div class="shell"><nav>${[['overview','Overview','Przegląd'],['settings','Models & activity','Modele i aktywność'],['presets','Presets','Presety'],['setup','Account & setup','Konto i start']].map(([id,en,pl])=>`<button data-view="${id}" aria-current="${view===id?'page':'false'}">${t(en,pl)}</button>`).join('')}<small>${t('Editing','Edytujesz')}:<br>${escapeHTML(draft?.target||'—')}</small></nav><main>${notice?`<div class="message ${failed?'error':''}" role="status">${escapeHTML(notice)}</div>`:''}${pending?`<p role="status">${t('Working…','Pracuję…')}</p>`:''}${({overview:overviewView,settings:settingsView,presets:presetsView,setup:setupView}[view])()}</main></div>`;
  bind();renderJob();
}
async function load(id) {
  draft=await api('preset?id='+encodeURIComponent(id));draft.target=draft.public?draft.id+'-local':draft.id;dirty=false;
}
function bind() {
  root.querySelector('#language').onchange=e=>{capture();language=e.target.value;localStorage.setItem('nia-language',language);render();};
  root.querySelectorAll('[data-view]').forEach(el=>el.onclick=()=>{capture();view=el.dataset.view;render();});
  root.querySelectorAll('[data-field],[data-model],[data-asset],[data-prompt],[data-pin],#preset-name,#preset-description').forEach(el=>el.addEventListener('input',()=>{dirty=true;}));
  root.querySelectorAll('[data-range]').forEach(el=>el.oninput=()=>{const key=el.dataset.range;draft.fields[key] ||= [0,0];draft.fields[key][Number(el.dataset.index)]=el.value===''?null:Number(el.value);dirty=true;});
  const on=(id,fn)=>{const el=root.querySelector('#'+id);if(el)el.onclick=fn;};
  on('load',()=>{const id=root.querySelector('#preset-library').value;if(dirty&&!confirm(t('Discard unsaved edits and load this preset?','Odrzucić niezapisane zmiany i wczytać ten preset?')))return;action(async()=>{await load(id);notice=t('Preset loaded. Bundled presets are read-only; save a private copy.','Preset wczytany. Gotowe presety są tylko do odczytu; zapisz prywatną kopię.');});});
  on('new',()=>{if(dirty&&!confirm(t('Discard unsaved edits and create a new preset?','Odrzucić niezapisane zmiany i utworzyć nowy preset?')))return;
    capture();draft={id:null,target:'my-preset',meta:{opis:''},revision:null,models:clone(status.roles),prompts:{},assets:{positive:'Write clearly. Distinguish evidence, inference and uncertainty.',negative:'Do not invent facts, sources, quotations or personal experience.',corpus:''},pins:{},fields:{'konto.uchwyt':'your-handle','konto.nazwa_marki':'Your Publication','temat.nisza':'','temat.kat_redakcyjny':'','temat.jezyk':'English','temat.znaki_niszy':[],'temat.hasla_szukania':[],'temat.dziedziny':[],'zrodla.kanaly_rss':{},'zrodla.kanaly_youtube':{},'zrodla.domeny_preferowane':[],'zrodla.blokowane_hosty':[],'styl.opis':'','modele.obraz':'','modele.zapasowy_pisarz':'deepseek-v4-flash','wolumeny.notki_dziennie':2,'wolumeny.artykuly_tygodniowo':1,'wolumeny.komentarze_dziennie':[0,0],'wolumeny.lajki_dziennie':[0,0],'wolumeny.restacki_dziennie':[0,0],'wolumeny.follow_miesiecznie':[0,0],'wolumeny.subskrypcje_miesiecznie':[0,0],'harmonogram.godziny_przebiegow_utc':['12:30'],'harmonogram.godzina_artykulu_utc':'14:00','pieniadze.sufit_przebiegu_usd':1.6,'pieniadze.sufit_dzienny_usd':3.5,'pieniadze.sufit_miesieczny_usd':25}};dirty=true;view='presets';notice='';render();});
  on('apply-fields',()=>{try{const fields=JSON.parse(root.querySelector('#advanced-fields').value);if(!fields||Array.isArray(fields)||typeof fields!=='object')throw Error('Expected an object');draft.fields=fields;draft.models={...status.roles,...fields['modele.role']};dirty=true;notice=t('Fields applied to the editor. Validate before saving.','Pola zastosowane w edytorze. Sprawdź je przed zapisem.');failed=false;}catch(e){notice=e.message;failed=true;}render();});
  on('validate',()=>{const p=payload();action(async()=>{const result=await api('validate',p);notice=t('Preset is valid.','Preset jest poprawny.')+'\n'+result.warnings.join('\n');});});
  on('save',()=>{const p=payload();action(async()=>{const result=await api('save',p);draft=result.preset;draft.target=draft.id;dirty=false;notice=t('Saved.','Zapisano.')+(result.reactivated?t(' Active instance updated.',' Aktywna instancja zaktualizowana.'):'')+'\n'+result.warnings.join('\n');});});
  on('activate',()=>{const name=root.querySelector('#activate-preset').value,instance=root.querySelector('#instance-name').value;action(async()=>{await api('activate',{name,instance});notice=t('Preset activated.','Preset aktywowany.');});});
  on('account',()=>{const values={SUBSTACK_HANDLE:root.querySelector('#handle').value,NAZWA_MARKI:root.querySelector('#brand').value};root.querySelectorAll('[data-secret]').forEach(el=>{if(el.value)values[el.dataset.secret]=el.value;});action(async()=>{await api('account',values);notice=t('Account saved. API key values are never returned to the panel.','Konto zapisane. Wartości kluczy API nie są zwracane do panelu.');});});
  const start=kind=>action(async()=>{await api('start',{action:kind});view='overview';notice=t('Operation started. Follow the log below.','Operacja uruchomiona. Obserwuj log poniżej.');});
  for(const [id,kind] of [['preview','dry'],['check','check'],['costs','costs'],['login','login'],['session','session']])on(id,()=>start(kind));
  on('run',()=>{const kind=root.querySelector('#workflow').value+'-'+root.querySelector('#run-mode').value;if(dirty){notice=t('Save or reload your preset before starting a paid run.','Zapisz lub wczytaj ponownie preset przed płatnym przebiegiem.');failed=true;render();return;}start(kind);});
}
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
async function boot(){try{status=await api('status');if(status.presets.length)await load(status.active||status.presets[0].id);render();}catch(e){root.textContent=e.message;}}
boot();
setInterval(async()=>{if(pending)return;try{const next=await api('status');const was=status?.job?.running;status=next;if(was&&!next.job?.running){capture();render();}else renderJob();}catch(e){const el=root.querySelector('#job-status');if(el)el.textContent=t('Panel connection lost. Reopen the launcher.','Utracono połączenie z panelem. Uruchom ponownie panel.');}},2500);
