import requests
import pandas as pd
import json

class BagreBackend:
    """
    Motor Central de Dados - Bagre.ai
    Integra múltiplas fontes: RapidAPI (Live Data), Transfermarkt e FBref.
    """
    
    def __init__(self):
        # Configurações de autenticação e endpoints base
        self.base_url = "https://free-api-live-football-data.p.rapidapi.com"
        self.headers = {
            "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
            "x-rapidapi-key": "4a59c92d94msh556847df4740a06p1ac94ajsn08537f3f721a"
        }

    def _executar_get(self, url, params=None, headers=None):
        """
        Gerenciador universal de requisições HTTP GET.
        Suporta diferentes headers para alternar entre APIs na RapidAPI.
        """
        try:
            h = headers if headers else self.headers
            response = requests.get(url, headers=h, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Falha na comunicação com o servidor: {e}")
            return None

    # ==========================================
    # MÓDULO I: FOOTBALL LIVE DATA
    # ==========================================

    def pesquisa_global(self, termo):
        """Busca abrangente por jogadores, clubes e ligas."""
        return self._executar_get(f"{self.base_url}/football-all-search", {"search": termo})

    def buscar_jogador(self, nome_jogador):
        """Localiza o perfil e o ID único de um atleta."""
        return self._executar_get(f"{self.base_url}/football-players-search", {"search": nome_jogador})

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
        """Lista todos os jogadores vinculados a um ID de time."""
        return self._executar_get(f"{self.base_url}/football-get-list-player", {"teamid": team_id})

# --- BLOCO DE VALIDAÇÃO DO SISTEMA ---
if __name__ == "__main__":
    motor = BagreBackend()
    print("Iniciando validação do motor multicloud...")
    
    # Teste simples de conectividade
    teste = motor.buscar_jogador("Arrascaeta")
    if teste and teste.get("status") == "success":
        print("Backend Bagre.ai operacional: Pronto para integração múltipla.")
    else:
        print("Aviso: Verifique a conectividade ou validade da API Key.")