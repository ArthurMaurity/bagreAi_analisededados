"""
bagre_auth.py - Controle de acesso por tier para o Bagre.ai
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from bagre_database import BagreDatabase

# Mapeamento: funcionalidade → planos que têm acesso
FUNCIONALIDADES: dict[str, list[str]] = {
    "scout":             ["varzea", "olheiro", "diretor"],
    "hype_index":        ["olheiro", "diretor"],
    "espelho_pedigree":  ["olheiro", "diretor"],
    "gini":              ["diretor"],
    "ciclo_vida":        ["diretor"],
    "relatorio_docx":    ["diretor"],
}

DESCRICAO_PLANO = {
    "varzea":  "Várzea (gratuito)  — 5 scouts/dia, sem analytics avancados",
    "olheiro": "Olheiro (R$29,90)  — 50 scouts/dia, Hype Index e Espelho Pedigree",
    "diretor": "Diretor (R$997,00) — ilimitado, acesso total",
}

_db = BagreDatabase()


def _chave_plano(plano: str) -> str:
    return plano.replace("á", "a").replace("é", "e")


def verificar_acesso(api_key: str, funcionalidade: str) -> tuple[bool, str]:
    """
    Verifica se a api_key tem acesso à funcionalidade solicitada.

    Retorna:
        (True,  "Acesso permitido.")          → pode prosseguir
        (False, "<motivo legível>")           → bloquear com a mensagem
    """
    usuario = _db.autenticar(api_key)
    if usuario is None:
        return False, "API key inválida ou não encontrada."

    plano      = usuario["plano"]
    plano_key  = _chave_plano(plano)
    permitidos = FUNCIONALIDADES.get(funcionalidade, [])

    if plano_key not in permitidos:
        tiers_ok = " e ".join(
            DESCRICAO_PLANO.get(p, p).split("—")[0].strip()
            for p in permitidos
        )
        return (
            False,
            f"Funcionalidade '{funcionalidade}' não disponível no plano {plano}. "
            f"Requer: {tiers_ok}.",
        )

    # Para scouts, verificar limite diário
    if funcionalidade == "scout":
        if not _db.verificar_limite(usuario["id"]):
            from bagre_database import LIMITES
            lim = LIMITES.get(plano_key, 0)
            return (
                False,
                f"Limite diário de {lim} scouts atingido para o plano {plano}. "
                f"Renova à meia-noite ou faça upgrade.",
            )

    return True, "Acesso permitido."


def info_plano(api_key: str) -> dict | None:
    """Retorna informações do plano do usuário ou None se api_key inválida."""
    from bagre_database import LIMITES
    usuario = _db.autenticar(api_key)
    if not usuario:
        return None

    plano_key   = _chave_plano(usuario["plano"])
    limite_dia  = LIMITES.get(plano_key, 0)
    funcoes_ok  = [f for f, planos in FUNCIONALIDADES.items() if plano_key in planos]

    return {
        "email":          usuario["email"],
        "nome":           usuario["nome"],
        "plano":          usuario["plano"],
        "limite_dia":     "ilimitado" if limite_dia == -1 else limite_dia,
        "requests_hoje":  usuario["requests_hoje"],
        "funcionalidades": funcoes_ok,
    }


# ── DEMONSTRAÇÃO ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sqlite3

    # Buscar api_keys dos usuários de teste
    conn = sqlite3.connect("bagre.db")
    conn.row_factory = sqlite3.Row
    usuarios = conn.execute("SELECT email, plano, api_key FROM usuarios").fetchall()
    conn.close()

    print("\n" + "=" * 60)
    print("  BAGRE.AI — Teste de Controle de Acesso")
    print("=" * 60)

    funcoes_teste = [
        "scout", "hype_index", "espelho_pedigree",
        "gini", "ciclo_vida", "relatorio_docx",
    ]

    for u in usuarios:
        print(f"\n  Usuário: {u['email']}  [{u['plano'].upper()}]")
        print(f"  API KEY: {u['api_key']}")
        print(f"  {'Funcionalidade':<22} {'Acesso':>8}  Motivo")
        print("  " + "-" * 55)
        for func in funcoes_teste:
            ok, motivo = verificar_acesso(u["api_key"], func)
            status = "OK" if ok else "NEGADO"
            msg    = "Permitido" if ok else motivo.split(".")[0]
            print(f"  {func:<22} {status:>8}  {msg}")
