export async function api(method, path, body){
  const opts = { method, headers: {'Content-Type':'application/json','X-API-Key':window.K} };
  if(body!==undefined) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  const d = await r.json().catch(()=>({}));
  if(!r.ok) throw {status:r.status, detail: d.detail||r.statusText};
  return d;
}
