import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, time
from dotenv import load_dotenv
import os

load_dotenv()

# Período da campanha
DATA_INICIO_CAMPANHA = datetime(2026, 6, 8)  # Ajuste conforme necessário
DATA_FIM_CAMPANHA = datetime(2026, 7, 19)      # Ajuste conforme necessário

# Configuração WhatsApp
WHATSAPP_NUMERO = os.getenv("WHATSAPP_NUMERO")
WHATSAPP_MENSAGEM = os.getenv("WHATSAPP_MENSAGEM")


@st.cache_data(ttl=300)
def carregar_base_drivers():
    """Carrega a base de entregadores (cache 5 min)"""
    caminho = Path(__file__).parent.parent / "data" / "base.parquet"
    return pd.read_parquet(caminho)

@st.cache_data(ttl=300)
def carregar_performance():
    """Carrega a base de performance filtrada (cache 5 min)"""
    caminho = Path(__file__).parent.parent / "data" / "perfomance.parquet"
    df = pd.read_parquet(caminho)
    df['data_do_periodo'] = pd.to_datetime(df['data_do_periodo'])
    df = df[(df['data_do_periodo'] >= DATA_INICIO_CAMPANHA) &
            (df['data_do_periodo'] <= DATA_FIM_CAMPANHA)]
    return df

@st.cache_data(ttl=300)
def carregar_jogos_copa():
    caminho = Path(__file__).parent.parent / "data" / "jogos_copa.parquet"
    if caminho.exists():
        return pd.read_parquet(caminho)
    return pd.DataFrame()

@st.cache_data(ttl=300)
def carregar_bolao():
    caminho = Path(__file__).parent.parent / "data" / "bolao_participantes.parquet"
    if caminho.exists():
        return pd.read_parquet(caminho)
    return pd.DataFrame

def converter_tempo_para_segundos(tempo) -> int:
    """Converte tempo (HH:MM:SS, timedelta ou datetime.time) para segundos"""
    if pd.isna(tempo):
        return 0
    if isinstance(tempo, time):
        return tempo.hour * 3600 + tempo.minute * 60 + tempo.second
    if isinstance(tempo, str):
        partes = tempo.split(':')
        if len(partes) == 3:
            h, m, s = partes
            return int(h) * 3600 + int(m) * 60 + int(float(s))
    elif hasattr(tempo, 'total_seconds'):
        return int(tempo.total_seconds())
    return 0

def calcular_pontuacao_driver(driver_id: str, cpf: str, is_elite: bool, df_performance: pd.DataFrame = None) -> dict:
    """
    Calcula a pontuação detalhada de um driver.
    """
    if df_performance is None:
        df_performance = carregar_performance()

    df_driver = df_performance[df_performance['id_da_pessoa_entregadora'] == driver_id]

    multiplicador = 2 if is_elite else 1

    resultado = {
        'turnos_atuados': 0,
        'pontos_turnos': 0,
        'turnos_tempo_online_ok': 0,
        'pontos_tempo_online': 0,
        'turnos_aceitacao_ok': 0,
        'pontos_aceitacao': 0,
        'turnos_conclusao_ok': 0,
        'pontos_conclusao': 0,
        'pontos_jogos_brasil': 0,
        'jogos_brasil_atuados': 0,
        'pontos_final': 0,
        'atuou_final': False,
        'pontos_bolao': 0,
        'participou_bolao': False,
        'pontos_total': 0,
        'percentual_tempo_online': 0.0,
        'percentual_aceitacao': 0.0,
        'percentual_conclusao': 0.0,
        'total_pedidos_concluidos': 0,
        'total_rejeicoes': 0,
    }

    if df_driver.empty:
        return resultado

    df_ativo = df_driver[df_driver['tempo_disponivel_escalado'] > 0]
    turnos_atuados = len(df_ativo)
    resultado['turnos_atuados'] = turnos_atuados
    resultado['pontos_turnos'] = turnos_atuados * 1 * multiplicador

    if df_ativo.empty:
        return resultado

    # === TEMPO ONLINE ===
    total_disponivel_seg = df_ativo['tempo_disponivel_absoluto'].apply(converter_tempo_para_segundos).sum()
    total_duracao_seg = df_ativo['duracao_do_periodo'].apply(converter_tempo_para_segundos).sum()

    if total_duracao_seg > 0:
        resultado['percentual_tempo_online'] = (total_disponivel_seg / total_duracao_seg) * 100

    for _, row in df_ativo.iterrows():
        disp_seg = converter_tempo_para_segundos(row['tempo_disponivel_absoluto'])
        dur_seg = converter_tempo_para_segundos(row['duracao_do_periodo'])
        if dur_seg > 0 and (disp_seg / dur_seg) * 100 >= 75:
            resultado['turnos_tempo_online_ok'] += 1
    resultado['pontos_tempo_online'] = resultado['turnos_tempo_online_ok'] * 5 * multiplicador

    # === TAXA DE ACEITAÇÃO ===
    total_aceitas = df_ativo['numero_de_corridas_aceitas'].sum()
    total_ofertadas = df_ativo['numero_de_corridas_ofertadas'].sum()
    total_rejeitadas = df_ativo['numero_de_corridas_rejeitadas'].sum()

    if total_ofertadas > 0:
        resultado['percentual_aceitacao'] = (total_aceitas / total_ofertadas) * 100

    for _, row in df_ativo.iterrows():
        aceitas = row['numero_de_corridas_aceitas']
        ofertadas = row['numero_de_corridas_ofertadas']
        if ofertadas > 0 and (aceitas / ofertadas) * 100 >= 75:
            resultado['turnos_aceitacao_ok'] += 1
    resultado['pontos_aceitacao'] = resultado['turnos_aceitacao_ok'] * 3 * multiplicador

    # === TAXA DE CONCLUSÃO ===
    total_completadas = df_ativo['numero_de_corridas_completadas'].sum()

    if total_aceitas > 0:
        resultado['percentual_conclusao'] = (total_completadas / total_aceitas) * 100

    for _, row in df_ativo.iterrows():
        aceitas = row['numero_de_corridas_aceitas']
        completadas = row['numero_de_corridas_completadas']
        if aceitas > 0 and (completadas / aceitas) * 100 >= 95:
            resultado['turnos_conclusao_ok'] += 1
    resultado['pontos_conclusao'] = resultado['turnos_conclusao_ok'] * 2 * multiplicador

    # === JOGOS DO BRASIL E FINAL ===
    df_jogos = carregar_jogos_copa()
    if not df_jogos.empty:
        hoje = datetime.now().date()

        for _, jogo in df_jogos.iterrows():
            data_jogo = pd.to_datetime(jogo['data_jogo']).date()

            # Só conta jogos que já aconteceram
            if data_jogo > hoje:
                continue

            # Verifica se o driver atuou nesse dia
            df_dia = df_ativo[pd.to_datetime(df_ativo['data_do_periodo']).dt.date == data_jogo]

            if not df_dia.empty:
                # Verifica se cumpriu os critérios no dia do jogo
                cumpriu_criterios = False
                for _, turno in df_dia.iterrows():
                    disp_seg = converter_tempo_para_segundos(turno['tempo_disponivel_absoluto'])
                    dur_seg = converter_tempo_para_segundos(turno['duracao_do_periodo'])
                    aceitas = turno['numero_de_corridas_aceitas']
                    ofertadas = turno['numero_de_corridas_ofertadas']
                    completadas = turno['numero_de_corridas_completadas']

                    tempo_ok = dur_seg > 0 and (disp_seg / dur_seg) * 100 >= 75
                    aceitacao_ok = ofertadas > 0 and (aceitas / ofertadas) * 100 >= 75
                    conclusao_ok = aceitas > 0 and (completadas / aceitas) * 100 >= 95

                    if tempo_ok and aceitacao_ok and conclusao_ok:
                        cumpriu_criterios = True
                        break

                if cumpriu_criterios:
                    if jogo['jogo_brasil']:
                        resultado['jogos_brasil_atuados'] += 1
                        resultado['pontos_jogos_brasil'] += 10 * multiplicador

                    if jogo['jogo_final']:
                        resultado['atuou_final'] = True
                        resultado['pontos_final'] = 10 * multiplicador

    # === BOLÃO ===
    df_bolao = carregar_bolao()
    if not df_bolao.empty:
        cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))
        df_bolao['cpf_limpo'] = df_bolao['cpf'].astype(str).apply(lambda x: ''.join(filter(str.isdigit, x)))
        participacao = df_bolao[df_bolao['cpf_limpo'] == cpf_limpo]
        if not participacao.empty:
            resultado['participou_bolao'] = True
            pontos_bolao_base = participacao['pontos_bolao'].sum()
            resultado['pontos_bolao'] = int(pontos_bolao_base) * multiplicador

    # === DESEMPATE ===
    resultado['total_pedidos_concluidos'] = df_ativo['numero_de_pedidos_aceitos_e_concluidos'].sum()
    resultado['total_rejeicoes'] = total_rejeitadas

    # === TOTAL ===
    resultado['pontos_total'] = (
        resultado['pontos_turnos'] +
        resultado['pontos_tempo_online'] +
        resultado['pontos_aceitacao'] +
        resultado['pontos_conclusao'] +
        resultado['pontos_jogos_brasil'] +
        resultado['pontos_final'] +
        resultado['pontos_bolao']
    )

    return resultado


@st.cache_data(ttl=300)
def calcular_ranking_geral_cached() -> pd.DataFrame:
    """
    Calcula o ranking de todos os drivers (cache 5 min).
    """
    df_drivers = carregar_base_drivers()
    df_performance = carregar_performance()

    ranking = []
    for _, driver in df_drivers.iterrows():
        is_elite = str(driver.get('ELITE', 'NÃO')).upper() == 'SIM'
        cpf = str(driver.get('CPF', ''))
        pontos = calcular_pontuacao_driver(driver['ID'], cpf, is_elite, df_performance)

        ranking.append({
            'id': driver['ID'],
            'nome': driver['Nome'],
            'modal': driver.get('Modal', ''),
            'elite': 'SIM' if is_elite else 'NÃO',
            'pontos': pontos['pontos_total'],
            'turnos': pontos['turnos_atuados'],
            'tempo_online': pontos['percentual_tempo_online'],
            'aceitacao': pontos['percentual_aceitacao'],
            'conclusao': pontos['percentual_conclusao'],
            'pedidos': pontos['total_pedidos_concluidos'],
            'rejeicoes': pontos['total_rejeicoes'],
        })

    df_ranking = pd.DataFrame(ranking)
    df_ranking = df_ranking.sort_values(
        by=['pontos', 'pedidos', 'rejeicoes'],
        ascending=[False, False, True]
    ).reset_index(drop=True)
    df_ranking['posicao'] = df_ranking.index + 1

    return df_ranking

def calcular_ranking_geral() -> pd.DataFrame:
    """Wrapper para manter compatibilidade"""
    return calcular_ranking_geral_cached()

def obter_posicao_driver(driver_id: str) -> int:
    """Retorna a posição do driver no ranking"""
    df_ranking = calcular_ranking_geral_cached()
    posicao = df_ranking[df_ranking['id'] == driver_id]['posicao']
    if not posicao.empty:
        return int(posicao.iloc[0])
    return 0

def tela_driver():
    """Renderiza o painel do entregador"""

    dados = st.session_state.dados_usuario
    driver_id = dados.get('ID', '')
    nome = dados.get('Nome', 'Entregador')
    is_elite = str(dados.get('ELITE', 'NÃO')).upper() == 'SIM'

    # === NAVBAR ===
    col_titulo, col_regras, col_logout = st.columns([6, 1, 1])

    with col_titulo:
        st.markdown("# APP COPA LOGÍSTICA 2026")

    with col_regras:
        if st.button("Regras", use_container_width=True):
            st.session_state.mostrar_regras = not st.session_state.get('mostrar_regras', False)

    with col_logout:
        if st.button("Sair", use_container_width=True):
            st.session_state.logado = False
            st.session_state.tipo_usuario = None
            st.session_state.dados_usuario = None
            st.rerun()

    st.markdown("---")

    # === REGRAS (se clicou no botão) ===
    if st.session_state.get('mostrar_regras', False):
        st.markdown("""
        ### APP COPA LOGÍSTICA 2026 — JUNTE PONTOS E GANHE!

        **Período:** 08/06/2026 até 19/07/2026

        **Como acumular pontos:**
        | Critério | Pontos | Elite (2x) |
        |----------|--------|------------|
        | Turno jogo Brasil* | +10 | +20 |
        | Turno Final* | +10 | +20 |
        | Tempo online ≥ 75% | +5 | +10 |
        | Aceitação ≥ 75% | +3 | +6 |
        | Conclusão ≥ 95% | +2 | +4 |
        | Cada turno atuado | +1 | +2 |
        | Bolão da Copa | +1 | +2 |

        **Premiação:**
        - 1º lugar — R$ 10.000
        - 2º lugar — R$ 6.000
        - 3º lugar — R$ 4.000
        - 4º e 5º — R$ 2.000 cada
        - 6º e 7º — R$ 1.000 cada
        - 8º ao 15º — R$ 500 cada

        **Critérios de desempate:**
        1. Maior número de pedidos entregues
        2. Menor número de rejeições
        """, unsafe_allow_html=True)
        st.markdown("---")

    # === HEADER DO DRIVER ===
    st.markdown(f" ### Olá {nome}!")
    if is_elite:
        st.markdown("**Programa Elite** — Seus pontos valem **2x**!")

    st.markdown("---")

    # === CÁLCULO DOS PONTOS ===
    with st.spinner("Calculando sua pontuação..."):
        df_performance = carregar_performance()
        cpf = str(dados.get('CPF', ''))
        pontos = calcular_pontuacao_driver(driver_id, cpf, is_elite, df_performance)
        posicao = obter_posicao_driver(driver_id)

    # === CARDS PRINCIPAIS ===
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Sua Pontuação",
            value=f"{pontos['pontos_total']} pts"
        )

    with col2:
        st.metric(
            label="Posição no Ranking",
            value=f"{posicao}º lugar"
        )

    with col3:
        st.metric(
            label="Turnos Atuados",
            value=pontos['turnos_atuados']
        )

    st.markdown("---")

    # === DETALHAMENTO DOS PONTOS ===
    st.markdown("### Detalhamento dos Pontos")

    mult_texto = " (2x Elite)" if is_elite else ""

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Por Critério")

        # Calcular pontos base (sem multiplicador)
        base_turnos = pontos['turnos_atuados'] * 1
        base_tempo = pontos['turnos_tempo_online_ok'] * 5
        base_aceitacao = pontos['turnos_aceitacao_ok'] * 3
        base_conclusao = pontos['turnos_conclusao_ok'] * 2

        if is_elite:
            st.markdown(f"""
            | Critério | Turnos OK | Pontos | ELITE (2x) |
            |----------|-----------|--------|------------|
            | Turnos atuados | {pontos['turnos_atuados']} | {base_turnos} | **{pontos['pontos_turnos']}** |
            | Tempo online ≥ 75% | {pontos['turnos_tempo_online_ok']} | {base_tempo} | **{pontos['pontos_tempo_online']}** |
            | Aceitação ≥ 75% | {pontos['turnos_aceitacao_ok']} | {base_aceitacao} | **{pontos['pontos_aceitacao']}** |
            | Conclusão ≥ 95% | {pontos['turnos_conclusao_ok']} | {base_conclusao} | **{pontos['pontos_conclusao']}** |
            """)
        else:
            st.markdown(f"""
            | Critério | Turnos OK | Pontos | Total |
            |----------|-----------|--------|-------|
            | Turnos atuados | {pontos['turnos_atuados']} | {base_turnos} | **{pontos['pontos_turnos']}** |
            | Tempo online ≥ 75% | {pontos['turnos_tempo_online_ok']} | {base_tempo} | **{pontos['pontos_tempo_online']}** |
            | Aceitação ≥ 75% | {pontos['turnos_aceitacao_ok']} | {base_aceitacao} | **{pontos['pontos_aceitacao']}** |
            | Conclusão ≥ 95% | {pontos['turnos_conclusao_ok']} | {base_conclusao} | **{pontos['pontos_conclusao']}** |
            """)

    with col2:
        st.markdown("#### Seus Percentuais Gerais")

        def icone_meta(valor, meta):
            return "" if valor >= meta else ""

        st.markdown(f"""
        | Métrica | Seu Valor | Meta |
        |---------|-----------|------|
        | Tempo Online | {pontos['percentual_tempo_online']:.1f}% | {icone_meta(pontos['percentual_tempo_online'], 75)} ≥ 75% |
        | Taxa Aceitação | {pontos['percentual_aceitacao']:.1f}% | {icone_meta(pontos['percentual_aceitacao'], 75)} ≥ 75% |
        | Taxa Conclusão | {pontos['percentual_conclusao']:.1f}% | {icone_meta(pontos['percentual_conclusao'], 95)} ≥ 95% |
        """)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🇧🇷 Jogos do Brasil",
            value=f"{pontos['pontos_jogos_brasil']} pts",
            help=f"{pontos['jogos_brasil_atuados']} jogo(s) com critérios cumpridos"
        )

    with col2:
        st.metric(
            label="Final",
            value=f"{pontos['pontos_final']} pts",
            help="Atuou na final" if pontos['atuou_final'] else "Ainda não ocorreu"
        )

    with col3:
        st.metric(
            label="Bolão",
            value=f"{pontos['pontos_bolao']} pts",
            help="Participando" if pontos['participou_bolao'] else "Não participou"
        )

    st.markdown("---")

    # === DESEMPATE ===
    st.markdown("### Critérios de Desempate")
    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="Pedidos Entregues",
            value=pontos['total_pedidos_concluidos']
        )

    with col2:
        st.metric(
            label="Total de Rejeições",
            value=pontos['total_rejeicoes']
        )

    st.markdown("---")

    # === SUPORTE WHATSAPP ===
    st.markdown("### Precisa de Ajuda?")

    whatsapp_link = f"https://wa.me/{WHATSAPP_NUMERO}?text={WHATSAPP_MENSAGEM.replace(' ', '%20')}"

    st.markdown(f"""
    <a href="{whatsapp_link}" target="_blank" class="whatsapp-link">
        Falar no WhatsApp
    </a>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.caption("## Em caso de dúvidas sobre sua pontuação ou a campanha, entre em contato.")
