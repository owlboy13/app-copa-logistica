import streamlit as st
import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv
import requests
import bcrypt

load_dotenv()

# Configuração do Admin
ADMIN_CNPJ = os.getenv("ADMIN_CNPJ")
ADMIN_SENHA = os.getenv("ADMIN_SENHA")

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_headers():
    """Headers para API do Supabase"""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def hash_senha(senha: str) -> str:
    """Gera hash da senha"""
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha confere com o hash"""
    return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))

def carregar_base_drivers():
    """Carrega a base de entregadores"""
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


def validar_cpf(cpf: str) -> dict | None:
    """Valida se o CPF existe na base e retorna os dados do driver"""
    cpf_limpo = ''.join(filter(str.isdigit, cpf))
    df = carregar_base_drivers()
    df['CPF_limpo'] = df['CPF'].astype(str).apply(lambda x: ''.join(filter(str.isdigit, x)))
    driver = df[df['CPF_limpo'] == cpf_limpo]
    if not driver.empty:
        return driver.iloc[0].to_dict()
    return None

def buscar_senha(cpf: str) -> str | None:
    """Busca a senha do driver no Supabase via REST API"""
    cpf_limpo = ''.join(filter(str.isdigit, cpf))
    url = f"{SUPABASE_URL}/rest/v1/senhas_drivers?cpf=eq.{cpf_limpo}&select=senha_hash"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200 and response.json():
        return response.json()[0]['senha_hash']
    return None

def salvar_senha(cpf: str, senha: str) -> bool:
    """Salva a senha do driver no Supabase via REST API"""
    cpf_limpo = ''.join(filter(str.isdigit, cpf))
    senha_hash = hash_senha(senha)
    url = f"{SUPABASE_URL}/rest/v1/senhas_drivers"
    data = {"cpf": cpf_limpo, "senha_hash": senha_hash}
    try:
        response = requests.post(url, json=data, headers=get_headers())
        return response.status_code in [200, 201]
    except Exception as e:
        st.error(f"Erro ao salvar senha: {e}")
        return False

def validar_admin(cnpj: str, senha: str) -> bool:
    """Valida credenciais do admin"""
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    return cnpj_limpo == ADMIN_CNPJ and senha == ADMIN_SENHA

def tela_login():
    """Renderiza a tela de login"""

    # Inicializa estados
    if "etapa_login" not in st.session_state:
        st.session_state.etapa_login = "cpf"
    if "cpf_validado" not in st.session_state:
        st.session_state.cpf_validado = None
    if "dados_driver" not in st.session_state:
        st.session_state.dados_driver = None
    if "senha_criada" not in st.session_state:
        st.session_state.senha_criada = None

    query_params = st.query_params
    modo_admin = query_params.get("admin") == "1"

    # Header
    st.markdown("# APP COPA LOGÍSTICA 2026")
    st.markdown("---")

    if modo_admin:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("## Acesso Franquia")
            st.markdown("### Acesso administrativo ao ranking geral")
            cnpj_input = st.text_input(
                "CNPJ",
                placeholder="Digite o CNPJ da franquia",
                key="cnpj_admin",
                max_chars=18
            )
            senha_input = st.text_input(
                "Senha",
                type="password",
                placeholder="Digite a senha",
                key="senha_admin"
            )
            if st.button("Entrar", key="btn_admin", use_container_width=True):
                if cnpj_input and senha_input:
                    if validar_admin(cnpj_input, senha_input):
                        st.session_state.logado = True
                        st.session_state.tipo_usuario = "admin"
                        st.session_state.dados_usuario = {"tipo": "admin"}
                        st.rerun()
                    else:
                        st.error("CNPJ ou senha incorretos.")
                else:
                    st.warning("Preencha CNPJ e senha para continuar.")

    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("## Área do Entregador")

            # === ETAPA 1: DIGITAR CPF ===
            if st.session_state.etapa_login == "cpf":
                st.markdown("### Veja sua pontuação e posição no ranking")
                cpf_input = st.text_input(
                    "CPF",
                    placeholder="Digite seu CPF",
                    key="cpf_driver",
                    max_chars=14
                )
                if st.button("Continuar", key="btn_cpf", use_container_width=True):
                    if cpf_input:
                        dados = validar_cpf(cpf_input)
                        if dados:
                            st.session_state.dados_driver = dados
                            st.session_state.cpf_validado = cpf_input
                            # Verifica se já tem senha
                            senha_existente = buscar_senha(cpf_input)
                            if senha_existente:
                                st.session_state.etapa_login = "senha"
                            else:
                                st.session_state.etapa_login = "criar_senha"
                            st.rerun()
                        else:
                            st.error("CPF não encontrado na base de entregadores.")
                    else:
                        st.warning("Digite seu CPF para continuar.")

            # === ETAPA 2: CRIAR SENHA (primeiro acesso) ===
            elif st.session_state.etapa_login == "criar_senha":

                # Se a senha já foi criada, mostrar confirmação
                if st.session_state.senha_criada:
                    st.success("Senha criada com sucesso!")
                    st.warning("IMPORTANTE: Copie e salve sua senha!")
                    st.markdown("**Sua senha:**")
                    st.code(st.session_state.senha_criada, language=None)
                    st.caption("Clique no ícone para copiar")

                    if st.button("Já anotei, continuar", key="btn_continuar", use_container_width=True):
                        st.session_state.logado = True
                        st.session_state.tipo_usuario = "driver"
                        st.session_state.dados_usuario = st.session_state.dados_driver
                        st.session_state.etapa_login = "cpf"
                        st.session_state.cpf_validado = None
                        st.session_state.dados_driver = None
                        st.session_state.senha_criada = None
                        st.rerun()

                # Se ainda não criou, mostrar formulário
                else:
                    st.markdown("### Primeiro Acesso")
                    st.info(f"Olá, {st.session_state.dados_driver.get('Nome', '')}! Crie uma senha para acessar o sistema.")

                    nova_senha = st.text_input(
                        "Criar Senha",
                        type="password",
                        placeholder="Digite uma senha (mínimo 4 caracteres)",
                        key="nova_senha"
                    )
                    confirmar_senha = st.text_input(
                        "Confirmar Senha",
                        type="password",
                        placeholder="Digite a senha novamente",
                        key="confirmar_senha"
                    )

                    col_voltar, col_salvar = st.columns(2)
                    with col_voltar:
                        if st.button("← Voltar", key="btn_voltar_criar", use_container_width=True):
                            st.session_state.etapa_login = "cpf"
                            st.session_state.cpf_validado = None
                            st.session_state.dados_driver = None
                            st.rerun()

                    with col_salvar:
                        if st.button("Salvar Senha", key="btn_salvar_senha", use_container_width=True):
                            if nova_senha and confirmar_senha:
                                if len(nova_senha) < 4:
                                    st.error("A senha deve ter pelo menos 4 caracteres.")
                                elif nova_senha != confirmar_senha:
                                    st.error("As senhas não conferem.")
                                else:
                                    if salvar_senha(st.session_state.cpf_validado, nova_senha):
                                        st.session_state.senha_criada = nova_senha
                                        st.rerun()
                                    else:
                                        st.error("Erro ao salvar senha. Tente novamente.")
                            else:
                                st.warning("Preencha os dois campos de senha.")

            # === ETAPA 3: DIGITAR SENHA (já tem cadastro) ===
            elif st.session_state.etapa_login == "senha":
                st.markdown("### Digite sua Senha")
                st.info(f"Olá, {st.session_state.dados_driver.get('Nome', '')}!")

                senha_input = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="Digite sua senha",
                    key="senha_driver"
                )

                col_voltar, col_entrar = st.columns(2)
                with col_voltar:
                    if st.button("← Voltar", key="btn_voltar_senha", use_container_width=True):
                        st.session_state.etapa_login = "cpf"
                        st.session_state.cpf_validado = None
                        st.session_state.dados_driver = None
                        st.rerun()

                with col_entrar:
                    if st.button("Entrar", key="btn_entrar", use_container_width=True):
                        if senha_input:
                            senha_hash = buscar_senha(st.session_state.cpf_validado)
                            if senha_hash and verificar_senha(senha_input, senha_hash):
                                st.session_state.logado = True
                                st.session_state.tipo_usuario = "driver"
                                st.session_state.dados_usuario = st.session_state.dados_driver
                                st.session_state.etapa_login = "cpf"
                                st.session_state.cpf_validado = None
                                st.session_state.dados_driver = None
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                        else:
                            st.warning("Digite sua senha para continuar.")
