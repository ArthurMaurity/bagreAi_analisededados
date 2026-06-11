import os
import time
import requests
import pandas as pd
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def clean_currency(val):
    """Converte strings de moeda do Transfermarkt para float em euros.
    Ex: '€15m' -> 15000000.0 | '€500k' -> 500000.0 | '-' ou vazio -> 0.0"""
    if not val or val == '-':
        return 0.0
    val_str = str(val).replace('€', '').strip()
    multiplier = 1.0
    if 'm' in val_str.lower():
        multiplier = 1_000_000.0
        val_str = val_str.lower().replace('m', '')
    elif 'k' in val_str.lower():
        multiplier = 1_000.0
        val_str = val_str.lower().replace('k', '')
    try:
        return float(val_str) * multiplier
    except ValueError:
        return 0.0


# ── Dataset mock 2026 — fallback quando as APIs externas estão indisponíveis ──
MOCK_PLAYERS = [
    # ── BRASILEIROS (21) ─────────────────────────────────────────────────────
    # Pedigrees — alto rendimento, valor baixo
    {"id": "1",  "name": "Giorgian De Arrascaeta", "teamName": "Flamengo",
     "teamId": "101", "league": "Brasileirao", "goals": 25, "assists": 19,
     "transferValue": 14_000_000},
    {"id": "2",  "name": "Kaio Jorge",             "teamName": "Cruzeiro",
     "teamId": "103", "league": "Brasileirao", "goals": 21, "assists": 8,
     "transferValue": 12_000_000},
    {"id": "3",  "name": "Yuri Alberto",           "teamName": "Corinthians",
     "teamId": "102", "league": "Brasileirao", "goals": 19, "assists": 6,
     "transferValue": 15_000_000},
    {"id": "4",  "name": "Pedro Guilherme",        "teamName": "Flamengo",
     "teamId": "101", "league": "Brasileirao", "goals": 15, "assists": 4,
     "transferValue": 20_000_000},
    {"id": "5",  "name": "Vitor Roque",            "teamName": "Palmeiras",
     "teamId": "105", "league": "Brasileirao", "goals": 14, "assists": 5,
     "transferValue": 25_000_000},
    {"id": "6",  "name": "Neymar Jr",              "teamName": "Santos",
     "teamId": "107", "league": "Brasileirao", "goals": 8,  "assists": 6,
     "transferValue": 15_000_000},
    # Regulares brasileiros
    {"id": "7",  "name": "Raphinha",               "teamName": "Barcelona",
     "teamId": "202", "league": "LaLiga",       "goals": 22, "assists": 16,
     "transferValue": 70_000_000},
    {"id": "8",  "name": "Gabriel Martinelli",     "teamName": "Arsenal",
     "teamId": "303", "league": "Premier League","goals": 15, "assists": 8,
     "transferValue": 75_000_000},
    {"id": "9",  "name": "Matheus Cunha",          "teamName": "Manchester United",
     "teamId": "307", "league": "Premier League","goals": 12, "assists": 7,
     "transferValue": 40_000_000},
    {"id": "10", "name": "Savinho",                "teamName": "Manchester City",
     "teamId": "304", "league": "Premier League","goals": 9,  "assists": 11,
     "transferValue": 45_000_000},
    {"id": "11", "name": "Estevao Willian",        "teamName": "Chelsea",
     "teamId": "311", "league": "Premier League","goals": 12, "assists": 10,
     "transferValue": 60_000_000},
    {"id": "12", "name": "Endrick Felipe",         "teamName": "Lyon",
     "teamId": "308", "league": "Ligue 1",      "goals": 8,  "assists": 3,
     "transferValue": 35_000_000},
    {"id": "13", "name": "Igor Jesus",             "teamName": "Nottingham Forest",
     "teamId": "309", "league": "Premier League","goals": 11, "assists": 5,
     "transferValue": 18_000_000},
    {"id": "14", "name": "Igor Thiago",            "teamName": "Brentford",
     "teamId": "310", "league": "Premier League","goals": 11, "assists": 4,
     "transferValue": 22_000_000},
    {"id": "15", "name": "Andreas Pereira",        "teamName": "Palmeiras",
     "teamId": "105", "league": "Brasileirao", "goals": 6,  "assists": 9,
     "transferValue": 15_000_000},
    # PediRatos brasileiros — superestimados
    {"id": "16", "name": "Vinicius Junior",        "teamName": "Real Madrid",
     "teamId": "201", "league": "LaLiga",       "goals": 9,  "assists": 7,
     "transferValue": 180_000_000},
    {"id": "17", "name": "Richarlison",            "teamName": "Tottenham",
     "teamId": "306", "league": "Premier League","goals": 5,  "assists": 2,
     "transferValue": 45_000_000},
    {"id": "18", "name": "Antony Matheus",         "teamName": "Real Betis",
     "teamId": "402", "league": "LaLiga",       "goals": 4,  "assists": 3,
     "transferValue": 30_000_000},
    {"id": "19", "name": "Gabriel Jesus",          "teamName": "Arsenal",
     "teamId": "303", "league": "Premier League","goals": 5,  "assists": 3,
     "transferValue": 40_000_000},
    {"id": "20", "name": "Casemiro",               "teamName": "Manchester United",
     "teamId": "307", "league": "Premier League","goals": 2,  "assists": 2,
     "transferValue": 20_000_000},
    {"id": "21", "name": "Joao Gomes",             "teamName": "Wolverhampton",
     "teamId": "302", "league": "Premier League","goals": 1,  "assists": 3,
     "transferValue": 28_000_000},
    # ── EUROPEUS FAMOSOS (9) ──────────────────────────────────────────────────
    # Pedigrees europeus
    {"id": "22", "name": "Lamine Yamal",           "teamName": "Barcelona",
     "teamId": "202", "league": "LaLiga",       "goals": 18, "assists": 16,
     "transferValue": 180_000_000},
    {"id": "23", "name": "Antoine Griezmann",      "teamName": "Atletico Madrid",
     "teamId": "401", "league": "LaLiga",       "goals": 16, "assists": 11,
     "transferValue": 20_000_000},
    {"id": "24", "name": "Bruno Fernandes",        "teamName": "Manchester United",
     "teamId": "307", "league": "Premier League","goals": 15, "assists": 17,
     "transferValue": 65_000_000},
    # Regulares europeus
    {"id": "25", "name": "Erling Haaland",         "teamName": "Manchester City",
     "teamId": "304", "league": "Premier League","goals": 27, "assists": 6,
     "transferValue": 200_000_000},
    {"id": "26", "name": "Lautaro Martinez",       "teamName": "Inter Milan",
     "teamId": "403", "league": "Serie A",      "goals": 20, "assists": 8,
     "transferValue": 110_000_000},
    {"id": "27", "name": "Pedri Gonzalez",         "teamName": "Barcelona",
     "teamId": "202", "league": "LaLiga",       "goals": 9,  "assists": 13,
     "transferValue": 90_000_000},
    # PediRatos europeus
    {"id": "28", "name": "Kylian Mbappe",          "teamName": "Real Madrid",
     "teamId": "201", "league": "LaLiga",       "goals": 18, "assists": 7,
     "transferValue": 250_000_000},
    {"id": "29", "name": "Jack Grealish",          "teamName": "Manchester City",
     "teamId": "304", "league": "Premier League","goals": 4,  "assists": 5,
     "transferValue": 75_000_000},
    {"id": "30", "name": "Riyad Mahrez",           "teamName": "Al Ahli",
     "teamId": "501", "league": "Saudi Pro League","goals": 5, "assists": 4,
     "transferValue": 12_000_000},
]


class BagreBackend:
    """
    Motor Central de Dados - Bagre.ai
    Integra múltiplas fontes: API-Football v3 (Gols/Assists) e Transfermarkt (Valores).
    """

    def __init__(self):
        # Suporta tanto chave direta da API-Sports quanto via RapidAPI
        api_key = os.getenv("RAPIDAPI_KEY", "").strip()
        self.season = os.getenv("SEASON", "2024").strip()
        
        # Chaves diretas da API-Sports possuem exatamente 32 caracteres hexadecimais
        import re
        if api_key and re.match(r"^[0-9a-f]{32}$", api_key):
            self.base_url = "https://v3.football.api-sports.io"
            self.headers = {
                "x-apisports-key": api_key,
            }
        else:
            self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
            self.headers = {
                "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
                "x-rapidapi-key": api_key,
            }

    def _executar_get(self, url, params=None, headers=None):
        """
        Gerenciador universal de requisições HTTP GET.
        Suporta diferentes headers para alternar entre APIs na RapidAPI.
        2 retries com 2s de delay entre tentativas; timeout de 10s por tentativa.
        """
        h = headers if headers else self.headers
        last_err = None
        for attempt in range(3):
            try:
                response = requests.get(url, headers=h, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                last_err = e
                if attempt < 2:
                    time.sleep(2)
        print(f"Falha na comunicação com o servidor após 3 tentativas: {last_err}")
        return None

    # ==========================================
    # MÓDULO I: FOOTBALL LIVE DATA (API-Football v3)
    # ==========================================

    def pesquisa_global(self, termo):
        """Busca abrangente por jogadores, clubes e ligas."""
        return self.buscar_jogador(termo)

    def buscar_jogador(self, nome_jogador):
        """Localiza o perfil e o ID único de um atleta na API-Football v3."""
        # Se a chave for placeholder, cai direto no mock para evitar erros 401
        api_key = self.headers.get("x-rapidapi-key") or self.headers.get("x-apisports-key") or ""
        if not api_key or "your_rapidapi_key_here" in api_key:
            return self._buscar_jogador_mock(nome_jogador)

        result = self._executar_get(f"{self.base_url}/players", {"search": nome_jogador, "season": self.season})
        if result and result.get("response"):
            suggestions = []
            for item in result["response"]:
                player = item.get("player", {})
                stats = item.get("statistics", [{}])[0] if item.get("statistics") else {}
                team = stats.get("team", {})
                league = stats.get("league", {})
                suggestions.append({
                    "id": player.get("id"),
                    "name": player.get("name"),
                    "teamName": team.get("name", ""),
                    "teamId": team.get("id"),
                    "league": league.get("name", ""),
                    "type": "player"
                })
            return {
                "status": "success",
                "response": {
                    "suggestions": suggestions
                }
            }
        return {
            "status": "success",
            "response": {
                "suggestions": []
            }
        }

    def _buscar_jogador_mock(self, nome_jogador):
        nome_lower = nome_jogador.lower()
        matches = [p for p in MOCK_PLAYERS if nome_lower in p["name"].lower()]
        return {
            "status": "success",
            "response": {
                "suggestions": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "teamName": p["teamName"],
                        "teamId": p["teamId"],
                        "type": "player",
                        "league": p["league"],
                    }
                    for p in matches
                ]
            },
        }

    def _obter_detalhes_jogador_mock(self, player_id):
        match = None
        for p in MOCK_PLAYERS:
            if str(p["id"]) == str(player_id):
                match = p
                break
        if not match:
            return None
        return {
            "response": [
                {
                    "player": {
                        "id": int(match["id"]) if str(match["id"]).isdigit() else match["id"],
                        "name": match["name"]
                    },
                    "statistics": [
                        {
                            "team": {
                                "id": int(match["teamId"]) if str(match["teamId"]).isdigit() else match["teamId"],
                                "name": match["teamName"]
                            },
                            "league": {
                                "name": match["league"]
                            },
                            "goals": {
                                "total": match["goals"],
                                "assists": match["assists"]
                            }
                        }
                    ]
                }
            ]
        }

    def obter_detalhes_jogador(self, player_id):
        """Recupera estatísticas do jogador por ID na API-Football v3."""
        api_key = self.headers.get("x-rapidapi-key") or self.headers.get("x-apisports-key") or ""
        if not api_key or "your_rapidapi_key_here" in api_key:
            return self._obter_detalhes_jogador_mock(player_id)
        
        result = self._executar_get(f"{self.base_url}/players", {"id": player_id, "season": self.season})
        if result and result.get("response"):
            return result
        return {"response": []}

    def obter_estatisticas_partida(self, event_id):
        """Coleta dados táticos detalhados de um jogo específico (mantido por compatibilidade)."""
        return self._executar_get(f"{self.base_url}/fixtures/statistics", {"fixture": event_id})

    # ==========================================
    # MÓDULO II: TRANSFERMARKT (FINANCEIRO & SCRAPER FALLBACK)
    # ==========================================

    def obter_valor_mercado_scraped(self, nome_jogador):
        """
        [Opção A] Scraper Nativo do Transfermarkt (Fallback de emergência)
        Extrai o valor de mercado a partir da página de busca clássica que não usa Svelte.
        """
        headers_sc = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche"
        params = {"query": nome_jogador}
        
        try:
            from bs4 import BeautifulSoup
            response = requests.get(url, headers=headers_sc, params=params, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                tables = soup.find_all("table")
                if tables:
                    table = tables[0]
                    rows = table.find_all("tr")
                    for row in rows[1:]:
                        cells = row.find_all(["td", "th"])
                        for cell in cells:
                            text = cell.text.strip()
                            if text.startswith("€") or text == "-":
                                print(f"[SCRAPER ✓] Transfermarkt Scraped: '{nome_jogador}' = {text}")
                                return {
                                    "response": {
                                        "players": [
                                            {
                                                "marketValue": text
                                            }
                                        ]
                                    }
                                }
        except Exception as e:
            print(f"[SCRAPER WARN] Erro ao raspar Transfermarkt: {e}")
        return None

    def obter_valor_mercado(self, nome_jogador):
        """
        Consulta o valor de mercado atualizado via API do Transfermarkt (RapidAPI).
        Cai automaticamente no Scraper Nativo (Opção A) se a chave for inválida ou falhar.
        """
        # Se for chave direta da API-Sports, não funciona na RapidAPI do Transfermarkt; cai no scraper
        if "x-apisports-key" in self.headers:
            return self.obter_valor_mercado_scraped(nome_jogador)

        api_key = self.headers.get("x-rapidapi-key", "")
        if not api_key or "your_rapidapi_key_here" in api_key:
            return self.obter_valor_mercado_scraped(nome_jogador)

        url = "https://transfermarkt.p.rapidapi.com/players/search"
        headers_tm = {
            "x-rapidapi-host": "transfermarkt.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }
        result = self._executar_get(url, params={"query": nome_jogador}, headers=headers_tm)
        if result and result.get("response", {}).get("players"):
            return result
            
        # Fallback para o scraper próprio
        return self.obter_valor_mercado_scraped(nome_jogador)

    # ==========================================
    # MÓDULO III: FBREF (SCOUTING AVANÇADO)
    # ==========================================

    def obter_tabela_fbref(self, url_atleta):
        """
        Captura tabelas de performance diretamente do FBref (mantido para compatibilidade).
        """
        try:
            from io import StringIO
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            response = requests.get(url_atleta, headers=headers, timeout=15)
            response.raise_for_status()
            tabelas = pd.read_html(StringIO(response.text))
            return tabelas[0] if tabelas else pd.DataFrame()
        except Exception as e:
            print(f"Erro ao processar dados do FBref: {e}")
            return pd.DataFrame()

    def buscar_stats_fbref(self, nome_jogador):
        """
        Tenta buscar gols e assists no FBref via redirect (mantido para compatibilidade).
        """
        try:
            from io import StringIO
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            response = requests.get(
                "https://fbref.com/en/search/search.fcgi",
                params={"search": nome_jogador},
                headers=headers,
                timeout=10,
                allow_redirects=True,
            )
            response.raise_for_status()
            if "/en/players/" not in response.url:
                return None
            tabelas = pd.read_html(StringIO(response.text))
            for df in tabelas:
                if "Gls" in df.columns and "Ast" in df.columns:
                    try:
                        return int(df["Gls"].iloc[0]), int(df["Ast"].iloc[0])
                    except Exception:
                        continue
            return None
        except Exception as e:
            print(f"FBref indisponível: {e}")
            return None

    # ==========================================
    # MÓDULO IV: UTILITÁRIOS DE ELENCO
    # ==========================================

    def listar_elenco_clube(self, team_id):
        """
        Lista jogadores vinculados a um ID de time com suas estatísticas de Gols e Assists.
        Usa o endpoint /players da API-Football v3 restringindo por clube e temporada.
        """
        api_key = self.headers.get("x-rapidapi-key") or self.headers.get("x-apisports-key") or ""
        if not api_key or "your_rapidapi_key_here" in api_key:
            return self._listar_elenco_clube_mock(team_id)

        result = self._executar_get(f"{self.base_url}/players", {"team": team_id, "season": self.season})
        if result and result.get("response"):
            members = []
            for item in result["response"]:
                player = item.get("player", {})
                stats = item.get("statistics", [{}])[0] if item.get("statistics") else {}
                goals = stats.get("goals", {})
                members.append({
                    "id": player.get("id"),
                    "name": player.get("name"),
                    "teamName": stats.get("team", {}).get("name", ""),
                    "goals": goals.get("total") or 0,
                    "assists": goals.get("assists") or 0,
                    "transferValue": 0, # Será resolvido pelo scraper do Transfermarkt
                    "league": stats.get("league", {}).get("name", ""),
                })
            return {"response": {"squad": [{"members": members}]}}

        return {"response": {"squad": [{"members": []}]}}

    def _listar_elenco_clube_mock(self, team_id):
        members = [
            {
                "id": p["id"],
                "name": p["name"],
                "teamName": p["teamName"],
                "goals": p["goals"],
                "assists": p["assists"],
                "transferValue": p["transferValue"],
                "league": p["league"],
            }
            for p in MOCK_PLAYERS if str(p["teamId"]) == str(team_id)
        ]
        return {"response": {"squad": [{"members": members}]}}


if __name__ == "__main__":
    casos = [
        ('€15m',   15_000_000.0),
        ('€500k',  500_000.0),
        ('€1.2m',  1_200_000.0),
        ('-',      0.0),
        ('',       0.0),
    ]
    print("=== Testes clean_currency ===")
    todos_ok = True
    for entrada, esperado in casos:
        resultado = clean_currency(entrada)
        status = "OK" if resultado == esperado else "FAIL"
        if status == "FAIL":
            todos_ok = False
        print(f"  [{status}] clean_currency({entrada!r}) = {resultado} (esperado: {esperado})")
    print("Todos os testes passaram!" if todos_ok else "ATENÇÃO: há falhas nos testes.")
    print()

    motor = BagreBackend()
    print("Iniciando validação do motor...")
    teste = motor.buscar_jogador("Arrascaeta")
    if teste and teste.get("status") == "success":
        print("Backend Bagre.ai operacional: Pronto para integração múltipla.")
    else:
        print("Aviso: Verifique a conectividade ou validade da API Key.")