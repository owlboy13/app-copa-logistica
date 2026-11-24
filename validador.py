import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

class Validador:
    def __init__(self, value) -> None:
        self.value = value

    def validando_rotas(self):
        if not self.value == None:
            try:
                db_parquet = pd.read_excel(f"{DATA_DIR}/{self.value}.xlsx")
                dataframe = pd.DataFrame(db_parquet)
                df_soma_rotas = dataframe.groupby(
                    'pessoa_entregadora')['numero_de_corridas_completadas'
                                          ].sum()
                
                return df_soma_rotas.sort_values(ascending=False).head(10)
                
            except Exception as e:
                print(f"Erro na validação de rotas {e}")

        return None
    
if __name__ == '__main__':
    v1 = Validador('perfomance')

    print(v1.validando_rotas())

