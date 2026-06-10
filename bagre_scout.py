from bagre_engine import BagreBackend, clean_currency
from bagre_database import BagreDatabase
from concurrent.futures import ThreadPoolExecutor
import unicodedata


def normalizar_texto(texto):
    """Remove acentos e converte para minúsculas para comparações insensíveis a acentos e case."""
    if not texto:
        return ""
    texto_normalizado = unicodedata.normalize("NFD", texto)
    texto_normalizado = "".join(
        [c for c in texto_normalizado if unicodedata.category(c) != "Mn"]
    )
    return texto_normalizado.strip().lower()


def realizar_scout_processado(nome_jogador, player_id=None, team_id=None):
    """
    Pipeline de scout com waterfall de 6 passos:
      STEP 0: cache SQLite fresco (< 24h)         → fonte="cache"
      STEP 1: RapidAPI Football Live Data          → fonte="api_principal"
      STEP 2: Transfermarkt (valor de mercado)     → fonte="transfermarkt"
      STEP 3: FBref scraping (gols / assists)      → fonte="fbref"
      STEP 4: cache SQLite expirado                → fonte="cache_expirado"
      STEP 5: todas as fontes falharam             → status="unavailable"
    """
    motor = BagreBackend()
    db = BagreDatabase()
    nome_norm = normalizar_texto(nome_jogador)

    # ── STEP 0: cache fresco ─────────────────────────────────────────────────
    cached = db.buscar_cache(nome_norm)
    if cached:
        print(f"[CACHE HIT] {nome_jogador}")
        return {**cached, "fonte": "cache", "status": "success"}

    gols = None
    assists = None
    valor_milhoes = None
    fonte = None
    clube_nome = ""
    liga_nome = ""

    # Processamento simultâneo — seção 4.1 do artigo
    print(f"[PARALLEL] Buscando '{nome_jogador}' via Live API + Transfermarkt simultaneamente...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        _fut_busca = executor.submit(motor.buscar_jogador, nome_jogador)
        _fut_tm    = executor.submit(motor.obter_valor_mercado, nome_jogador)

    try:
        _busca_pre = _fut_busca.result()
    except Exception as _e:
        print(f"[PARALLEL WARN] buscar_jogador: {_e}")
        _busca_pre = None
    try:
        _tm_pre = _fut_tm.result()
    except Exception as _e:
        print(f"[PARALLEL WARN] obter_valor_mercado: {_e}")
        _tm_pre = None

    # ── STEP 1: RapidAPI Football Live Data (+ fallback mock) ────────────────
    try:
        # Resolver player_id via busca por nome se não fornecido
        if not player_id or not str(player_id).isdigit():
            print(f"[STEP 1] Buscando sugestões para: {nome_jogador}")
            busca = _busca_pre  # usa resultado pré-buscado em paralelo
            suggestions = (busca.get("response", {}).get("suggestions", [])
                           if busca else [])

            if not suggestions:
                print("[STEP 1] Nenhuma sugestão encontrada.")
            elif len(suggestions) == 1:
                player_id = suggestions[0].get("id")
                team_id = suggestions[0].get("teamId")
                nome_jogador = suggestions[0].get("name", nome_jogador)
                clube_nome = suggestions[0].get("teamName", "")
                liga_nome = suggestions[0].get("league", "")
                print(f"[STEP 1] Único resultado: {nome_jogador} (ID: {player_id})")
            else:
                nome_norm_search = normalizar_texto(nome_jogador)
                match = None
                for s in suggestions:
                    if normalizar_texto(s.get("name", "")) == nome_norm_search:
                        match = s
                        break

                if match:
                    player_id = match.get("id")
                    team_id = match.get("teamId")
                    nome_jogador = match.get("name", nome_jogador)
                    clube_nome = match.get("teamName", "")
                    liga_nome = match.get("league", "")
                    print(f"[STEP 1] Match exato: {nome_jogador} (ID: {player_id})")
                else:
                    print(f"[STEP 1] Busca ambígua para '{nome_jogador}'.")
                    return {
                        "status": "ambiguous",
                        "message": (
                            f"Múltiplos jogadores encontrados para '{nome_jogador}'. "
                            "Por favor selecione um."
                        ),
                        "suggestions": [
                            {
                                "player_id": s.get("id"),
                                "team_id": s.get("teamId"),
                                "nome": s.get("name"),
                                "clube": s.get("teamName"),
                                "liga": s.get("league", ""),
                                "tipo": s.get("type"),
                            }
                            for s in suggestions[:10]
                        ],
                    }

        # Buscar dados diretamente via detalhes do jogador (API v3)
        if player_id and str(player_id).isdigit():
            print(f"[STEP 1] Buscando estatísticas diretas do jogador ID {player_id}...")
            detalhes = motor.obter_detalhes_jogador(player_id)
            if detalhes and detalhes.get("response"):
                total_gols = 0
                total_assists = 0
                for item in detalhes["response"]:
                    player_info = item.get("player", {})
                    if not nome_jogador:
                        nome_jogador = player_info.get("name", nome_jogador)
                    stats_list = item.get("statistics", [])
                    for stat in stats_list:
                        team = stat.get("team", {})
                        league = stat.get("league", {})
                        if not clube_nome:
                            clube_nome = team.get("name", "")
                        if not liga_nome:
                            liga_nome = league.get("name", "")
                        
                        g_info = stat.get("goals", {})
                        total_gols += g_info.get("total") or 0
                        total_assists += g_info.get("assists") or 0
                
                gols = total_gols
                assists = total_assists
                fonte = "api_principal"
                print(
                    f"[STEP 1 ✓] {gols} Gols | {assists} Assists "
                    f"| {clube_nome} ({liga_nome})"
                )
            else:
                print("[STEP 1] Detalhes do jogador não encontrados.")
    except Exception as e:
        print(f"[STEP 1 WARN] RapidAPI falhou: {e}")

    # ── STEP 2: Transfermarkt (valor de mercado) ──────────────────────────────
    if valor_milhoes is None:
        try:
            print("[STEP 2] Usando resultado Transfermarkt pré-buscado...")
            dados_tm = _tm_pre  # usa resultado pré-buscado em paralelo
            val_str = None
            if dados_tm and dados_tm.get("response", {}).get("players"):
                val_str = dados_tm["response"]["players"][0].get("marketValue")
            
            # Se não obtivemos valor ou se o valor for '-' ou 0, e o nome resolvido for diferente do termo de busca original, tentamos buscar com o nome resolvido
            if (not val_str or val_str == "-" or clean_currency(val_str) == 0.0) and normalizar_texto(nome_jogador) != nome_norm:
                print(f"[STEP 2] Valor inválido com termo original '{nome_norm}'. Tentando buscar resolved name '{nome_jogador}'...")
                dados_tm = motor.obter_valor_mercado(nome_jogador)
                if dados_tm and dados_tm.get("response", {}).get("players"):
                    val_str = dados_tm["response"]["players"][0].get("marketValue")

            if val_str:
                valor_eur = clean_currency(val_str)
                valor_milhoes = max(valor_eur / 1_000_000, 0.1)
                fonte = "transfermarkt"
                print(f"[STEP 2 ✓] Transfermarkt: €{valor_milhoes:.2f}M")
            else:
                print("[STEP 2 WARN] Transfermarkt não retornou dados.")
        except Exception as e:
            print(f"[STEP 2 WARN] Transfermarkt falhou: {e}")

    # ── STEP 3: FBref scraping (gols / assists) ───────────────────────────────
    if gols is None or assists is None:
        try:
            print(f"[STEP 3] Buscando stats no FBref para: {nome_jogador}")
            stats = motor.buscar_stats_fbref(nome_jogador)
            if stats is not None:
                gols, assists = stats
                fonte = "fbref"
                print(f"[STEP 3 ✓] FBref: {gols} Gols | {assists} Assists")
            else:
                print("[STEP 3 WARN] FBref não retornou dados.")
        except Exception as e:
            print(f"[STEP 3 WARN] FBref falhou: {e}")

    # Salvar no cache e retornar se temos dados suficientes
    if valor_milhoes is not None or gols is not None or assists is not None:
        gols = gols if gols is not None else 0
        assists = assists if assists is not None else 0
        valor_milhoes = max(valor_milhoes or 1.0, 0.1)
        pedirato = (gols + assists) / valor_milhoes

        if pedirato > 1.5:
            ranking_contexto = "Pedigree"
        elif pedirato > 0.5:
            ranking_contexto = "Regular"
        else:
            ranking_contexto = "PediRato"

        print("-" * 40)
        print(f"ATLETA FINALIZADO: {nome_jogador.upper()}")
        print(f"ESTATÍSTICAS: {gols} Gols | {assists} Assistências")
        print(f"VALOR: €{valor_milhoes:.2f}M  |  PEDIRATO: {pedirato:.2f}  |  {ranking_contexto}")
        print(f"FONTE: {fonte}")
        print("-" * 40 + "\n")

        result = {
            "status": "success",
            "nome": nome_jogador,
            "clube": clube_nome,
            "liga": liga_nome,
            "gols": gols,
            "assists": assists,
            "valor_milhoes": valor_milhoes,
            "pedirato": pedirato,
            "ranking_contexto": ranking_contexto,
            "fonte": fonte or "api_principal",
        }
        db.salvar_cache(nome_norm, result)
        return result

    # ── STEP 4: cache stale (expirado mas melhor que nada) ────────────────────
    stale = db.buscar_cache_stale(nome_norm)
    if stale:
        print(f"[CACHE STALE] {nome_jogador}")
        return {**stale, "fonte": "cache_expirado", "status": "success"}

    # ── STEP 5: todas as fontes falharam ──────────────────────────────────────
    return {
        "status": "unavailable",
        "nome": nome_jogador,
        "fonte": "nenhuma",
        "aviso": (
            f"Nenhuma fonte de dados respondeu para '{nome_jogador}'. "
            "Tente novamente em instantes."
        ),
    }
