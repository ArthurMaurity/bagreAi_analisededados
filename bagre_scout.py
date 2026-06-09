from bagre_engine import BagreBackend, clean_currency
from bagre_database import BagreDatabase
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

    # ── STEP 1: RapidAPI Football Live Data (+ fallback mock) ────────────────
    try:
        # Resolver player_id via busca por nome se não fornecido
        if not player_id or not str(player_id).isdigit():
            print(f"[STEP 1] Buscando sugestões para: {nome_jogador}")
            busca = motor.buscar_jogador(nome_jogador)
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

        # Buscar dados no elenco do clube
        if player_id and str(player_id).isdigit():
            if not team_id or not str(team_id).isdigit():
                print(f"[STEP 1] Buscando time do jogador ID {player_id}...")
                busca = motor.buscar_jogador(nome_jogador)
                suggestions = (busca.get("response", {}).get("suggestions", [])
                               if busca else [])
                for sug in suggestions:
                    if str(sug.get("id")) == str(player_id):
                        team_id = sug.get("teamId")
                        if not clube_nome:
                            clube_nome = sug.get("teamName", "")
                        if not liga_nome:
                            liga_nome = sug.get("league", "")
                        break

            if team_id and str(team_id).isdigit():
                print(f"[STEP 1] Buscando elenco do clube ID {team_id}...")
                elenco_data = motor.listar_elenco_clube(team_id)
                resp_data = elenco_data.get("response", {}) if elenco_data else {}
                squad = (resp_data.get("list", {}).get("squad", [])
                         or resp_data.get("squad", []))

                for group in squad:
                    for member in group.get("members", []):
                        if str(member.get("id")) == str(player_id):
                            gols = member.get("goals", 0)
                            assists = member.get("assists", 0)
                            val_bytes = member.get("transferValue", 0)
                            if val_bytes:
                                valor_milhoes = max(val_bytes / 1_000_000, 0.1)
                            if not clube_nome:
                                clube_nome = member.get("teamName", "")
                            if not liga_nome:
                                liga_nome = member.get("league", "")
                            fonte = "api_principal"
                            print(
                                f"[STEP 1 ✓] {gols} Gols | {assists} Assists "
                                f"| €{valor_milhoes}M | {clube_nome} ({liga_nome})"
                            )
                            break
                    if gols is not None:
                        break

                if gols is None:
                    print("[STEP 1] Jogador não encontrado no elenco.")
    except Exception as e:
        print(f"[STEP 1 WARN] RapidAPI falhou: {e}")

    # ── STEP 2: Transfermarkt (valor de mercado) ──────────────────────────────
    if valor_milhoes is None:
        try:
            print("[STEP 2] Buscando valor no Transfermarkt...")
            dados_tm = motor.obter_valor_mercado(nome_jogador)
            if dados_tm and dados_tm.get("response", {}).get("players"):
                val_str = dados_tm["response"]["players"][0].get("marketValue", "1m")
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

        print("-" * 40)
        print(f"ATLETA FINALIZADO: {nome_jogador.upper()}")
        print(f"ESTATÍSTICAS: {gols} Gols | {assists} Assistências")
        print(f"VALOR: €{valor_milhoes:.2f}M  |  PEDIRATO: {pedirato:.2f}")
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
