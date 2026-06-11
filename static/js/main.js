import { api } from './api.js';
import { $, esc, spin, err, toast, img, badge } from './ui.js';

/* STATE */
window.K = sessionStorage.getItem('bagre_key') || '';
window.ME = null;
window.sessao = [];

/* UTILS */

/* Toast notifications — verde (sucesso) / vermelho (erro) */



/* ════════════════════════════════════════════════════════════════
   CHART.JS — gráficos interativos (Hype, Ciclo) no frontend.
   Tema Cyberpunk: fundo transparente, grid #333, séries #39FF14/#FF3131.
   O Espelho Pedigree continua usando o radar PNG (img()).
   ════════════════════════════════════════════════════════════════ */
const NEON = '#39FF14', RAT = '#FF3131', GRID = '#333333', INK = '#cccccc', SUB = '#888888';
window._charts = window._charts || {};

/* Cria/recria um gráfico no canvas, destruindo instância anterior. */
function makeChart(canvasId, config){
  if(typeof Chart === 'undefined') return false;     // CDN indisponível → degrada sem quebrar
  const cv = $(canvasId);
  if(!cv) return false;
  if(window._charts[canvasId]){ try{ window._charts[canvasId].destroy(); }catch(_){ } }
  window._charts[canvasId] = new Chart(cv, config);
  return true;
}

/* Eixos no tema escuro Cyberpunk. */
function cyberScales(xTitle, yTitle){
  return {
    x:{ title:{display:true, text:xTitle, color:SUB},
        grid:{color:GRID}, ticks:{color:INK} },
    y:{ title:{display:true, text:yTitle, color:SUB},
        grid:{color:GRID}, ticks:{color:INK} }
  };
}
/* Plugins comuns: legenda interativa (clicável) + tooltips. */
function cyberPlugins(tooltipLabel){
  return {
    legend:{ labels:{ color:'#fff', usePointStyle:true } },
    tooltip:{ backgroundColor:'#1A1A1A', borderColor:NEON, borderWidth:1,
              titleColor:NEON, bodyColor:'#fff',
              callbacks: tooltipLabel ? {label:tooltipLabel} : {} }
  };
}

/* HYPE INDEX — scatter Performance × Valor + reta de regressão. */
function buildHypeChart(canvasId, d){
  const js = d.jogadores || [];
  const cor = {PediRato:RAT, Pedigree:NEON, Regular:SUB};
  const grupos = {PediRato:[], Pedigree:[], Regular:[]};
  js.forEach(j=>{
    const cls = grupos[j.classificacao] ? j.classificacao : 'Regular';
    grupos[cls].push({x:j.performance, y:j.valor_milhoes, nome:j.nome});
  });
  // Reta de regressão = pontos (performance, valor_predito) ordenados por x.
  const reta = js.map(j=>({x:j.performance, y:j.valor_predito})).sort((a,b)=>a.x-b.x);
  const datasets = [];
  ['Pedigree','Regular','PediRato'].forEach(cls=>{
    if(grupos[cls].length) datasets.push({
      label:cls, data:grupos[cls], type:'scatter',
      backgroundColor:cor[cls], borderColor:cor[cls],
      pointRadius:6, pointHoverRadius:9
    });
  });
  datasets.push({ label:'Regressão', data:reta, type:'line', borderColor:'#ffffff',
    borderWidth:2, borderDash:[6,4], pointRadius:0, fill:false });
  makeChart(canvasId, {
    type:'scatter',
    data:{datasets},
    options:{ responsive:true, maintainAspectRatio:false,
      scales:cyberScales('Performance (Gols + Assists)','Valor de Mercado (€M)'),
      plugins:cyberPlugins(c=>{ const p=c.raw;
        return (p.nome?p.nome+' — ':'')+'perf '+p.x+' · €'+p.y+'M'; }) }
  });
}

/* CICLO DE VIDA — scatter Idade × Valor + curva polinomial (grau 2). */
function buildCicloChart(canvasId, d){
  const tab = d.tabela || [];
  const pts = tab.map(j=>({x:j.idade, y:j.valor_milhoes, nome:j.nome}));
  const c = d.coeficientes || {};
  const a = +c.a||0, b = +c.b||0, cc = +c.c||0;
  const xs = tab.map(j=>j.idade);
  let xmin = Math.min.apply(null, xs), xmax = Math.max.apply(null, xs);
  if(!isFinite(xmin)){ xmin=15; xmax=40; }
  const curva = []; const N = 40;
  for(let i=0;i<=N;i++){ const x = xmin + (xmax-xmin)*i/N; curva.push({x:x, y:a*x*x + b*x + cc}); }
  makeChart(canvasId, {
    type:'scatter',
    data:{datasets:[
      { label:'Jogadores', data:pts, type:'scatter',
        backgroundColor:NEON, borderColor:NEON, pointRadius:6, pointHoverRadius:9 },
      { label:'Curva (grau 2)', data:curva, type:'line', borderColor:'#ffffff',
        borderWidth:2, pointRadius:0, fill:false, tension:0.3 }
    ]},
    options:{ responsive:true, maintainAspectRatio:false,
      scales:cyberScales('Idade','Valor de Mercado (€M)'),
      plugins:cyberPlugins(c=>{ const p=c.raw;
        return (p.nome?p.nome+' — ':'')+(Math.round(p.x*10)/10)+' anos · €'+(Math.round(p.y*10)/10)+'M'; }) }
  });
}




/* LOGIN */
async function doLogin(k){
  if(!k) return;
  $('login-error').textContent = '';
  try {
    window.K = k;
    const me = await api('GET','/v1/me');
    sessionStorage.setItem('bagre_key', k);
    window.ME = me;
    boot(me);
  } catch(e) {
    window.K='';
    $('login-error').textContent = e.status===401 ? 'Erro de autenticação.' : `Erro ${e.status}: ${e.detail}`;
  }
}

function doLogout(){
  sessionStorage.removeItem('bagre_key');
  window.K=''; window.ME=null; window.sessao=[];
  $('app').classList.remove('visible');
  $('login-screen').classList.remove('hidden');
  $('login-error').textContent='';
  updBar();
}

/* BOOT */
function boot(me){
  $('login-screen').classList.add('hidden');
  $('app').classList.add('visible');

  const pk = (me.plano||'varzea').toLowerCase().replace('á','a').replace('é','e');
  const pe = $('hdr-plano');
  pe.textContent = (me.plano||'várzea').toUpperCase();
  pe.className = pk;

  const uso=me.uso_hoje??0, lim=me.limite_diario;
  $('hdr-uso').textContent = lim==='ilimitado' ? 'Ilimitado' : `${uso} / ${lim} scouts hoje`;

  const funcoes = me.funcionalidades||[];
  document.querySelectorAll('#sidebar ul li').forEach(li=>{
    const req = li.dataset.req;
    if(!req || funcoes.includes(req)){   // itens sem data-req (ex.: Dashboard) ficam sempre liberados
      li.classList.remove('locked');
      const lb=li.querySelector('.lbadge');
      if(lb) lb.remove();
    } else {
      li.classList.add('locked');
    }
  });

  // pre-populate name lists
  if(!$('hype-names').children.length){
    ['Arrascaeta','Vinicius Junior','Kylian Mbappe'].forEach(n=>addNameRow('hype-names',n));
  }
  if(!$('pool-names').children.length){
    ['Arrascaeta','Griezmann','Bruno Fernandes'].forEach(n=>addNameRow('pool-names',n));
  }
  if(!$('ref-nome').value){
    $('ref-nome').value='Kylian Mbappe';
  }
  if(!$('ciclo-names').children.length){
    ['Endrick Felipe','Raphinha','Erling Haaland'].forEach(n=>addNameRow('ciclo-names',n));
  }

  const first = document.querySelector('#sidebar ul li:not(.locked)');
  if(first) nav(first);
}

/* NAV */
function nav(li){
  if(li.classList.contains('locked')){
    const badge = li.querySelector('.lbadge');
    const t = badge ? badge.textContent.toLowerCase() : '';
    const plano = t.includes('diretor') ? 'DIRETOR' : t.includes('olheiro') ? 'OLHEIRO' : 'superior';
    $('plan-modal-msg').innerHTML = `🔒 Esta funcionalidade requer o plano <strong style="color:var(--green)">${plano}</strong>.`;
    $('plan-modal').style.display = 'flex';
    return;
  }
  document.querySelectorAll('#sidebar ul li').forEach(l=>l.classList.remove('active'));
  li.classList.add('active');
  const sid = li.dataset.sec;
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  const sec = $(sid);
  if(sec){
    sec.classList.add('active');
    if(sid==='s-docx') refreshDocx();
    if(sid==='s-dash') refreshDash();
  }
}

/* PEDIRATO DA SEMANA */
async function loadPediratoDaSemana(){
  if(window._pediratoDaSemanaLoaded) return;
  const el=$('pedirato-semana-inner');
  if(!el) return;
  try {
    const d=await api('GET','/v1/pedirato-da-semana');
    const pr=typeof d.pedirato==='number'?d.pedirato.toFixed(2):d.pedirato;
    el.innerHTML=`
      <div class="psemana-header">
        <span class="psemana-label">⭐ PEDIGREE DA SEMANA</span>
        <span class="psemana-week">Semana ${d.semana}</span>
      </div>
      <div class="psemana-nome">${esc(d.nome)}</div>
      <div class="psemana-sub">${esc(d.clube)} · ${esc(d.liga)}</div>
      <div class="psemana-body">
        <div class="psemana-stats">
          <div class="psemana-stat">
            <span class="val">${d.gols}</span><span class="lbl">Gols</span>
          </div>
          <div class="psemana-stat">
            <span class="val">${d.assists}</span><span class="lbl">Assists</span>
          </div>
          <div class="psemana-stat">
            <span class="val">€${d.valor_milhoes}M</span><span class="lbl">Valor Mercado</span>
          </div>
        </div>
        <div class="psemana-score">
          <div class="big">${pr}</div>
          <div class="lbl">PediRato Score</div>
        </div>
      </div>
      <div class="psemana-footer">
        Destaque automático · muda toda semana · disponível para todos os planos
      </div>`;
    window._pediratoDaSemanaLoaded=true;
  } catch(_){
    el.innerHTML=`<div style="color:var(--muted);font-size:.82rem;padding:8px 0">Destaque semanal indisponível no momento.</div>`;
  }
}

/* DASHBOARD */
function goSection(secId){
  // Reutiliza a navegação do sidebar (inclui o modal de plano se a seção estiver bloqueada).
  const li = document.querySelector(`#sidebar ul li[data-sec="${secId}"]`);
  if(li) nav(li);
}

function refreshDash(){
  loadPediratoDaSemana();
  const me = window.ME || {};
  const s  = window.sessao || [];

  // KPI 1 — Análises na Sessão
  $('dash-kpi-sessao').textContent = s.length;

  // KPI 2 — PediRato Médio (média dos scores dos jogadores da sessão)
  const scores = s.map(j=>parseFloat(j.pedirato_score)).filter(v=>!isNaN(v));
  $('dash-kpi-pedirato').textContent = scores.length
    ? (scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1) : '—';

  // KPI 3 — Último Jogador adicionado
  $('dash-kpi-ultimo').textContent = s.length ? s[s.length-1].nome : '—';

  // KPI 4 — Plano Atual
  $('dash-kpi-plano').textContent = (me.plano || '—').toUpperCase();

  // Cadeado nos cards de frentes bloqueadas pelo tier do usuário
  const funcoes = me.funcionalidades || [];
  document.querySelectorAll('#dash-grid .dash-card').forEach(card=>{
    const req    = card.dataset.req;
    const lockEl = card.querySelector('.dash-lock');
    if(req && !funcoes.includes(req)){
      card.classList.add('locked');
      const tier = ['ciclo_vida','relatorio_docx','golden_list'].includes(req) ? 'diretor' : 'olheiro+';
      if(lockEl) lockEl.textContent = '🔒 ' + tier;
    } else {
      card.classList.remove('locked');
      if(lockEl) lockEl.textContent = '';
    }
  });
}

/* DYNAMIC TABLES */
const PH = {nome:'Nome',clube:'Nome do Clube',idade:'',gols:'',assists:'',
            valor_milhoes:'',valor_total_elenco_milhoes:'Valor €M'};

function addRow(tid, fields){
  clearOut(tid);
  const tb = document.querySelector(`#${tid} tbody`);
  const tr = document.createElement('tr');
  fields.forEach(f=>{
    const td=document.createElement('td');
    const inp=document.createElement('input');
    inp.type = (f==='nome'||f==='clube') ? 'text' : 'number';
    if(f!=='nome'&&f!=='clube'){ inp.step='0.1'; inp.min='0'; }
    inp.placeholder = (f in PH) ? PH[f] : f;
    inp.dataset.field = f;
    inp.addEventListener('input', ()=>clearOut(tid));
    td.appendChild(inp); tr.appendChild(td);
  });
  const tdx=document.createElement('td');
  const btn=document.createElement('button');
  btn.className='btn-rm'; btn.textContent='✕';
  btn.onclick=()=>{ tr.remove(); clearOut(tid); };
  tdx.appendChild(btn); tr.appendChild(tdx);
  tb.appendChild(tr);
}

function readTbl(tid, fields){
  const rows=[];
  document.querySelectorAll(`#${tid} tbody tr`).forEach(tr=>{
    const o={};
    fields.forEach(f=>{
      const inp=tr.querySelector(`[data-field="${f}"]`);
      if(!inp) return;
      o[f]=(f==='nome'||f==='clube') ? inp.value.trim() : (inp.value!==''?parseFloat(inp.value):null);
    });
    if(o[fields[0]]) rows.push(o);
  });
  return rows;
}

/* ── NAME-LIST HELPERS ──────────────────────────────────────── */
const IDADES = {
  'arrascaeta':32,'vinicius junior':24,'kylian mbappe':26,'erling haaland':24,
  'endrick felipe':18,'raphinha':28,'griezmann':33,'bruno fernandes':30,
  'pedri':22,'gavi':20,'lamine yamal':17,'rodri':28,'jude bellingham':21,
  'phil foden':24,'bukayo saka':23,'jamal musiala':22,'florian wirtz':21,
  'federico valverde':26,'arda guler':19,'camavinga':22,'tchouameni':24,
  'dani olmo':26,'leroy sane':29,'niclas fullkrug':32,'harry kane':31,
  'heung-min son':32,'marcus rashford':27,'gabriel martinelli':23,'cody gakpo':25,
  'xavi simons':22,
};

function addNameRow(listId, prefill){
  const div=$(listId);
  const row=document.createElement('div');
  row.style.cssText='display:flex;gap:6px;margin-bottom:6px;align-items:center;width:100%;';
  
  const container = document.createElement('div');
  container.style.cssText = 'position:relative;flex:1;';

  const inp=document.createElement('input');
  inp.type='text'; inp.className='bagre-input name-inp';
  inp.placeholder='Nome do jogador'; inp.style.width='100%'; inp.setAttribute('autocomplete', 'off');
  if(prefill) inp.value=prefill;

  const ac = document.createElement('div');
  ac.className = 'ac-dropdown';
  ac.style.display = 'none';

  container.appendChild(inp);
  container.appendChild(ac);

  const btn=document.createElement('button');
  btn.className='btn-rm'; btn.textContent='✕';
  btn.onclick=()=>row.remove();
  
  row.appendChild(container); row.appendChild(btn);
  div.appendChild(row);

  registrarAutocompleteDinamico(inp, ac);

  return inp;
}

function registrarAutocompleteDinamico(inp, ac) {
  let debounceTimer = null;
  inp.addEventListener('input', e => {
    clearTimeout(debounceTimer);
    const q = e.target.value.trim();
    if (q.length < 2) {
      ac.innerHTML = '';
      ac.style.display = 'none';
      return;
    }
    debounceTimer = setTimeout(async () => {
      try {
        const d = await api('GET', `/v1/search?query=${encodeURIComponent(q)}`);
        const sugs = d.response?.suggestions || [];
        if (!sugs.length) {
          ac.innerHTML = '';
          ac.style.display = 'none';
          return;
        }
        ac.innerHTML = sugs.map(s => {
          const club = s.teamName ? s.teamName : '';
          const label = club ? `<span class="ac-team">${esc(club)}</span>` : '';
          const nameEsc = encodeURIComponent(s.name);
          return `
            <div class="ac-item" onclick="this.parentElement.style.display='none'; this.parentElement.previousElementSibling.value=decodeURIComponent('${nameEsc}');">
              <span>${esc(s.name)}</span>
              ${label}
            </div>
          `;
        }).join('');
        ac.style.display = 'block';
      } catch (err) {
        console.error("Dynamic autocomplete error:", err);
      }
    }, 250);
  });

  inp.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      setTimeout(() => { ac.innerHTML = ''; ac.style.display = 'none'; }, 150);
    }
  });
}

function readNames(listId){
  return Array.from(document.querySelectorAll(`#${listId} .name-inp`))
    .map(i=>i.value.trim()).filter(n=>n.length>=3);
}

async function fetchScouts(names, outEl){
  outEl.innerHTML=`<div class="w" style="color:#ffd700">🔍 Buscando dados de ${names.length} jogadores...</div>`;
  const results=await Promise.all(names.map(n=>
    api('GET',`/v1/scout?nome=${encodeURIComponent(n)}`).catch(e=>({status:'error',nome:n,_err:e}))
  ));
  const valid=[], warns=[];
  results.forEach((r,i)=>{ if(r.status==='success') valid.push(r); else warns.push(names[i]); });
  let warnHtml='';
  if(warns.length) warnHtml=warns.map(n=>`<div class="w" style="color:#ffd700;font-size:.82rem">⚠️ Sem dados para '${esc(n)}' — ignorado</div>`).join('');
  outEl.innerHTML=warnHtml;
  return {valid, warns};
}

/* ── AUTOCOMPLETE JOGADORES ─────────────────────────────────── */
let scDebounceTimer = null;

$('sc-nome').addEventListener('input', e => {
  clearTimeout(scDebounceTimer);
  const q = e.target.value.trim();
  if (q.length < 2) {
    hideAutocomplete();
    return;
  }
  scDebounceTimer = setTimeout(async () => {
    try {
      const d = await api('GET', `/v1/search?query=${encodeURIComponent(q)}`);
      const sugs = d.response?.suggestions || [];
      showAutocomplete(sugs);
    } catch (err) {
      console.error("Autocomplete error:", err);
    }
  }, 250);
});

$('sc-nome').addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    setTimeout(hideAutocomplete, 150);
  }
});

function showAutocomplete(sugs) {
  const ac = $('sc-autocomplete');
  if (!sugs.length) {
    hideAutocomplete();
    return;
  }
  ac.innerHTML = sugs.map(s => {
    const club = s.teamName ? s.teamName : '';
    const label = club ? `<span class="ac-team">${esc(club)}</span>` : '';
    const nameEsc = encodeURIComponent(s.name);
    return `
      <div class="ac-item" onclick="selectAutocomplete(decodeURIComponent('${nameEsc}'))">
        <span>${esc(s.name)}</span>
        ${label}
      </div>
    `;
  }).join('');
  ac.style.display = 'block';
}

function selectAutocomplete(name) {
  $('sc-nome').value = name;
  hideAutocomplete();
  doScout(name);
}

function hideAutocomplete() {
  const ac = $('sc-autocomplete');
  if (ac) {
    ac.innerHTML = '';
    ac.style.display = 'none';
  }
}

// Hide dropdown when clicking outside
let refDebounceTimer = null;

$('ref-nome').addEventListener('input', e => {
  clearTimeout(refDebounceTimer);
  const q = e.target.value.trim();
  if (q.length < 2) {
    hideRefAutocomplete();
    return;
  }
  refDebounceTimer = setTimeout(async () => {
    try {
      const d = await api('GET', `/v1/search?query=${encodeURIComponent(q)}`);
      const sugs = d.response?.suggestions || [];
      showRefAutocomplete(sugs);
    } catch (err) {
      console.error("Autocomplete error:", err);
    }
  }, 250);
});

$('ref-nome').addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    setTimeout(hideRefAutocomplete, 150);
  }
});

function showRefAutocomplete(sugs) {
  const ac = $('ref-autocomplete');
  if (!sugs.length) {
    hideRefAutocomplete();
    return;
  }
  ac.innerHTML = sugs.map(s => {
    const club = s.teamName ? s.teamName : '';
    const label = club ? `<span class="ac-team">${esc(club)}</span>` : '';
    const nameEsc = encodeURIComponent(s.name);
    return `
      <div class="ac-item" onclick="selectRefAutocomplete(decodeURIComponent('${nameEsc}'))">
        <span>${esc(s.name)}</span>
        ${label}
      </div>
    `;
  }).join('');
  ac.style.display = 'block';
}

function selectRefAutocomplete(name) {
  $('ref-nome').value = name;
  hideRefAutocomplete();
}

function hideRefAutocomplete() {
  const ac = $('ref-autocomplete');
  if (ac) {
    ac.innerHTML = '';
    ac.style.display = 'none';
  }
}

document.addEventListener('click', e => {
  if (e.target.id !== 'sc-nome' && e.target.id !== 'sc-autocomplete') {
    hideAutocomplete();
  }
  if (e.target.id !== 'ref-nome' && e.target.id !== 'ref-autocomplete') {
    hideRefAutocomplete();
  }
  if (!e.target.classList.contains('name-inp') && !e.target.classList.contains('ac-item')) {
    document.querySelectorAll('.ac-dropdown').forEach(el => {
      el.innerHTML = '';
      el.style.display = 'none';
    });
  }
});

/* ── SCOUT ──────────────────────────────────────────────────── */
const FONTE_BADGE = {
  api_principal:  `<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:.65rem;font-weight:700;letter-spacing:1px;background:rgba(57,255,20,.15);color:#39FF14;border:1px solid #39FF14;margin-left:8px">🔴 Ao Vivo</span>`,
  transfermarkt:  `<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:.65rem;font-weight:700;letter-spacing:1px;background:rgba(90,160,255,.15);color:#5aa0ff;border:1px solid #5aa0ff;margin-left:8px">💰 Transfermarkt</span>`,
  fbref:          `<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:.65rem;font-weight:700;letter-spacing:1px;background:rgba(150,150,150,.15);color:#aaa;border:1px solid #666;margin-left:8px">📊 FBref</span>`,
  cache:          `<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:.65rem;font-weight:700;letter-spacing:1px;background:rgba(150,150,150,.15);color:#aaa;border:1px solid #666;margin-left:8px">📦 Cache</span>`,
  cache_expirado: `<span style="display:inline-block;padding:2px 8px;border-radius:3px;font-size:.65rem;font-weight:700;letter-spacing:1px;background:rgba(255,170,0,.12);color:#fa0;border:1px solid #fa0;margin-left:8px">⚠️ Cache desatualizado</span>`,
};

async function doScout(override){
  const nome = override||$('sc-nome').value.trim();
  const out=$('scout-out');
  if(!nome){ err(out,'Informe o nome do jogador.'); return; }
  $('sc-nome').value = '';
  spin(out);
  const url=`/v1/scout?nome=${encodeURIComponent(nome)}`;
  try {
    const d = await api('GET', url);
    if(d.status === 'unavailable'){
      out.innerHTML=`<div class="e" style="font-size:.88rem;padding:13px 16px">⚠ ${esc(d.aviso||'Nenhuma fonte de dados respondeu.')}</div>`;
      return;
    }
    renderScout(out, d, nome);
    toast('ok', 'Scout: ' + (d.nome||nome));
  } catch(e){
    if(e.status===409&&e.detail?.sugestoes) renderSug(out, e.detail.sugestoes);
    else if(e.status===429) out.innerHTML=`<div class="w">🚫 ${esc(e.detail)}</div>`;
    else err(out, e.detail||`Erro ${e.status}`);
  }
}

function renderScout(el, d, nome){
  const sc = d.pedirato_score??d.score??d.pedirato??0;
  const cls = d.ranking_contexto||d.classificacao||(sc>1.5?'Pedigree':sc>0.5?'Regular':'PediRato');
  const scoreCol = cls==='PediRato'?'#ff3131':cls==='Pedigree'?'#39FF14':'#fff';
  const barCol   = cls==='PediRato'?'#ff3131':cls==='Pedigree'?'#39FF14':'#888';
  const pct = Math.min(100,(sc/3)*100).toFixed(0);
  const jdata = {
    nome: d.nome||nome, clube: d.clube||d.team||'—', liga: d.liga||d.league||'—',
    idade: d.idade||d.age||'—', valor_milhoes: d.valor_mercado_milhoes??d.valor_milhoes??'—',
    gols: d.gols??'—', assists: d.assists??'—', pedirato_score: sc, classificacao: cls,
  };
  const fonteBadge = FONTE_BADGE[d.fonte] || '';
  const lims = d.limitacoes_metodologicas||[];
  const limsHtml = lims.length ? `
    <details style="margin-top:10px;font-size:.78rem">
      <summary style="cursor:pointer;color:var(--muted)">ℹ️ Sobre o Índice PediRato</summary>
      <ul style="margin:6px 0 0 16px;color:var(--muted);line-height:1.6">
        ${lims.map(l=>`<li>${esc(l)}</li>`).join('')}
      </ul>
    </details>` : '';
  el.innerHTML=`
    <div class="sc">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:3px">
        <div>
          <div class="sc-name">${esc(jdata.nome)}${fonteBadge}</div>
          <div class="sc-meta">${esc(jdata.clube)} · ${esc(jdata.liga)}</div>
        </div>
        ${badge(cls)}
      </div>
      <div class="sc-stats">
        <div class="sc-stat"><span class="val">€${esc(String(jdata.valor_milhoes))}M</span><span class="lbl">Valor Mercado</span></div>
        <div class="sc-stat"><span class="val">${esc(String(jdata.gols))}</span><span class="lbl">Gols</span></div>
        <div class="sc-stat"><span class="val">${esc(String(jdata.assists))}</span><span class="lbl">Assists</span></div>
        <div class="sc-stat"><span class="val" style="color:${scoreCol}">${typeof sc==='number'?sc.toFixed(2):sc}</span><span class="lbl">PediRato Score</span></div>
      </div>
      <div class="sbar-wrap">
        <div class="sbar-lbl">Índice PediRato = (Gols + Assists) / Valor€M · Pedigree &gt;1.5 · PediRato ≤0.5</div>
        <div class="sbar"><div class="sbar-fill" style="width:${pct}%;background:${barCol}"></div></div>
      </div>
      <button class="btn-s" onclick='addSessao(${JSON.stringify(JSON.stringify(jdata))})'>+ Adicionar à Sessão</button>
      <span id="sadd-msg" style="margin-left:11px;font-size:.78rem;color:var(--muted)"></span>
      ${limsHtml}
    </div>`;
}

function renderSug(el, sugs){
  const items = sugs.map((s,i)=>`
    <li onclick="doScout('${esc(s.nome||s.name||s)}')">
      <span class="sug-n">${i+1}</span><span>${esc(s.nome||s.name||JSON.stringify(s))}</span>
    </li>`).join('');
  el.innerHTML=`<div class="card" style="margin-top:14px">
    <div class="ctitle">Múltiplos encontrados — selecione:</div>
    <ul class="sug-list">${items}</ul></div>`;
}

function addSessao(jsonStr){
  const j=JSON.parse(jsonStr);
  const msg=$('sadd-msg');
  if(window.sessao.find(x=>x.nome===j.nome)){
    if(msg) msg.textContent='Já está na sessão.'; return;
  }
  window.sessao.push(j); updBar();
  if(msg){ msg.textContent='Adicionado!'; setTimeout(()=>msg.textContent='',2000); }
}

/* ── HYPE INDEX ─────────────────────────────────────────────── */
async function doHype(){
  const names=readNames('hype-names');
  const out=$('hype-out');
  if(names.length<3) return err(out,'Mínimo de 3 jogadores necessários.');
  const {valid}=await fetchScouts(names,out);
  if(valid.length<3) return err(out,'Mínimo de 3 jogadores com dados disponíveis necessários.');
  const js=valid.map(p=>({nome:p.nome,valor_milhoes:p.valor_milhoes,gols:p.gols,assists:p.assists}));
  spin(out);
  try {
    const d=await api('POST','/v1/analytics/hype-index',{jogadores:js});
    toast('ok', 'Hype Index calculado');
    const rows=(d.jogadores||[]).map(j=>`<tr>
      <td>${esc(j.nome)}</td><td>€${j.valor_milhoes}M</td>
      <td>${(j.performance||0).toFixed(2)}</td><td>€${(j.valor_predito||0).toFixed(1)}M</td>
      <td>${(j.residuo||0).toFixed(2)}</td><td>${badge(j.classificacao)}</td></tr>`).join('');
    out.innerHTML=`<div class="card" style="margin-top:14px">
      <div class="ctitle">Resultado — Hype Index</div>
      <div class="twrap"><table class="dt"><thead><tr>
        <th>Jogador</th><th>Valor</th><th>Performance</th><th>Val.Previsto</th><th>Resíduo</th><th>Class.</th>
      </tr></thead><tbody>${rows}</tbody></table></div>
      <div class="chart-box"><canvas id="chart-hype"></canvas></div></div>`;
    buildHypeChart('chart-hype', d);
  } catch(e){
    if(e.status===403) err(out,'🔒 Acesso negado. Requer plano OLHEIRO ou superior.');
    else err(out,e.detail||`Erro ${e.status}`);
  }
}

/* ── ESPELHO PEDIGREE ───────────────────────────────────────── */
async function doEsp(){
  const out=$('esp-out');
  const refNome=$('ref-nome').value.trim();
  if(!refNome) return err(out,'Informe o nome do jogador referencial.');
  const poolNames=readNames('pool-names');
  if(!poolNames.length) return err(out,'Adicione ao menos 1 candidato ao pool.');
  const allNames=[refNome,...poolNames.filter(n=>n.toLowerCase()!==refNome.toLowerCase())];
  const {valid}=await fetchScouts(allNames,out);
  if(!valid.length) return err(out,'Nenhum jogador com dados disponíveis.');
  const refLow=refNome.toLowerCase();
  const refPlayer=valid.find(p=>(p.nome||'').toLowerCase().includes(refLow))||valid[0];
  const pool=valid.filter(p=>p!==refPlayer);
  if(!pool.length) return err(out,'Nenhum candidato no pool com dados disponíveis.');
  spin(out);
  try {
    const d=await api('POST','/v1/analytics/espelho-pedigree',{
      jogador_ref:{nome:refPlayer.nome,gols:refPlayer.gols,assists:refPlayer.assists,valor_milhoes:refPlayer.valor_milhoes},
      pool:pool.map(p=>({nome:p.nome,gols:p.gols,assists:p.assists,valor_milhoes:p.valor_milhoes}))});
    toast('ok', 'Espelho Pedigree calculado');
    const rows=(d.top_3_similares||[]).map((j,i)=>`<tr>
      <td>${i+1}º</td>
      <td>${esc(j.nome)}</td>
      <td>${(j['similaridade_%']||0).toFixed(1)}%</td>
      <td>€${j.valor_milhoes}M</td>
      <td>€${(j.economia_estimada_milhoes||0).toFixed(1)}M</td></tr>`).join('');
    out.innerHTML=`<div class="card" style="margin-top:14px">
      <div class="ctitle">Top 3 Similares a ${esc(d.referencial||'')}</div>
      <div class="twrap"><table class="dt"><thead><tr>
        <th>#</th><th>Jogador</th><th>Similaridade</th><th>Valor</th><th>Economia Est.</th>
      </tr></thead><tbody>${rows}</tbody></table></div>
      ${img(d.grafico_url)}</div>`;
  } catch(e){
    if(e.status===403) err(out,'🔒 Acesso negado. Requer plano OLHEIRO ou superior.');
    else err(out,e.detail||`Erro ${e.status}`);
  }
}

/* ── CICLO DE VIDA ──────────────────────────────────────────── */
async function doCiclo(){
  const names=readNames('ciclo-names');
  const out=$('ciclo-out');
  const ageWarn=$('ciclo-age-warnings');
  if(ageWarn) ageWarn.innerHTML='';
  if(names.length<3) return err(out,'Mínimo de 3 jogadores necessários.');
  const {valid}=await fetchScouts(names,out);
  if(valid.length<3) return err(out,'Mínimo de 3 jogadores com dados disponíveis necessários.');
  const ageWarnings=[];
  const js=valid.map(p=>{
    const key=(p.nome||'').toLowerCase();
    let idade=IDADES[key];
    if(idade===undefined){
      const found=Object.keys(IDADES).find(k=>k.includes(key)||key.includes(k));
      if(found) idade=IDADES[found];
    }
    if(idade===undefined){ ageWarnings.push(p.nome); idade=25; }
    return {nome:p.nome,idade,valor_milhoes:p.valor_milhoes,gols:p.gols,assists:p.assists};
  });
  if(ageWarnings.length&&ageWarn)
    ageWarn.innerHTML=ageWarnings.map(n=>`<div class="w" style="color:#ffd700;font-size:.82rem">⚠️ Idade de '${esc(n)}' não encontrada — usando 25 como padrão</div>`).join('');
  spin(out);
  try {
    const d=await api('POST','/v1/analytics/ciclo-vida',{jogadores:js});
    toast('ok', 'Ciclo de Vida calculado');
    const rows=(d.tabela||[]).map(j=>`<tr>
      <td>${esc(j.nome)}</td><td>${j.idade}</td>
      <td>€${j.valor_milhoes}M</td><td>€${(j.valor_predito||0).toFixed(1)}M</td>
      <td>${(j['desvio_%']||j.desvio||0).toFixed(1)}%</td></tr>`).join('');
    out.innerHTML=`<div class="card" style="margin-top:14px">
      <div class="ctitle">Resultado — Ciclo de Vida</div>
      <div class="krow">
        <div class="kbox"><div class="kval">${d.idade_pico??'—'}</div><div class="klbl">Idade de Pico</div></div>
        <div class="kbox"><div class="kval">€${(d.valor_pico_milhoes||0).toFixed(1)}M</div><div class="klbl">Valor no Pico</div></div>
        <div class="kbox"><div class="kval">${d.janela_revenda?.inicio??'—'} – ${d.janela_revenda?.fim??'—'}</div><div class="klbl">Janela Revenda</div></div>
      </div>
      <div class="twrap"><table class="dt"><thead><tr>
        <th>Jogador</th><th>Idade</th><th>Val.Real</th><th>Val.Previsto</th><th>Desvio</th>
      </tr></thead><tbody>${rows}</tbody></table></div>
      <div class="chart-box"><canvas id="chart-ciclo"></canvas></div></div>`;
    if(js.length===3) out.innerHTML+=`<div class="w" style="margin-top:10px">⚠️ Com apenas 3 jogadores o ajuste é exato. Adicione mais para análise significativa.</div>`;
    buildCicloChart('chart-ciclo', d);   // após o += (que reescreve o innerHTML)
  } catch(e){
    if(e.status===403) err(out,'🔒 Acesso negado. Requer plano DIRETOR.');
    else err(out,e.detail||`Erro ${e.status}`);
  }
}

/* ── GOLDEN LIST ────────────────────────────────────────────── */
function clearGoldenNames(){
  const div=$('golden-names');
  if(div) div.innerHTML='';
  doGoldenList();
}

async function doGoldenList(){
  const out=$('golden-out');
  const names=readNames('golden-names');
  const topn=parseInt($('golden-topn').value)||10;
  if(topn<1||topn>50) return err(out,'Top N deve estar entre 1 e 50.');
  let rows=[];
  if(names.length){
    const {valid}=await fetchScouts(names,out);
    rows=valid.map(p=>({nome:p.nome,valor_milhoes:p.valor_milhoes,gols:p.gols,assists:p.assists}));
  }
  spin(out);
  const body=rows.length?{jogadores:rows,top_n:topn}:{top_n:topn};
  try {
    const d=await api('POST','/v1/golden-list', body);
    toast('ok','Golden List gerada — '+d.total_pedigrees+' Pedigrees');
    const MEDALS=['🥇','🥈','🥉'];
    const fonte = d.fonte==='dataset_padrao'
      ? '<span style="color:var(--muted);font-size:.72rem">Dataset curado Bagre.ai</span>'
      : '<span style="color:var(--muted);font-size:.72rem">Pool personalizado</span>';
    const rows_html=(d.golden_list||[]).map(j=>{
      const medal = j.posicao<=3 ? `<span class="gl-medal">${MEDALS[j.posicao-1]}</span>`
                                 : `<span class="gl-pos">${j.posicao}º</span>`;
      const barPct=Math.min(100,(j.pedirato/((d.golden_list[0]||{}).pedirato||1))*100).toFixed(0);
      return `<tr>
        <td style="text-align:center;width:44px">${medal}</td>
        <td class="gl-nome">${esc(j.nome)}</td>
        <td>${j.gols}</td>
        <td>${j.assists}</td>
        <td>€${j.valor_milhoes}M</td>
        <td>
          <span class="gl-score">${j.pedirato.toFixed(2)}</span>
          <div style="margin-top:3px;height:3px;background:#1a2a1a;border-radius:2px;width:80px">
            <div style="height:100%;width:${barPct}%;background:var(--green);border-radius:2px;
                        box-shadow:0 0 4px rgba(57,255,20,.5)"></div>
          </div>
        </td>
        <td><span class="badge b-ped">PEDIGREE</span></td>
      </tr>`;
    }).join('');
    out.innerHTML=`<div class="card" style="margin-top:14px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <div class="ctitle" style="margin-bottom:0">🏆 Golden List — Top ${d.top_n}</div>
        ${fonte}
      </div>
      <div class="krow" style="margin-bottom:14px">
        <div class="kbox">
          <div class="kval" style="color:#fa0">${d.total_pedigrees}</div>
          <div class="klbl">Pedigrees Encontrados</div>
        </div>
        <div class="kbox">
          <div class="kval">${((d.golden_list||[])[0]||{}).nome||'—'}</div>
          <div class="klbl">Lider da Golden List</div>
        </div>
        <div class="kbox">
          <div class="kval">${((d.golden_list||[])[0]||{}).pedirato?.toFixed(2)||'—'}</div>
          <div class="klbl">Maior PediRato</div>
        </div>
      </div>
      <div class="twrap"><table class="dt">
        <thead><tr>
          <th>#</th><th>Jogador</th><th>Gols</th><th>Assists</th>
          <th>Valor</th><th>PediRato Score</th><th>Class.</th>
        </tr></thead>
        <tbody>${rows_html}</tbody>
      </table></div>
    </div>`;
  } catch(e){
    if(e.status===403) err(out,'🔒 Acesso negado. A Golden List é exclusiva do plano DIRETOR.');
    else err(out,e.detail||`Erro ${e.status}`);
  }
}

/* ── DOCX ───────────────────────────────────────────────────── */
function refreshDocx(){
  const el=$('docx-info'), btn=$('docx-btn');
  if(!window.sessao.length){
    el.innerHTML='<div class="w">Sessão vazia. Use o Scout para adicionar jogadores.</div>';
    btn.disabled=true; return;
  }
  const chips=window.sessao.map(j=>`<span class="chip">${esc(j.nome)}</span>`).join(' ');
  el.innerHTML=`<div style="display:flex;flex-wrap:wrap;gap:7px;margin-bottom:8px">${chips}</div>
    <div style="color:var(--muted);font-size:.78rem">${window.sessao.length} jogador(es)</div>`;
  btn.disabled=false;
}

async function doDocx(){
  if(!window.sessao.length) return alert('Adicione jogadores via Scout primeiro.');
  const me=window.ME;
  if(me&&!me.funcionalidades.includes('relatorio_docx')){
    const out=$('docx-out')||$('sdl');
    if(out) out.innerHTML='<div class="w">🔒 Relatório DOCX requer plano Diretor.</div>'; return;
  }
  const btn=$('sdocx-btn'), btn2=$('docx-btn'), dlEl=$('sdl'), outEl=$('docx-out');
  if(btn) btn.disabled=true; if(btn2) btn2.disabled=true;
  if(dlEl) dlEl.innerHTML='<span class="spinner" style="font-size:.72rem">GERANDO...</span>';
  try {
    const d=await api('POST','/v1/reports/docx',{jogadores:window.sessao});
    toast('ok', 'Relatório DOCX gerado');
    const link=`<a href="${esc(d.download_url)}" target="_blank" class="btn-p" style="display:inline-block;margin-top:8px;text-decoration:none">⬇ Baixar ${esc(d.filename)}</a>`;
    if(dlEl) dlEl.innerHTML=link;
    if(outEl) outEl.innerHTML=`<div class="i" style="margin-top:10px">Relatório gerado! ${link}</div>`;
  } catch(e){
    const m=`<div class="e">⚠ ${esc(e.detail||'Erro ao gerar.')}</div>`;
    if(dlEl) dlEl.innerHTML=m; if(outEl) outEl.innerHTML=m;
    toast('err', e.detail||'Erro ao gerar.');
  } finally {
    if(btn) btn.disabled=false; if(btn2) btn2.disabled=false;
  }
}

/* SESSION BAR */
function updBar(){
  if($('dash-kpi-sessao')) refreshDash();   // mantém os KPIs do Dashboard em dia
  const pe=$('splayers'), db=$('sdocx-btn'), dl=$('sdl');
  
  if(!window.sessao.length){ 
    if(pe) pe.innerHTML='<div style="color:var(--muted);font-size:0.8rem;text-align:center;padding:20px 0;">Sessão vazia.<br>Adicione jogadores via Scout.</div>';
    if(db) db.disabled=true;
    if(dl) dl.innerHTML='';
    return; 
  }
  
  if(pe) pe.innerHTML=window.sessao.map((j,i)=>`
    <div class="chip">${esc(j.nome)}<span class="rm" onclick="rmSessao(${i})" title="Remover">✕</span></div>`).join('');
    
  const can=window.ME&&window.ME.funcionalidades.includes('relatorio_docx');
  if(db) {
    db.disabled=!can; 
    db.title=can?'Gerar DOCX':'Requer plano Diretor';
  }
  if(dl) dl.innerHTML='';
}

function rmSessao(i){ window.sessao.splice(i,1); updBar(); }

/* INIT */
(async function(){
  if(window.K){
    try { const me=await api('GET','/v1/me'); window.ME=me; boot(me); }
    catch(_){ sessionStorage.removeItem('bagre_key'); window.K=''; }
  }
})();
// Expose functions to window for HTML onclick handlers
window.doLogin = doLogin;
window.doLogout = doLogout;
window.nav = nav;
window.doDocx = doDocx;
window.doScout = doScout;
window.doHype = doHype;
window.doEsp = doEsp;
window.doCiclo = doCiclo;
window.doGoldenList = doGoldenList;
window.rmSessao = rmSessao;
window.addNameRow = addNameRow;
window.selectAutocomplete = selectAutocomplete;
window.selectRefAutocomplete = selectRefAutocomplete;
window.addSessao = addSessao;
