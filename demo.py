from datetime import time
from pathlib import Path
import random
import uuid
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def formatar_cpf(digitos: str) -> str:
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


nomes = [
    "Carlos Eduardo Silva", "Lucas Gabriel Santos", "Rafael Oliveira",
    "Mateus Souza", "Bruno Henrique Lima", "Diego Ferreira",
    "Thiago Alves", "Gabriel Costa", "Felipe Rodrigues", "Rodrigo Pereira",
    "André Luiz Martins", "Gustavo Rocha", "Marcelo Carvalho", "Leonardo Gomes",
    "Vinícius Ribeiro", "Eduardo Almeida", "Caio Nascimento", "Henrique Araújo",
    "Renato Barbosa", "Alexandre Monteiro", "Daniel Cardoso", "Igor Teixeira",
    "Fábio Correia", "João Pedro Mendes", "Pedro Henrique Dias"
]

# 1. base_entregadores.parquet
entregadores = []
for i, nome in enumerate(nomes):
    cpf_limpo = "11111111111" if i == 0 else f"{10000000000 + i * 1234567:011d}"[:11]
    entregadores.append({
        "ID": str(uuid.uuid4()),
        "Nome": nome,
        "CPF": cpf_limpo,
        "Modal": random.choice(["Moto", "Moto", "Moto", "Bike"]),
        "ELITE": "SIM" if i % 3 == 0 else "NÃO",
    })

df_base = pd.DataFrame(entregadores)
df_base.to_parquet(DATA_DIR / "base.parquet", index=False)

# 2. jogos_copa.parquet (mesma estrutura e tipos de jogos_copa.xlsx)
jogos = [
    {
        "id": 1,
        "data_jogo": pd.Timestamp("2026-06-13"),
        "horario_inicio": time(19, 0, 0),
        "horario_fim": time(21, 0, 0),
        "time_casa": "Brasil",
        "time_visitante": "Marrocos",
        "fase": "Fase de grupo",
        "jogo_brasil": True,
        "jogo_final": False,
    },
    {
        "id": 2,
        "data_jogo": pd.Timestamp("2026-06-19"),
        "horario_inicio": time(22, 0, 0),
        "horario_fim": time(23, 59, 0),
        "time_casa": "Brasil",
        "time_visitante": "Haiti",
        "fase": "Fase de grupo",
        "jogo_brasil": True,
        "jogo_final": False,
    },
    {
        "id": 3,
        "data_jogo": pd.Timestamp("2026-06-24"),
        "horario_inicio": time(19, 0, 0),
        "horario_fim": time(21, 0, 0),
        "time_casa": "Escócia",
        "time_visitante": "Brasil",
        "fase": "Fase de grupo",
        "jogo_brasil": True,
        "jogo_final": False,
    },
    {
        "id": 4,
        "data_jogo": pd.Timestamp("2026-07-19"),
        "horario_inicio": time(16, 0, 0),
        "horario_fim": time(18, 30, 0),
        "time_casa": "Brasil",
        "time_visitante": "Finalista",
        "fase": "Final",
        "jogo_brasil": True,
        "jogo_final": True,
    },
]
df_jogos = pd.DataFrame(jogos)
df_jogos.to_parquet(DATA_DIR / "jogos_copa.parquet", index=False)

# 3. bolao_participantes.parquet (cpf formatado XXX.XXX.XXX-XX como na planilha original)
datas_bolao = [
    pd.Timestamp("2026-06-12"),
    pd.Timestamp("2026-06-18"),
    pd.Timestamp("2026-06-23"),
    pd.Timestamp("2026-07-18"),
]
participacoes = []
for _, ent in df_base.iterrows():
    cpf_fmt = formatar_cpf(ent["CPF"])
    for dt_b in random.sample(datas_bolao, k=random.randint(2, 4)):
        participacoes.append({
            "cpf": cpf_fmt,
            "data_participacao": dt_b,
            "pontos_bolao": 1,
        })

df_bolao = pd.DataFrame(participacoes)
df_bolao.to_parquet(DATA_DIR / "bolao_participantes.parquet", index=False)

# 4. perfomance_entregadores.parquet
datas_turnos = pd.date_range("2026-06-08", "2026-07-19", freq="D")
turnos = []
for _, ent in df_base.iterrows():
    dias_trabalhados = set(random.sample(list(datas_turnos), k=random.randint(20, 32)))
    dias_trabalhados.update([
        pd.Timestamp("2026-06-13"),
        pd.Timestamp("2026-06-19"),
        pd.Timestamp("2026-07-19"),
    ])
    for dt in sorted(dias_trabalhados):
        duracao = random.choice([240, 300, 360])
        disp_abs = int(duracao * random.uniform(0.76, 0.98))
        ofertadas = random.randint(10, 22)
        rejeitadas = random.randint(0, 2)
        aceitas = max(1, ofertadas - rejeitadas)
        completadas = aceitas if random.random() > 0.08 else max(1, aceitas - 1)
        turnos.append({
            "id_da_pessoa_entregadora": ent["ID"],
            "data_do_periodo": dt.strftime("%Y-%m-%d"),
            "tempo_disponivel_escalado": duracao,
            "tempo_disponivel_absoluto": disp_abs,
            "duracao_do_periodo": duracao,
            "numero_de_corridas_aceitas": aceitas,
            "numero_de_corridas_ofertadas": ofertadas,
            "numero_de_corridas_rejeitadas": rejeitadas,
            "numero_de_corridas_completadas": completadas,
            "numero_de_pedidos_aceitos_e_concluidos": completadas,
        })

df_perf = pd.DataFrame(turnos)
df_perf.to_parquet(DATA_DIR / "perfomance.parquet", index=False)

print("Todos os 4 arquivos .parquet fictícios foram gerados em data/!")