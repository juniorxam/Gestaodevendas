"""
login.py - Página de login
"""

import os

import streamlit as st

from config import CONFIG
from core.security import Security
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class LoginPage:
    """Página de login"""
    
    def __init__(self, auth, audit):
        self.auth = auth
        self.audit = audit
    
    def render(self):
        """Renderiza a página de login"""
        st.title(f"🔐 {CONFIG.app_title}")
        
        if os.path.exists(CONFIG.logo_path):
            import base64
            with open(CONFIG.logo_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            
            st.markdown(
                f"""
                <div style="text-align: center; margin-bottom: 20px;">
                    <img src="data:image/png;base64,{data}" style="max-height: 100px;">
                </div>
                """,
                unsafe_allow_html=True
            )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container():
                st.markdown("""
                <div style="text-align: center; margin-bottom: 30px;">
                    <h3 style="color: #1e3a8a;">ElectroGest</h3>
                    <p style="color: #6b7280;">Sistema de Gestão Comercial</p>
                </div>
                """, unsafe_allow_html=True)

                with st.form("login_form"):
                    login = st.text_input(
                        "👤 Usuário",
                        placeholder="Digite seu login",
                        key="login_user"
                    )
                    
                    senha = st.text_input(
                        "🔒 Senha",
                        type="password",
                        placeholder="Digite sua senha",
                        key="login_password"
                    )

                    col_btn1, col_btn2 = st.columns([3, 1])
                    with col_btn1:
                        submit = st.form_submit_button(
                            "🔓 Entrar",
                            type="primary"
                        )
                    with col_btn2:
                        reset = st.form_submit_button(
                            "🔄 Limpar",
                            type="secondary"
                        )

                    if submit:
                        if not login or not senha:
                            st.error("⚠️ Preencha todos os campos!")
                        else:
                            with st.spinner("Validando credenciais..."):
                                usuario = self.auth.login(login, senha)
                                if usuario:
                                    st.session_state.logado = True
                                    st.session_state.usuario_login = login
                                    st.session_state.usuario_nome = usuario["nome"]
                                    st.session_state.nivel_acesso = usuario["nivel_acesso"]
                                    st.session_state.pagina_atual = "dashboard"
                                    
                                    st.success(f"✅ Bem-vindo(a), {usuario['nome']}!")
                                    
                                    self.audit.registrar(
                                        login,
                                        "AUTH",
                                        "Login realizado",
                                        f"Login bem-sucedido: {usuario['nome']}",
                                        "127.0.0.1"
                                    )
                                    
                                    st.rerun()
                                else:
                                    st.error("❌ Login ou senha incorretos!")
                                    self.audit.registrar(
                                        login,
                                        "AUTH",
                                        "Tentativa de login falha",
                                        "Credenciais inválidas",
                                        "127.0.0.1"
                                    )

        st.markdown("---")
        st.markdown(
            """
            <div style="text-align: center; color: #6b7280; font-size: 12px;">
                <p>ElectroGest v1.0 | Sistema de Gestão Comercial</p>
                <p>© 2026 - Todos os direitos reservados</p>
            </div>
            """,
            unsafe_allow_html=True
        )