import pandas as pd
from bagre_analytics import analisar_hype_index
import os

df = pd.DataFrame([
    {"nome": "A", "valor_milhoes": 10, "gols": 5, "assists": 2},
    {"nome": "B", "valor_milhoes": 20, "gols": 8, "assists": 3},
    {"nome": "C", "valor_milhoes": 15, "gols": 6, "assists": 1}
])

try:
    print("Iniciando analise...")
    res = analisar_hype_index(df)
    print("Analise concluida!")
    print(res.columns)
except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
