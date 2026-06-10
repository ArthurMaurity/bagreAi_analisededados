"""
bagre_database.py - Persistencia SQLite para o Bagre.ai
Sem dependencias externas: usa apenas sqlite3 nativo do Python.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from typing import Optional
import os
import sqlite3
import uuid
import json
from datetime import datetime, date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DB_PATH = os.getenv("DATABASE_PATH", "bagre.db")

LIMITES = {
    "varzea":  5,
    "olheiro": 50,
    "diretor": -1,   # ilimitado
}

# Normaliza o plano para chave sem acento (usado internamente)
def _chave_plano(plano: str) -> str:
    return plano.replace("á", "a").replace("é", "e")


class BagreDatabase:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._inicializar()

    # ── CONEXÃO ────────────────────────────────────────────────────────────────
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ── CRIAÇÃO DAS TABELAS ────────────────────────────────────────────────────
    def _inicializar(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    email           TEXT    UNIQUE NOT NULL,
                    nome            TEXT    NOT NULL,
                    plano           TEXT    NOT NULL,
                    api_key         TEXT    UNIQUE NOT NULL,
                    criado_em       TEXT    NOT NULL,
                    requests_hoje   INTEGER NOT NULL DEFAULT 0,
                    data_requests   TEXT    NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS analises (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id  INTEGER NOT NULL,
                    tipo        TEXT    NOT NULL,
                    input_json  TEXT    NOT NULL,
                    output_json TEXT    NOT NULL,
                    criado_em   TEXT    NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                );

                CREATE TABLE IF NOT EXISTS jogadores_cache (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_normalizado TEXT    UNIQUE NOT NULL,
                    dados_json       TEXT    NOT NULL,
                    atualizado_em    TEXT    NOT NULL
                );
            """)

        self._seed_usuarios()
        removidos = self.limpar_cache_invalido()
        if removidos:
            print(f"[DB] {removidos} entrada(s) de cache inválido removida(s).")

    # ── SEED DE USUÁRIOS DE TESTE ──────────────────────────────────────────────
    def _seed_usuarios(self):
        seeds = [
            ("teste_free@bagre.ai",     "Usuario Varzea",   "varzea"),
            ("teste_olheiro@bagre.ai",  "Usuario Olheiro",  "olheiro"),
            ("teste_diretor@bagre.ai",  "Usuario Diretor",  "diretor"),
        ]
        with self._conn() as conn:
            existentes = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
            if existentes > 0:
                return

            print("\n" + "=" * 56)
            print("  BAGRE.AI — Primeira inicializacao do banco de dados")
            print("=" * 56)
            for email, nome, plano in seeds:
                api_key = self.criar_usuario(email, nome, plano)
                print(f"  [{plano.upper():>8}]  {email}")
                print(f"             API KEY: {api_key}\n")
            print("=" * 56 + "\n")

    # ── USUÁRIOS ───────────────────────────────────────────────────────────────
    def criar_usuario(self, email: str, nome: str, plano: str) -> str:
        """Cria usuario e retorna api_key (uuid4)."""
        api_key   = str(uuid.uuid4())
        criado_em = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO usuarios (email, nome, plano, api_key, criado_em) "
                "VALUES (?, ?, ?, ?, ?)",
                (email, nome, plano, api_key, criado_em),
            )
        return api_key

    def autenticar(self, api_key: str) -> Optional[dict]:
        """Retorna dict do usuario ou None se api_key invalida."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM usuarios WHERE api_key = ?", (api_key,)
            ).fetchone()
        return dict(row) if row else None

    # ── LIMITES ────────────────────────────────────────────────────────────────
    def verificar_limite(self, usuario_id: int) -> bool:
        """
        Retorna True se o usuario ainda pode fazer requests hoje.
        Reseta o contador automaticamente quando a data muda.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT plano, requests_hoje, data_requests FROM usuarios WHERE id = ?",
                (usuario_id,),
            ).fetchone()
            if not row:
                return False

            plano          = row["plano"]
            requests_hoje  = row["requests_hoje"]
            data_requests  = row["data_requests"]
            hoje           = date.today().isoformat()

            # Resetar contador se virou o dia
            if data_requests != hoje:
                conn.execute(
                    "UPDATE usuarios SET requests_hoje = 0, data_requests = ? WHERE id = ?",
                    (hoje, usuario_id),
                )
                requests_hoje = 0

            limite = LIMITES.get(_chave_plano(plano), 0)
            return limite == -1 or requests_hoje < limite

    def _incrementar_requests(self, usuario_id: int):
        hoje = date.today().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE usuarios "
                "SET requests_hoje = requests_hoje + 1, data_requests = ? "
                "WHERE id = ?",
                (hoje, usuario_id),
            )

    # ── ANÁLISES ───────────────────────────────────────────────────────────────
    def salvar_analise(self, usuario_id: int, tipo: str, input_data: dict, output_data: dict):
        """Persiste uma analise e incrementa o contador de requests para scouts."""
        criado_em   = datetime.now().isoformat()
        input_json  = json.dumps(input_data,  ensure_ascii=False)
        output_json = json.dumps(output_data, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO analises (usuario_id, tipo, input_json, output_json, criado_em) "
                "VALUES (?, ?, ?, ?, ?)",
                (usuario_id, tipo, input_json, output_json, criado_em),
            )
        if tipo == "scout":
            self._incrementar_requests(usuario_id)

    def get_historico(self, usuario_id: int, limite: int = 10) -> list:
        """Retorna as ultimas `limite` analises do usuario."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, tipo, input_json, output_json, criado_em "
                "FROM analises WHERE usuario_id = ? "
                "ORDER BY criado_em DESC LIMIT ?",
                (usuario_id, limite),
            ).fetchall()
        return [
            {
                "id":         r["id"],
                "tipo":       r["tipo"],
                "input":      json.loads(r["input_json"]),
                "output":     json.loads(r["output_json"]),
                "criado_em":  r["criado_em"],
            }
            for r in rows
        ]

    # ── CACHE DE JOGADORES ─────────────────────────────────────────────────────
    def buscar_cache(self, nome_normalizado: str) -> Optional[dict]:
        """
        Retorna dados em cache se existirem e tiverem menos de 24h.
        Retorna None se expirado ou inexistente.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT dados_json, atualizado_em FROM jogadores_cache "
                "WHERE nome_normalizado = ?",
                (nome_normalizado,),
            ).fetchone()
        if not row:
            return None

        atualizado_em = datetime.fromisoformat(row["atualizado_em"])
        delta = datetime.now() - atualizado_em
        if delta.total_seconds() > 86_400:   # 24 horas
            return None

        return json.loads(row["dados_json"])

    def buscar_cache_stale(self, nome_normalizado: str) -> Optional[dict]:
        """Retorna dados em cache ignorando o limite de 24h (fallback de último recurso)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT dados_json FROM jogadores_cache WHERE nome_normalizado = ?",
                (nome_normalizado,),
            ).fetchone()
        return json.loads(row["dados_json"]) if row else None

    def salvar_cache(self, nome: str, dados: dict):
        """Insere ou atualiza o cache de um jogador."""
        agora = datetime.now().isoformat()
        dados_json = json.dumps(dados, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO jogadores_cache (nome_normalizado, dados_json, atualizado_em) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(nome_normalizado) DO UPDATE SET "
                "dados_json = excluded.dados_json, atualizado_em = excluded.atualizado_em",
                (nome, dados_json, agora),
            )

    def limpar_cache_invalido(self) -> int:
        """
        Remove entradas de cache com gols=0, assists=0 e pedirato=0 —
        resultados de lookups fracassados que foram acidentalmente persistidos.
        Retorna o número de linhas removidas.
        """
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, dados_json FROM jogadores_cache"
            ).fetchall()
            ids_invalidos = []
            for row in rows:
                try:
                    d = json.loads(row["dados_json"])
                    if (
                        d.get("gols", 1) == 0
                        and d.get("assists", 1) == 0
                        and d.get("pedirato", 1) == 0
                    ):
                        ids_invalidos.append(row["id"])
                except Exception:
                    pass
            if ids_invalidos:
                conn.execute(
                    f"DELETE FROM jogadores_cache WHERE id IN "
                    f"({','.join('?' * len(ids_invalidos))})",
                    ids_invalidos,
                )
        return len(ids_invalidos)


# ── INICIALIZAÇÃO STANDALONE ───────────────────────────────────────────────────
if __name__ == "__main__":
    db_file = DB_PATH
    primeira_vez = not os.path.exists(db_file)

    db = BagreDatabase()

    if not primeira_vez:
        print("Banco ja existente. Listando usuarios:")
        with db._conn() as conn:
            rows = conn.execute(
                "SELECT id, email, plano, api_key, requests_hoje FROM usuarios"
            ).fetchall()
        for r in rows:
            print(f"  [{r['plano'].upper():>8}]  {r['email']}")
            print(f"             API KEY: {r['api_key']}")
            print(f"             Requests hoje: {r['requests_hoje']}\n")
