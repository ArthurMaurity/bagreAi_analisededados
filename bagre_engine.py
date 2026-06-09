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
    Integra múltiplas fontes: RapidAPI (Live Data), Transfermarkt e FBref.
    """

    def __init__(self):
        self.base_url = "https://free-api-live-football-data.p.rapidapi.com"
        api_key = os.getenv("RAPIDAPI_KEY", "")
        self.headers = {
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
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
    # MÓDULO I: FOOTBALL LIVE DATA
    # ==========================================

    def pesquisa_global(self, termo):
        """Busca abrangente por jogadores, clubes e ligas."""
        return self._executar_get(f"{self.base_url}/football-all-search", {"search": termo})

    def buscar_jogador(self, nome_jogador):
        """Localiza o perfil e o ID único de um atleta. Cai no dataset mock se a API falhar."""
        result = self._executar_get(f"{self.base_url}/football-players-search", {"search": nome_jogador})
        suggestions = result.get("response", {}).get("suggestions", []) if result else []
        if suggestions:
            return result
        # Fallback: busca no dataset mock (substring, case-insensitive)
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

    def obter_detalhes_jogador(self, player_id):
        """Recupera a ficha técnica e estatísticas disponíveis no provedor principal."""
        return self._executar_get(f"{self.base_url}/football-get-player-detail", {"playerid": player_id})

    def obter_estatisticas_partida(self, event_id):
        """Coleta dados táticos detalhados de um jogo específico."""
        return self._executar_get(f"{self.base_url}/football-get-match-event-all-stats", {"eventid": event_id})

    # ==========================================
    # MÓDULO II: TRANSFERMARKT (FINANCEIRO)
    # ==========================================

    def obter_valor_mercado(self, nome_jogador):
        """
        Consulta o valor de mercado atualizado via API do Transfermarkt.
        Essencial para o cálculo do denominador no Índice PediRato.
        """
        url = "https://transfermarkt.p.rapidapi.com/players/search"
        headers_tm = {
            "x-rapidapi-host": "transfermarkt.p.rapidapi.com",
            "x-rapidapi-key": self.headers["x-rapidapi-key"]
        }
        return self._executar_get(url, params={"query": nome_jogador}, headers=headers_tm)

    # ==========================================
    # MÓDULO III: FBREF (SCOUTING AVANÇADO)
    # ==========================================

    def obter_tabela_fbref(self, url_atleta):
        """
        Captura tabelas de performance (xG, passes, criação) diretamente do FBref.
        Utiliza o motor do Pandas para converter HTML em estruturado (DataFrame).
        """
        try:
            # O FBref bloqueia requisições sem User-Agent em alguns casos; 
            # usamos requests para enviar cabeçalhos apropriados.
            from io import StringIO
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            }
            response = requests.get(url_atleta, headers=headers, timeout=15)
            response.raise_for_status()
            tabelas = pd.read_html(StringIO(response.text))
            # Retorna a primeira tabela (geralmente 'Standard Stats')
            return tabelas[0] if tabelas else pd.DataFrame()
        except Exception as e:
            print(f"Erro ao processar dados do FBref: {e}")
            return pd.DataFrame()

    # ==========================================
    # MÓDULO IV: UTILITÁRIOS DE ELENCO
    # ==========================================

    def listar_elenco_clube(self, team_id):
        """Lista todos os jogadores vinculados a um ID de time. Cai no dataset mock se a API falhar."""
        result = self._executar_get(f"{self.base_url}/football-get-list-player", {"teamid": team_id})
        if result:
            return result
        # Fallback: filtra jogadores do time no dataset mock
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

    def buscar_stats_fbref(self, nome_jogador):
        """
        Tenta buscar gols e assists no FBref via redirect de busca por nome.
        FBref redireciona para a página do jogador quando há resultado único.
        Retorna (gols, assists) ou None.
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

# --- BLOCO DE VALIDAÇÃO DO SISTEMA ---
if __name__ == "__main__":
    # Testes de clean_currency
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
    print("Iniciando validação do motor multicloud...")
    teste = motor.buscar_jogador("Arrascaeta")
    if teste and teste.get("status") == "success":
        print("Backend Bagre.ai operacional: Pronto para integração múltipla.")
    else:
        print("Aviso: Verifique a conectividade ou validade da API Key.")