import streamlit as st
from pathlib import Path
import sys

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.login import tela_login
from src.driver import tela_driver
from src.admin import tela_admin

# Configuração da página
st.set_page_config(
    page_title="APP COPA LOGÍSTICA 2026",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Carrega CSS externo
def carregar_css():
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

carregar_css()

# Inicializa estado da sessão
if "logado" not in st.session_state:
    st.session_state.logado = False
if "tipo_usuario" not in st.session_state:
    st.session_state.tipo_usuario = None
if "dados_usuario" not in st.session_state:
    st.session_state.dados_usuario = None

# Navegação principal
def main():
    if not st.session_state.logado:
        tela_login()
    else:
        if st.session_state.tipo_usuario == "driver":
            tela_driver()
        elif st.session_state.tipo_usuario == "admin":
            tela_admin()

if __name__ == "__main__":
    main()
