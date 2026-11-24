import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, time

# Período da campanha
DATA_INICIO_CAMPANHA = datetime(2026, 6, 8)
DATA_FIM_CAMPANHA = datetime(2026, 7, 19)

@st.cache_data(ttl=300)
def carregar_performance():
    """Carrega a base de performance (cache 5 min)"""
    caminho = Path(__file__).parent.parent / "data" / "perfomance.parquet"
    df = pd.read_parquet(caminho)
    df['data_do_periodo'] = pd.to_datetime(df['data_do_periodo'])
    df = df[(df['data_do_periodo'] >= DATA_INICIO_CAMPANHA) &
            (df['data_do_periodo'] <= DATA_FIM_CAMPANHA)]
    return df

@st.cache_data(ttl=300)
def carregar_base_drivers():
    """Carrega a base de entregadores (cache 5 min)"""
    caminho = Path(__file__).parent.parent / "data" / "base.parquet"
    return pd.read_parquet(caminho)

@st.cache_data(ttl=300)
def carregar_jogos_copa():
    """Carrega a tabela de jogos da Copa (cache 5 min)"""
    caminho = Path(__file__).parent.parent / "data" / "jogos_copa.parquet"
    if caminho.exists():
        return pd.read_parquet(caminho)
    return pd.DataFrame()

@st.cache_data(ttl=300)
def carregar_bolao():
    """Carrega os participantes do bolão (cache 5 min)"""
    caminho = Path(__file__).parent.parent / "data" / "bolao_participantes.parquet"
    if caminho.exists():
        return pd.read_parquet(caminho)
    return pd.DataFrame()


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

def calcular_pontuacao_driver(driver_id: str, cpf: str, is_elite: bool, df_performance: pd.DataFrame) -> dict:
    """
    Calcula a pontuação detalhada de um driver.
    """
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

    # Tempo online
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

    # Aceitação
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

    # Conclusão
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

    # Desempate
    resultado['total_pedidos_concluidos'] = df_ativo['numero_de_pedidos_aceitos_e_concluidos'].sum()
    resultado['total_rejeicoes'] = total_rejeitadas

    # Total
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
def calcular_ranking_geral() -> pd.DataFrame:
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
            'jogos_brasil': pontos['pontos_jogos_brasil'],
            'bolao': pontos['pontos_bolao'],
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

def medalha(posicao: int) -> str:
    """Retorna emoji de medalha para top 3"""
    return f"{posicao}º"

def tela_admin():
    """Renderiza o painel administrativo"""

    # === NAVBAR ===
    col_titulo, col_regras, col_logout = st.columns([6, 1, 1])

    with col_titulo:
        st.markdown("# APP COPA LOGÍSTICA 2026")

    with col_regras:
        if st.button("Regras", use_container_width=True):
            st.session_state.mostrar_regras_admin = not st.session_state.get('mostrar_regras_admin', False)

    with col_logout:
        if st.button("Sair", use_container_width=True):
            st.session_state.logado = False
            st.session_state.tipo_usuario = None
            st.session_state.dados_usuario = None
            st.rerun()

    st.markdown("### Painel da Franquia")
    st.markdown("---")

    # === REGRAS (container simples) ===
    if st.session_state.get('mostrar_regras_admin', False):
        st.markdown("""
        <div class="regras-container">
        <h3>APP COPA LOGÍSTICA 2026 — JUNTE PONTOS E GANHE!</h3>

        <p><strong>Período:</strong> 08/06/2026 até 19/07/2026</p>

        <p><strong>Como acumular pontos:</strong></p>

        | Critério | Pontos | Elite (2x) |
        |----------|--------|------------|
        | Turno jogo Brasil* | +10 | +20 |
        | Turno Final* | +10 | +20 |
        | Tempo online ≥ 75% | +5 | +10 |
        | Aceitação ≥ 75% | +3 | +6 |
        | Conclusão ≥ 95% | +2 | +4 |
        | Cada turno atuado | +1 | +2 |
        | Bolão da Copa | +1 | +2 |

        <p><strong>Premiação:</strong> R$10k | R$6k | R$4k | 4º-5º R$2k | 6º-7º R$1k | 8º-15º R$500</p>

        <p><strong>Desempate:</strong> 1) Mais pedidos 2) Menos rejeições</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

    # === CARREGAR RANKING ===
    with st.spinner("Carregando ranking..."):
        df_ranking = calcular_ranking_geral()

    # === MÉTRICAS GERAIS ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Entregadores", len(df_ranking))

    with col2:
        ativos = len(df_ranking[df_ranking['turnos'] > 0])
        st.metric("Com Turnos", ativos)

    with col3:
        elite_count = len(df_ranking[df_ranking['elite'] == 'SIM'])
        st.metric("Elite", elite_count)

    with col4:
        total_pontos = df_ranking['pontos'].sum()
        st.metric("Total Pontos", f"{total_pontos:,}")

    st.markdown("---")

    # === FILTROS ===
    st.markdown("### Filtros")
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        busca_nome = st.text_input("Buscar por nome", placeholder="Digite o nome do entregador")

    with col2:
        filtro_elite = st.selectbox("Elite", ["Todos", "SIM", "NÃO"])

    with col3:
        top_n = st.selectbox("Exibir", [15, 50, 100, "Todos"])

    # Aplicar filtros
    df_filtrado = df_ranking.copy()

    if busca_nome:
        df_filtrado = df_filtrado[df_filtrado['nome'].str.contains(busca_nome, case=False, na=False)]

    if filtro_elite != "Todos":
        df_filtrado = df_filtrado[df_filtrado['elite'] == filtro_elite]

    if top_n != "Todos":
        df_filtrado = df_filtrado.head(top_n)

    st.markdown("---")

    # === RANKING (tabela interativa) ===
    st.markdown(f"### Ranking ({len(df_filtrado)} entregadores)")

    if df_filtrado.empty:
        st.warning("Nenhum entregador encontrado com os filtros aplicados.")
    else:
          # Preparar dados para exibição
          df_display = df_filtrado.copy()
          df_display['Pos'] = df_display['posicao'].apply(medalha)
          df_display['Elite'] = df_display['elite'].apply(lambda x: '' if x == 'SIM' else '')
          df_display['Tempo Online'] = df_display['tempo_online'].apply(lambda x: f"{x:.1f}%")
          df_display['Aceitação'] = df_display['aceitacao'].apply(lambda x: f"{x:.1f}%")
          df_display['Conclusão'] = df_display['conclusao'].apply(lambda x: f"{x:.1f}%")
          df_display['🇧🇷 Brasil'] = df_display['jogos_brasil'].apply(lambda x: f"+{x}" if x > 0 else "-")
          df_display['Bolão'] = df_display['bolao'].apply(lambda x: f"+{x}" if x > 0 else "-")

          # Renomear colunas
          df_display = df_display.rename(columns={
              'nome': 'Nome',
              'pontos': 'Pontos',
              'turnos': 'Turnos',
              'pedidos': 'Pedidos',
              'rejeicoes': 'Rejeições'
          })

          # Selecionar colunas para exibir
          colunas = ['Pos', 'Nome', 'Elite', 'Pontos', 'Turnos', 'Tempo Online', 'Aceitação', 'Conclusão', '🇧🇷 Brasil', 'Bolão', 'Pedidos', 'Rejeições']

          st.dataframe(
              df_display[colunas],
              use_container_width=True,
              hide_index=True,
              height=500
          )

    st.markdown("---")
