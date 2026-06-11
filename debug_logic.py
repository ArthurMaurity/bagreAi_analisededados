import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def analisar_hype_index_debug(df: pd.DataFrame):
    try:
        print("1. Iniciando processamento...")
        df = df.copy().reset_index(drop=True)
        df["performance"] = df["gols"] + df["assists"]
        print("2. Performance calculada.")

        X = df[["performance"]].values
        y = df["valor_milhoes"].values.astype(float)

        print("3. Treinando modelo...")
        modelo = LinearRegression()
        modelo.fit(X, y)

        print("4. Realizando previsões...")
        preds = modelo.predict(X).flatten()
        df["valor_previsto"] = np.round(preds, 2)
        df["residuo"] = np.round(df["valor_milhoes"] - df["valor_previsto"], 2)

        print("5. Classificando...")
        std = float(df["residuo"].std())
        if np.isnan(std) or std == 0:
            std = 0.001
            
        df["classificacao"] = df["residuo"].apply(
            lambda r: "PediRato" if r > std else ("Pedigree" if r < -std else "Regular")
        )
        print("6. Sucesso!")
        return df
    except Exception as e:
        print(f"!!! ERRO NA FUNCAO: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_df = pd.DataFrame([
        {"nome": "A", "valor_milhoes": 10, "gols": 5, "assists": 2},
        {"nome": "B", "valor_milhoes": 20, "gols": 8, "assists": 3},
        {"nome": "C", "valor_milhoes": 15, "gols": 6, "assists": 1}
    ])
    res = analisar_hype_index_debug(test_df)
    print(res)
