"""
app.py - Bagre.ai REST API v1
Autenticação por API key (header X-API-Key).
Endpoints organizados por tier: várzea / olheiro / diretor.
"""
import os
import shutil
import uuid
import json
from typing import List, Optional, Union

import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from bagre_database import BagreDatabase
from bagre_auth import verificar_acesso, info_plano, FUNCIONALIDADES
from bagre_engine import BagreBackend
from bagre_scout import realizar_scout_processado, normalizar_texto
from bagre_relatorios import GeradorRelatorios
from bagre_analytics import (
    analisar_hype_index,
    analisar_ciclo_de_vida,
    analisar_concentracao_liga,
    espelho_pedigree,
)

# ── SETUP ──────────────────────────────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(
    title="Bagre.ai API",
    description=(
        "API REST comercial de Inteligência de Mercado no Futebol.\n\n"
        "**Autenticação:** header `X-API-Key: <sua_chave>`\n\n"
        "**Tiers:** `várzea` (free) · `olheiro` (R$29,90) · `diretor` (R$997,00)"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db    = BagreDatabase()
motor = BagreBackend()


# ── AUTENTICAÇÃO ───────────────────────────────────────────────────────────────
def get_current_user(x_api_key: str = Header(..., alias="X-API-Key")) -> dict:
    usuario = db.autenticar(x_api_key)
    if not usuario:
        raise HTTPException(status_code=401, detail="API key inválida ou não encontrada.")
    # Injeta a api_key no dict para reuso nos endpoints sem nova query ao banco
    return {**dict(usuario), "_api_key": x_api_key}


def _verificar_tier(usuario: dict, funcionalidade: str):
    """Checa tier e limite; levanta 403/429 conforme o caso."""
    permitido, motivo = verificar_acesso(usuario["_api_key"], funcionalidade)
    if not permitido:
        if "Limite diário" in motivo:
            raise HTTPException(status_code=429, detail=motivo)
        raise HTTPException(status_code=403, detail=motivo)


def _copiar_grafico(nome_fixo: str, prefixo: str) -> str:
    """Copia o gráfico de nome fixo para um arquivo com UUID e retorna a URL pública."""
    src = os.path.join(STATIC_DIR, nome_fixo)
    if not os.path.exists(src):
        return ""
    uid  = uuid.uuid4().hex[:8]
    dest = os.path.join(STATIC_DIR, f"{prefixo}_{uid}.png")
    shutil.copy2(src, dest)
    return f"/static/{prefixo}_{uid}.png"


# ── MODELS ─────────────────────────────────────────────────────────────────────
class JogadorHype(BaseModel):
    nome: str
    valor_milhoes: float
    gols: int
    assists: int

class JogadorVida(BaseModel):
    nome: str
    idade: int
    valor_milhoes: float

class ClubeGini(BaseModel):
    clube: str
    valor_total_elenco_milhoes: float

class JogadorRef(BaseModel):
    nome: str
    gols: int
    assists: int
    valor_milhoes: float

class HypeIndexRequest(BaseModel):
    jogadores: List[JogadorHype]

    model_config = {"json_schema_extra": {"example": {
        "jogadores": [
            {"nome": "Neymar Jr.",  "valor_milhoes": 90, "gols": 3,  "assists": 2},
            {"nome": "Lookman",     "valor_milhoes": 38, "gols": 17, "assists": 9},
            {"nome": "Vinicius Jr.","valor_milhoes": 180,"gols": 21, "assists": 8},
        ]
    }}}

class EspelhoPedigreeRequest(BaseModel):
    jogador_ref: JogadorRef
    pool: List[JogadorRef]

class GiniRequest(BaseModel):
    clubes: List[ClubeGini]

class CicloVidaRequest(BaseModel):
    jogadores: List[JogadorVida]

class DocxReportRequest(BaseModel):
    jogadores: List[dict]


# ── FRONTEND LEGADO ────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_frontend():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "templates", "index.html")
    try:
        with open(html_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h3>Frontend (templates/index.html) não encontrado.</h3>"


# ── HEALTH ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Sistema"])
def health():
    """Verifica status da API e do banco de dados. Não requer autenticação."""
    try:
        with db._conn() as conn:
            n_usuarios = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        db_ok = True
    except Exception:
        n_usuarios = 0
        db_ok = False

    return {
        "status": "ok",
        "version": "1.0.0",
        "database": "ok" if db_ok else "erro",
        "usuarios_cadastrados": n_usuarios,
    }


# ── ME ─────────────────────────────────────────────────────────────────────────
@app.get("/v1/me", tags=["Conta"])
def get_me(usuario: dict = Depends(get_current_user)):
    """Retorna dados do usuário autenticado, plano e histórico recente."""
    from bagre_database import LIMITES, _chave_plano
    plano_key   = _chave_plano(usuario["plano"])
    limite_dia  = LIMITES.get(plano_key, 0)
    funcoes_ok  = [f for f, planos in FUNCIONALIDADES.items() if plano_key in planos]
    historico   = db.get_historico(usuario["id"], limite=5)

    return {
        "email":           usuario["email"],
        "nome":            usuario["nome"],
        "plano":           usuario["plano"],
        "uso_hoje":        usuario["requests_hoje"],
        "limite_diario":   "ilimitado" if limite_dia == -1 else limite_dia,
        "funcionalidades": funcoes_ok,
        "historico":       [
            {"tipo": h["tipo"], "criado_em": h["criado_em"], "input": h["input"]}
            for h in historico
        ],
    }


# ── TIER VÁRZEA — SCOUT ────────────────────────────────────────────────────────
@app.get("/v1/scout", tags=["Várzea (free)"])
@limiter.limit("10/minute")
def scout(
    request: Request,
    nome: str = Query(..., description="Nome do jogador"),
    valor_mercado: Optional[float] = Query(None, description="Valor manual em €M"),
    gols: Optional[int]   = Query(None),
    assists: Optional[int] = Query(None),
    usuario: dict = Depends(get_current_user),
):
    """
    **Tier mínimo: várzea.**
    Busca e calcula o Índice PediRato de um jogador.
    Usa cache de 24h para economizar chamadas externas.
    """
    _verificar_tier(usuario, "scout")

    nome_norm = normalizar_texto(nome)

    # Verificar cache
    cached = db.buscar_cache(nome_norm)
    if cached:
        db.salvar_analise(usuario["id"], "scout",
                          {"nome": nome, "fonte": "cache"}, cached)
        return {**cached, "fonte": "cache"}

    # Buscar via APIs externas
    resultado = realizar_scout_processado(
        nome_jogador=nome,
        valor_mercado_manual=valor_mercado,
        gols_manual=gols,
        assists_manual=assists,
    )

    if resultado.get("status") == "ambiguous":
        raise HTTPException(
            status_code=409,
            detail={
                "mensagem": "Múltiplos jogadores encontrados. Refine a busca.",
                "sugestoes": resultado.get("suggestions", [])[:5],
            },
        )

    if resultado.get("status") != "success":
        raise HTTPException(status_code=404, detail="Jogador não encontrado.")

    db.salvar_cache(nome_norm, resultado)
    db.salvar_analise(usuario["id"], "scout", {"nome": nome}, resultado)
    return {**resultado, "fonte": "api"}


# ── TIER OLHEIRO — HYPE INDEX ──────────────────────────────────────────────────
@app.post("/v1/analytics/hype-index", tags=["Olheiro"])
@limiter.limit("5/minute")
def hype_index(request: Request, req: HypeIndexRequest, usuario: dict = Depends(get_current_user)):
    """
    **Tier mínimo: olheiro.**
    Regressão linear Performance × Valor. Classifica jogadores em
    PediRato / Pedigree / Regular pelos resíduos.
    """
    _verificar_tier(usuario, "hype_index")

    if len(req.jogadores) < 3:
        raise HTTPException(status_code=422,
                            detail="Mínimo de 3 jogadores para análise de regressão.")

    df = pd.DataFrame([j.model_dump() for j in req.jogadores])
    resultado_df = analisar_hype_index(df)
    grafico_url  = _copiar_grafico("hype_index.png", "hype")

    registros = resultado_df[
        ["nome", "valor_milhoes", "performance", "valor_predito", "residuo", "classificacao"]
    ].to_dict("records")

    output = {"jogadores": registros, "grafico_url": grafico_url}
    db.salvar_analise(usuario["id"], "hype_index",
                      {"n_jogadores": len(req.jogadores)}, output)
    return output


# ── TIER OLHEIRO — ESPELHO PEDIGREE ───────────────────────────────────────────
@app.post("/v1/analytics/espelho-pedigree", tags=["Olheiro"])
@limiter.limit("5/minute")
def espelho_pedigree_endpoint(
    request: Request,
    req: EspelhoPedigreeRequest,
    usuario: dict = Depends(get_current_user),
):
    """
    **Tier mínimo: olheiro.**
    Similaridade cosseno para encontrar os 3 jogadores mais similares
    ao referencial com valor < 60% do referencial.
    """
    _verificar_tier(usuario, "espelho_pedigree")

    ref  = req.jogador_ref.model_dump()
    pool = [j.model_dump() for j in req.pool]

    if not pool:
        raise HTTPException(status_code=422, detail="Pool de candidatos vazio.")

    resultado_df = espelho_pedigree(ref, pool)
    grafico_url  = _copiar_grafico("radar_pedigree.png", "radar")

    if resultado_df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum candidato com valor < 60% de €{ref['valor_milhoes']:.1f}M encontrado."
        )

    similares = resultado_df.to_dict("records")
    output = {
        "referencial":   ref["nome"],
        "top_3_similares": similares,
        "grafico_url":   grafico_url,
    }
    db.salvar_analise(usuario["id"], "espelho_pedigree",
                      {"referencial": ref["nome"]}, output)
    return output


# ── TIER DIRETOR — GINI ────────────────────────────────────────────────────────
@app.post("/v1/analytics/gini", tags=["Diretor"])
@limiter.limit("5/minute")
def gini(request: Request, req: GiniRequest, usuario: dict = Depends(get_current_user)):
    """
    **Tier mínimo: diretor.**
    Coeficiente de Gini e Curva de Lorenz para concentração de riqueza por liga.
    """
    _verificar_tier(usuario, "gini")

    if len(req.clubes) < 2:
        raise HTTPException(status_code=422, detail="Mínimo de 2 clubes.")

    df      = pd.DataFrame([c.model_dump() for c in req.clubes])
    res     = analisar_concentracao_liga(df)
    grafico = _copiar_grafico("gini_liga.png", "gini")

    output = {
        "gini":            res["gini"],
        "interpretacao":   res["interpretacao"],
        "clube_mais_rico": res["clube_mais_rico"],
        "clube_mais_pobre":res["clube_mais_pobre"],
        "razao":           res["razao"],
        "tabela":          res["df"][["clube","valor_total_elenco_milhoes",
                                      "concentracao_acumulada_%"]].to_dict("records"),
        "grafico_url":     grafico,
    }
    db.salvar_analise(usuario["id"], "gini",
                      {"n_clubes": len(req.clubes)}, output)
    return output


# ── TIER DIRETOR — CICLO DE VIDA ───────────────────────────────────────────────
@app.post("/v1/analytics/ciclo-vida", tags=["Diretor"])
@limiter.limit("5/minute")
def ciclo_vida(request: Request, req: CicloVidaRequest, usuario: dict = Depends(get_current_user)):
    """
    **Tier mínimo: diretor.**
    Regressão polinomial Idade × Valor. Retorna pico estimado e janela de revenda.
    """
    _verificar_tier(usuario, "ciclo_vida")

    if len(req.jogadores) < 3:
        raise HTTPException(status_code=422,
                            detail="Mínimo de 3 jogadores para regressão polinomial.")

    df  = pd.DataFrame([j.model_dump() for j in req.jogadores])
    res = analisar_ciclo_de_vida(df)
    grafico = _copiar_grafico("ciclo_vida.png", "ciclo")

    output = {
        "idade_pico":        res["idade_pico"],
        "valor_pico_milhoes":res["valor_pico_milhoes"],
        "janela_revenda":    {"inicio": res["janela_revenda"][0],
                              "fim":    res["janela_revenda"][1]},
        "coeficientes":      {"a": res["coeficientes"][0],
                              "b": res["coeficientes"][1],
                              "c": res["coeficientes"][2]},
        "tabela":            res["df"][["nome","idade","valor_milhoes",
                                        "valor_predito","desvio_%"]].to_dict("records"),
        "grafico_url":       grafico,
    }
    db.salvar_analise(usuario["id"], "ciclo_vida",
                      {"n_jogadores": len(req.jogadores)}, output)
    return output


# ── TIER DIRETOR — RELATÓRIO DOCX ─────────────────────────────────────────────
@app.post("/v1/reports/docx", tags=["Diretor"])
@limiter.limit("2/minute")
def gerar_relatorio_docx(request: Request, req: DocxReportRequest, usuario: dict = Depends(get_current_user)):
    """
    **Tier mínimo: diretor.**
    Gera relatório Word completo com tabela, gráficos e metodologia.
    Retorna URL de download do `.docx`.
    """
    _verificar_tier(usuario, "relatorio_docx")

    if not req.jogadores:
        raise HTTPException(status_code=422, detail="Lista de jogadores vazia.")

    uid      = uuid.uuid4().hex[:8]
    filename = os.path.join(STATIC_DIR, f"relatorio_{uid}.docx")

    caminho = GeradorRelatorios.gerar_relatorio_completo_docx(
        historico_jogadores=req.jogadores,
        resultados_analytics={},
        filename=filename,
    )
    if not caminho:
        raise HTTPException(status_code=500, detail="Falha ao gerar o relatório Word.")

    download_url = f"/static/relatorio_{uid}.docx"
    db.salvar_analise(usuario["id"], "relatorio_docx",
                      {"n_jogadores": len(req.jogadores)},
                      {"download_url": download_url})
    return {"download_url": download_url, "filename": f"relatorio_{uid}.docx"}


# ── ENDPOINTS LEGADOS (sem auth — compatibilidade com frontend existente) ───────
@app.get("/api/search", include_in_schema=False)
def search_legacy(query: str):
    if not query:
        raise HTTPException(status_code=400, detail="Parâmetro 'query' obrigatório.")
    resultado = motor.buscar_jogador(query)
    return resultado or {"status": "success", "response": {"suggestions": []}}


@app.post("/api/scout", include_in_schema=False)
def scout_legacy(req: dict):
    try:
        return realizar_scout_processado(
            nome_jogador=req.get("nome_jogador", ""),
            player_id=req.get("player_id"),
            team_id=req.get("team_id"),
            valor_mercado_manual=req.get("valor_mercado_manual"),
            gols_manual=req.get("gols_manual"),
            assists_manual=req.get("assists_manual"),
            url_fbref=req.get("url_fbref"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
