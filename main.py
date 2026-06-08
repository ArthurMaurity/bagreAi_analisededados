import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from bagre_scout import realizar_scout_processado
from bagre_relatorios import GeradorRelatorios

# ── SESSÃO EM MEMÓRIA ──────────────────────────────────────────────────────────
sessao = []  # lista de dicts: {nome, gols, assists, valor_milhoes, pedirato, idade}

# ── HELPERS ────────────────────────────────────────────────────────────────────
def _perguntar_salvar(caminho):
    resp = input("Deseja salvar o gráfico gerado? (s/n): ").strip().lower()
    if resp != 's' and os.path.exists(caminho):
        os.remove(caminho)
        print("Gráfico descartado.")
    else:
        print(f"Gráfico salvo em: {caminho}")

def _verificar_sessao(minimo=1):
    if len(sessao) < minimo:
        msg = "Nenhum jogador" if minimo == 1 else f"Mínimo de {minimo} jogadores"
        print(f"{msg} na sessão. Use [1] para adicionar.")
        return False
    return True

# ── [1] SCOUT DE JOGADOR ───────────────────────────────────────────────────────
def opcao_scout():
    print("\n--- Scout de Jogador ---")
    nome = input("Nome do jogador: ").strip()
    if not nome:
        print("Nome inválido.")
        return

    idade_s = input("Idade (Enter para pular): ").strip()
    valor_s = input("Valor de mercado em €M (Enter para buscar auto): ").strip()
    gols_s  = input("Gols (Enter para buscar auto): ").strip()
    ast_s   = input("Assistências (Enter para buscar auto): ").strip()

    idade = int(idade_s) if idade_s.isdigit() else None
    valor = float(valor_s.replace(',', '.')) if valor_s else None
    gols  = int(gols_s)  if gols_s.isdigit()  else None
    ast   = int(ast_s)   if ast_s.isdigit()   else None

    print(f"\nBuscando dados de {nome}...")
    res = realizar_scout_processado(
        nome_jogador=nome,
        valor_mercado_manual=valor,
        gols_manual=gols,
        assists_manual=ast,
    )

    if res.get("status") == "ambiguous":
        print("\nMúltiplos resultados:")
        sugs = res["suggestions"]
        for i, s in enumerate(sugs, 1):
            print(f"  [{i}] {s['nome']} — {s['clube']}")
        esc = input("Escolha o número (Enter para cancelar): ").strip()
        if not esc.isdigit() or not (1 <= int(esc) <= len(sugs)):
            print("Cancelado.")
            return
        s = sugs[int(esc) - 1]
        res = realizar_scout_processado(
            nome_jogador=s["nome"],
            player_id=s["player_id"],
            team_id=s["team_id"],
            valor_mercado_manual=valor,
            gols_manual=gols,
            assists_manual=ast,
        )

    if res.get("status") == "success":
        res["idade"] = idade
        sessao.append(res)
        print(f"✓ {res['nome']} adicionado à sessão ({len(sessao)} jogador(es)).")
    else:
        print("Falha ao obter dados do jogador.")

# ── [2] ANÁLISE DE SESSÃO ──────────────────────────────────────────────────────
def opcao_analise_sessao():
    print("\n--- Análise de Sessão ---")
    if not _verificar_sessao():
        return

    print(f"\n{'Atleta':<30} {'Gols':>5} {'Ast':>5} {'€M':>8} {'PediRato':>10}")
    print("-" * 62)
    for j in sessao:
        print(f"{j['nome'].upper():<30} {j['gols']:>5} {j['assists']:>5} {j['valor_milhoes']:>7.1f}M {j['pedirato']:>10.3f}")

    md = GeradorRelatorios.gerar_relatorio_markdown(sessao, filename="relatorio_scout.md")
    img = GeradorRelatorios.gerar_grafico_comparativo(sessao, filename="comparativo_pedirato.png")
    if img:
        _perguntar_salvar(img)

# ── [3] HYPE INDEX ─────────────────────────────────────────────────────────────
def opcao_hype_index():
    print("\n--- Hype Index (Regressão Linear) ---")
    if not _verificar_sessao(3):
        return

    df = pd.DataFrame(sessao)
    df["performance"] = df["gols"] + df["assists"]

    # X = performance, Y = valor → resíduo positivo = caro demais para o que entrega
    x = df["performance"].values.astype(float)
    y = df["valor_milhoes"].values.astype(float)
    coef = np.polyfit(x, y, 1)
    y_pred = np.polyval(coef, x)
    df["residuo"] = y - y_pred

    limite = df["residuo"].std()
    df["classe"] = df["residuo"].apply(
        lambda r: "PediRato" if r > limite else ("Pedigree" if r < -limite else "Regular")
    )

    print(f"\n{'Atleta':<30} {'Perf':>5} {'€M':>7} {'Resíduo':>9} {'Classe'}")
    print("-" * 65)
    for _, row in df.sort_values("residuo", ascending=False).iterrows():
        print(f"{row['nome'].upper():<30} {row['performance']:>5.0f} {row['valor_milhoes']:>6.1f}M {row['residuo']:>+9.2f}  {row['classe']}")

    img_path = "hype_index.png"
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor("#000000")
    fig.patch.set_facecolor("#000000")

    cores = {"PediRato": "#FF3131", "Pedigree": "#39FF14", "Regular": "#FFFFFF"}
    for cls, grp in df.groupby("classe"):
        ax.scatter(grp["performance"], grp["valor_milhoes"],
                   label=cls, color=cores[cls], s=110, zorder=5)

    x_line = np.linspace(x.min(), x.max(), 200)
    ax.plot(x_line, np.polyval(coef, x_line), color="#666666", linestyle="--", label="Regressão")

    for _, row in df.iterrows():
        ax.annotate(row["nome"], (row["performance"], row["valor_milhoes"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=8, color="#FFFFFF")

    ax.set_xlabel("Performance (Gols + Assists)", color="#FFFFFF")
    ax.set_ylabel("Valor de Mercado (€M)", color="#FFFFFF")
    ax.set_title("Hype Index — Bagre.ai", color="#39FF14", fontsize=14)
    ax.tick_params(colors="#FFFFFF")
    ax.legend(labelcolor="#FFFFFF")
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    _perguntar_salvar(img_path)

# ── [4] ESPELHO PEDIGREE ───────────────────────────────────────────────────────
def opcao_espelho_pedigree():
    print("\n--- Espelho Pedigree ---")
    if not _verificar_sessao(2):
        return

    for i, j in enumerate(sessao, 1):
        print(f"  [{i}] {j['nome']}  €{j['valor_milhoes']:.1f}M")

    esc = input("Jogador de referência (número): ").strip()
    if not esc.isdigit() or not (1 <= int(esc) <= len(sessao)):
        print("Seleção inválida.")
        return

    ref = sessao[int(esc) - 1]
    candidatos = [j for j in sessao if j["nome"] != ref["nome"]]
    if not candidatos:
        print("Sem outros jogadores para comparar.")
        return

    features = ["gols", "assists", "pedirato"]
    todos = [ref] + candidatos
    df = pd.DataFrame(todos)[features].astype(float)

    # Normalização min-max
    for col in features:
        rng = df[col].max() - df[col].min()
        df[col] = (df[col] - df[col].min()) / (rng if rng > 0 else 1)

    ref_vec = df.iloc[0].values
    distancias = [(candidatos[i], np.linalg.norm(df.iloc[i + 1].values - ref_vec))
                  for i in range(len(candidatos))]
    distancias.sort(key=lambda t: t[1])
    top3 = [t[0] for t in distancias[:3]]

    print(f"\nSimilares a {ref['nome']} (€{ref['valor_milhoes']:.1f}M):")
    for j in top3:
        eco = ref["valor_milhoes"] - j["valor_milhoes"]
        sinal = "+" if eco >= 0 else ""
        print(f"  {j['nome']:<30} €{j['valor_milhoes']:.1f}M  Economia: {sinal}€{eco:.1f}M  PediRato: {j['pedirato']:.3f}")

    # Radar Chart
    img_path = "espelho_pedigree.png"
    labels = ["Gols", "Assistências", "PediRato"]
    n = len(labels)
    angles = [i * 2 * np.pi / n for i in range(n)] + [0]

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_facecolor("#000000")
    fig.patch.set_facecolor("#000000")

    jogadores_radar = [ref] + top3
    cores_radar = ["#39FF14", "#FFFFFF", "#00BFFF", "#FF8C00"]
    max_vals = [max(j.get(k, 0) for j in jogadores_radar) or 1
                for k in ["gols", "assists", "pedirato"]]

    for idx, jog in enumerate(jogadores_radar):
        vals = [jog.get("gols", 0), jog.get("assists", 0), jog.get("pedirato", 0)]
        vals_n = [v / m for v, m in zip(vals, max_vals)] + [vals[0] / max_vals[0]]
        ax.plot(angles, vals_n, color=cores_radar[idx], linewidth=2, label=jog["nome"])
        ax.fill(angles, vals_n, color=cores_radar[idx], alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color="#FFFFFF")
    ax.set_yticklabels([])
    ax.set_title("Espelho Pedigree — Bagre.ai", color="#39FF14", fontsize=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), labelcolor="#FFFFFF")
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    _perguntar_salvar(img_path)

# ── [5] CICLO DE VIDA ──────────────────────────────────────────────────────────
def opcao_ciclo_vida():
    print("\n--- Ciclo de Vida (Curva de Valor por Idade) ---")
    if not _verificar_sessao():
        return

    validos = [j for j in sessao if j.get("idade")]
    if len(validos) < 2:
        print("Mínimo de 2 jogadores com idade informada. Informe a idade no scout [1].")
        return

    df = pd.DataFrame(validos)
    x = df["idade"].values.astype(float)
    y = df["valor_milhoes"].values.astype(float)

    grau = min(2, len(validos) - 1)
    coef = np.polyfit(x, y, grau)
    x_line = np.linspace(x.min() - 1, x.max() + 1, 200)
    y_line = np.polyval(coef, x_line)
    pico_idade = x_line[np.argmax(y_line)]
    print(f"\nPico de valor projetado: ~{pico_idade:.1f} anos")

    img_path = "ciclo_vida.png"
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor("#000000")
    fig.patch.set_facecolor("#000000")

    ax.scatter(x, y, color="#39FF14", s=110, zorder=5, label="Jogadores")
    ax.plot(x_line, y_line, color="#FFFFFF", linestyle="--", label=f"Curva (grau {grau})")
    ax.axvline(pico_idade, color="#FF3131", linestyle=":", label=f"Pico ~{pico_idade:.1f} anos")

    for _, row in df.iterrows():
        ax.annotate(row["nome"], (row["idade"], row["valor_milhoes"]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8, color="#FFFFFF")

    ax.set_xlabel("Idade", color="#FFFFFF")
    ax.set_ylabel("Valor de Mercado (€M)", color="#FFFFFF")
    ax.set_title("Ciclo de Vida — Curva de Valor", color="#39FF14", fontsize=14)
    ax.tick_params(colors="#FFFFFF")
    ax.legend(labelcolor="#FFFFFF")
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    _perguntar_salvar(img_path)

# ── [6] CONCENTRAÇÃO DE RIQUEZA — GINI ────────────────────────────────────────
def _gini(valores):
    v = np.sort(np.array(valores, dtype=float))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * np.dot(idx, v) / (n * v.sum())) - (n + 1) / n)

def opcao_gini():
    print("\n--- Concentração de Riqueza por Liga (Gini) ---")
    if not _verificar_sessao(3):
        return

    gini = _gini([j["valor_milhoes"] for j in sessao])
    print(f"\nCoeficiente de Gini da sessão: {gini:.4f}")
    if gini < 0.3:
        print("Distribuição: Relativamente igualitária.")
    elif gini < 0.5:
        print("Distribuição: Concentração moderada.")
    else:
        print("Distribuição: Alta concentração de riqueza.")

    vals = sorted(j["valor_milhoes"] for j in sessao)
    n = len(vals)
    cum_val = np.cumsum(vals) / sum(vals)
    cum_pop = np.arange(1, n + 1) / n

    img_path = "gini_lorenz.png"
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor("#000000")
    fig.patch.set_facecolor("#000000")

    ax.plot([0] + list(cum_pop), [0] + list(cum_val),
            color="#39FF14", linewidth=2, label=f"Lorenz  (Gini={gini:.3f})")
    ax.plot([0, 1], [0, 1], color="#FFFFFF", linestyle="--", label="Igualdade perfeita")
    ax.fill_between([0] + list(cum_pop), [0] + list(cum_val),
                    [0] + list(cum_pop), alpha=0.2, color="#39FF14")

    ax.set_xlabel("Proporção de Jogadores", color="#FFFFFF")
    ax.set_ylabel("Proporção do Valor de Mercado", color="#FFFFFF")
    ax.set_title("Curva de Lorenz — Concentração de Valor", color="#39FF14", fontsize=14)
    ax.tick_params(colors="#FFFFFF")
    ax.legend(labelcolor="#FFFFFF")
    plt.tight_layout()
    plt.savefig(img_path, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    _perguntar_salvar(img_path)

# ── [7] RELATÓRIO COMPLETO (.docx e .md) ──────────────────────────────────────
def opcao_relatorio_completo():
    print("\n--- Gerar Relatorio Completo ---")
    if not _verificar_sessao():
        return

    # Garantir gráfico comparativo atualizado na pasta static
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    os.makedirs(static_dir, exist_ok=True)
    GeradorRelatorios.gerar_grafico_comparativo(
        sessao, filename=os.path.join(static_dir, "comparativo_pedirato.png")
    )

    # Relatório Markdown
    md_path = "relatorio_bagre_completo.md"
    GeradorRelatorios.gerar_relatorio_markdown(sessao, filename=md_path)
    print(f"Markdown: {md_path}")

    # Relatório Word completo
    docx_path = "relatorio_bagre_completo.docx"
    resultado = GeradorRelatorios.gerar_relatorio_completo_docx(
        historico_jogadores=sessao,
        resultados_analytics={},
        filename=docx_path,
    )
    if resultado:
        print(f"Word (.docx): {docx_path}")

# ── MENU PRINCIPAL ─────────────────────────────────────────────────────────────
MENU = """
+============================================================+
|     BAGRE.AI -- INTELIGENCIA DE MERCADO NO FUTEBOL         |
+============================================================+
|  [1] Scout de Jogador                                      |
|  [2] Analise de Sessao                                     |
|  [3] Hype Index -- Detectar PediRatos (Frente 4)           |
|  [4] Espelho Pedigree -- Encontrar similares (Frente 5)    |
|  [5] Ciclo de Vida -- Curva de Valor por Idade (Frente 2)  |
|  [6] Concentracao de Riqueza por Liga -- Gini (Frente 3)   |
|  [7] Gerar Relatorio Completo (.docx e .md)                |
|  [0] Sair                                                  |
+============================================================+"""

_OPCOES = {
    "1": opcao_scout,
    "2": opcao_analise_sessao,
    "3": opcao_hype_index,
    "4": opcao_espelho_pedigree,
    "5": opcao_ciclo_vida,
    "6": opcao_gini,
    "7": opcao_relatorio_completo,
}

def main():
    print(MENU)
    while True:
        info = f" [{len(sessao)} na sessão]" if sessao else ""
        escolha = input(f"\nOpção{info}: ").strip()

        if escolha == "0":
            print("Encerrando Bagre.ai. Até logo!")
            break

        func = _OPCOES.get(escolha)
        if func:
            try:
                func()
            except KeyboardInterrupt:
                print("\nOperação cancelada.")
            except Exception as e:
                print(f"Erro: {e}")
        else:
            print("Opção inválida. Digite um número de 0 a 7.")

        print(MENU)

if __name__ == "__main__":
    main()
