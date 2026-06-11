import pandas as pd
import sqlite3
import json
import os
import unicodedata
from datetime import datetime

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).lower().strip()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return texto

def limpar_e_moldar():
    csv_path = "importar_dataset - Página1.csv"
    if not os.path.exists(csv_path):
        print(f"Erro: Arquivo {csv_path} não encontrado.")
        return

    # 1. Carregar CSV
    df = pd.read_csv(csv_path)
    
    # 2. Conectar ao banco para buscar stats existentes (enriquecimento)
    conn = sqlite3.connect("bagre.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT nome_normalizado, dados_json FROM jogadores_cache")
    cache_existente = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
    
    jogadores_moldados = []
    agora = datetime.now().isoformat()
    
    print(f"Processando {len(df)} jogadores do CSV...")
    
    for _, row in df.iterrows():
        nome_original = row["player_name"]
        nome_norm = normalizar_texto(nome_original)
        
        # Valor em milhões
        valor_eur = float(row["market_value_eur"]) if not pd.isna(row["market_value_eur"]) else 0
        valor_milhoes = valor_eur / 1_000_000
        
        # Tenta buscar stats do cache
        stats_cache = cache_existente.get(nome_norm, {})
        gols = stats_cache.get("gols", 0)
        assists = stats_cache.get("assists", 0)
        
        # Cálculo de PediRato
        v_calc = max(valor_milhoes, 0.1)
        pedirato = (gols + assists) / v_calc
        
        # Ranking
        if pedirato > 1.5: ranking = "Pedigree"
        elif pedirato > 0.5: ranking = "Regular"
        else: ranking = "PediRato"
        
        dados_json = {
            "status": "success",
            "nome": nome_original,
            "clube": row["club_name"],
            "liga": row["domestic_competition_id"],
            "idade": int(row["age"]) if not pd.isna(row["age"]) else 0,
            "gols": gols,
            "assists": assists,
            "valor_milhoes": valor_milhoes,
            "pedirato": round(pedirato, 2),
            "ranking_contexto": ranking,
            "fonte": "csv_import_enriquecido" if stats_cache else "csv_import"
        }
        
        jogadores_moldados.append((nome_norm, json.dumps(dados_json, ensure_ascii=False), agora))

    # 3. Inserir/Atualizar no banco
    print(f"Inserindo {len(jogadores_moldados)} jogadores no banco de dados...")
    cursor.executemany(
        "INSERT INTO jogadores_cache (nome_normalizado, dados_json, atualizado_em) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(nome_normalizado) DO UPDATE SET "
        "dados_json = excluded.dados_json, atualizado_em = excluded.atualizado_em",
        jogadores_moldados
    )
    
    conn.commit()
    conn.close()
    print("Sucesso! Banco de dados atualizado com os novos jogadores do CSV.")

if __name__ == "__main__":
    limpar_e_moldar()
