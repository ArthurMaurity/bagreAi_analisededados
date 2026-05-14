from bagre_engine import BagreBackend
import pandas as pd

def extrair_stats_fbref(motor, url_fbref):
    """
    Tenta extrair gols e assistências diretamente da tabela do FBref.
    """
    df = motor.obter_tabela_fbref(url_fbref)
    if df.empty:
        return 0, 0
    
    try:
        # No FBref, a linha 'Soma' ou a primeira linha costuma ter os totais
        # Vamos buscar as colunas 'Gls' (Gols) e 'Ast' (Assistências)
        gols = int(df['Gls'].iloc[0]) if 'Gls' in df.columns else 0
        assists = int(df['Ast'].iloc[0]) if 'Ast' in df.columns else 0
        return gols, assists
    except:
        return 0, 0

def realizar_scout_robusto(nome_jogador, url_fbref=None):
    motor = BagreBackend()
    print(f"\nIniciando Varredura Multicloud: {nome_jogador}")
    
    # 1. Busca de Valor de Mercado (Transfermarkt)
    print("Buscando valor no Transfermarkt...")
    dados_tm = motor.obter_valor_mercado(nome_jogador)
    valor_eur = 1000000 # Valor padrão caso falhe
    
    if dados_tm and dados_tm.get('response', {}).get('players'):
        try:
            # Extração e limpeza do valor (ex: '€15m' -> 15000000)
            val_str = dados_tm['response']['players'][0].get('marketValue', '1m')
            valor_eur = int(''.join(filter(str.isdigit, val_str.replace('m', '000000'))))
        except: pass

    # 2. Busca de Performance (Live Data com Fallback para FBref)
    print("Buscando performance...")
    busca_live = motor.buscar_jogador(nome_jogador)
    gols, assists = 0, 0
    
    if busca_live and busca_live.get('response', {}).get('suggestions'):
        p_id = busca_live['response']['suggestions'][0]['id']
        detalhes = motor.obter_detalhes_jogador(p_id)
        # Tenta extrair da API principal
        resp = detalhes.get('response', {})
        stats = resp.get('playerStats') or (resp.get('seasons')[0].get('statistics') if resp.get('seasons') else {})
        gols = int(stats.get('goals', 0) or 0)
        assists = int(stats.get('assists', 0) or 0)

    # 3. SE CONTINUAR ZERADO: Forçar busca no FBref
    if (gols + assists == 0) and url_fbref:
        print("Dados zerados na API principal. Acionando contingência FBref...")
        gols, assists = extrair_stats_fbref(motor, url_fbref)

    # 4. Cálculo do PediRato
    valor_milhoes = max(valor_eur / 1_000_000, 0.1)
    pedirato = (gols + assists) / valor_milhoes

    print("-" * 40)
    print(f"ATLETA: {nome_jogador.upper()}")
    print(f"FONTE DE PERFORMANCE: {'FBref' if (url_fbref and gols+assists > 0) else 'Live API'}")
    print(f"ESTATÍSTICAS: {gols} Gols | {assists} Assistências")
    print(f"VALOR: €{valor_milhoes}M")
    print(f"ÍNDICE PEDIRATO: {round(pedirato, 2)}")
    print("-" * 40)

if __name__ == "__main__":
    # Para o teste funcionar, você precisa passar a URL do jogador no FBref
    # Exemplo: Pedro no FBref (URL hipotética para o teste)
    url_pedro = "https://fbref.com/pt/jogadores/33f6770f/Pedro" 
    realizar_scout_robusto("Pedro", url_fbref=url_pedro)