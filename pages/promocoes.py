"""
promocoes.py - Página de gerenciamento de promoções
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Formatters
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class PromocoesPage:
    """Página de promoções"""
    
    def __init__(self, db, promocoes, auth):
        self.db = db
        self.promocoes = promocoes
        self.auth = auth
    
    def render(self):
        """Renderiza página de promoções"""
        st.title("🎯 Promoções")
        UIComponents.breadcrumb("🏠 Início", "Promoções")

        tab1, tab2 = st.tabs(["📋 Listar Promoções", "➕ Nova Promoção"])

        with tab1:
            self._render_listar()

        with tab2:
            self._render_nova()
    
    def _render_listar(self):
        """Renderiza lista de promoções"""
        st.subheader("📋 Promoções Cadastradas")

        col1, col2 = st.columns(2)

        with col1:
            filtro_status = st.selectbox(
                "Status:",
                ["TODOS", "ATIVA", "PLANEJADA", "CONCLUÍDA", "CANCELADA"],
                key="filtro_status_promocao"
            )

        with col2:
            filtro_tipo = st.selectbox(
                "Tipo:",
                ["TODOS", "DESCONTO_PERCENTUAL", "DESCONTO_FIXO", "LEVE_MAIS"],
                key="filtro_tipo_promocao"
            )

        if st.button("🔍 Buscar Promoções", type="primary"):
            with st.spinner("Buscando promoções..."):
                status = None if filtro_status == "TODOS" else filtro_status
                promocoes = self.promocoes.listar_promocoes(status=status)
                
                if filtro_tipo != "TODOS":
                    promocoes = promocoes[promocoes['tipo'] == filtro_tipo]
                
                st.session_state.promocoes_filtradas = promocoes
                UIComponents.show_success_message(f"{len(promocoes)} promoções encontradas")

        # Exibir resultados
        if st.session_state.get('promocoes_filtradas') is not None:
            promocoes = st.session_state.promocoes_filtradas

            if not promocoes.empty:
                for _, promocao in promocoes.iterrows():
                    self._render_card_promocao(promocao)
            else:
                UIComponents.show_info_message("Nenhuma promoção encontrada com os filtros selecionados.")
    
    def _render_card_promocao(self, promocao):
        """Renderiza card de uma promoção"""
        # Definir ícone baseado no status
        status_icon = {
            "ATIVA": "🟢",
            "PLANEJADA": "🟡",
            "CONCLUÍDA": "🔵",
            "CANCELADA": "🔴"
        }.get(promocao['status'], "⚪")
        
        # Definir ícone baseado no tipo
        tipo_icon = {
            "DESCONTO_PERCENTUAL": "📉",
            "DESCONTO_FIXO": "💰",
            "LEVE_MAIS": "🎁"
        }.get(promocao['tipo'], "🏷️")
        
        with st.container():
            st.markdown(f"""
            <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0;">{status_icon} {tipo_icon} {promocao['nome']}</h3>
                        <p style="color: #666; margin: 5px 0;">{promocao['descricao']}</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="margin: 0;"><strong>Período:</strong> {Formatters.formatar_data_br(promocao['data_inicio'])} a {Formatters.formatar_data_br(promocao['data_fim'])}</p>
                        <p style="margin: 0;"><strong>Valor:</strong> {self._formatar_valor_promocao(promocao)}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Ações
            col_acoes1, col_acoes2, col_acoes3, col_acoes4 = st.columns([1, 1, 1, 3])

            with col_acoes1:
                if st.button("✏️ Editar", key=f"edit_promo_{promocao['id']}"):
                    st.session_state.promocao_editar = dict(promocao)
                    st.rerun()

            with col_acoes2:
                if promocao['status'] == 'ATIVA':
                    if st.button("⏸️ Pausar", key=f"pause_promo_{promocao['id']}"):
                        self._atualizar_status(promocao['id'], 'PLANEJADA')
                else:
                    if st.button("▶️ Ativar", key=f"activate_promo_{promocao['id']}"):
                        self._atualizar_status(promocao['id'], 'ATIVA')

            with col_acoes3:
                if st.session_state.nivel_acesso == 'ADMIN':
                    if st.button("🗑️ Excluir", key=f"del_promo_{promocao['id']}", type="secondary"):
                        st.session_state.promocao_excluir = dict(promocao)
                        st.rerun()

            st.markdown("---")

        # Modal de edição
        if st.session_state.get('promocao_editar') and st.session_state.promocao_editar['id'] == promocao['id']:
            self._render_editar_promocao(st.session_state.promocao_editar)

        # Modal de exclusão
        if st.session_state.get('promocao_excluir') and st.session_state.promocao_excluir['id'] == promocao['id']:
            self._render_modal_exclusao()
    
    def _formatar_valor_promocao(self, promocao):
        """Formata o valor da promoção para exibição"""
        if promocao['tipo'] == 'DESCONTO_PERCENTUAL':
            return f"{promocao['valor_desconto']}% de desconto"
        elif promocao['tipo'] == 'DESCONTO_FIXO':
            return f"R$ {promocao['valor_desconto']:,.2f} de desconto".replace(",", "X").replace(".", ",").replace("X", ".")
        elif promocao['tipo'] == 'LEVE_MAIS':
            return "Leve mais por menos"
        return "Valor não especificado"
    
    def _atualizar_status(self, promocao_id: int, novo_status: str):
        """Atualiza o status de uma promoção"""
        sucesso, msg = self.promocoes.atualizar_promocao(
            promocao_id,
            {"status": novo_status},
            st.session_state.usuario_nome
        )
        
        if sucesso:
            UIComponents.show_success_message(msg)
            # Recarregar lista
            if 'promocoes_filtradas' in st.session_state:
                del st.session_state.promocoes_filtradas
            st.rerun()
        else:
            UIComponents.show_error_message(msg)
    
    def _render_nova(self):
        """Renderiza formulário de nova promoção"""
        st.subheader("➕ Nova Promoção")

        with st.form("form_nova_promocao", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input(
                    "Nome da Promoção:*",
                    placeholder="Ex: Liquidação de Verão",
                    key="promo_nome"
                )

                tipo = st.selectbox(
                    "Tipo de Promoção:*",
                    ["DESCONTO_PERCENTUAL", "DESCONTO_FIXO", "LEVE_MAIS"],
                    key="promo_tipo",
                    format_func=lambda x: {
                        "DESCONTO_PERCENTUAL": "📉 Percentual",
                        "DESCONTO_FIXO": "💰 Valor Fixo",
                        "LEVE_MAIS": "🎁 Leve Mais"
                    }[x]
                )

            with col2:
                data_inicio = st.date_input(
                    "Data de Início:*",
                    value=date.today(),
                    key="promo_inicio"
                )

                data_fim = st.date_input(
                    "Data de Término:*",
                    value=date.today() + timedelta(days=30),
                    key="promo_fim"
                )

            col3, col4 = st.columns(2)

            with col3:
                if tipo in ["DESCONTO_PERCENTUAL", "DESCONTO_FIXO"]:
                    valor_desconto = st.number_input(
                        "Valor do Desconto:*",
                        min_value=0.01,
                        value=10.0,
                        step=0.01,
                        format="%.2f",
                        help="Percentual (%) ou valor em R$",
                        key="promo_valor"
                    )
                else:
                    valor_desconto = 0.0
                    st.info("Promoção do tipo 'Leve Mais' - configure manualmente")

            with col4:
                status = st.selectbox(
                    "Status:*",
                    ["PLANEJADA", "ATIVA"],
                    index=0,
                    key="promo_status"
                )

            descricao = st.text_area(
                "Descrição:*",
                placeholder="Descreva os detalhes da promoção...",
                height=100,
                key="promo_descricao"
            )

            st.markdown("*Campos obrigatórios")

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                submit = st.form_submit_button(
                    "💾 Criar Promoção",
                    type="primary"
                )

            with col_btn2:
                st.form_submit_button(
                    "🗑️ Cancelar",
                    type="secondary"
                )

            if submit:
                self._processar_criacao(nome, descricao, tipo, valor_desconto,
                                       data_inicio, data_fim, status)
    
    def _processar_criacao(self, nome, descricao, tipo, valor_desconto,
                          data_inicio, data_fim, status):
        """Processa criação de promoção"""
        if not nome.strip():
            UIComponents.show_error_message("Nome da promoção é obrigatório!")
            st.stop()

        if not descricao.strip():
            UIComponents.show_error_message("Descrição é obrigatória!")
            st.stop()

        if data_fim < data_inicio:
            UIComponents.show_error_message("Data de término deve ser posterior à data de início!")
            st.stop()

        if tipo in ["DESCONTO_PERCENTUAL", "DESCONTO_FIXO"] and valor_desconto <= 0:
            UIComponents.show_error_message("Valor do desconto deve ser maior que zero!")
            st.stop()

        sucesso, mensagem = self.promocoes.criar_promocao(
            nome=nome.strip(),
            descricao=descricao.strip(),
            tipo=tipo,
            valor_desconto=valor_desconto,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status=status,
            usuario=st.session_state.usuario_nome
        )

        if sucesso:
            UIComponents.show_success_message(mensagem)
            AccessibilityManager.announce_message("Promoção criada com sucesso")
            
            # Limpar cache
            if 'promocoes_filtradas' in st.session_state:
                del st.session_state.promocoes_filtradas
            
            st.rerun()
        else:
            UIComponents.show_error_message(mensagem)
    
    def _render_editar_promocao(self, promocao):
        """Renderiza formulário de edição de promoção"""
        st.markdown("---")
        st.subheader(f"✏️ Editando: {promocao['nome']}")

        with st.form(f"form_editar_promocao_{promocao['id']}"):
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input(
                    "Nome da Promoção:*",
                    value=promocao['nome'],
                    key=f"edit_nome_{promocao['id']}"
                )

                tipo = st.selectbox(
                    "Tipo de Promoção:*",
                    ["DESCONTO_PERCENTUAL", "DESCONTO_FIXO", "LEVE_MAIS"],
                    index=["DESCONTO_PERCENTUAL", "DESCONTO_FIXO", "LEVE_MAIS"].index(promocao['tipo']),
                    key=f"edit_tipo_{promocao['id']}"
                )

            with col2:
                data_inicio = st.date_input(
                    "Data de Início:*",
                    value=Formatters.parse_date(promocao['data_inicio']),
                    key=f"edit_inicio_{promocao['id']}"
                )

                data_fim = st.date_input(
                    "Data de Término:*",
                    value=Formatters.parse_date(promocao['data_fim']),
                    key=f"edit_fim_{promocao['id']}"
                )

            valor_desconto = st.number_input(
                "Valor do Desconto:*",
                min_value=0.01,
                value=float(promocao['valor_desconto']) if promocao['valor_desconto'] else 0.0,
                step=0.01,
                format="%.2f",
                key=f"edit_valor_{promocao['id']}"
            )

            status = st.selectbox(
                "Status:*",
                ["PLANEJADA", "ATIVA", "CONCLUÍDA", "CANCELADA"],
                index=["PLANEJADA", "ATIVA", "CONCLUÍDA", "CANCELADA"].index(promocao['status']),
                key=f"edit_status_{promocao['id']}"
            )

            descricao = st.text_area(
                "Descrição:*",
                value=promocao['descricao'],
                height=100,
                key=f"edit_descricao_{promocao['id']}"
            )

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                    dados = {
                        "nome": nome.strip(),
                        "descricao": descricao.strip(),
                        "tipo": tipo,
                        "valor_desconto": valor_desconto,
                        "data_inicio": data_inicio,
                        "data_fim": data_fim,
                        "status": status
                    }
                    
                    sucesso, msg = self.promocoes.atualizar_promocao(
                        int(promocao['id']),
                        dados,
                        st.session_state.usuario_nome
                    )
                    
                    if sucesso:
                        UIComponents.show_success_message(msg)
                        del st.session_state.promocao_editar
                        if 'promocoes_filtradas' in st.session_state:
                            del st.session_state.promocoes_filtradas
                        st.rerun()
                    else:
                        UIComponents.show_error_message(msg)

            with col_btn2:
                if st.form_submit_button("❌ Cancelar"):
                    del st.session_state.promocao_editar
                    st.rerun()
    
    def _render_modal_exclusao(self):
        """Renderiza modal de confirmação de exclusão"""
        promocao = st.session_state.promocao_excluir

        st.markdown("---")
        st.error("⚠️ **CONFIRMAÇÃO DE EXCLUSÃO**")

        st.markdown(f"""
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; padding: 15px; margin: 10px 0;">
            <h4 style="color: #856404;">Você está prestes a excluir permanentemente esta promoção:</h4>
            <ul>
                <li><strong>ID:</strong> {promocao['id']}</li>
                <li><strong>Nome:</strong> {promocao['nome']}</li>
                <li><strong>Tipo:</strong> {promocao['tipo']}</li>
                <li><strong>Período:</strong> {Formatters.formatar_data_br(promocao['data_inicio'])} a {Formatters.formatar_data_br(promocao['data_fim'])}</li>
            </ul>
            <p style="color: #dc3545; font-weight: bold;">Esta ação é IRREVERSÍVEL!</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("✅ Confirmar Exclusão", type="primary"):
                with st.spinner("Excluindo promoção..."):
                    sucesso, msg = self.promocoes.excluir_promocao(
                        int(promocao['id']),
                        st.session_state.usuario_nome
                    )
                    
                    if sucesso:
                        UIComponents.show_success_message(msg)
                        del st.session_state.promocao_excluir
                        if 'promocoes_filtradas' in st.session_state:
                            del st.session_state.promocoes_filtradas
                        st.rerun()
                    else:
                        UIComponents.show_error_message(msg)

        with col2:
            if st.button("❌ Cancelar"):
                del st.session_state.promocao_excluir
                st.rerun()