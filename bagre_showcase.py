"""
================================================================================
 bagre_showcase.py  —  SCRIPT ÚNICO DE DEMONSTRAÇÃO DO BAGRE.AI
================================================================================
 Demonstração consolidada para AVALIAÇÃO ACADÊMICA.

 BIBLIOTECAS DA DISCIPLINA EM DESTAQUE (foco da avaliação):
 ----------------------------------------------------------------------------
   • pandas      → MODO [1]: criação do DataFrame, .head(), .describe(),
                   .groupby('liga'), cálculo vetorizado de ROI, agregação de
                   elencos por clube. (procure os comentários "# PANDAS:")
   • matplotlib  → MODO [1]: todos os gráficos das 5 frentes são salvos como
                   .png pelo módulo bagre_analytics (backend 'Agg', tema dark).
   • seaborn     → MODO [1]: scatterplot com 'hue' no Hype Index (Frente 4).
   • sqlite3     → MODO [2]: conexão nativa, PRAGMA table_info (schema),
                   SELECT, GROUP BY e JOIN ao vivo. (comentários "# SQLITE3:")

 COMPLEMENTOS PONTUAIS (marcados como EXTRA, fora do escopo principal):
 ----------------------------------------------------------------------------
   • numpy        → usado dentro de bagre_analytics para regressões/Gini e aqui
                    apenas para a seed de reprodutibilidade. (# EXTRA (numpy))
   • scikit-learn → LinearRegression (Hype Index) e cosine_similarity (Espelho
                    Pedigree), dentro de bagre_analytics.   (# EXTRA (sklearn))

 ESTRUTURA:
   [1] DEMO ANALÍTICA (offline) ... pandas / matplotlib / seaborn — as 5 frentes
   [2] DEMO DO BANCO   (offline) ... sqlite3 — schema, dados e queries ao vivo
   [3] DEMO DA API REST (online) ... requer servidor (python app.py)
   [0] Sair

 Os MODOS [1] e [2] rodam 100% OFFLINE e são reprodutíveis.
 O MODO [3] precisa do servidor FastAPI rodando em localhost:8000.
================================================================================
"""
import sys
import os
import sqlite3

# Saída UTF-8 no terminal do Windows (acentos, ✅, €, etc.)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# numpy: usado SÓ para a seed de reprodutibilidade neste arquivo.
import numpy as np  # EXTRA (numpy)

# pandas: BIBLIOTECA-CHAVE da disciplina — protagonista do MODO [1].
import pandas as pd

# Caminho do banco usado pelo projeto (mesmo do app.py / bagre_database.py).
DB_PATH = os.getenv("DATABASE_PATH", "bagre.db")

# E-mails dos 3 usuários de teste semeados em bagre_database.py (um por plano).
EMAILS_TESTE = [
    "teste_free@bagre.ai",      # plano: varzea
    "teste_olheiro@bagre.ai",   # plano: olheiro
    "teste_diretor@bagre.ai",   # plano: diretor
]


# ==============================================================================
#  UTILIDADES VISUAIS (separadores didáticos)
# ==============================================================================
def titulo(texto: str, simbolo: str = "=", largura: int = 78):
    """Imprime um título centralizado entre duas linhas de separadores."""
    print("\n" + simbolo * largura)
    print(f"  {texto}")
    print(simbolo * largura)


def subtitulo(texto: str):
    """Separador menor para subseções dentro de um modo."""
    print("\n" + "-" * 78)
    print(f"  ▸ {texto}")
    print("-" * 78)


def tabela_simples(headers: list, linhas: list):
    """
    Imprime uma tabela ASCII alinhada SEM dependências externas.
    Usada no MODO [2] e [3] para mostrar resultados de queries e a matriz de acesso.
    """
    larguras = [len(str(h)) for h in headers]
    for linha in linhas:
        for i, celula in enumerate(linha):
            larguras[i] = max(larguras[i], len(str(celula)))

    def _fmt(valores):
        return "  " + " | ".join(str(v).ljust(larguras[i]) for i, v in enumerate(valores))

    print(_fmt(headers))
    print("  " + "-+-".join("-" * w for w in larguras))
    for linha in linhas:
        print(_fmt(linha))


# ==============================================================================
#  DATASET SINTÉTICO (pandas) — usado pelo MODO [1]
# ==============================================================================
def gerar_dataset_sintetico() -> pd.DataFrame:
    """
    Constrói um DataFrame pandas com 20 jogadores fictícios.

    Reprodutibilidade: os dados são DETERMINÍSTICOS (lista fixa) e a seed do
    numpy é fixada para garantir que qualquer etapa aleatória futura seja
    estável. Toda execução produz exatamente o mesmo resultado.

    PediRatos plantados (caros, baixa entrega ofensiva) e Pedigrees plantados
    (baratos, alta entrega) garantem que as 5 frentes tenham sinais claros.

    Colunas: nome, idade, clube, liga, gols, assists, valor_milhoes
    """
    np.random.seed(42)  # EXTRA (numpy): seed fixa para reprodutibilidade total.

    # (nome, idade, clube, liga, gols, assists, valor_milhoes)
    dados = [
        # ── PEDIRATOS plantados: muito caros para o que entregam ──────────────
        ("Hype Silva",      24, "PSG",          "Ligue 1",        3,  1, 140.0),
        ("Branding Costa",  27, "Real Madrid",  "La Liga",        4,  2, 130.0),
        ("Marketing Jr.",   22, "Man City",     "Premier League", 2,  3, 120.0),

        # ── PEDIGREES plantados: baratos e altamente produtivos ───────────────
        ("Pedigree Souza",  23, "Palmeiras",    "Brasileirao",   22, 11,  18.0),
        ("Joia Pereira",    21, "Monaco",       "Ligue 1",       19, 13,  25.0),
        ("Achado Lima",     25, "Arsenal",      "Premier League",18, 12,  30.0),

        # ── REGULARES: relação valor × performance dentro da curva ────────────
        ("Carlos Mendes",   28, "Man City",     "Premier League",14,  9,  85.0),
        ("Diego Ramos",     30, "Arsenal",      "Premier League",11,  7,  60.0),
        ("Lucas Vidal",     26, "Real Madrid",  "La Liga",       16,  8,  95.0),
        ("Paulo Nunes",     29, "Barcelona",    "La Liga",       12, 10,  78.0),
        ("Andre Rocha",     24, "Barcelona",    "La Liga",        9,  6,  50.0),
        ("Felipe Antunes",  27, "PSG",          "Ligue 1",       15,  7,  88.0),
        ("Rafael Cunha",    23, "Monaco",       "Ligue 1",       10,  8,  45.0),
        ("Bruno Tavares",   31, "Flamengo",     "Brasileirao",   13,  5,  40.0),
        ("Gustavo Pinto",   22, "Flamengo",     "Brasileirao",    8,  9,  35.0),
        ("Mateus Farias",   25, "Palmeiras",    "Brasileirao",   11,  6,  38.0),
        ("Thiago Borges",   28, "Man City",     "Premier League",17, 10, 110.0),
        ("Vitor Hugo",      33, "Real Madrid",  "La Liga",        7,  4,  22.0),
        ("Igor Macedo",     20, "Monaco",       "Ligue 1",        6,  5,  28.0),
        ("Renato Dias",     26, "PSG",          "Ligue 1",       13,  9,  70.0),
    ]

    # PANDAS: construção do DataFrame a partir de uma lista de tuplas + colunas.
    df = pd.DataFrame(
        dados,
        columns=["nome", "idade", "clube", "liga", "gols", "assists", "valor_milhoes"],
    )
    return df


# ==============================================================================
#  MODO [1] — DEMO ANALÍTICA (offline)  →  pandas / matplotlib / seaborn
# ==============================================================================
def modo_analitico():
    titulo("MODO [1] — DEMO ANALÍTICA (OFFLINE)  |  pandas · matplotlib · seaborn")

    # As funções das frentes 2–5 vivem em bagre_analytics (matplotlib/seaborn).
    from bagre_analytics import (
        analisar_ciclo_de_vida,
        analisar_concentracao_liga,
        analisar_hype_index,
        espelho_pedigree,
        STATIC_DIR,
    )
    from bagre_relatorios import GeradorRelatorios

    df = gerar_dataset_sintetico()
    graficos_gerados = []

    # ──────────────────────────────────────────────────────────────────────────
    #  EXPLORAÇÃO DOS DADOS COM PANDAS (o que o professor ensinou)
    # ──────────────────────────────────────────────────────────────────────────
    subtitulo("Exploração do dataset com PANDAS")

    # PANDAS: .head() mostra as primeiras linhas do DataFrame.
    print("\n# PANDAS: df.head() — primeiros 5 jogadores do dataset")
    print(df.head().to_string(index=False))

    # PANDAS: .describe() resume estatísticas das colunas numéricas.
    print("\n# PANDAS: df.describe() — estatísticas descritivas (numéricas)")
    print(df.describe().round(2).to_string())

    # PANDAS: .groupby('liga') agrega métricas por liga.
    print("\n# PANDAS: df.groupby('liga') — médias por liga")
    resumo_liga = (
        df.groupby("liga")[["gols", "assists", "valor_milhoes"]]
        .mean()
        .round(2)
        .sort_values("valor_milhoes", ascending=False)
    )
    print(resumo_liga.to_string())

    # ──────────────────────────────────────────────────────────────────────────
    #  FRENTE 1 — ROI DE JOGADORES  (cálculo 100% em pandas)
    # ──────────────────────────────────────────────────────────────────────────
    subtitulo("FRENTE 1 — ROI de Jogadores  (Gols + Assistências) / Valor de Mercado")

    # PANDAS: operação VETORIZADA — cria a coluna 'roi' para as 20 linhas de uma vez.
    df["roi"] = ((df["gols"] + df["assists"]) / df["valor_milhoes"]).round(4)

    # PANDAS: .sort_values() ordena pelo ROI (eficiência de capital ofensivo).
    ranking = df.sort_values("roi", ascending=False)
    print("\n  TOP 5 — Maior ROI (mais eficientes / candidatos a Pedigree):")
    print(ranking.head(5)[["nome", "clube", "gols", "assists", "valor_milhoes", "roi"]].to_string(index=False))
    print("\n  BOTTOM 5 — Menor ROI (menos eficientes / candidatos a PediRato):")
    print(ranking.tail(5)[["nome", "clube", "gols", "assists", "valor_milhoes", "roi"]].to_string(index=False))

    # ──────────────────────────────────────────────────────────────────────────
    #  FRENTE 2 — CICLO DE VIDA E CURVA DE VALOR
    # ──────────────────────────────────────────────────────────────────────────
    subtitulo("FRENTE 2 — Ciclo de Vida (Idade × Valor)")
    # EXTRA (numpy/sklearn): a regressão polinomial grau 2 usa numpy.polyfit internamente.
    res_vida = analisar_ciclo_de_vida(df[["nome", "idade", "valor_milhoes"]])
    print(f"  → Pico estimado: {res_vida['idade_pico']} anos  |  "
          f"Janela de revenda: {res_vida['janela_revenda']}")
    graficos_gerados.append(os.path.join(STATIC_DIR, "ciclo_vida.png"))

    # ──────────────────────────────────────────────────────────────────────────
    #  FRENTE 3 — CONCENTRAÇÃO DE RIQUEZA POR LIGA (GINI)
    # ──────────────────────────────────────────────────────────────────────────
    subtitulo("FRENTE 3 — Concentração de Riqueza (Gini por clube)")
    # PANDAS: groupby + sum agrega o valor de mercado dos jogadores em elencos por clube.
    df_clubes = (
        df.groupby("clube", as_index=False)["valor_milhoes"]
        .sum()
        .rename(columns={"valor_milhoes": "valor_total_elenco_milhoes"})
    )
    print("\n# PANDAS: elencos agregados por clube (groupby + sum):")
    print(df_clubes.to_string(index=False))
    # EXTRA (numpy): o coeficiente de Gini é calculado manualmente com numpy.
    res_gini = analisar_concentracao_liga(df_clubes)
    print(f"  → Gini = {res_gini['gini']} ({res_gini['interpretacao']})  |  "
          f"Mais rico: {res_gini['clube_mais_rico']}  ·  Mais pobre: {res_gini['clube_mais_pobre']}")
    graficos_gerados.append(os.path.join(STATIC_DIR, "gini_liga.png"))

    # ──────────────────────────────────────────────────────────────────────────
    #  FRENTE 4 — HYPE INDEX (detecção de PediRatos)  → seaborn scatter
    # ──────────────────────────────────────────────────────────────────────────
    subtitulo("FRENTE 4 — Hype Index (Performance × Valor)")
    # EXTRA (sklearn): LinearRegression ajusta a reta; SEABORN desenha o scatter com hue.
    df_hype = analisar_hype_index(df[["nome", "valor_milhoes", "gols", "assists"]])
    n_ratos = int((df_hype["classificacao"] == "PediRato").sum())
    n_pedis = int((df_hype["classificacao"] == "Pedigree").sum())
    print(f"  → PediRatos detectados: {n_ratos}  |  Pedigrees detectados: {n_pedis}")
    graficos_gerados.append(os.path.join(STATIC_DIR, "hype_index.png"))

    # ──────────────────────────────────────────────────────────────────────────
    #  FRENTE 5 — ESPELHO PEDIGREE (similaridade)  → gráfico de radar
    # ──────────────────────────────────────────────────────────────────────────
    subtitulo("FRENTE 5 — Espelho Pedigree (jogador caro × espelhos baratos)")
    # Referência: um bom jogador CARO; o sistema busca espelhos mais baratos e similares.
    referencia = {"nome": "Thiago Borges", "gols": 17, "assists": 10, "valor_milhoes": 110.0}
    # Pool = todos os demais jogadores (lista de dicts vinda do DataFrame pandas).
    pool = (
        df[df["nome"] != referencia["nome"]][["nome", "gols", "assists", "valor_milhoes"]]
        .to_dict("records")
    )
    # EXTRA (sklearn): a similaridade usa cosine_similarity sobre vetores de features.
    df_espelho = espelho_pedigree(referencia, pool)
    if not df_espelho.empty:
        print(f"  → Espelhos mais baratos de {referencia['nome']}: "
              f"{', '.join(df_espelho['nome'].tolist())}")
    graficos_gerados.append(os.path.join(STATIC_DIR, "radar_pedigree.png"))

    # ──────────────────────────────────────────────────────────────────────────
    #  RELATÓRIO AUTOMATIZADO (.docx) — entregável do tier Diretor
    # ──────────────────────────────────────────────────────────────────────────
    subtitulo("RELATÓRIO AUTOMATIZADO (.docx)")
    # PANDAS: monta a lista de jogadores com o PediRato (eficiência) já calculado.
    df["pedirato"] = ((df["gols"] + df["assists"]) / df["valor_milhoes"]).round(4)
    jogadores_docx = df[["nome", "gols", "assists", "valor_milhoes", "pedirato"]].to_dict("records")
    caminho_docx = GeradorRelatorios.gerar_relatorio_completo_docx(
        historico_jogadores=jogadores_docx,
        resultados_analytics={},
        filename="Relatorio_Showcase.docx",
    )

    # ──────────────────────────────────────────────────────────────────────────
    #  RESUMO DOS ARQUIVOS GERADOS
    # ──────────────────────────────────────────────────────────────────────────
    titulo("RESUMO — ARQUIVOS GERADOS NESTA DEMO", simbolo="*")
    print("  Gráficos (matplotlib/seaborn):")
    for g in graficos_gerados:
        existe = "✅" if os.path.exists(g) else "❌"
        print(f"    {existe}  {g}")
    print("\n  Relatório (python-docx):")
    if caminho_docx and os.path.exists(caminho_docx):
        print(f"    ✅  {os.path.abspath(caminho_docx)}")
    else:
        print("    ❌  Falha ao gerar o .docx (verifique python-docx).")
    print()


# ==============================================================================
#  MODO [2] — DEMO DO BANCO (offline)  →  sqlite3 nativo, didático
# ==============================================================================
def modo_banco():
    titulo("MODO [2] — DEMO DO BANCO (OFFLINE)  |  sqlite3 nativo (sem ORM)")

    if not os.path.exists(DB_PATH):
        print(f"\n  ❌ Banco '{DB_PATH}' não encontrado.")
        print("     Crie-o rodando uma vez:  python bagre_database.py\n")
        return

    # SQLITE3: abre a conexão com o arquivo de banco (.db). Sem ORM, SQL puro.
    conn = sqlite3.connect(DB_PATH)
    # SQLITE3: row_factory=Row permite acessar colunas por nome (row["coluna"]).
    conn.row_factory = sqlite3.Row

    try:
        # ──────────────────────────────────────────────────────────────────────
        #  SCHEMA DE CADA TABELA  (PRAGMA table_info)
        # ──────────────────────────────────────────────────────────────────────
        subtitulo("SCHEMA das tabelas (PRAGMA table_info)")
        # SQLITE3: lista os nomes das tabelas a partir da tabela de sistema sqlite_master.
        tabelas = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        for tabela in tabelas:
            print(f"\n  TABELA: {tabela}")
            # SQLITE3: PRAGMA table_info(<tabela>) devolve as colunas e seus tipos.
            cols = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
            linhas = [
                (c["cid"], c["name"], c["type"], "PK" if c["pk"] else "",
                 "NOT NULL" if c["notnull"] else "")
                for c in cols
            ]
            tabela_simples(["#", "coluna", "tipo", "chave", "obrig."], linhas)

        # ──────────────────────────────────────────────────────────────────────
        #  USUÁRIOS DE TESTE
        # ──────────────────────────────────────────────────────────────────────
        subtitulo("Usuários de teste (SELECT)")
        sql_usuarios = (
            "SELECT id, email, nome, plano, requests_hoje\n"
            "FROM usuarios\n"
            "ORDER BY id"
        )
        print(f"\n# SQLITE3: query executada:\n  {sql_usuarios.replace(chr(10), chr(10)+'  ')}\n")
        rows = conn.execute(sql_usuarios).fetchall()
        tabela_simples(
            ["id", "email", "nome", "plano", "reqs_hoje"],
            [(r["id"], r["email"], r["nome"], r["plano"], r["requests_hoje"]) for r in rows],
        )

        # ──────────────────────────────────────────────────────────────────────
        #  QUERY 1 — usuários por plano (GROUP BY)
        # ──────────────────────────────────────────────────────────────────────
        subtitulo("Query 1 — Contagem de usuários por plano (GROUP BY)")
        sql_q1 = (
            "SELECT plano, COUNT(*) AS total\n"
            "FROM usuarios\n"
            "GROUP BY plano\n"
            "ORDER BY total DESC"
        )
        # SQLITE3: GROUP BY agrega linhas por valor da coluna 'plano'.
        print(f"\n# SQLITE3: query executada:\n  {sql_q1.replace(chr(10), chr(10)+'  ')}\n")
        rows = conn.execute(sql_q1).fetchall()
        tabela_simples(["plano", "total"], [(r["plano"], r["total"]) for r in rows])

        # ──────────────────────────────────────────────────────────────────────
        #  QUERY 2 — análises por tipo (GROUP BY)
        # ──────────────────────────────────────────────────────────────────────
        subtitulo("Query 2 — Análises registradas por tipo (GROUP BY)")
        sql_q2 = (
            "SELECT tipo, COUNT(*) AS total\n"
            "FROM analises\n"
            "GROUP BY tipo\n"
            "ORDER BY total DESC"
        )
        print(f"\n# SQLITE3: query executada:\n  {sql_q2.replace(chr(10), chr(10)+'  ')}\n")
        rows = conn.execute(sql_q2).fetchall()
        if rows:
            tabela_simples(["tipo", "total"], [(r["tipo"], r["total"]) for r in rows])
        else:
            print("  (nenhuma análise registrada ainda — tabela 'analises' vazia)")

        # ──────────────────────────────────────────────────────────────────────
        #  QUERY 3 — JOIN usuarios + analises
        # ──────────────────────────────────────────────────────────────────────
        subtitulo("Query 3 — JOIN usuarios + analises (análises por usuário)")
        sql_q3 = (
            "SELECT u.email, u.plano, COUNT(a.id) AS qtd_analises\n"
            "FROM usuarios AS u\n"
            "LEFT JOIN analises AS a ON a.usuario_id = u.id\n"
            "GROUP BY u.id\n"
            "ORDER BY qtd_analises DESC"
        )
        # SQLITE3: LEFT JOIN conecta cada usuário às suas análises (0 ou mais).
        print(f"\n# SQLITE3: query executada:\n  {sql_q3.replace(chr(10), chr(10)+'  ')}\n")
        rows = conn.execute(sql_q3).fetchall()
        tabela_simples(
            ["email", "plano", "qtd_analises"],
            [(r["email"], r["plano"], r["qtd_analises"]) for r in rows],
        )

    finally:
        # SQLITE3: SEMPRE fechar a conexão ao final (libera o arquivo .db).
        conn.close()
        print("\n  Conexão sqlite3 encerrada.\n")


# ==============================================================================
#  MODO [3] — DEMO DA API REST (online)  →  requer servidor (python app.py)
# ==============================================================================
def _buscar_api_keys() -> dict:
    """
    Lê as api_keys dos 3 usuários de teste diretamente do banco.
    Robusto: funciona mesmo que as chaves tenham sido regeneradas.
    Retorna {plano: {'email':..., 'api_key':...}}.
    """
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        keys = {}
        for email in EMAILS_TESTE:
            row = conn.execute(
                "SELECT email, plano, api_key FROM usuarios WHERE email = ?", (email,)
            ).fetchone()
            if row:
                keys[row["plano"]] = {"email": row["email"], "api_key": row["api_key"]}
        return keys
    finally:
        conn.close()


def modo_api():
    titulo("MODO [3] — DEMO DA API REST (ONLINE)  |  requer servidor FastAPI")

    # 'requests' faz as chamadas HTTP à API local.
    try:
        import requests
    except ImportError:
        print("\n  ❌ Biblioteca 'requests' não instalada (pip install requests).\n")
        return

    BASE = "http://localhost:8000"

    # Recupera as 3 chaves de teste do banco.
    keys = _buscar_api_keys()
    if len(keys) < 3:
        print("\n  ❌ Usuários de teste não encontrados no banco.")
        print("     Rode uma vez:  python bagre_database.py\n")
        return

    # ── Verifica se o servidor está no ar (GET /health) ───────────────────────
    subtitulo("Verificando o servidor (GET /health)")
    try:
        r = requests.get(f"{BASE}/health", timeout=3)
        health = r.json()
        print(f"  ✅ Servidor online — status={health.get('status')} | "
              f"versão={health.get('version')} | "
              f"banco={health.get('database')} | "
              f"usuários={health.get('usuarios_cadastrados')}")
    except requests.exceptions.RequestException:
        # Mensagem amigável SEM quebrar o script (requisito do enunciado).
        print(f"  ❌ Servidor não respondeu em {BASE}.")
        print("     Inicie com:  python app.py\n")
        return

    # ── GET /v1/me para cada plano ────────────────────────────────────────────
    subtitulo("Identidade de cada plano (GET /v1/me)")
    for plano in ["varzea", "olheiro", "diretor"]:
        info = keys[plano]
        r = requests.get(f"{BASE}/v1/me",
                         headers={"X-API-Key": info["api_key"]}, timeout=5)
        if r.status_code == 200:
            me = r.json()
            print(f"  [{plano.upper():>8}] {me['email']:<24} "
                  f"limite/dia={me['limite_diario']:<10} "
                  f"funcs={len(me['funcionalidades'])}")
        else:
            print(f"  [{plano.upper():>8}] erro {r.status_code}")

    # ── Endpoints de analytics testados por cada plano → MATRIZ DE ACESSO ─────
    subtitulo("Testando endpoints por plano → montando MATRIZ DE ACESSO")

    # Cada endpoint: (rótulo, método, caminho, corpo/params). Payloads mínimos válidos.
    jhype = [
        {"nome": "A", "valor_milhoes": 90, "gols": 3,  "assists": 2},
        {"nome": "B", "valor_milhoes": 38, "gols": 17, "assists": 9},
        {"nome": "C", "valor_milhoes": 180, "gols": 21, "assists": 8},
    ]
    jvida = [
        {"nome": "A", "idade": 21, "valor_milhoes": 120},
        {"nome": "B", "idade": 28, "valor_milhoes": 80},
        {"nome": "C", "idade": 34, "valor_milhoes": 20},
    ]
    jgini = [
        {"clube": "X", "valor_total_elenco_milhoes": 800},
        {"clube": "Y", "valor_total_elenco_milhoes": 90},
    ]
    jpedi = {
        "jogador_ref": {"nome": "Caro", "gols": 17, "assists": 10, "valor_milhoes": 110},
        "pool": [{"nome": "Barato", "gols": 18, "assists": 12, "valor_milhoes": 30}],
    }

    endpoints = [
        # (rótulo,            método, caminho,                          payload)
        ("scout",            "GET",  "/v1/scout",                       {"nome": "Teste", "valor_mercado": 50, "gols": 10, "assists": 5}),
        ("hype_index",       "POST", "/v1/analytics/hype-index",        {"jogadores": jhype}),
        ("espelho_pedigree", "POST", "/v1/analytics/espelho-pedigree",  jpedi),
        ("gini",             "POST", "/v1/analytics/gini",              {"clubes": jgini}),
        ("ciclo_vida",       "POST", "/v1/analytics/ciclo-vida",        {"jogadores": jvida}),
        ("relatorio_docx",   "POST", "/v1/reports/docx",                {"jogadores": [{"nome": "A", "gols": 1, "assists": 1, "valor_milhoes": 10, "pedirato": 0.2}]}),
    ]

    planos = ["varzea", "olheiro", "diretor"]

    def _simbolo(status_code: int) -> str:
        """Traduz o HTTP status em símbolo da matriz de acesso."""
        if status_code == 200:
            return "✅"            # acesso liberado
        if status_code == 429:
            return "limite"        # tier ok, mas limite diário atingido
        if status_code in (401, 403):
            return "🔒"            # bloqueado pelo tier
        return f"err{status_code}"  # erro inesperado (422, 500, ...)

    # Monta a matriz: para cada endpoint (linha) e plano (coluna), faz a chamada real.
    matriz = []
    for rotulo, metodo, caminho, payload in endpoints:
        linha = [rotulo]
        for plano in planos:
            api_key = keys[plano]["api_key"]
            headers = {"X-API-Key": api_key}
            try:
                if metodo == "GET":
                    r = requests.get(f"{BASE}{caminho}", headers=headers,
                                     params=payload, timeout=10)
                else:
                    r = requests.post(f"{BASE}{caminho}", headers=headers,
                                      json=payload, timeout=20)
                linha.append(_simbolo(r.status_code))
            except requests.exceptions.RequestException:
                linha.append("offline")
        matriz.append(linha)

    print()
    tabela_simples(
        ["funcionalidade", "VÁRZEA", "OLHEIRO", "DIRETOR"],
        matriz,
    )
    print("\n  Legenda:  ✅ liberado   🔒 bloqueado pelo tier   "
          "limite = limite diário atingido   errNNN = status inesperado")
    print()


# ==============================================================================
#  MENU PRINCIPAL
# ==============================================================================
def menu():
    """Loop do menu de terminal. Modos 1 e 2 offline; modo 3 requer servidor."""
    while True:
        print("\n" + "=" * 50)
        print("  === BAGRE.AI — SHOWCASE PARA AVALIAÇÃO ===")
        print("=" * 50)
        print("  [1] DEMO ANALÍTICA (offline) — as 5 frentes em pandas/matplotlib/seaborn")
        print("  [2] DEMO DO BANCO (sqlite3) — schema, dados e queries ao vivo")
        print("  [3] DEMO DA API REST (requer servidor) — endpoints e tiers")
        print("  [0] Sair")
        print("=" * 50)

        try:
            escolha = input("  Escolha uma opção: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Encerrando.\n")
            break

        if escolha == "1":
            modo_analitico()
        elif escolha == "2":
            modo_banco()
        elif escolha == "3":
            modo_api()
        elif escolha == "0":
            print("\n  Até logo! — Bagre.ai\n")
            break
        else:
            print("  Opção inválida. Tente novamente.")


if __name__ == "__main__":
    menu()
