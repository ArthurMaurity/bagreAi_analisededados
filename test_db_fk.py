import sqlite3
try:
    conn = sqlite3.connect('bagre.db')
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO analises (usuario_id, tipo, input_json, output_json, criado_em) VALUES (0, 'test', '{}', '{}', '2024-01-01')")
    conn.commit()
    print("Sucesso ao inserir ID 0")
except Exception as e:
    print(f"Erro ao inserir ID 0: {e}")
finally:
    conn.close()
