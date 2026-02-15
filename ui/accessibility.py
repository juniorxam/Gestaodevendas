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
        </style>
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