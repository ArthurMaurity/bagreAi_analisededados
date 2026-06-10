export const $ = id => document.getElementById(id);
export function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
export function spin(el){
  el.innerHTML=`
    <div class="sk-card">
      <div class="sk-line w40" style="height:18px"></div>
      <div class="sk-line w60"></div>
      <div class="sk-grid">
        <div class="sk-box"></div><div class="sk-box"></div>
        <div class="sk-box"></div><div class="sk-box"></div>
      </div>
      <div class="sk-line w100" style="height:130px;margin-top:6px"></div>
    </div>`;
}
export function err(el,m){
  const txt = esc(typeof m==='object'?JSON.stringify(m):m);
  el.innerHTML=`<div class="e">⚠ ${txt}</div>`;
  toast('err', m);
}
export function toast(type, msg){
  const wrap = $('toast-wrap'); if(!wrap) return;
  const t = document.createElement('div');
  t.className = 'toast ' + (type==='ok' ? 'toast-ok' : 'toast-err');
  const icon = type==='ok' ? '✓' : '⚠';
  t.innerHTML = `<span class="toast-ic">${icon}</span><span>${esc(typeof msg==='object'?JSON.stringify(msg):msg)}</span>`;
  wrap.appendChild(t);
  setTimeout(()=>{ t.classList.add('toast-out'); setTimeout(()=>t.remove(), 320); }, 3200);
}
export function img(url){
  if(!url) return '';
  return `<div class="chart-wrap"><img src="${url}?t=${Date.now()}" alt="grafico">
          <div class="chart-ts">Gerado em ${new Date().toLocaleTimeString('pt-BR')}</div></div>`;
}
export function badge(cls){
  if(!cls) return '';
  const c=cls.toLowerCase();
  if(c.includes('pedigree')&&!c.includes('rato')) return `<span class="badge b-ped">PEDIGREE</span>`;
  if(c.includes('pedirato')||c.includes('rato'))  return `<span class="badge b-rat">PEDIRATO</span>`;
  return `<span class="badge b-reg">REGULAR</span>`;
}
