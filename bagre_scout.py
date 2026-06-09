from bagre_engine import BagreBackend, clean_currency
import pandas as pd
import unicodedata

def normalizar_texto(texto):
    """
    Remove acentos e converte para minúsculas para comparações insensíveis a acentos e case.
    """
    if not texto:
        return ""
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_normalizado = "".join([c for c in texto_normalizado if unicodedata.category(c) != 'Mn'])
    return texto_normalizado.strip().lower()

def extrair_stats_fbref(motor, url_fbref):
    """
    Tenta extrair gols e assistências diretamente da tabela do FBref.
    """
    df = motor.obter_tabela_fbref(url_fbref)
    if df.empty:
        return None
    
    try:
        gols = int(df['Gls'].iloc[0]) if 'Gls' in df.columns else 0
        assists = int(df['Ast'].iloc[0]) if 'Ast' in df.columns else 0
        return gols, assists
    except Exception as e:
        print(f"Erro ao processar colunas do FBref: {e}")
        return None

def realizar_scout_processado(nome_jogador, player_id=None, team_id=None, valor_mercado_manual=None, gols_manual=None, assists_manual=None, url_fbref=None):
    """
    Processa a análise do jogador de forma não-interativa.
    Busca automaticamente por nome caso player_id esteja ausente.
    Retorna dados do jogador ou lista de sugestões se a busca for ambígua.
    """
    motor = BagreBackend()
    
    # 1. Se não temos player_id, tentamos descobrir via busca pelo nome digitado
    if not player_id or not str(player_id).isdigit():
        print(f"Buscando sugestões para o nome: {nome_jogador}")
        busca = motor.buscar_jogador(nome_jogador)
        suggestions = busca.get('response', {}).get('suggestions', []) if busca else []
        
        if not suggestions:
            print("Nenhum jogador encontrado para o nome digitado nas APIs.")
        elif len(suggestions) == 1:
            player_id = suggestions[0].get('id')
            team_id = suggestions[0].get('teamId')
            nome_jogador = suggestions[0].get('name')
            print(f"Encontrado único jogador correspondente: {nome_jogador} (ID: {player_id})")
        else:
            # Múltiplas sugestões. Verificamos se há um match exato de nome (desconsiderando acentos/case)
            nome_pesquisa_norm = normalizar_texto(nome_jogador)
            primeiro_nome_norm = normalizar_texto(suggestions[0].get('name'))
            
            # Se for match exato de nome, prosseguimos com a primeira opção
            if nome_pesquisa_norm == primeiro_nome_norm:
                player_id = suggestions[0].get('id')
                team_id = suggestions[0].get('teamId')
                nome_jogador = suggestions[0].get('name')
                print(f"Match exato encontrado: {nome_jogador} (ID: {player_id})")
            else:
                # Caso contrário, retornamos as opções para desambiguação
                print(f"Busca ambígua para '{nome_jogador}'. Retornando lista de opções.")
                return {
                    "status": "ambiguous",
                    "message": f"Múltiplos jogadores encontrados para '{nome_jogador}'. Por favor selecione um.",
                    "suggestions": [
                        {
                            "player_id": s.get('id'),
                            "team_id": s.get('teamId'),
                            "nome": s.get('name'),
                            "clube": s.get('teamName'),
                            "tipo": s.get('type')
                        }
                        for s in suggestions[:10]
                    ]
                }
                
    # Inicializar variáveis com None para controle
    gols, assists, valor_milhoes = None, None, None

    # 2. Tentativa via Roster/Squad do Clube (API de Elenco)
    if player_id and str(player_id).isdigit():
        # Se não fornecido o team_id, tentamos descobrir via buscar_jogador
        if not team_id or not str(team_id).isdigit():
            print(f"Buscando time do jogador ID {player_id} via busca...")
            busca = motor.buscar_jogador(nome_jogador)
            suggestions = busca.get('response', {}).get('suggestions', []) if busca else []
            for sug in suggestions:
                if str(sug.get('id')) == str(player_id):
                    team_id = sug.get('teamId')
                    break
        
        if team_id and str(team_id).isdigit():
            print(f"Buscando elenco do clube ID {team_id}...")
            elenco_data = motor.listar_elenco_clube(team_id)
            resp_data = elenco_data.get('response', {}) if elenco_data else {}
            squad = resp_data.get('list', {}).get('squad', []) or resp_data.get('squad', [])
            
            for group in squad:
                for member in group.get('members', []):
                    if str(member.get('id')) == str(player_id):
                        # Encontramos o jogador no elenco!
                        gols = member.get('goals', 0)
                        assists = member.get('assists', 0)
                        val_bytes = member.get('transferValue', 0)
                        if val_bytes:
                            valor_milhoes = max(val_bytes / 1_000_000, 0.1)
                        print(f"[✓] Dados obtidos da API do clube: {gols} Gols | {assists} Assists | Valor: €{valor_milhoes}M")
                        break
                if gols is not None:
                    break

    # 3. Obter Valor de Mercado (Override ou Fallbacks)
    if valor_mercado_manual is not None and valor_mercado_manual > 0:
        try:
            valor_milhoes = float(valor_mercado_manual)
            print(f"[Override Manual] Valor de Mercado: €{valor_milhoes:.2f}M")
        except ValueError:
            pass
            
    if valor_milhoes is None:
        print("Buscando valor no Transfermarkt...")
        dados_tm = motor.obter_valor_mercado(nome_jogador)
        if dados_tm and dados_tm.get('response', {}).get('players'):
            try:
                val_str = dados_tm['response']['players'][0].get('marketValue', '1m')
                valor_eur = clean_currency(val_str)
                valor_milhoes = max(valor_eur / 1_000_000, 0.1)
                print(f"[✓] Valor encontrado via API: €{valor_milhoes:.2f}M")
            except Exception as e:
                print(f"Erro ao ler valor da API Transfermarkt: {e}")
                
        if valor_milhoes is None:
            if valor_mercado_manual is not None:
                valor_milhoes = float(valor_mercado_manual)
            else:
                valor_milhoes = 1.0
            print(f"[Padrão/Manual] Usando valor: €{valor_milhoes:.2f}M")

    # 4. Obter Gols e Assistências (API Principal ou FBref)
    if (gols is None or assists is None) and player_id and str(player_id).isdigit():
        print(f"Buscando detalhes para o Player ID: {player_id}")
        detalhes = motor.obter_detalhes_jogador(player_id)
        if detalhes and detalhes.get('status') == 'success':
            try:
                resp = detalhes.get('response', {})
                stats = resp.get('playerStats') or (resp.get('seasons')[0].get('statistics') if resp.get('seasons') else {})
                gols = int(stats.get('goals', 0) or 0)
                assists = int(stats.get('assists', 0) or 0)
                print(f"[✓] Estatísticas obtidas da API Principal: {gols} Gols | {assists} Assistências")
            except Exception as e:
                print(f"Erro ao analisar estatísticas da API: {e}")

    if (gols is None or assists is None or (gols + assists == 0)) and url_fbref and url_fbref != "string":
        print(f"Buscando contingência no FBref: {url_fbref}")
        stats_fbref = extrair_stats_fbref(motor, url_fbref)
        if stats_fbref is not None:
            gols, assists = stats_fbref
            print(f"[✓] Estatísticas obtidas do FBref: {gols} Gols | {assists} Assistências")

    # Manual Fallbacks se continuarem vazios
    if gols_manual is not None and (gols_manual > 0 or gols is None):
        gols = int(gols_manual)
    if assists_manual is not None and (assists_manual > 0 or assists is None):
        assists = int(assists_manual)

    gols = gols if gols is not None else 0
    assists = assists if assists is not None else 0

    # 5. Calcular PediRato
    valor_milhoes = max(valor_milhoes, 0.1)
    pedirato = (gols + assists) / valor_milhoes
    
    print("-" * 40)
    print(f"ATLETA FINALIZADO: {nome_jogador.upper()}")
    print(f"ESTATÍSTICAS: {gols} Gols | {assists} Assistências")
    print(f"VALOR: €{valor_milhoes:.2f}M")
    print(f"ÍNDICE PEDIRATO: {pedirato:.2f}")
    print("-" * 40 + "\n")

    return {
        "status": "success",
        "nome": nome_jogador,
        "gols": gols,
        "assists": assists,
        "valor_milhoes": valor_milhoes,
        "pedirato": pedirato
    }