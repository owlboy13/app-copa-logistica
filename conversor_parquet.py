import pandas as pd
from datetime import time
  
def timedelta_para_time(td):
    """Converte timedelta para datetime.time"""
    if pd.isna(td):
        return None
    # Se já for time, retorna como está
    if isinstance(td, time):
        return td
    # Se for timedelta, converte
    if hasattr(td, 'total_seconds'):
        total_seg = int(td.total_seconds())
        horas = total_seg // 3600
        minutos = (total_seg % 3600) // 60
        segundos = total_seg % 60
        return time(horas, minutos, segundos)
    return td

df = pd.read_excel('data/base.xlsx')
df.to_parquet('data/base.parquet', index=False)

df = pd.read_excel('data/perfomance.xlsx')

# Converter colunas de tempo de timedelta para datetime.time
colunas_tempo = ['duracao_do_periodo', 'tempo_disponivel_absoluto']
for col in colunas_tempo:
    if col in df.columns:
        df[col] = df[col].apply(timedelta_para_time)

df.to_parquet('data/perfomance.parquet', index=False)


df = pd.read_excel('data/jogos_copa.xlsx')
df['data_jogo'] = pd.to_datetime(df['data_jogo']).dt.date
df.to_parquet('data/jogos_copa.parquet', index=False)

df = pd.read_excel('data/bolao_participantes.xlsx')
if 'data_participacao' in df.columns and not df.empty:
    df['data_participacao'] = pd.to_datetime(df['data_participacao']).dt.date
df.to_parquet('data/bolao_participantes.parquet', index=False)

