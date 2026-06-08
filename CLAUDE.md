# CLAUDE.md - Diretrizes do Projeto Bagre.ai

## 1. Visão Geral do Projeto
**Nome da Startup:** Bagre.ai  
**Segmento:** Inteligência de Mercado, Data Scouting e Eficiência Financeira no Futebol.  
**Objetivo:** Construir uma ferramenta de análise de dados para o mercado de transferências de futebol utilizando Python. O foco é identificar ineficiências financeiras de clubes, descobrindo talentos subvalorizados de alta performance (**Pedigrees**) e expondo contratações superestimadas infladas por "hype" que drenam os cofres (**PediRatos**).

### Identidade Visual (Cyberpunk Football):
Ao gerar interfaces ou visualizações de dados, utilize a seguinte paleta de cores:
- **Fundo:** Preto Absoluto (`#000000`) e Cinza Chumbo (`#1A1A1A`) para corporativo/seriedade.
- **Destaques:** Verde Neon (`#39FF14`) para inovação/gramado e Branco (`#FFFFFF`).

## 2. Modelo de Negócios e Restrições de Infraestrutura (Bootstrapping)
O projeto é guiado pela filosofia 100% *Bootstrapping* e *Sweat Equity* (Investimento Inicial: R$ 0,00).
- **Regra de Infraestrutura:** Toda a arquitetura inicial deve rodar em tiers gratuitos de nuvem (ex: Render, Supabase, GitHub Actions). O código deve ser otimizado para não estourar limites de memória e CPU dessas camadas gratuitas.
- **Monetização SaaS (Tiers de Assinatura):**
  1. *Várzea (Gratuito):* Estatísticas gerais e acesso ao "PediRato da Semana".
  2. *Olheiro (R$ 29,90/mês):* B2C. Acesso ao Hype Index completo e buscas personalizadas.
  3. *Diretor (R$ 997,00/mês):* B2B. Geração ilimitada de relatórios automatizados (`.docx`) e acesso à "Golden List".

## 3. Stack Tecnológica
- **Linguagem Principal:** Python 3.10+
- **Processamento de Dados:** `pandas`, `numpy`
- **Visualização de Dados:** `seaborn`, `matplotlib` (configurados com tema escuro/dark mode)
- **Automação de Relatórios:** `python-docx`
- **Ingestão de Dados:** `requests` para consumo via RapidAPI (`transfermarkt-api`, `FBref` e `API-Football`).

## 4. Conceitos Fundamentais e Regras de Negócio (Métricas)
O Claude Code deve implementar rigorosamente os algoritmos e cálculos para as 5 frentes de análise:

1. **ROI de Jogadores:**
   $$\text{ROI} = \frac{\text{Gols} + \text{Assistências}}{\text{Valor de Mercado}}$$
   *Regra:* Determina a eficiência de entrega ofensiva por unidade de capital investido.

2. **Ciclo de Vida e Curva de Valor:**
   Correlação estatística de regressão ou agrupamento entre Idade e Valor de Mercado para prever janelas ideais de revenda e depreciação.

3. **Concentração de Riqueza por Liga:**
   Análise de desigualdade (ex: Coeficiente de Gini adaptado) comparando o valor total de mercado dos elencos de uma mesma liga.

4. **Hype Index (Detecção de PediRatos):**
   Regressão linear simples/múltipla cruzando métricas de Performance Real (eixo Y) vs. Preço/Valor de Mercado (eixo X). Jogadores com resíduos altamente positivos (preço muito acima do desempenho projetado pela reta) são classificados como **PediRatos**.

5. **Índice Pedigree (O "Espelho Pedigree"):**
   Algoritmo de busca por similaridade (ex: distância euclidiana ou cosseno em matriz de scouts normalizada). Dado um jogador de alto custo, o sistema deve retornar os 3 atletas mais semelhantes estatisticamente com valor de mercado drasticamente inferior e alto "Índice Pedigree". O output visual obrigatório para comparação é um **Gráfico de Radar**.

## 5. Arquitetura de Código de Referência
Abaixo está o pipeline base estruturado que deve ditar o estilo de escrita de código no projeto:

```python
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from docx import Document
import io

# 1. TRATAMENTO DE DADOS (PANDAS)
def clean_currency(val):
    """Trata strings de moeda do Transfermarkt (ex: €15m, €500k) para float."""
    if not val or val == '-': 
        return 0.0
    val_str = str(val).replace('€', '').strip()
    multiplier = 1.0
    if 'm' in val_str:
        multiplier = 1000000.0
        val_str = val_str.replace('m', '')
    elif 'k' in val_str:
        multiplier = 1000.0
        val_str = val_str.replace('k', '')
    try:
        return float(val_str) * multiplier
    except ValueError:
        return 0.0

# 2. VISUALIZAÇÃO DE SCOUTING (SEABORN com identidade Cyberpunk)
def gerar_grafico_scouting(df):
    """Gera matriz de scouting alinhada ao visual Cyberpunk do Bagre.ai."""
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Paleta alinhada: Verde Neon para Pedigrees, Vermelho para PediRatos
    cores_status = {'Pedigree': '#39FF14', 'PediRato': '#FF3131', 'Regular': '#FFFFFF'}
    
    sns.scatterplot(data=df, x='market_value', y='performance_score', hue='status', palette=cores_status, ax=ax)
    ax.axhline(df['performance_score'].mean(), color='#666666', linestyle='--', label='Média de Performance')
    
    ax.set_title("Matriz Bagre.ai: Identificando Pedigrees vs PediRatos", color='#39FF14', fontsize=14, pad=15)
    ax.set_facecolor('#000000')
    fig.patch.set_facecolor('#000000')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close()
    return buf

# 3. RELATÓRIO AUTOMATIZADO (PYTHON-DOCX - Plano Diretor)
def gerar_relatorio_scout(df, filename='Relatorio_BagreAI.docx'):
    """Gera o relatório corporativo automatizado em formato Word (.docx)."""
    doc = Document()
    doc.add_heading('Bagre.ai: Relatório de Inteligência de Mercado', 0)
    
    doc.add_heading('Análise Pedigree vs PediRato', level=1)
    doc.add_paragraph("Análise automatizada baseada em eficiência de capital: identificação de talentos subvalorizados e riscos financeiros baseados em dados reais de performance.")
    
    grafico = gerar_grafico_scouting(df)
    doc.add_picture(grafico)
    
    doc.save(filename)