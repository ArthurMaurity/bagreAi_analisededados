"""
bagre_demo.py - Demonstracao standalone do Bagre.ai
Roda sem API keys ou conexao com internet.
Dataset sintetico com numpy.random.seed(42) para reprodutibilidade.

Uso: python bagre_demo.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

from bagre_analytics import (
    analisar_hype_index,
    analisar_ciclo_de_vida,
    analisar_concentracao_liga,
    espelho_pedigree,
)
from bagre_relatorios import GeradorRelatorios

np.random.seed(42)

# ── DATASET SINTETICO ──────────────────────────────────────────────────────────
# Estrutura: 4 PediRatos | 4 Pedigrees | 12 Regulares
# PediRatos = alto valor, baixa performance (residuo positivo na regressao)
# Pedigrees = baixo valor, alta performance (residuo negativo)

NOMES = [
    # PediRatos (0-3)
    "Neymar Jr.",        "Antony",            "Roberto Firmino",   "Philippe Coutinho",
    # Pedigrees (4-7)
    "Ademola Lookman",   "Vangelis Pavlidis", "Taty Castellanos",  "Gustavo Scarpa",
    # Regulares (8-19)
    "Raphinha",          "Rodrygo",           "Gabriel Martinelli","Bruno Guimaraes",
    "Marquinhos",        "Gerson",            "Richarlison",       "Eder Militao",
    "Alisson Becker",    "Fabinho",           "Fred Rodrigues",    "Hulk Givanildo",
]

CLUBES = [
    "Al-Hilal",     "Man. United",   "Al-Qadsiah",    "Vasco da Gama",
    "Atalanta",     "Benfica",       "Lazio",         "Atletico-MG",
    "Barcelona",    "Real Madrid",   "Arsenal",       "Newcastle",
    "PSG",          "Flamengo",      "Tottenham",     "Real Madrid",
    "Liverpool",    "Al-Ittihad",    "Man. United",   "Atletico-MG",
]

LIGAS = [
    "Saudi League",  "Prem. League",  "Saudi League",  "Brasileirao",
    "Serie A",       "Primeira Liga", "Serie A",       "Brasileirao",
    "La Liga",       "La Liga",       "Prem. League",  "Prem. League",
    "Ligue 1",       "Brasileirao",   "Prem. League",  "La Liga",
    "Prem. League",  "Saudi League",  "Prem. League",  "Brasileirao",
]

# Idades aleatorias dentro de faixas realistas por categoria
idades = np.concatenate([
    np.random.randint(30, 34, 4),   # PediRatos: carreira declinante
    np.random.randint(24, 30, 4),   # Pedigrees: prime
    np.random.randint(22, 33, 12),  # Regulares: variado
])

# Gols e assists controlados para garantir a distribuicao desejada
gols = np.concatenate([
    np.random.randint(2,  6,  4),   # PediRatos: baixa producao
    np.random.randint(13, 21, 4),   # Pedigrees: alta producao
    np.random.randint(4,  16, 12),  # Regulares: moderada
])

assists = np.concatenate([
    np.random.randint(1, 4,  4),    # PediRatos
    np.random.randint(5, 12, 4),    # Pedigrees
    np.random.randint(2, 10, 12),   # Regulares
])

# Valores de mercado com ruido uniforme para realismo
valores_base = np.concatenate([
    np.random.uniform(55, 95, 4),   # PediRatos: caros
    np.random.uniform(6,  40, 4),   # Pedigrees: baratos
    np.random.uniform(20, 85, 12),  # Regulares
])
valores = (valores_base + np.random.uniform(-0.5, 0.5, 20)).clip(min=1.0).round(1)

df = pd.DataFrame({
    "nome":          NOMES,
    "idade":         idades,
    "clube":         CLUBES,
    "liga":          LIGAS,
    "gols":          gols.astype(int),
    "assists":       assists.astype(int),
    "valor_milhoes": valores,
})

# ── SEPARADOR VISUAL ───────────────────────────────────────────────────────────
SEP = "=" * 65

def _secao(titulo):
    print(f"\n{SEP}")
    print(f"  {titulo}")
    print(SEP)

# ── 1. HYPE INDEX ──────────────────────────────────────────────────────────────
_secao("FRENTE 4 | Hype Index — Regressao Linear")
df_hype = df[["nome", "valor_milhoes", "gols", "assists"]].copy()
df_resultado = analisar_hype_index(df_hype)

# ── 2. CICLO DE VIDA ───────────────────────────────────────────────────────────
_secao("FRENTE 2 | Ciclo de Vida — Curva de Valor por Idade")
df_vida = df[["nome", "idade", "valor_milhoes"]].copy()
analisar_ciclo_de_vida(df_vida)

# ── 3. CONCENTRACAO POR LIGA ───────────────────────────────────────────────────
_secao("FRENTE 3 | Concentracao de Riqueza por Liga — Gini")
df_liga = (
    df.groupby("liga", as_index=False)["valor_milhoes"]
      .sum()
      .rename(columns={"valor_milhoes": "valor_total_elenco_milhoes"})
      .rename(columns={"liga": "clube"})
)
# Renomeia coluna para a interface esperada pela funcao
df_liga.columns = ["clube", "valor_total_elenco_milhoes"]
analisar_concentracao_liga(df_liga)

# ── 4. ESPELHO PEDIGREE ────────────────────────────────────────────────────────
_secao("FRENTE 5 | Espelho Pedigree — Similaridade Cosseno + Radar")
idx_ref = df["valor_milhoes"].idxmax()
ref     = df.loc[idx_ref, ["nome", "gols", "assists", "valor_milhoes"]].to_dict()
pool    = df.drop(index=idx_ref)[["nome", "gols", "assists", "valor_milhoes"]].to_dict("records")

print(f"\n  Jogador de referencia (maior valor): {ref['nome']} (E{ref['valor_milhoes']:.1f}M)")
espelho_pedigree(ref, pool)

# ── 5. RELATORIO WORD COMPLETO ─────────────────────────────────────────────────
_secao("RELATORIO COMPLETO | Gerando .docx e .md")

# Monta historico no formato esperado pelo GeradorRelatorios
historico = []
for _, row in df.iterrows():
    val = max(float(row["valor_milhoes"]), 0.1)
    historico.append({
        "nome":          row["nome"],
        "gols":          int(row["gols"]),
        "assists":       int(row["assists"]),
        "valor_milhoes": val,
        "pedirato":      round((int(row["gols"]) + int(row["assists"])) / val, 3),
    })

GeradorRelatorios.gerar_relatorio_markdown(historico, filename="Relatorio_BagreAI_Demo.md")
GeradorRelatorios.gerar_grafico_comparativo(historico, filename="static/comparativo_pedirato.png")
GeradorRelatorios.gerar_relatorio_completo_docx(
    historico_jogadores=historico,
    resultados_analytics={},
    filename="Relatorio_BagreAI_Demo.docx",
)

# ── CONCLUSAO ──────────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("  Demo concluida.")
print("  Verifique a pasta static/ e o arquivo Relatorio_BagreAI_Demo.docx")
print(SEP)
print(f"\n  Graficos gerados em static/:")
print("    ciclo_vida.png         — Frente 2")
print("    gini_liga.png          — Frente 3")
print("    hype_index.png         — Frente 4")
print("    radar_pedigree.png     — Frente 5")
print("    comparativo_pedirato.png — Sessao geral")
print(f"\n  Relatorios:")
print("    Relatorio_BagreAI_Demo.md   — Markdown")
print("    Relatorio_BagreAI_Demo.docx — Word (Tier Diretor)")
print()
