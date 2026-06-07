from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Union
import os

from bagre_engine import BagreBackend
from bagre_scout import realizar_scout_processado
from bagre_relatorios import GeradorRelatorios

app = FastAPI(
    title="Bagre.ai API",
    description="Backend REST API do motor central de análise e scouting Bagre.ai",
    version="1.0.0"
)

# Configurar diretório estático
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Montar diretório static para servir os relatórios e gráficos gerados
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configuração de CORS para permitir conexões de qualquer futuro frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS DE ENTRADA (SCHEMAS) ---

class ScoutRequest(BaseModel):
    nome_jogador: str
    player_id: Optional[Union[str, int]] = None
    team_id: Optional[Union[str, int]] = None
    valor_mercado_manual: Optional[float] = None
    gols_manual: Optional[int] = None
    assists_manual: Optional[int] = None
    url_fbref: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "nome_jogador": "Ousmane Dembélé"
            }
        }
    }

class JogadorData(BaseModel):
    nome: str
    gols: int
    assists: int
    valor_milhoes: float
    pedirato: float

class CompareRequest(BaseModel):
    jogadores: List[JogadorData]

# --- INSTÂNCIAS ---
motor = BagreBackend()

# --- ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
def read_root():
    """
    Serve o painel web interativo principal (frontend integrado).
    """
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    html_path = os.path.join(templates_dir, "index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h3>Frontend templates/index.html não encontrado no servidor.</h3>"

@app.get("/api/search")
def search_player(query: str):
    """
    Busca jogadores, clubes e ligas na API principal.
    Retorna sugestões estruturadas para desambiguação no frontend.
    """
    if not query:
        raise HTTPException(status_code=400, detail="O parâmetro 'query' de busca é obrigatório.")
        
    print(f"Buscando termo: {query}")
    resultado = motor.buscar_jogador(query)
    
    if not resultado:
        return {"status": "success", "response": {"suggestions": []}}
        
    return resultado

@app.post("/api/scout")
def scout_player(req: ScoutRequest):
    """
    Executa o processo de scouting do jogador de forma não interativa.
    Combina dados de APIs com as contingências e overrides manuais fornecidos pelo frontend.
    """
    try:
        dados = realizar_scout_processado(
            nome_jogador=req.nome_jogador,
            player_id=req.player_id,
            team_id=req.team_id,
            valor_mercado_manual=req.valor_mercado_manual,
            gols_manual=req.gols_manual,
            assists_manual=req.assists_manual,
            url_fbref=req.url_fbref
        )
        return dados
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar scout: {str(e)}")

@app.post("/api/compare")
def compare_players(req: CompareRequest):
    """
    Recebe a lista de jogadores da sessão do usuário e gera dinamicamente:
    1. O relatório Markdown
    2. O gráfico comparativo de Índice PediRato
    Retorna o texto markdown do relatório e os caminhos dos arquivos estáticos gerados.
    """
    if not req.jogadores:
        raise HTTPException(status_code=400, detail="É necessário fornecer pelo menos um jogador para comparação.")
        
    # Converter dados de pydantic para formato de dicionário simples esperado pelas funções
    lista_jogadores = [j.model_dump() for j in req.jogadores]
    
    # Definir caminhos de salvamento na pasta estática
    md_filename = os.path.join(STATIC_DIR, "relatorio_scout.md")
    img_filename = os.path.join(STATIC_DIR, "comparativo_pedirato.png")
    
    # Gerar os arquivos usando o GeradorRelatorios
    markdown_content = GeradorRelatorios.gerar_relatorio_markdown(lista_jogadores, filename=md_filename)
    img_path = GeradorRelatorios.gerar_grafico_comparativo(lista_jogadores, filename=img_filename)
    
    if markdown_content is None or img_path is None:
        raise HTTPException(status_code=500, detail="Falha ao gerar os relatórios e gráficos comparativos no servidor.")
        
    return {
        "markdown": markdown_content,
        "relatorio_url": "/static/relatorio_scout.md",
        "grafico_url": "/static/comparativo_pedirato.png"
    }

if __name__ == "__main__":
    import uvicorn
    # Inicializa o servidor local na porta 8000
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
