"""
qa_tester.py — Bagre.ai QA Suite
Roda contra http://localhost:8000 e imprime relatório completo.
Uso: python qa_tester.py
"""
import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"

KEYS = {
    "varzea":  "3d5d355c-0f8e-4e34-8c48-7f2163c63a2e",
    "olheiro": "bc066b0a-2fb3-40ec-8714-e182a5109c75",
    "diretor": "920996aa-e49f-4613-8b74-1015d1397658",
}

# ── Contadores ────────────────────────────────────────────────────────────────
_ok = _fail = _warn = 0
_results = []


def _log(status, label, detail=""):
    global _ok, _fail, _warn
    sym = {"OK": "✓", "FAIL": "✗", "WARN": "⚠"}[status]
    color = {"OK": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}[status]
    reset = "\033[0m"
    line = f"  {color}{sym}{reset} {label}"
    if detail:
        line += f"  →  {detail}"
    print(line)
    _results.append((status, label, detail))
    if status == "OK":   _ok   += 1
    if status == "FAIL": _fail += 1
    if status == "WARN": _warn += 1


def section(title):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")


def get(path, key=None, params=None):
    h = {"X-API-Key": key} if key else {}
    return requests.get(f"{BASE}{path}", headers=h, params=params, timeout=10)


def post(path, body, key=None):
    h = {"Content-Type": "application/json"}
    if key:
        h["X-API-Key"] = key
    return requests.post(f"{BASE}{path}", headers=h, data=json.dumps(body), timeout=15)


# ─────────────────────────────────────────────────────────────────────────────
# 1. INFRA
# ─────────────────────────────────────────────────────────────────────────────
section("1. INFRAESTRUTURA")

try:
    r = get("/health")
    d = r.json()
    if r.status_code == 200 and d.get("status") == "ok":
        _log("OK", "GET /health", f"database={d['database']} | usuarios={d['usuarios_cadastrados']}")
    else:
        _log("FAIL", "GET /health", f"status={r.status_code}")
except Exception as e:
    _log("FAIL", "GET /health — app inacessível", str(e))
    print("\n  App não está rodando em localhost:8000. Inicie com: python app.py\n")
    sys.exit(1)

r = get("/")
if r.status_code == 200 and "plan-card" in r.text:
    _log("OK", "GET / — frontend servido com cards de plano")
elif r.status_code == 200:
    _log("WARN", "GET / — frontend servido mas sem plan-card", "verifique templates/index.html")
else:
    _log("FAIL", "GET /", f"status={r.status_code}")

r = get("/docs")
_log("OK" if r.status_code == 200 else "FAIL", "GET /docs — Swagger UI", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. AUTENTICAÇÃO
# ─────────────────────────────────────────────────────────────────────────────
section("2. AUTENTICAÇÃO")

r = get("/v1/me")
# FastAPI retorna 422 para header obrigatório ausente (comportamento padrão do framework)
_log("OK" if r.status_code in (401, 422) else "FAIL",
     "Sem API key → 401/422", f"status={r.status_code}")

r = get("/v1/me", key="chave-invalida-000")
_log("OK" if r.status_code == 401 else "FAIL",
     "Key inválida → 401", f"status={r.status_code}")

for plano, key in KEYS.items():
    r = get("/v1/me", key=key)
    if r.status_code == 200:
        d = r.json()
        _log("OK", f"/v1/me [{plano}]",
             f"email={d['email']} | uso={d['uso_hoje']}/{d['limite_diario']} | funções={d['funcionalidades']}")
    else:
        _log("FAIL", f"/v1/me [{plano}]", f"status={r.status_code} — {r.text[:80]}")


# ─────────────────────────────────────────────────────────────────────────────
# 3. TIER VÁRZEA — endpoints gratuitos
# ─────────────────────────────────────────────────────────────────────────────
section("3. TIER VÁRZEA — endpoints gratuitos")

key_v = KEYS["varzea"]

r = get("/v1/pedirato-da-semana", key=key_v)
if r.status_code == 200:
    d = r.json()
    _log("OK", "GET /v1/pedirato-da-semana",
         f"{d['nome']} | pedirato={d['pedirato']} | semana={d['semana']}")
else:
    _log("FAIL", "GET /v1/pedirato-da-semana", f"status={r.status_code}")

r = get("/v1/search", key=key_v, params={"query": "Neymar"})
if r.status_code == 200:
    sugs = r.json().get("response", {}).get("suggestions", [])
    _log("OK", "GET /v1/search?query=Neymar", f"{len(sugs)} sugestão(ões)")
else:
    _log("FAIL", "GET /v1/search", f"status={r.status_code}")

r = get("/v1/search", key=key_v, params={"query": "x"})
_log("OK" if r.status_code == 200 else "FAIL",
     "GET /v1/search query muito curta (1 char)", f"status={r.status_code}")

r = get("/v1/scout", key=key_v, params={"nome": "Arrascaeta"})
if r.status_code == 200:
    d = r.json()
    _log("OK", "GET /v1/scout?nome=Arrascaeta",
         f"gols={d.get('gols')} assists={d.get('assists')} valor={d.get('valor_milhoes')}M pedirato={d.get('pedirato')} fonte={d.get('fonte')}")
else:
    _log("FAIL", "GET /v1/scout?nome=Arrascaeta", f"status={r.status_code} — {r.text[:120]}")

r = get("/v1/scout", key=key_v, params={"nome": "ab"})
_log("OK" if r.status_code == 400 else "FAIL",
     "GET /v1/scout nome muito curto → 400", f"status={r.status_code}")

r = get("/v1/scout", key=key_v, params={"nome": ""})
_log("OK" if r.status_code in (400, 422) else "FAIL",
     "GET /v1/scout nome vazio → 400/422", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. CONTROLE DE ACESSO — várzea tentando acessar features superiores
# ─────────────────────────────────────────────────────────────────────────────
section("4. CONTROLE DE ACESSO — várzea bloqueada em features superiores")

bloqueios = [
    ("POST", "/v1/analytics/hype-index",   {"jogadores": [{"nome":"A","valor_milhoes":10,"gols":5,"assists":3}]*3}),
    ("POST", "/v1/analytics/espelho-pedigree", {"jogador_ref":{"nome":"X","gols":5,"assists":3,"valor_milhoes":100},"pool":[{"nome":"Y","gols":4,"assists":2,"valor_milhoes":20}]}),
    ("POST", "/v1/analytics/ciclo-vida",   {"jogadores": [{"nome":"A","idade":25,"valor_milhoes":10}]*3}),
    ("POST", "/v1/golden-list",            {"top_n": 5}),
    ("POST", "/v1/reports/docx",           {"jogadores": [{"nome":"X","gols":1,"assists":1,"valor_milhoes":10}]}),
]

for method, path, body in bloqueios:
    r = post(path, body, key=key_v) if method == "POST" else get(path, key=key_v)
    _log("OK" if r.status_code == 403 else "FAIL",
         f"várzea → {path} deve retornar 403", f"status={r.status_code}")

section("4b. CONTROLE DE ACESSO — olheiro bloqueado em features diretor")

key_o = KEYS["olheiro"]
bloqueios_dir = [
    ("POST", "/v1/analytics/ciclo-vida",   {"jogadores": [{"nome":"A","idade":25,"valor_milhoes":10}]*3}),
    ("POST", "/v1/golden-list",            {"top_n": 5}),
    ("POST", "/v1/reports/docx",           {"jogadores": [{"nome":"X","gols":1,"assists":1,"valor_milhoes":10}]}),
]
for method, path, body in bloqueios_dir:
    r = post(path, body, key=key_o) if method == "POST" else get(path, key=key_o)
    _log("OK" if r.status_code == 403 else "FAIL",
         f"olheiro → {path} deve retornar 403", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. TIER OLHEIRO — Hype Index
# ─────────────────────────────────────────────────────────────────────────────
section("5. TIER OLHEIRO — Hype Index")

jogadores_hype = [
    {"nome": "Arrascaeta",     "valor_milhoes": 14,  "gols": 25, "assists": 19},
    {"nome": "Vinicius Junior","valor_milhoes": 180, "gols": 9,  "assists": 7},
    {"nome": "Kylian Mbappe",  "valor_milhoes": 250, "gols": 18, "assists": 7},
    {"nome": "Griezmann",      "valor_milhoes": 20,  "gols": 16, "assists": 11},
    {"nome": "Haaland",        "valor_milhoes": 200, "gols": 27, "assists": 6},
]

r = post("/v1/analytics/hype-index", {"jogadores": jogadores_hype}, key=key_o)
if r.status_code == 200:
    d = r.json()
    classifs = {j["nome"]: j["classificacao"] for j in d["jogadores"]}
    _log("OK", "POST /v1/analytics/hype-index",
         f"grafico={bool(d.get('grafico_url'))} | classifs={classifs}")
else:
    _log("FAIL", "POST /v1/analytics/hype-index", f"status={r.status_code} — {r.text[:120]}")

r = post("/v1/analytics/hype-index", {"jogadores": jogadores_hype[:2]}, key=key_o)
_log("OK" if r.status_code == 422 else "FAIL",
     "Hype Index com < 3 jogadores → 422", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 6. TIER OLHEIRO — Espelho Pedigree
# ─────────────────────────────────────────────────────────────────────────────
section("6. TIER OLHEIRO — Espelho Pedigree")

ref  = {"nome": "Kylian Mbappe", "gols": 18, "assists": 7, "valor_milhoes": 250}
pool = [
    {"nome": "Arrascaeta",    "gols": 25, "assists": 19, "valor_milhoes": 14},
    {"nome": "Griezmann",     "gols": 16, "assists": 11, "valor_milhoes": 20},
    {"nome": "Bruno Fernandes","gols": 15, "assists": 17, "valor_milhoes": 65},
    {"nome": "Lamine Yamal",  "gols": 18, "assists": 16, "valor_milhoes": 180},
]

r = post("/v1/analytics/espelho-pedigree", {"jogador_ref": ref, "pool": pool}, key=key_o)
if r.status_code == 200:
    d = r.json()
    similares = [(s["nome"], s["similaridade_%"], s["economia_estimada_milhoes"]) for s in d["top_3_similares"]]
    _log("OK", "POST /v1/analytics/espelho-pedigree",
         f"ref={d['referencial']} | top3={similares}")
else:
    _log("FAIL", "POST /v1/analytics/espelho-pedigree", f"status={r.status_code} — {r.text[:120]}")

r = post("/v1/analytics/espelho-pedigree", {"jogador_ref": ref, "pool": []}, key=key_o)
_log("OK" if r.status_code == 422 else "FAIL",
     "Espelho Pedigree pool vazio → 422", f"status={r.status_code}")

# Pool onde ninguém tem valor < 60% do ref
pool_caro = [{"nome": "Haaland", "gols": 27, "assists": 6, "valor_milhoes": 200}]
r = post("/v1/analytics/espelho-pedigree", {"jogador_ref": ref, "pool": pool_caro}, key=key_o)
_log("OK" if r.status_code == 404 else "FAIL",
     "Espelho Pedigree sem candidatos < 60% → 404", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 7. TIER DIRETOR — Ciclo de Vida
# ─────────────────────────────────────────────────────────────────────────────
section("7. TIER DIRETOR — Ciclo de Vida")

key_d = KEYS["diretor"]

jogadores_ciclo = [
    {"nome": "Endrick",    "idade": 18, "valor_milhoes": 35},
    {"nome": "Raphinha",   "idade": 28, "valor_milhoes": 70},
    {"nome": "Griezmann",  "idade": 33, "valor_milhoes": 20},
    {"nome": "Haaland",    "idade": 24, "valor_milhoes": 200},
    {"nome": "Modric",     "idade": 39, "valor_milhoes": 5},
]

r = post("/v1/analytics/ciclo-vida", {"jogadores": jogadores_ciclo}, key=key_d)
if r.status_code == 200:
    d = r.json()
    _log("OK", "POST /v1/analytics/ciclo-vida",
         f"pico={d['idade_pico']}anos €{d['valor_pico_milhoes']}M | janela={d['janela_revenda']}")
else:
    _log("FAIL", "POST /v1/analytics/ciclo-vida", f"status={r.status_code} — {r.text[:120]}")

r = post("/v1/analytics/ciclo-vida", {"jogadores": jogadores_ciclo[:2]}, key=key_d)
_log("OK" if r.status_code == 422 else "FAIL",
     "Ciclo de Vida com < 3 jogadores → 422", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 8. TIER DIRETOR — Golden List
# ─────────────────────────────────────────────────────────────────────────────
section("8. TIER DIRETOR — Golden List")

r = post("/v1/golden-list", {"top_n": 5}, key=key_d)
if r.status_code == 200:
    d = r.json()
    nomes = [j["nome"] for j in d["golden_list"]]
    _log("OK", "POST /v1/golden-list (dataset padrão)",
         f"fonte={d['fonte']} | total_pedigrees={d['total_pedigrees']} | top5={nomes}")
else:
    _log("FAIL", "POST /v1/golden-list", f"status={r.status_code} — {r.text[:120]}")

pool_custom = [
    {"nome": "Arrascaeta",  "valor_milhoes": 14,  "gols": 25, "assists": 19},
    {"nome": "Mbappe",      "valor_milhoes": 250, "gols": 18, "assists": 7},
    {"nome": "Griezmann",   "valor_milhoes": 20,  "gols": 16, "assists": 11},
]
r = post("/v1/golden-list", {"top_n": 3, "jogadores": pool_custom}, key=key_d)
if r.status_code == 200:
    d = r.json()
    _log("OK", "POST /v1/golden-list (pool personalizado)",
         f"fonte={d['fonte']} | pedigrees={[j['nome'] for j in d['golden_list']]}")
else:
    _log("FAIL", "POST /v1/golden-list pool custom", f"status={r.status_code} — {r.text[:120]}")

r = post("/v1/golden-list", {"top_n": 5, "jogadores": [pool_custom[0]]}, key=key_d)
_log("OK" if r.status_code == 422 else "FAIL",
     "Golden List com < 2 jogadores → 422", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 9. TIER DIRETOR — Relatório DOCX
# ─────────────────────────────────────────────────────────────────────────────
section("9. TIER DIRETOR — Relatório DOCX")

# Rate limit: 2/min — aguarda janela limpa
print("  (aguardando 62s para limpar rate limit do endpoint DOCX...)")
time.sleep(62)

jogadores_docx = [
    {"nome": "Arrascaeta",  "gols": 25, "assists": 19, "valor_milhoes": 14,  "pedirato": 3.14},
    {"nome": "Haaland",     "gols": 27, "assists": 6,  "valor_milhoes": 200, "pedirato": 0.165},
    {"nome": "Griezmann",   "gols": 16, "assists": 11, "valor_milhoes": 20,  "pedirato": 1.35},
]

r = post("/v1/reports/docx", {"jogadores": jogadores_docx}, key=key_d)
if r.status_code == 200:
    d = r.json()
    url = d.get("download_url", "")
    _log("OK", "POST /v1/reports/docx", f"download_url={url}")
    if url:
        r2 = get(url)
        _log("OK" if r2.status_code == 200 else "FAIL",
             f"Download do .docx gerado", f"status={r2.status_code} | bytes={len(r2.content)}")
else:
    _log("FAIL", "POST /v1/reports/docx", f"status={r.status_code} — {r.text[:120]}")

r = post("/v1/reports/docx", {"jogadores": []}, key=key_d)
_log("OK" if r.status_code == 422 else "FAIL",
     "DOCX lista vazia → 422", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 10. ENDPOINTS LEGADOS (sem auth)
# ─────────────────────────────────────────────────────────────────────────────
section("10. ENDPOINTS LEGADOS (sem auth — compatibilidade frontend)")

r = get("/api/search", params={"query": "Neymar"})
_log("OK" if r.status_code == 200 else "WARN",
     "GET /api/search (legacy)", f"status={r.status_code}")

r = post("/api/scout", {"nome_jogador": "Haaland"})
_log("OK" if r.status_code == 200 else "WARN",
     "POST /api/scout (legacy)", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 11. EDGE CASES — validações de input
# ─────────────────────────────────────────────────────────────────────────────
section("11. EDGE CASES — validações de input")

r = get("/v1/scout", key=key_v, params={"nome": "A" * 101})
_log("OK" if r.status_code == 400 else "FAIL",
     "Scout nome > 100 chars → 400", f"status={r.status_code}")

r = post("/v1/analytics/hype-index", {"jogadores": [
    {"nome": "X", "valor_milhoes": 0, "gols": 0, "assists": 0},
    {"nome": "Y", "valor_milhoes": 0, "gols": 0, "assists": 0},
    {"nome": "Z", "valor_milhoes": 0, "gols": 0, "assists": 0},
]}, key=key_o)
_log("OK" if r.status_code in (200, 422) else "FAIL",
     "Hype Index com valores zerados", f"status={r.status_code}")

r = post("/v1/golden-list", {"top_n": 999}, key=key_d)
if r.status_code == 200:
    top_n = r.json().get("top_n")
    _log("OK" if top_n <= 50 else "FAIL",
         "Golden List top_n=999 limitado a 50", f"top_n retornado={top_n}")
elif r.status_code == 429:
    _log("WARN", "Golden List top_n=999 → rate limited (429)", "aguarde 1 min e rode novamente")
else:
    _log("WARN", "Golden List top_n=999", f"status={r.status_code}")

r = get("/v1/rota-inexistente", key=key_v)
_log("OK" if r.status_code == 404 else "FAIL",
     "Rota inexistente → 404", f"status={r.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# RELATÓRIO FINAL
# ─────────────────────────────────────────────────────────────────────────────
total = _ok + _fail + _warn
print(f"\n{'═'*60}")
print(f"  RELATÓRIO FINAL — Bagre.ai QA")
print(f"{'═'*60}")
print(f"  Total de testes:  {total}")
print(f"  \033[92m✓ OK:    {_ok}\033[0m")
print(f"  \033[91m✗ FAIL:  {_fail}\033[0m")
print(f"  \033[93m⚠ WARN:  {_warn}\033[0m")

if _fail == 0:
    print(f"\n  \033[92m✓ PENTE FINO LIMPO — nenhuma falha crítica encontrada.\033[0m")
else:
    print(f"\n  \033[91m✗ {_fail} FALHA(S) ENCONTRADA(S):\033[0m")
    for status, label, detail in _results:
        if status == "FAIL":
            print(f"    • {label}")
            if detail:
                print(f"      {detail}")

print()
