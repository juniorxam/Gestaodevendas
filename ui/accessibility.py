"""
accessibility.py - Componentes de acessibilidade simplificados
"""

import streamlit as st


class AccessibilityManager:
    """Gerencia recursos de acessibilidade da aplicação"""
    
    @staticmethod
    def inject_accessibility_js():
        """Injeta JavaScript para melhorar acessibilidade"""
        st.markdown("""
        <script>
        // Melhorar navegação por teclado
        document.addEventListener('keydown', function(e) {
            if (e.key === 'f' || e.key === 'F') {
                const searchInputs = document.querySelectorAll('input[type="text"]');
                for (let input of searchInputs) {
                    if (input.placeholder && input.placeholder.toLowerCase().includes('buscar')) {
                        input.focus();
                        e.preventDefault();
                        break;
                    }
                }
            }
            
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                const submitButtons = document.querySelectorAll('button[type="submit"]');
                if (submitButtons.length > 0) {
                    submitButtons[0].click();
                }
            }
        });
        </script>
        
        <style>
        :focus {
            outline: 3px solid #4A90E2 !important;
            outline-offset: 2px !important;
        }
        
        .high-contrast {
            background-color: black !important;
            color: yellow !important;
        }
        
        .high-contrast button {
            background-color: yellow !important;
            color: black !important;
        }
        
        /* Skip to content link */
        .skip-to-content {
            position: absolute;
            left: -9999px;
            top: auto;
            width: 1px;
            height: 1px;
            overflow: hidden;
        }
        
        .skip-to-content:focus {
            position: fixed;
            top: 10px;
            left: 10px;
            width: auto;
            height: auto;
            padding: 10px;
            background: #4A90E2;
            color: white;
            z-index: 9999;
            text-decoration: none;
            border-radius: 4px;
            outline: 3px solid white;
        }
        </style>
        
        <!-- Skip to content link -->
        <a href="#main-content" class="skip-to-content">Pular para o conteúdo principal</a>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_high_contrast_toggle():
        """Cria botão para alternar alto contraste"""
        if 'high_contrast' not in st.session_state:
            st.session_state.high_contrast = False
        
        col1, col2 = st.columns([1, 10])
        with col1:
            if st.button(
                "👁️" + (" (AC)" if st.session_state.high_contrast else ""),
                help="Alternar alto contraste",
                key="contrast_toggle"
            ):
                st.session_state.high_contrast = not st.session_state.high_contrast
                st.rerun()
        
        # Aplicar CSS de alto contraste se ativado
        if st.session_state.high_contrast:
            st.markdown("""
            <style>
            .main, .stApp {
                background-color: black !important;
                color: yellow !important;
            }
            .stButton button {
                background-color: yellow !important;
                color: black !important;
                border: 2px solid white !important;
            }
            .stTextInput input, .stSelectbox select {
                background-color: #333 !important;
                color: yellow !important;
                border: 1px solid yellow !important;
            }
            label, .stMarkdown, p, h1, h2, h3, h4 {
                color: yellow !important;
            }
            [data-testid="stSidebar"] {
                background-color: #222 !important;
                border-right: 2px solid yellow !important;
            }
            </style>
            """, unsafe_allow_html=True)

    @staticmethod
    def announce_message(message: str):
        """
        Anuncia uma mensagem para leitores de tela (acessibilidade).
        
        Args:
            message: Mensagem a ser anunciada
        """
        # Feedback visual (toast) para todos os usuários
        st.toast(message)
        
        # Região ARIA live oculta para leitores de tela
        st.markdown(
            f'<div aria-live="polite" style="position: absolute; width: 1px; height: 1px; overflow: hidden;">{message}</div>',
            unsafe_allow_html=True
        )
