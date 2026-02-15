"""
alterar_senha.py - Página para usuário alterar própria senha
"""

import streamlit as st

from config import CONFIG
from core.security import Security
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class AlterarSenhaPage:
    """Página para alteração de senha do próprio usuário"""
    
    def __init__(self, db, auth, audit):
        self.db = db
        self.auth = auth
        self.audit = audit
    
    def render(self):
        """Renderiza página de alteração de senha"""
        st.title("🔐 Alterar Minha Senha")
        UIComponents.breadcrumb("🏠 Início", "Alterar Senha")
        
        usuario_login = st.session_state.get('usuario_login', '')
        usuario_nome = st.session_state.get('usuario_nome', 'Usuário')
        nivel_acesso = st.session_state.get('nivel_acesso', 'VISUALIZADOR')
        
        if not usuario_login and usuario_nome:
            row = self.db.fetchone(
                "SELECT login FROM usuarios WHERE nome = ? AND ativo = 1",
                (usuario_nome,)
            )
            if row:
                usuario_login = row['login']
                st.session_state.usuario_login = usuario_login
        
        if not usuario_login:
            UIComponents.show_error_message("Não foi possível identificar o login do usuário!")
            st.stop()
        
        st.info(f"**Usuário:** {usuario_nome} | **Login:** {usuario_login} | **Nível:** {nivel_acesso}")
        st.markdown("---")

        if 'senha_alterada' not in st.session_state:
            st.session_state.senha_alterada = False

        if st.session_state.senha_alterada:
            UIComponents.show_success_message("Senha alterada com sucesso!")
            st.balloons()
            st.info("🔐 Use sua nova senha no próximo login.")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🏠 Voltar ao Dashboard", type="primary"):
                    st.session_state.senha_alterada = False
                    st.session_state.pagina_atual = "dashboard"
                    st.rerun()
            return

        with st.form("form_alterar_senha"):
            st.markdown("### 🔑 Alterar Senha")
            
            senha_atual = AccessibilityManager.create_accessible_input(
                label="Senha Atual:",
                key="senha_atual",
                input_type="password",
                placeholder="Digite sua senha atual",
                required=True
            )
            
            nova_senha = AccessibilityManager.create_accessible_input(
                label="Nova Senha:",
                key="nova_senha",
                input_type="password",
                placeholder="Digite a nova senha (mínimo 6 caracteres)",
                required=True,
                help_text="A senha deve ter pelo menos 6 caracteres"
            )
            
            confirmar_senha = AccessibilityManager.create_accessible_input(
                label="Confirmar Nova Senha:",
                key="confirmar_senha",
                input_type="password",
                placeholder="Digite a nova senha novamente",
                required=True
            )

            st.markdown("### 📋 Requisitos da senha:")
            st.markdown("""
            - ✅ Mínimo de 6 caracteres
            - ✅ Não pode ser igual à senha atual
            - ✅ Recomendado usar letras e números
            """)

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                submit = st.form_submit_button(
                    "✅ Alterar Senha",
                    type="primary"
                )

            with col_btn2:
                cancelar = st.form_submit_button(
                    "❌ Cancelar"
                )

            if submit:
                self._processar_alteracao(usuario_login, usuario_nome, senha_atual, nova_senha, confirmar_senha)

            if cancelar:
                st.session_state.pagina_atual = "dashboard"
                st.rerun()
    
    def _processar_alteracao(self, usuario_login, usuario_nome, senha_atual, nova_senha, confirmar_senha):
        """Processa a alteração de senha"""
        
        if not usuario_login:
            UIComponents.show_error_message("Login do usuário não encontrado!")
            st.stop()
        
        if not senha_atual:
            UIComponents.show_error_message("A senha atual é obrigatória!")
            st.stop()
        
        if not nova_senha:
            UIComponents.show_error_message("A nova senha é obrigatória!")
            st.stop()
        
        if not confirmar_senha:
            UIComponents.show_error_message("A confirmação da senha é obrigatória!")
            st.stop()
        
        if nova_senha != confirmar_senha:
            UIComponents.show_error_message("As senhas não conferem!")
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Tentativa falha de alteração de senha",
                "Confirmação de senha não confere",
                "127.0.0.1"
            )
            st.stop()
        
        if len(nova_senha) < 6:
            UIComponents.show_error_message("A nova senha deve ter pelo menos 6 caracteres!")
            st.stop()
        
        # Verificar senha atual
        senha_atual_hash = Security.sha256_hex(senha_atual)
        
        row = self.db.fetchone(
            "SELECT login FROM usuarios WHERE login = ? AND senha = ? AND ativo = 1",
            (usuario_login, senha_atual_hash)
        )
        
        if not row:
            UIComponents.show_error_message("Senha atual incorreta!")
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Tentativa falha de alteração de senha",
                "Senha atual incorreta",
                "127.0.0.1"
            )
            st.stop()
        
        if nova_senha == senha_atual:
            UIComponents.show_error_message("A nova senha não pode ser igual à senha atual!")
            st.stop()
        
        try:
            nova_senha_hash = Security.sha256_hex(nova_senha)
            self.db.execute(
                "UPDATE usuarios SET senha = ? WHERE login = ?",
                (nova_senha_hash, usuario_login)
            )
            
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Alterou própria senha",
                "Senha alterada com sucesso",
                "127.0.0.1"
            )
            
            AccessibilityManager.announce_message("Senha alterada com sucesso")
            st.session_state.senha_alterada = True
            st.rerun()
            
        except Exception as e:
            UIComponents.show_error_message(f"Erro ao alterar senha: {str(e)}")
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Erro ao alterar senha",
                f"Erro: {str(e)}",
                "127.0.0.1"
            )