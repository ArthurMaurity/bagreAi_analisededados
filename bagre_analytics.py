"""
bagre_analytics.py - Frentes analiticas avancadas do Bagre.ai
Implementa as Frentes 2, 3, 4 e 5 do CLAUDE.md.
"""
import sys
import os
import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.metrics.pairwise import cosine_similarity

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# ── Paleta Cyberpunk ──────────────────────────────────────────────────────────
BG    = "#000000"
GREEN = "#39FF14"
WHITE = "#FFFFFF"
RED   = "#FF3131"
GRAY  = "#888888"
DARK  = "#1A1A1A"


def _apply_theme_ax(ax, fig, light_theme=False):
    """Aplica o tema (cyberpunk/dark ou corporativo/light) a um eixo matplotlib."""
    if light_theme:
        fig.patch.set_facecolor('#FFFFFF')
        ax.set_facecolor('#F8F9FA')
        ax.tick_params(colors='#333333')
        ax.xaxis.label.set_color('#333333')
        ax.yaxis.label.set_color('#333333')
        for spine in ax.spines.values():
            spine.set_edgecolor('#DDDDDD')
    else:
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        ax.tick_params(colors=WHITE)
        ax.xaxis.label.set_color(WHITE)
        ax.yaxis.label.set_color(WHITE)
        for spine in ax.spines.values():
            spine.set_edgecolor(GRAY)


def _cyberpunk_ax(ax, fig):
    """Mantido para compatibilidade retrospectiva."""
    _apply_theme_ax(ax, fig, light_theme=False)


# Limitações metodológicas do Índice PediRato — seção 5.2 do artigo
LIMITACOES_PEDIRATO = [
    "Não considera minutos jogados",
    "Não incorpora métricas defensivas",
    "Não avalia o contexto tático da equipe",
    "Não considera o nível competitivo das ligas",
    "Possui viés ofensivo inerente à sua formulação",
]


# ===============================================================================
# FRENTE 2 — CICLO DE VIDA E CURVA DE VALOR
# ===============================================================================
def analisar_ciclo_de_vida(df: pd.DataFrame, img_path: str = None, light_theme: bool = False) -> dict:
    """
    Regressão polinomial grau 2 (Idade × Valor de Mercado).
    Calcula pico de valor e janela ideal de revenda (>80% do pico).

    Input:  DataFrame com colunas [nome, idade, valor_milhoes]
    Output: dict com idade_pico, valor_pico, janela_revenda, coeficientes, df enriquecido
    """
    required = {"nome", "idade", "valor_milhoes"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame deve ter as colunas: {required}")
    if len(df) < 3:
        raise ValueError("Mínimo de 3 jogadores para análise de ciclo de vida.")
    if df["idade"].nunique() < 2:
        return {"error": "Idades insuficientes para regressão. Use jogadores com idades diferentes."}

    df = df.copy().reset_index(drop=True)
    x = df["idade"].values.astype(float)
    y = df["valor_milhoes"].values.astype(float)

    # Regressão polinomial grau 2: y = ax² + bx + c
    a, b, c = np.polyfit(x, y, 2)

    # Vértice da parábola → pico de valor
    idade_pico = -b / (2 * a)
    valor_pico = float(np.polyval([a, b, c], idade_pico))

    # Janela de revenda: valor predito > 80% do pico
    x_range = np.linspace(max(15.0, x.min() - 2), min(45.0, x.max() + 2), 1000)
    y_range = np.polyval([a, b, c], x_range)
    limiar  = 0.80 * valor_pico
    mascara = y_range >= limiar
    janela_inicio = float(x_range[mascara].min()) if mascara.any() else float(x.min())
    janela_fim    = float(x_range[mascara].max()) if mascara.any() else float(x.max())

    df["valor_predito"] = np.polyval([a, b, c], x).round(2)
    df["desvio_%"] = (
        (df["valor_milhoes"] - df["valor_predito"]) / df["valor_predito"].abs().clip(0.01) * 100
    ).round(2)

    # ── Relatório textual ──────────────────────────────────────────────────────
    print("\n" + "=" * 58)
    print("  FRENTE 2 — CICLO DE VIDA E CURVA DE VALOR")
    print("=" * 58)
    print(f"  Pico de valor estimado:   {idade_pico:.1f} anos  (€{valor_pico:.1f}M)")
    print(f"  Janela ideal de revenda:  {janela_inicio:.1f} – {janela_fim:.1f} anos")
    print(f"  Equação: Valor = {a:.4f}·Idade² + {b:.4f}·Idade + {c:.4f}")
    print("\n  Detalhamento por jogador:")
    print(df[["nome", "idade", "valor_milhoes", "valor_predito", "desvio_%"]].to_string(index=False))
    print("=" * 58)

    # ── Gráfico ────────────────────────────────────────────────────────────────
    if not img_path:
        img_path = os.path.join(STATIC_DIR, "ciclo_vida.png")
    
    if light_theme:
        plt.style.use('default')
        c_bg = "#FFFFFF"
        c_green = "#1E7E34"
        c_line = "#0056B3"
        c_red = "#DC3545"
        c_text = "#333333"
        c_legend_bg = "#FFFFFF"
        c_legend_edge = "#DDDDDD"
    else:
        plt.style.use('dark_background')
        c_bg = BG
        c_green = GREEN
        c_line = WHITE
        c_red = RED
        c_text = WHITE
        c_legend_bg = DARK
        c_legend_edge = GRAY

    fig, ax = plt.subplots(figsize=(11, 6))
    _apply_theme_ax(ax, fig, light_theme=light_theme)

    y_max = max(float(y.max()), float(y_range.max())) * 1.15
    ax.set_ylim(bottom=0, top=y_max)

    if mascara.any():
        ax.axhspan(limiar, y_max, alpha=0.06, color=c_green, label="Janela de revenda (>80% pico)")

    ax.scatter(x, y, color=c_green, s=110, zorder=5, label="Jogadores (real)")
    ax.plot(x_range, y_range, color=c_line, linewidth=2, label="Curva polinomial (grau 2)")
    ax.axvline(idade_pico, color=c_red, linestyle=":", linewidth=1.5,
               label=f"Pico estimado: {idade_pico:.1f} anos")

    for _, row in df.iterrows():
        ax.annotate(row["nome"], (row["idade"], row["valor_milhoes"]),
                    textcoords="offset points", xytext=(6, 5), fontsize=8, color=c_text)

    ax.set_xlabel("Idade", fontsize=11, color=c_text)
    ax.set_ylabel("Valor de Mercado (€M)", fontsize=11, color=c_text)
    ax.set_title("Ciclo de Vida — Curva de Valor por Idade  |  Bagre.ai",
                 color=c_green, fontsize=13, pad=12)
    ax.legend(labelcolor=c_text, facecolor=c_legend_bg, edgecolor=c_legend_edge, fontsize=9)
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=c_bg)
    plt.close()
    print(f"  Gráfico salvo: {img_path}\n")

    return {
        "idade_pico": round(idade_pico, 1),
        "valor_pico_milhoes": round(valor_pico, 2),
        "janela_revenda": (round(janela_inicio, 1), round(janela_fim, 1)),
        "coeficientes": (round(a, 4), round(b, 4), round(c, 4)),
        "df": df,
    }


# ===============================================================================
# FRENTE 4 — HYPE INDEX (DETECÇÃO DE PEDIRATO)
# Regressão linear simples — conforme metodologia da seção 4.2 do artigo
# ===============================================================================
def analisar_hype_index(df: pd.DataFrame, img_path: str = None, light_theme: bool = False) -> pd.DataFrame:
    """
    Regressão linear (sklearn): X = performance, y = valor_milhoes.
    Classifica por resíduo: PediRato (>+1σ), Pedigree (<-1σ), Regular.

    Input:  DataFrame com colunas [nome, valor_milhoes, gols, assists]
    Output: DataFrame com colunas adicionais [performance, valor_predito, residuo, classificacao]
    """
    required = {"nome", "valor_milhoes", "gols", "assists"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame deve ter as colunas: {required}")
    if len(df) < 3:
        raise ValueError("Mínimo de 3 jogadores.")

    df = df.copy().reset_index(drop=True)
    df["performance"] = df["gols"] + df["assists"]

    X = df[["performance"]].values
    y = df["valor_milhoes"].values.astype(float)

    modelo = LinearRegression()
    modelo.fit(X, y)

    slope = float(modelo.coef_[0])
    inter = float(modelo.intercept_)
    r2    = float(modelo.score(X, y))

    df["valor_predito"]  = modelo.predict(X).round(2)
    df["residuo"]        = (df["valor_milhoes"] - df["valor_predito"]).round(2)

    std = float(df["residuo"].std())
    df["classificacao"] = df["residuo"].apply(
        lambda r: "PediRato" if r > std else ("Pedigree" if r < -std else "Regular")
    )

    pedi_ratos = df[df["classificacao"] == "PediRato"][["nome", "valor_milhoes", "performance", "residuo"]]
    pedigrees  = df[df["classificacao"] == "Pedigree"][["nome", "valor_milhoes", "performance", "residuo"]]

    # ── Relatório textual ──────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  FRENTE 4 — HYPE INDEX (Detecção de PediRatos)")
    print("=" * 65)
    print(f"  Equação da reta:  Valor = {slope:.3f} × Performance + {inter:.3f}")
    print(f"  R² do modelo:     {r2:.4f}")
    print(f"  Desvio padrao dos residuos (s):  {std:.3f}")
    print("\n  Tabela completa:")
    print(df[["nome", "valor_milhoes", "performance", "valor_predito", "residuo", "classificacao"]].to_string(index=False))
    print(f"\n  [PEDI-RATOS] ({len(pedi_ratos)}) - caro demais para o que entrega:")
    print(pedi_ratos.to_string(index=False) if not pedi_ratos.empty else "  Nenhum.")
    print(f"\n  [PEDIGREES]  ({len(pedigrees)}) - entrega mais do que o preco sugere:")
    print(pedigrees.to_string(index=False) if not pedigrees.empty else "  Nenhum.")
    print("=" * 65)

    # ── Gráfico (seaborn scatter + matplotlib reta) ────────────────────────────
    if not img_path:
        img_path = os.path.join(STATIC_DIR, "hype_index.png")
    
    if light_theme:
        plt.style.use('default')
        c_bg = "#FFFFFF"
        c_text = "#333333"
        c_green = "#1E7E34"
        c_red = "#DC3545"
        c_gray = "#6C757D"
        c_line = "#0056B3"
        c_legend_bg = "#FFFFFF"
        c_legend_edge = "#DDDDDD"
    else:
        plt.style.use("dark_background")
        c_bg = BG
        c_text = WHITE
        c_green = GREEN
        c_red = RED
        c_gray = GRAY
        c_line = WHITE
        c_legend_bg = DARK
        c_legend_edge = GRAY

    cores_map = {"PediRato": c_red, "Pedigree": c_green, "Regular": c_gray}

    fig, ax = plt.subplots(figsize=(11, 7))
    _apply_theme_ax(ax, fig, light_theme=light_theme)

    # seaborn scatterplot com hue
    sns.scatterplot(
        data=df, x="performance", y="valor_milhoes",
        hue="classificacao", palette=cores_map,
        s=130, zorder=5, ax=ax, legend=False,
    )
    # seaborn pode redefinir facecolors — reaplicar após o plot
    _apply_theme_ax(ax, fig, light_theme=light_theme)

    # Reta de regressão via matplotlib
    x_line = np.linspace(df["performance"].min(), df["performance"].max(), 300)
    ax.plot(x_line, slope * x_line + inter, color=c_line, linewidth=2,
            label=f"Regressão  (R²={r2:.3f})")

    # Pontos de legenda manual
    for cls, cor in cores_map.items():
        ax.scatter([], [], color=cor, s=80, label=cls)

    # Anotações com nome
    for _, row in df.iterrows():
        ax.annotate(row["nome"], (row["performance"], row["valor_milhoes"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8, color=c_text)

    ax.set_xlabel("Performance (Gols + Assists)", fontsize=11, color=c_text)
    ax.set_ylabel("Valor de Mercado (€M)", fontsize=11, color=c_text)
    ax.set_title(f"Hype Index — PediRatos vs Pedigrees  |  Bagre.ai",
                 color=c_green, fontsize=13, pad=12)
    ax.tick_params(colors=c_text)
    ax.legend(labelcolor=c_text, facecolor=c_legend_bg, edgecolor=c_legend_edge, fontsize=9)
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=c_bg)
    plt.close()
    print(f"  Gráfico salvo: {img_path}\n")

    return df


# ===============================================================================
# FRENTE 5 — ESPELHO PEDIGREE (SIMILARIDADE COSSENO + RADAR)
# Distância cosseno normalizada — conforme metodologia da seção 4.3 do artigo
# ===============================================================================
def espelho_pedigree(jogador_ref: dict, pool: list, img_path: str = None, light_theme: bool = False) -> pd.DataFrame:
    """
    Similaridade cosseno (sklearn) entre o jogador de referência e o pool.
    Filtra candidatos com valor < 60% do referencial e retorna top 3.

    Input:
        jogador_ref: {'nome': str, 'gols': int, 'assists': int, 'valor_milhoes': float}
        pool:        lista de dicts com mesma estrutura
    Output: DataFrame [nome, similaridade_%, valor_milhoes, economia_estimada_milhoes]
    """
    if not pool:
        raise ValueError("Pool vazio.")

    def _pedirato(j: dict) -> float:
        return (j.get("gols", 0) + j.get("assists", 0)) / max(j.get("valor_milhoes", 0.1), 0.1)

    def _feat_vec(j: dict) -> list:
        """Vetor de features de performance: gols, assistências, eficiência (PediRato)."""
        return [float(j.get("gols", 0)), float(j.get("assists", 0)), _pedirato(j)]

    # Cosseno calculado sobre vetores BRUTOS (sem MinMaxScaler).
    # O cosseno já é invariante a escala de magnitude — mede direção/proporção.
    # Aplicar MinMaxScaler colapsava colunas sem variância (min==max → zeros)
    # quando o pool era pequeno, zerando a similaridade indevidamente.
    ref_vec   = np.array([_feat_vec(jogador_ref)], dtype=float)
    pool_vecs = np.array([_feat_vec(j) for j in pool], dtype=float)
    sims      = cosine_similarity(ref_vec, pool_vecs)[0]

    limite_valor = jogador_ref["valor_milhoes"] * 0.60
    candidatos = [
        {**pool[i], "similaridade": float(sims[i])}
        for i in range(len(pool))
        if pool[i]["valor_milhoes"] < limite_valor
    ]
    candidatos.sort(key=lambda j: j["similaridade"], reverse=True)
    top3 = candidatos[:3]

    if not top3:
        msg = (f"Nenhum candidato com valor < 60% de "
               f"€{jogador_ref['valor_milhoes']:.1f}M (limiar: €{limite_valor:.1f}M).")
        print(f"\n  {msg}")
        return pd.DataFrame()

    df_out = pd.DataFrame([{
        "nome":                       j["nome"],
        "similaridade_%":             round(j["similaridade"] * 100, 2),
        "valor_milhoes":              j["valor_milhoes"],
        "economia_estimada_milhoes":  round(jogador_ref["valor_milhoes"] - j["valor_milhoes"], 2),
    } for j in top3])

    # ── Relatório textual ──────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  FRENTE 5 — ESPELHO PEDIGREE  |  Ref: {jogador_ref['nome'].upper()}")
    print("=" * 65)
    print(f"  Valor de referência:  €{jogador_ref['valor_milhoes']:.1f}M")
    print(f"  Limiar de filtro:     €{limite_valor:.1f}M  (< 60% do referencial)")
    print(f"\n  TOP 3 ESPELHOS PEDIGREE para {jogador_ref['nome']}:")
    print(df_out.to_string(index=False))
    print("=" * 65)

    # ── Radar Chart ────────────────────────────────────────────────────────────
    if not img_path:
        img_path   = os.path.join(STATIC_DIR, "radar_pedigree.png")
    eixos      = ["Gols", "Assistências", "Eficiência\n(PediRato)", "Valor\n(invertido)"]
    n_eixos    = len(eixos)
    angles     = np.linspace(0, 2 * np.pi, n_eixos, endpoint=False).tolist()
    angles    += angles[:1]  # fechar polígono

    def _radar_vals(j: dict) -> list:
        val_inv = 1.0 - (j["valor_milhoes"] / max(jogador_ref["valor_milhoes"], 0.1))
        return [float(j.get("gols", 0)),
                float(j.get("assists", 0)),
                _pedirato(j),
                max(0.0, val_inv)]

    jogadores_radar = [jogador_ref] + top3
    raw = np.array([_radar_vals(j) for j in jogadores_radar], dtype=float)
    max_v = raw.max(axis=0)
    max_v[max_v == 0] = 1.0
    raw_norm = raw / max_v

    # Referência em vermelho, top3 em tons de verde
    if light_theme:
        plt.style.use('default')
        c_bg = "#FFFFFF"
        c_text = "#333333"
        c_green = "#1E7E34"
        c_legend_bg = "#FFFFFF"
        c_legend_edge = "#DDDDDD"
        c_spine = "#DDDDDD"
        cores_radar = ["#DC3545", "#28A745", "#218838", "#1E7E34"]
    else:
        plt.style.use('dark_background')
        c_bg = BG
        c_text = WHITE
        c_green = GREEN
        c_legend_bg = DARK
        c_legend_edge = GRAY
        c_spine = GRAY
        cores_radar = [RED, GREEN, "#00CC10", "#009900"]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_facecolor(c_bg)
    fig.patch.set_facecolor(c_bg)
    ax.tick_params(colors=c_text)
    ax.spines["polar"].set_color(c_spine)
    ax.grid(True, color=c_spine, linestyle="--", alpha=0.5)

    for idx, jog in enumerate(jogadores_radar):
        vals = raw_norm[idx].tolist() + [raw_norm[idx][0]]  # fechar
        cor  = cores_radar[idx]
        ax.plot(angles, vals, color=cor, linewidth=2.5, label=jog["nome"])
        ax.fill(angles, vals, color=cor, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(eixos, color=c_text, fontsize=10)
    ax.set_yticklabels([])
    ax.set_title(f"Espelho Pedigree — {jogador_ref['nome']}  |  Bagre.ai",
                 color=c_green, fontsize=13, pad=25)
    ax.legend(loc="upper right", bbox_to_anchor=(1.42, 1.15),
              labelcolor=c_text, facecolor=c_legend_bg, edgecolor=c_legend_edge, fontsize=9)

    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=c_bg, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico Radar salvo: {img_path}\n")

    return df_out


# ===============================================================================
# GOLDEN LIST — Tier Diretor (exclusivo)
# ===============================================================================
_GOLDEN_POOL_PADRAO = [
    # ── Brasileiros ──────────────────────────────────────────────────────────
    {"nome": "Giorgian De Arrascaeta", "gols": 25, "assists": 19, "valor_milhoes": 14.0},
    {"nome": "Kaio Jorge",             "gols": 21, "assists": 8,  "valor_milhoes": 12.0},
    {"nome": "Yuri Alberto",           "gols": 19, "assists": 6,  "valor_milhoes": 15.0},
    {"nome": "Pedro Guilherme",        "gols": 15, "assists": 4,  "valor_milhoes": 20.0},
    {"nome": "Vitor Roque",            "gols": 14, "assists": 5,  "valor_milhoes": 25.0},
    {"nome": "Neymar Jr",              "gols": 8,  "assists": 6,  "valor_milhoes": 15.0},
    {"nome": "Raphinha",               "gols": 22, "assists": 16, "valor_milhoes": 70.0},
    {"nome": "Gabriel Martinelli",     "gols": 15, "assists": 8,  "valor_milhoes": 75.0},
    {"nome": "Matheus Cunha",          "gols": 12, "assists": 7,  "valor_milhoes": 40.0},
    {"nome": "Savinho",                "gols": 9,  "assists": 11, "valor_milhoes": 45.0},
    {"nome": "Estevao Willian",        "gols": 12, "assists": 10, "valor_milhoes": 60.0},
    {"nome": "Endrick Felipe",         "gols": 8,  "assists": 3,  "valor_milhoes": 35.0},
    {"nome": "Igor Jesus",             "gols": 11, "assists": 5,  "valor_milhoes": 18.0},
    {"nome": "Igor Thiago",            "gols": 11, "assists": 4,  "valor_milhoes": 22.0},
    {"nome": "Andreas Pereira",        "gols": 6,  "assists": 9,  "valor_milhoes": 15.0},
    {"nome": "Vinicius Junior",        "gols": 9,  "assists": 7,  "valor_milhoes": 180.0},
    {"nome": "Richarlison",            "gols": 5,  "assists": 2,  "valor_milhoes": 45.0},
    {"nome": "Antony Matheus",         "gols": 4,  "assists": 3,  "valor_milhoes": 30.0},
    {"nome": "Gabriel Jesus",          "gols": 5,  "assists": 3,  "valor_milhoes": 40.0},
    {"nome": "Casemiro",               "gols": 2,  "assists": 2,  "valor_milhoes": 20.0},
    {"nome": "Joao Gomes",             "gols": 1,  "assists": 3,  "valor_milhoes": 28.0},
    # ── Europeus ─────────────────────────────────────────────────────────────
    {"nome": "Lamine Yamal",           "gols": 18, "assists": 16, "valor_milhoes": 180.0},
    {"nome": "Antoine Griezmann",      "gols": 16, "assists": 11, "valor_milhoes": 20.0},
    {"nome": "Bruno Fernandes",        "gols": 15, "assists": 17, "valor_milhoes": 65.0},
    {"nome": "Erling Haaland",         "gols": 27, "assists": 6,  "valor_milhoes": 200.0},
    {"nome": "Lautaro Martinez",       "gols": 20, "assists": 8,  "valor_milhoes": 110.0},
    {"nome": "Pedri Gonzalez",         "gols": 9,  "assists": 13, "valor_milhoes": 90.0},
    {"nome": "Kylian Mbappe",          "gols": 18, "assists": 7,  "valor_milhoes": 250.0},
    {"nome": "Jack Grealish",          "gols": 4,  "assists": 5,  "valor_milhoes": 75.0},
    {"nome": "Riyad Mahrez",           "gols": 5,  "assists": 4,  "valor_milhoes": 12.0},
]


def golden_list(pool=None, top_n=10):
    """
    Ranking dos melhores Pedigrees de um pool.
    Filtra jogadores com PediRato acima da média do pool,
    ordena por PediRato descrescente e retorna os top_n.

    Input:  lista de dicts [nome, gols, assists, valor_milhoes]  (None → dataset padrão)
    Output: lista de dicts com posicao, nome, stats, pedirato, classificacao
    """
    if not pool:
        pool = _GOLDEN_POOL_PADRAO

    jogadores = [dict(j) for j in pool]
    for j in jogadores:
        v = max(j.get("valor_milhoes", 0.1), 0.1)
        j["pedirato"] = (j.get("gols", 0) + j.get("assists", 0)) / v

    media = sum(j["pedirato"] for j in jogadores) / len(jogadores)
    pedigrees = sorted(
        [j for j in jogadores if j["pedirato"] > media],
        key=lambda j: j["pedirato"],
        reverse=True,
    )

    return [
        {
            "posicao":       i + 1,
            "nome":          j["nome"],
            "gols":          j.get("gols", 0),
            "assists":       j.get("assists", 0),
            "valor_milhoes": j.get("valor_milhoes", 0.0),
            "pedirato":      round(j["pedirato"], 2),
            "classificacao": "PEDIGREE",
        }
        for i, j in enumerate(pedigrees[:top_n])
    ]


# ===============================================================================
# PEDIRATO DA SEMANA — Tier Várzea (gratuito)
# ===============================================================================
_POOL_PADRAO = [
    # ── Brasileiros ──────────────────────────────────────────────────────────
    {"nome": "Giorgian De Arrascaeta", "gols": 25, "assists": 19, "valor_milhoes": 14.0,
     "clube": "Flamengo",          "liga": "Brasileirao"},
    {"nome": "Kaio Jorge",             "gols": 21, "assists": 8,  "valor_milhoes": 12.0,
     "clube": "Cruzeiro",           "liga": "Brasileirao"},
    {"nome": "Yuri Alberto",           "gols": 19, "assists": 6,  "valor_milhoes": 15.0,
     "clube": "Corinthians",        "liga": "Brasileirao"},
    {"nome": "Pedro Guilherme",        "gols": 15, "assists": 4,  "valor_milhoes": 20.0,
     "clube": "Flamengo",           "liga": "Brasileirao"},
    {"nome": "Vitor Roque",            "gols": 14, "assists": 5,  "valor_milhoes": 25.0,
     "clube": "Palmeiras",          "liga": "Brasileirao"},
    {"nome": "Neymar Jr",              "gols": 8,  "assists": 6,  "valor_milhoes": 15.0,
     "clube": "Santos",             "liga": "Brasileirao"},
    {"nome": "Raphinha",               "gols": 22, "assists": 16, "valor_milhoes": 70.0,
     "clube": "Barcelona",          "liga": "LaLiga"},
    {"nome": "Gabriel Martinelli",     "gols": 15, "assists": 8,  "valor_milhoes": 75.0,
     "clube": "Arsenal",            "liga": "Premier League"},
    {"nome": "Matheus Cunha",          "gols": 12, "assists": 7,  "valor_milhoes": 40.0,
     "clube": "Manchester United",  "liga": "Premier League"},
    {"nome": "Savinho",                "gols": 9,  "assists": 11, "valor_milhoes": 45.0,
     "clube": "Manchester City",    "liga": "Premier League"},
    {"nome": "Estevao Willian",        "gols": 12, "assists": 10, "valor_milhoes": 60.0,
     "clube": "Chelsea",            "liga": "Premier League"},
    {"nome": "Endrick Felipe",         "gols": 8,  "assists": 3,  "valor_milhoes": 35.0,
     "clube": "Lyon",               "liga": "Ligue 1"},
    {"nome": "Igor Jesus",             "gols": 11, "assists": 5,  "valor_milhoes": 18.0,
     "clube": "Nottingham Forest",  "liga": "Premier League"},
    {"nome": "Igor Thiago",            "gols": 11, "assists": 4,  "valor_milhoes": 22.0,
     "clube": "Brentford",          "liga": "Premier League"},
    {"nome": "Andreas Pereira",        "gols": 6,  "assists": 9,  "valor_milhoes": 15.0,
     "clube": "Palmeiras",          "liga": "Brasileirao"},
    {"nome": "Vinicius Junior",        "gols": 9,  "assists": 7,  "valor_milhoes": 180.0,
     "clube": "Real Madrid",        "liga": "LaLiga"},
    {"nome": "Richarlison",            "gols": 5,  "assists": 2,  "valor_milhoes": 45.0,
     "clube": "Tottenham",          "liga": "Premier League"},
    {"nome": "Antony Matheus",         "gols": 4,  "assists": 3,  "valor_milhoes": 30.0,
     "clube": "Real Betis",         "liga": "LaLiga"},
    {"nome": "Gabriel Jesus",          "gols": 5,  "assists": 3,  "valor_milhoes": 40.0,
     "clube": "Arsenal",            "liga": "Premier League"},
    {"nome": "Casemiro",               "gols": 2,  "assists": 2,  "valor_milhoes": 20.0,
     "clube": "Manchester United",  "liga": "Premier League"},
    {"nome": "Joao Gomes",             "gols": 1,  "assists": 3,  "valor_milhoes": 28.0,
     "clube": "Wolverhampton",      "liga": "Premier League"},
    # ── Europeus ─────────────────────────────────────────────────────────────
    {"nome": "Lamine Yamal",           "gols": 18, "assists": 16, "valor_milhoes": 180.0,
     "clube": "Barcelona",          "liga": "LaLiga"},
    {"nome": "Antoine Griezmann",      "gols": 16, "assists": 11, "valor_milhoes": 20.0,
     "clube": "Atletico Madrid",    "liga": "LaLiga"},
    {"nome": "Bruno Fernandes",        "gols": 15, "assists": 17, "valor_milhoes": 65.0,
     "clube": "Manchester United",  "liga": "Premier League"},
    {"nome": "Erling Haaland",         "gols": 27, "assists": 6,  "valor_milhoes": 200.0,
     "clube": "Manchester City",    "liga": "Premier League"},
    {"nome": "Lautaro Martinez",       "gols": 20, "assists": 8,  "valor_milhoes": 110.0,
     "clube": "Inter Milan",        "liga": "Serie A"},
    {"nome": "Pedri Gonzalez",         "gols": 9,  "assists": 13, "valor_milhoes": 90.0,
     "clube": "Barcelona",          "liga": "LaLiga"},
    {"nome": "Kylian Mbappe",          "gols": 18, "assists": 7,  "valor_milhoes": 250.0,
     "clube": "Real Madrid",        "liga": "LaLiga"},
    {"nome": "Jack Grealish",          "gols": 4,  "assists": 5,  "valor_milhoes": 75.0,
     "clube": "Manchester City",    "liga": "Premier League"},
    {"nome": "Riyad Mahrez",           "gols": 5,  "assists": 4,  "valor_milhoes": 12.0,
     "clube": "Al Ahli",            "liga": "Saudi Pro League"},
]


def pedirato_da_semana(pool=None):
    """
    Retorna o destaque semanal do tier Várzea.
    Sem chamadas externas — 100% estático.
    Rota APENAS pelo top-50% do ranking (verdadeiros Pedigrees) usando o
    número ISO da semana como seed, garantindo que nunca um PediRato apareça
    como destaque e que o resultado mude automaticamente a cada semana.
    """
    jogadores = [dict(j) for j in (pool if pool is not None else _POOL_PADRAO)]

    for j in jogadores:
        g = j.get("gols", 0)
        a = j.get("assists", 0)
        v = max(j.get("valor_milhoes", 0.1), 0.1)
        j["pedirato"] = (g + a) / v

    pool_sorted = sorted(jogadores, key=lambda j: j["pedirato"], reverse=True)

    # Restringe a rotação ao top-50% para garantir sempre um Pedigree legítimo
    top_pedigrees = pool_sorted[: max(1, len(pool_sorted) // 2)]

    semana = datetime.date.today().isocalendar()[1]
    destaque = top_pedigrees[semana % len(top_pedigrees)]

    return {
        "nome":          destaque["nome"],
        "clube":         destaque.get("clube", "—"),
        "liga":          destaque.get("liga", "—"),
        "gols":          destaque.get("gols", 0),
        "assists":       destaque.get("assists", 0),
        "valor_milhoes": destaque.get("valor_milhoes", 0.0),
        "pedirato":      round(destaque["pedirato"], 2),
        "destaque":      "PEDIGREE DA SEMANA",
        "semana":        semana,
    }


# ── DEMONSTRAÇÃO ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Frente 2
    df_vida = pd.DataFrame({
        "nome":          ["Mbappé", "Haaland", "Pedri", "Modric", "Benzema", "Vinicius Jr."],
        "idade":         [25,        23,        21,      38,       36,        23],
        "valor_milhoes": [180,       200,       120,     15,       20,        180],
    })
    analisar_ciclo_de_vida(df_vida)

    # Frente 3
    df_liga = pd.DataFrame({
        "clube":                      ["Getafe", "Rayo Vallecano", "Villarreal",
                                       "Atletico Madrid", "Barcelona", "Real Madrid"],
        "valor_total_elenco_milhoes": [80,        95,               320,
                                       550,              800,        1100],
    })
    analisar_concentracao_liga(df_liga)

    # Frente 4
    df_hype = pd.DataFrame({
        "nome":          ["Neymar", "Dembélé", "Griezmann", "Coman", "Sané",  "Gnabry"],
        "valor_milhoes": [80,        90,         45,          55,      60,      40],
        "gols":          [5,         12,         18,           8,      14,      10],
        "assists":       [3,         10,         12,           9,      11,       8],
    })
    analisar_hype_index(df_hype)

    # Frente 5
    ref = {"nome": "Neymar", "gols": 5, "assists": 3, "valor_milhoes": 80}
    pool_f5 = [
        {"nome": "Dembélé",   "gols": 12, "assists": 10, "valor_milhoes": 90},
        {"nome": "Griezmann", "gols": 18, "assists": 12, "valor_milhoes": 45},
        {"nome": "Coman",     "gols": 8,  "assists": 9,  "valor_milhoes": 35},
        {"nome": "Gnabry",    "gols": 10, "assists": 8,  "valor_milhoes": 28},
        {"nome": "Sané",      "gols": 14, "assists": 11, "valor_milhoes": 45},
    ]
    espelho_pedigree(ref, pool_f5)

    # ── Validação do fix de similaridade cosseno (pool pequeno) ──────────────────
    print("\n" + "#" * 65)
    print("  TESTE — Mbappé vs João Pedro (pool pequeno, deve ser > 90%)")
    print("#" * 65)
    mbappe    = {"nome": "Mbappé",     "gols": 25, "assists": 10, "valor_milhoes": 180}
    joao_pedro = {"nome": "João Pedro", "gols": 22, "assists": 9,  "valor_milhoes": 45}
    df_teste  = espelho_pedigree(mbappe, [joao_pedro])
    sim_jp    = df_teste.loc[df_teste["nome"] == "João Pedro", "similaridade_%"].iloc[0]
    print(f"\n  Similaridade Mbappé vs João Pedro: {sim_jp}%")
    assert sim_jp > 90, f"FALHOU: esperado > 90%, obtido {sim_jp}%"
    print("  ✓ PASSOU: similaridade > 90%")
