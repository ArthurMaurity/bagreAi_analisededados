import matplotlib
matplotlib.use('Agg') # Evita problemas com falta de display gráfico no terminal
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

class GeradorRelatorios:
    """
    Gerador de relatórios e visualizações para o Bagre.ai.
    Cria tabelas em Markdown e gráficos usando Matplotlib/Seaborn.
    """
    
    @staticmethod
    def gerar_relatorio_markdown(historico_jogadores, filename="relatorio_scout.md"):
        """
        Gera um arquivo Markdown formatado com a tabela dos jogadores pesquisados.
        Retorna o texto do Markdown gerado ou None se houver erro.
        """
        if not historico_jogadores:
            print("Nenhum dado no histórico para gerar o relatório.")
            return None
            
        try:
            # Garantir que o diretório pai existe
            dir_name = os.path.dirname(filename)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            md_lines = []
            md_lines.append("# Relatório de Scouting - Bagre.ai\n")
            md_lines.append("Este relatório contém os dados consolidados dos atletas analisados.\n")
            md_lines.append("## Tabela Comparativa\n")
            md_lines.append("| Atleta | Gols | Assistências | Valor de Mercado | Índice PediRato |")
            md_lines.append("| :--- | :---: | :---: | :---: | :---: |")
            
            for jogador in historico_jogadores:
                nome = jogador.get("nome", "Desconhecido").upper()
                gols = jogador.get("gols", 0)
                assists = jogador.get("assists", 0)
                valor = jogador.get("valor_milhoes", 0.0)
                pedirato = jogador.get("pedirato", 0.0)
                
                md_lines.append(f"| **{nome}** | {gols} | {assists} | €{valor}M | **{pedirato:.2f}** |")
                
            md_lines.append("\n*O Índice PediRato é calculado como: (Gols + Assistências) / Valor de Mercado (em milhões de euros). Quanto maior o índice, melhor a eficiência financeira/esportiva.*\n")
            
            markdown_content = "\n".join(md_lines)
            
            # Salvar no arquivo
            with open(filename, "w", encoding="utf-8") as f:
                f.write(markdown_content)
                
            print(f"Relatório Markdown salvo com sucesso em: {filename}")
            return markdown_content
        except Exception as e:
            print(f"Erro ao gerar relatório Markdown: {e}")
            return None

    @staticmethod
    def gerar_grafico_comparativo(historico_jogadores, filename="comparativo_pedirato.png"):
        """
        Gera um gráfico de barras comparando o Índice PediRato dos jogadores da sessão.
        Retorna o caminho do arquivo gerado ou None se houver erro.
        """
        if not historico_jogadores:
            print("Nenhum dado no histórico para gerar o gráfico.")
            return None
            
        try:
            # Garantir que o diretório pai existe
            dir_name = os.path.dirname(filename)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            # Converter para DataFrame
            dados = []
            for j in historico_jogadores:
                dados.append({
                    "Nome": j.get("nome", "Desconhecido").upper(),
                    "PediRato": j.get("pedirato", 0.0)
                })
            
            df = pd.DataFrame(dados)
            # Ordenar por PediRato decrescente
            df = df.sort_values(by="PediRato", ascending=False)
            
            # Configurar o estilo do Seaborn para uma estética premium
            sns.set_theme(style="darkgrid")
            plt.figure(figsize=(10, 6))
            
            # Paleta de cores moderna (degradê)
            colors = sns.color_palette("viridis", len(df))
            
            # Criar gráfico de barras
            ax = sns.barplot(
                x="PediRato", 
                y="Nome", 
                data=df, 
                palette=colors,
                hue="Nome",
                legend=False
            )
            
            # Adicionar rótulos de dados nas barras
            for i, p in enumerate(ax.patches):
                width = p.get_width()
                ax.text(
                    width + 0.05, 
                    p.get_y() + p.get_height() / 2, 
                    f"{width:.2f}", 
                    ha="left", 
                    va="center",
                    fontweight="bold"
                )
                
            plt.title("Comparação de Eficiência - Índice PediRato", fontsize=16, fontweight="bold", pad=15)
            plt.xlabel("Índice PediRato (Eficiência)", fontsize=12, fontweight="bold")
            plt.ylabel("Atleta", fontsize=12, fontweight="bold")
            
            plt.tight_layout()
            plt.savefig(filename, dpi=300)
            plt.close()
            
            print(f"Gráfico de comparação salvo com sucesso em: {filename}")
            return filename
        except Exception as e:
            print(f"Erro ao gerar gráfico comparativo: {e}")
            return None
