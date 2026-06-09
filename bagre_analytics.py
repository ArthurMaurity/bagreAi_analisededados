"""
bagre_analytics.py - Frentes analiticas avancadas do Bagre.ai
Implementa as Frentes 2, 3, 4 e 5 do CLAUDE.md.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
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


def _cyberpunk_ax(ax, fig):
    """Aplica estilo cyberpunk a um eixo matplotlib convencional."""
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    ax.tick_params(colors=WHITE)
    ax.xaxis.label.set_color(WHITE)
    ax.yaxis.label.set_color(WHITE)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRAY)


# ===============================================================================
# FRENTE 2 — CICLO DE VIDA E CURVA DE VALOR
# ===============================================================================
def analisar_ciclo_de_vida(df: pd.DataFrame) -> dict:
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
    img_path = os.path.join(STATIC_DIR, "ciclo_vida.png")
    fig, ax = plt.subplots(figsize=(11, 6))
    _cyberpunk_ax(ax, fig)

    y_max = max(float(y.max()), float(y_range.max())) * 1.15
    ax.set_ylim(bottom=0, top=y_max)

    if mascara.any():
        ax.axhspan(limiar, y_max, alpha=0.06, color=GREEN, label="Janela de revenda (>80% pico)")

    ax.scatter(x, y, color=GREEN, s=110, zorder=5, label="Jogadores (real)")
    ax.plot(x_range, y_range, color=WHITE, linewidth=2, label="Curva polinomial (grau 2)")
    ax.axvline(idade_pico, color=RED, linestyle=":", linewidth=1.5,
               label=f"Pico estimado: {idade_pico:.1f} anos")

    for _, row in df.iterrows():
        ax.annotate(row["nome"], (row["idade"], row["valor_milhoes"]),
                    textcoords="offset points", xytext=(6, 5), fontsize=8, color=WHITE)

    ax.set_xlabel("Idade", fontsize=11)
    ax.set_ylabel("Valor de Mercado (€M)", fontsize=11)
    ax.set_title("Ciclo de Vida — Curva de Valor por Idade  |  Bagre.ai",
                 color=GREEN, fontsize=13, pad=12)
    ax.legend(labelcolor=WHITE, facecolor=DARK, edgecolor=GRAY, fontsize=9)
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=BG)
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
# FRENTE 3 — CONCENTRAÇÃO DE RIQUEZA POR LIGA (GINI)
# ===============================================================================
def analisar_concentracao_liga(df: pd.DataFrame) -> dict:
    """
    Coeficiente de Gini calculado manualmente com numpy.
    Gera a Curva de Lorenz com área de desigualdade.

    Input:  DataFrame com colunas [clube, valor_total_elenco_milhoes]
    Output: dict com gini, interpretacao, clube mais rico/pobre, razão, df enriquecido
    """
    required = {"clube", "valor_total_elenco_milhoes"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame deve ter as colunas: {required}")
    if len(df) < 2:
        raise ValueError("Mínimo de 2 clubes para análise.")

    df = df.copy().sort_values("valor_total_elenco_milhoes").reset_index(drop=True)
    x  = df["valor_total_elenco_milhoes"].values.astype(float)
    n  = len(x)
    s  = x.sum()

    # Gini manual (numpy) — fórmula do CLAUDE.md
    idx  = np.arange(1, n + 1)
    gini = float((2 * np.dot(idx, x) / (n * s)) - (n + 1) / n)

    # Lorenz
    cum_x   = np.concatenate([[0.0], np.cumsum(x) / s])
    cum_pop = np.concatenate([[0.0], idx / n])

    mais_rico  = df.iloc[-1]
    mais_pobre = df.iloc[0]
    razao      = mais_rico["valor_total_elenco_milhoes"] / max(mais_pobre["valor_total_elenco_milhoes"], 0.01)
    df["concentracao_acumulada_%"] = (np.cumsum(x) / s * 100).round(2)

    if gini < 0.3:
        interpretacao = "Baixa desigualdade"
    elif gini < 0.5:
        interpretacao = "Média desigualdade"
    else:
        interpretacao = "Alta desigualdade"

    # ── Relatório textual ──────────────────────────────────────────────────────
    print("\n" + "=" * 58)
    print("  FRENTE 3 — CONCENTRAÇÃO DE RIQUEZA POR LIGA")
    print("=" * 58)
    print(f"  Coeficiente de Gini da Liga: {gini:.4f}")
    print(f"  Interpretação:               {interpretacao}")
    print(f"  Clube mais rico:   {mais_rico['clube']}  (€{mais_rico['valor_total_elenco_milhoes']:.1f}M)")
    print(f"  Clube mais pobre:  {mais_pobre['clube']}  (€{mais_pobre['valor_total_elenco_milhoes']:.1f}M)")
    print(f"  Razão rico/pobre:  {razao:.1f}×")
    print("\n  Concentração por clube (ordem crescente de valor):")
    print(df[["clube", "valor_total_elenco_milhoes", "concentracao_acumulada_%"]].to_string(index=False))
    print("=" * 58)

    # ── Gráfico Lorenz ─────────────────────────────────────────────────────────
    img_path = os.path.join(STATIC_DIR, "gini_liga.png")
    fig, ax = plt.subplots(figsize=(8, 7))
    _cyberpunk_ax(ax, fig)

    ax.plot(cum_pop, cum_x, color=GREEN, linewidth=2.5, label=f"Curva de Lorenz  (Gini = {gini:.3f})")
    ax.plot([0, 1], [0, 1], color=WHITE, linestyle="--", linewidth=1.5, label="Igualdade perfeita")
    ax.fill_between(cum_pop, cum_x, cum_pop, color=RED, alpha=0.3, label="Área de desigualdade")

    ax.set_xlabel("Proporção acumulada de clubes", fontsize=11)
    ax.set_ylabel("Proporção acumulada do valor de mercado", fontsize=11)
    ax.set_title("Curva de Lorenz — Concentração de Riqueza  |  Bagre.ai",
                 color=GREEN, fontsize=13, pad=12)
    ax.legend(labelcolor=WHITE, facecolor=DARK, edgecolor=GRAY, fontsize=9)
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=BG)
    plt.close()
    print(f"  Gráfico salvo: {img_path}\n")

    return {
        "gini": round(gini, 4),
        "interpretacao": interpretacao,
        "clube_mais_rico": mais_rico["clube"],
        "clube_mais_pobre": mais_pobre["clube"],
        "razao": round(razao, 2),
        "df": df,
    }


# ===============================================================================
# FRENTE 4 — HYPE INDEX (DETECÇÃO DE PEDIRATO)
# ===============================================================================
def analisar_hype_index(df: pd.DataFrame) -> pd.DataFrame:
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
    img_path = os.path.join(STATIC_DIR, "hype_index.png")
    cores_map = {"PediRato": RED, "Pedigree": GREEN, "Regular": GRAY}

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 7))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # seaborn scatterplot com hue
    sns.scatterplot(
        data=df, x="performance", y="valor_milhoes",
        hue="classificacao", palette=cores_map,
        s=130, zorder=5, ax=ax, legend=False,
    )
    # seaborn pode redefinir facecolors — reaplicar após o plot
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)

    # Reta de regressão via matplotlib
    x_line = np.linspace(df["performance"].min(), df["performance"].max(), 300)
    ax.plot(x_line, slope * x_line + inter, color=WHITE, linewidth=2,
            label=f"Regressão  (R²={r2:.3f})")

    # Pontos de legenda manual
    for cls, cor in cores_map.items():
        ax.scatter([], [], color=cor, s=80, label=cls)

    # Anotações com nome
    for _, row in df.iterrows():
        ax.annotate(row["nome"], (row["performance"], row["valor_milhoes"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8, color=WHITE)

    ax.set_xlabel("Performance (Gols + Assists)", fontsize=11, color=WHITE)
    ax.set_ylabel("Valor de Mercado (€M)", fontsize=11, color=WHITE)
    ax.set_title(f"Hype Index — PediRatos vs Pedigrees  |  Bagre.ai",
                 color=GREEN, fontsize=13, pad=12)
    ax.tick_params(colors=WHITE)
    ax.legend(labelcolor=WHITE, facecolor=DARK, edgecolor=GRAY, fontsize=9)
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=BG)
    plt.close()
    print(f"  Gráfico salvo: {img_path}\n")

    return df


# ===============================================================================
# FRENTE 5 — ESPELHO PEDIGREE (SIMILARIDADE COSSENO + RADAR)
# ===============================================================================
def espelho_pedigree(jogador_ref: dict, pool: list) -> pd.DataFrame:
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

    features = ["gols", "assists", "valor_milhoes"]

    # Matriz: referência na linha 0, pool nas demais
    todos    = [jogador_ref] + pool
    matrix   = np.array([[j.get(f, 0) for f in features] for j in todos], dtype=float)

    scaler      = MinMaxScaler()
    matrix_norm = scaler.fit_transform(matrix)

    ref_vec   = matrix_norm[[0]]
    pool_vecs = matrix_norm[1:]
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
    cores_radar = [RED, GREEN, "#00CC10", "#009900"]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    ax.tick_params(colors=WHITE)
    ax.spines["polar"].set_color(GRAY)

    for idx, jog in enumerate(jogadores_radar):
        vals = raw_norm[idx].tolist() + [raw_norm[idx][0]]  # fechar
        cor  = cores_radar[idx]
        ax.plot(angles, vals, color=cor, linewidth=2.5, label=jog["nome"])
        ax.fill(angles, vals, color=cor, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(eixos, color=WHITE, fontsize=10)
    ax.set_yticklabels([])
    ax.set_title(f"Espelho Pedigree — {jogador_ref['nome']}  |  Bagre.ai",
                 color=GREEN, fontsize=13, pad=25)
    ax.legend(loc="upper right", bbox_to_anchor=(1.42, 1.15),
              labelcolor=WHITE, facecolor=DARK, edgecolor=GRAY, fontsize=9)

    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico Radar salvo: {img_path}\n")

    return df_out


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
