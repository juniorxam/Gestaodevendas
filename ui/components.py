"""
components.py - Componentes reutilizáveis da UI
"""

from typing import *

import pandas as pd
import streamlit as st

from core.security import Security, Formatters


class UIComponents:
    """Componentes UI reutilizáveis"""
    
    @staticmethod
    def create_metric_card(label: str, value: Any, icon: str = "📊", color: str = "#3b82f6"):
        """
        Cria um card de métrica estilizado
        
        Args:
            label: Rótulo da métrica
            value: Valor a ser exibido
            icon: Ícone a ser exibido
            color: Cor de fundo do card
        """
        # Formatar valor se for numérico
        if isinstance(value, (int, float)):
            if isinstance(value, float):
                formatted_value = f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                formatted_value = f"{value:,}".replace(",", ".")
        else:
            formatted_value = str(value)
        
        st.markdown(
            f"""
            <div class="metric-card" style="background: linear-gradient(135deg, {color} 0%, {color}dd 100%);">
                <div style="font-size: 2em; margin-bottom: 5px;">{icon}</div>
                <div class="metric-value">{formatted_value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    @staticmethod
    def create_pagination_controls(
        total_items: int,
        items_per_page: int = 20,
        session_key: str = "pagina_atual"
    ) -> Tuple[int, int]:
        """
        Cria controles de paginação
        
        Args:
            total_items: Total de itens
            items_per_page: Itens por página
            session_key: Chave na sessão para controle da página
            
        Returns:
            Tuple[int, int]: (página atual, itens por página)
        """
        if session_key not in st.session_state:
            st.session_state[session_key] = 1
        
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

        with col1:
            st.markdown(f"**Total:** {total_items} itens")

        with col2:
            if st.button("◀️", key=f"prev_{session_key}", disabled=st.session_state[session_key] <= 1):
                st.session_state[session_key] -= 1
                st.rerun()

        with col3:
            st.markdown(f"**{st.session_state[session_key]} / {total_pages}**")

        with col4:
            if st.button("▶️", key=f"next_{session_key}", disabled=st.session_state[session_key] >= total_pages):
                st.session_state[session_key] += 1
                st.rerun()

        with col5:
            per_page_key = f"per_page_{session_key}"
            current_per_page = st.session_state.get(per_page_key, items_per_page)
            new_per_page = st.selectbox(
                "Itens por página:",
                [10, 20, 50, 100],
                index=[10, 20, 50, 100].index(current_per_page),
                key=per_page_key,
                label_visibility="collapsed"
            )
            if new_per_page != current_per_page:
                st.session_state[per_page_key] = new_per_page
                st.session_state[session_key] = 1
                st.rerun()

        return st.session_state[session_key], new_per_page

    @staticmethod
    def show_loading_indicator(message: str = "Carregando..."):
        """Mostra indicador de carregamento"""
        return st.spinner(message)

    @staticmethod
    def show_success_message(message: str):
        """Mostra mensagem de sucesso com ícone"""
        st.success(f"✅ {message}")

    @staticmethod
    def show_error_message(message: str):
        """Mostra mensagem de erro com ícone"""
        st.error(f"❌ {message}")

    @staticmethod
    def show_warning_message(message: str):
        """Mostra mensagem de aviso com ícone"""
        st.warning(f"⚠️ {message}")

    @staticmethod
    def show_info_message(message: str):
        """Mostra mensagem informativa"""
        st.info(f"ℹ️ {message}")

    @staticmethod
    def create_form_step(step_num: int, title: str, active: bool = False, completed: bool = False):
        """
        Cria passo de formulário
        
        Args:
            step_num: Número do passo
            title: Título do passo
            active: Se está ativo
            completed: Se está completo
        """
        classes = "form-step"
        if active:
            classes += " active"
        if completed:
            classes += " completed"

        st.markdown(
            f'<div class="{classes}"><strong>Passo {step_num}:</strong> {title}</div>',
            unsafe_allow_html=True
        )

    @staticmethod
    def create_filter_section(
        filters: List[Dict[str, Any]],
        key_prefix: str = "filter"
    ) -> Dict[str, Any]:
        """
        Cria seção de filtros dinâmicos
        
        Args:
            filters: Lista de configurações de filtros. Cada item deve ter:
                - label: Rótulo do filtro
                - type: Tipo ('text', 'select', 'date', 'daterange', 'number')
                - options: Lista de opções (para 'select')
                - default: Valor padrão
                - key: Chave única
            key_prefix: Prefixo para as chaves
            
        Returns:
            Dicionário com os valores dos filtros
        """
        values = {}
        
        with st.container():
            st.markdown("### 🔍 Filtros")
            
            cols = st.columns(len(filters))
            
            for i, filtro in enumerate(filters):
                with cols[i]:
                    key = f"{key_prefix}_{filtro['key']}"
                    label = filtro['label']
                    
                    if filtro['type'] == 'text':
                        values[filtro['key']] = st.text_input(
                            label,
                            value=filtro.get('default', ''),
                            key=key,
                            placeholder=filtro.get('placeholder', '')
                        )
                    
                    elif filtro['type'] == 'select':
                        values[filtro['key']] = st.selectbox(
                            label,
                            options=filtro['options'],
                            index=filtro.get('default_index', 0),
                            key=key
                        )
                    
                    elif filtro['type'] == 'date':
                        values[filtro['key']] = st.date_input(
                            label,
                            value=filtro.get('default'),
                            key=key
                        )
                    
                    elif filtro['type'] == 'number':
                        values[filtro['key']] = st.number_input(
                            label,
                            value=filtro.get('default', 0),
                            min_value=filtro.get('min_value', 0),
                            max_value=filtro.get('max_value', 1000000),
                            key=key
                        )
        
        return values

    @staticmethod
    def create_action_buttons(
        actions: List[Dict[str, Any]],
        key_prefix: str = "action"
    ) -> Dict[str, bool]:
        """
        Cria botões de ação
        
        Args:
            actions: Lista de ações. Cada item deve ter:
                - label: Rótulo do botão
                - key: Chave única
                - type: 'primary', 'secondary' ou 'danger'
                - icon: Ícone
            key_prefix: Prefixo para as chaves
            
        Returns:
            Dicionário com estados dos botões (True se clicado)
        """
        states = {}
        
        cols = st.columns(len(actions))
        
        for i, action in enumerate(actions):
            with cols[i]:
                button_type = action.get('type', 'secondary')
                label = f"{action.get('icon', '')} {action['label']}"
                
                if button_type == 'primary':
                    states[action['key']] = st.button(
                        label,
                        key=f"{key_prefix}_{action['key']}",
                        type="primary"
                    )
                elif button_type == 'danger':
                    states[action['key']] = st.button(
                        label,
                        key=f"{key_prefix}_{action['key']}",
                        type="secondary"
                    )
                else:
                    states[action['key']] = st.button(
                        label,
                        key=f"{key_prefix}_{action['key']}"
                    )
        
        return states

    @staticmethod
    def create_data_table(
        df: pd.DataFrame,
        key: str,
        column_config: Optional[Dict] = None,
        height: int = 400,
        use_container_width: bool = True
    ):
        """
        Cria tabela de dados com configurações personalizadas
        
        Args:
            df: DataFrame com os dados
            key: Chave única
            column_config: Configuração das colunas
            height: Altura da tabela
            use_container_width: Usar largura do container
        """
        if df.empty:
            st.info("📭 Nenhum dado para exibir.")
            return
        
        # Configuração padrão de colunas
        if column_config is None:
            column_config = {}
        
        # Adicionar formatação automática para CPF e valores monetários
        for col in df.columns:
            if col.lower() in ['cpf', 'documento']:
                column_config[col] = st.column_config.TextColumn(
                    col,
                    help="CPF formatado",
                    width="medium"
                )
            elif col.lower() in ['preco', 'valor', 'total', 'preco_venda', 'preco_custo', 'valor_total']:
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    help="Valor em R$",
                    format="R$ %.2f",
                    width="medium"
                )
        
        st.dataframe(
            df,
            use_container_width=use_container_width,
            height=height,
            hide_index=True,
            column_config=column_config
        )

    @staticmethod
    def create_confirmation_dialog(
        title: str,
        message: str,
        confirm_text: str = "Confirmar",
        cancel_text: str = "Cancelar",
        key: str = "confirm"
    ) -> Optional[bool]:
        """
        Cria diálogo de confirmação
        
        Args:
            title: Título do diálogo
            message: Mensagem de confirmação
            confirm_text: Texto do botão de confirmação
            cancel_text: Texto do botão de cancelamento
            key: Chave única
            
        Returns:
            True se confirmado, False se cancelado, None se não interagido
        """
        dialog_key = f"dialog_{key}"
        
        if dialog_key not in st.session_state:
            st.session_state[dialog_key] = None
        
        with st.container():
            st.markdown("---")
            st.warning(f"⚠️ **{title}**")
            st.markdown(message)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button(confirm_text, type="primary", key=f"confirm_{key}"):
                    st.session_state[dialog_key] = True
                    st.rerun()
            
            with col2:
                if st.button(cancel_text, key=f"cancel_{key}"):
                    st.session_state[dialog_key] = False
                    st.rerun()
        
        return st.session_state[dialog_key]

    @staticmethod
    def breadcrumb(*items: str):
        """
        Renderiza breadcrumb
        
        Args:
            *items: Itens do breadcrumb
        """
        html = '<div class="breadcrumb">'
        for i, item in enumerate(items):
            html += f'<span class="breadcrumb-item">{item}</span>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    @staticmethod
    def create_tooltip(element: str, tooltip: str):
        """
        Cria elemento com tooltip
        
        Args:
            element: HTML do elemento
            tooltip: Texto do tooltip
        """
        st.markdown(
            f'<span data-tooltip="{tooltip}">{element}</span>',
            unsafe_allow_html=True

        )
