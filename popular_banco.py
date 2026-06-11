import os
import sys
import time
import unicodedata
import requests

# Inicializar o caminho para carregar as dependências locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bagre_database import BagreDatabase
from bagre_engine import BagreBackend, clean_currency

# Dicionário das 6 ligas escolhidas (ID na API-Football)
LIGAS = {
    "1": ("Brasileirão Série A", 71),
    "2": ("Premier League (Inglaterra)", 39),
    "3": ("La Liga (Espanha)", 140),
    "4": ("Serie A (Itália)", 135),
    "5": ("Bundesliga (Alemanha)", 78),
    "6": ("Ligue 1 (França)", 61)
}

SEASON = os.getenv("SEASON", "2024").strip()

def normalizar_texto(texto):
    """Remove acentos e converte para minúsculas para chave do cache."""
    if not texto:
        return ""
    texto_normalizado = unicodedata.normalize("NFD", texto)
    texto_normalizado = "".join(
        [c for c in texto_normalizado if unicodedata.category(c) != "Mn"]
    )
    return texto_normalizado.strip().lower()

def popular_banco():
    db = BagreDatabase()
    motor = BagreBackend()

    # Verificar se a chave API está configurada
    api_key = os.getenv("RAPIDAPI_KEY", "")
    if not api_key or api_key == "your_rapidapi_key_here":
        print("\n[ERRO] A variável RAPIDAPI_KEY não está configurada no seu ambiente ou no arquivo .env!")
        print("Para rodar este script de população, você precisa primeiro configurar a sua chave no arquivo .env local.")
        print("Exemplo de linha no arquivo .env:")
        print("RAPIDAPI_KEY=sua_chave_real_aqui\n")
        return

    # Se uma opção for passada via argumento de linha de comando, usa ela diretamente
    if len(sys.argv) > 1:
        escolha = sys.argv[1].strip()
        print(f"Opção selecionada via argumento: {escolha}")
    else:
        # Menu de seleção de liga para respeitar o limite de 100 req/dia do plano grátis
        print("\n========================================================")
        print("        MENU DE SELEÇÃO - POPULAÇÃO DO BANCO")
        print("========================================================")
        print("Escolha qual liga você deseja importar hoje:")
        for opcao, (nome, _) in LIGAS.items():
            print(f"  [{opcao}] {nome}")
        print("  [7] Importar todas (Atenção: pode estourar o limite de 100 req/dia do plano grátis)")
        print("  [0] Cancelar e Sair")
        print("========================================================")
        
        escolha = input("Opção desejada: ").strip()
    
    if escolha == "0":
        print("Operação cancelada.")
        return
        
    ligas_para_processar = {}
    if escolha == "7":
        # Importar todas
        ligas_para_processar = {nome: lid for _, (nome, lid) in LIGAS.items()}
    elif escolha in LIGAS:
        # Importar apenas a selecionada
        nome, lid = LIGAS[escolha]
        ligas_para_processar = {nome: lid}
    else:
        print("Opção inválida.")
        return

    print("\n========================================================")
    print(f"  INICIANDO POPULAÇÃO DO BANCO LOCAL (Temporada {SEASON})")
    print("========================================================")
    print("Ligas que serão processadas:")
    for liga_nome, liga_id in ligas_para_processar.items():
        print(f" - {liga_nome} (ID: {liga_id})")
    print("========================================================\n")

    jogadores_adicionados = 0

    for liga_nome, liga_id in ligas_para_processar.items():
        print(f"\n>>> Processando liga: {liga_nome}...")
        page = 1
        total_pages = 1

        while page <= total_pages:
            print(f"  -> Requisitando página {page} de {total_pages}...")
            
            # Executar a busca de jogadores por liga
            params = {
                "league": str(liga_id),
                "season": SEASON,
                "page": str(page)
            }
            url = f"{motor.base_url}/players"
            data = motor._executar_get(url, params=params)

            if not data:
                print(f"  [AVISO] Nenhuma resposta da API para a página {page} da liga {liga_nome}.")
                break
                
            if data.get("errors"):
                print(f"  [ERRO DA API] {data.get('errors')}")
                # Se bater no limite diário da API, interrompe o script
                if "limit" in str(data.get("errors")).lower() or "rate" in str(data.get("errors")).lower():
                    print("  [CRÍTICO] Limite de cota diária ou taxa atingido. Interrompendo a população.")
                    return
                break
                
            if not data.get("response"):
                print(f"  [AVISO] Nenhum jogador retornado para a página {page} da liga {liga_nome}.")
                break

            # Atualizar total de páginas retornado pela API
            total_pages = data.get("paging", {}).get("total", 1)
            
            for item in data["response"]:
                player_info = item.get("player", {})
                nome_jogador = player_info.get("name")
                
                if not nome_jogador:
                    continue

                stats_list = item.get("statistics", [])
                gols = 0
                assists = 0
                clube_nome = ""
                liga_nome_res = ""

                for stat in stats_list:
                    team = stat.get("team", {})
                    league = stat.get("league", {})
                    
                    if not clube_nome:
                        clube_nome = team.get("name", "")
                    if not liga_nome_res:
                        liga_nome_res = league.get("name", "")

                    g_info = stat.get("goals", {})
                    gols += g_info.get("total") or 0
                    assists += g_info.get("assists") or 0

                # Obter valor de mercado no Transfermarkt via Scraper
                # Com delay de 0.5s para evitar bloqueio por parte do Transfermarkt
                time.sleep(0.5)
                valor_milhoes = None
                try:
                    dados_tm = motor.obter_valor_mercado(nome_jogador)
                    val_str = None
                    if dados_tm and dados_tm.get("response", {}).get("players"):
                        val_str = dados_tm["response"]["players"][0].get("marketValue")
                    
                    if val_str:
                        valor_milhoes = max(clean_currency(val_str) / 1_000_000, 0.1)
                except Exception as e:
                    print(f"    [Scraper Erro] Falha ao obter valor para '{nome_jogador}': {e}")

                # Se o valor não for encontrado, usa 1.0 como fallback provisório
                if valor_milhoes is None:
                    valor_milhoes = 1.0

                # Calcular métrica do PediRato
                pedirato = (gols + assists) / valor_milhoes
                if pedirato > 1.5:
                    ranking_contexto = "Pedigree"
                elif pedirato > 0.5:
                    ranking_contexto = "Regular"
                else:
                    ranking_contexto = "PediRato"

                # Guardar no cache SQLite
                nome_norm = normalizar_texto(nome_jogador)
                result = {
                    "status": "success",
                    "nome": nome_jogador,
                    "clube": clube_nome,
                    "liga": liga_nome_res or liga_nome,
                    "gols": gols,
                    "assists": assists,
                    "valor_milhoes": valor_milhoes,
                    "pedirato": pedirato,
                    "ranking_contexto": ranking_contexto,
                    "fonte": "api_seeding",
                }

                db.salvar_cache(nome_norm, result)
                jogadores_adicionados += 1
                
                print(f"    ✓ [Salvo] {nome_jogador.upper()} ({clube_nome}) - {gols}G | {assists}A | €{valor_milhoes:.2f}M | PediRato: {pedirato:.2f}")

            # Ir para a próxima página
            page += 1
            # Delay entre requisições de página para respeitar o limite de taxa da API
            time.sleep(1.0)

    print(f"\n========================================================")
    print(f"  POPULAÇÃO FINALIZADA!")
    print(f"  Total de jogadores importados/atualizados: {jogadores_adicionados}")
    print("========================================================\n")

if __name__ == "__main__":
    popular_banco()
