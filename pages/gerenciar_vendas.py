"""
gerenciar_vendas.py - Página para gerenciar e estornar vendas
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class GerenciarVendasPage:
    """Página para gerenciar vendas (estorno)"""
    
    def __init__(self, db, vendas, auth, audit):
        self.db = db
        self.vendas = vendas
        self.auth = auth
        self.audit = audit
    
    def render(self):
        """Renderiza página de gerenciamento de vendas"""
        st.title("📋 Gerenciar Vendas")
        UIComponents.breadcrumb("🏠 Início", "Gerenciar Vendas")

        nivel_acesso = st.session_state.get('nivel_acesso', 'VISUALIZADOR')
        if nivel_acesso not in ['ADMIN', 'OPERADOR']:
            UIComponents.show_error_message("Apenas administradores e operadores podem gerenciar vendas.")
            return

        tab1, tab2 = st.tabs(["🔍 Consultar e Estornar", "📊 Estatísticas"])

        with tab1:
            self._render_consulta()
        
        with tab2:
            self._render_estatisticas()
    
    def _render_consulta(self):
        """Renderiza consulta e estorno de vendas"""
        st.subheader("🔍 Consultar Vendas")

        col1, col2, col3 = st.columns(3)

        with col1:
            periodo = st.selectbox(
                "Período:",
                ["Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês anterior", "Personalizado"],
                key="periodo_consulta_venda"
            )

        with col2:
            if periodo == "Personalizado":
                data_inicio = st.date_input(
                    "Data inicial:",
                    value=date.today() - timedelta(days=30),
                    key="data_inicio_consulta_venda"
                )
                data_fim = st.date_input(
                    "Data final:",
                    value=date.today(),
                    key="data_fim_consulta_venda"
                )
            else:
                data_inicio, data_fim = self._calcular_periodo(periodo)
                st.text_input("Período:", value=f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}", disabled=True)

        with col3:
            if st.session_state.nivel_acesso == 'ADMIN':
                usuarios_df = self.db.read_sql(
                    "SELECT login, nome FROM usuarios WHERE ativo = 1 ORDER BY nome"
                )
                usuarios_list = ["Todos"] + [f"{row['nome']} ({row['login']})" for _, row in usuarios_df.iterrows()]
                usuario_filtro = st.selectbox(
                    "Vendedor:",
                    usuarios_list,
                    key="usuario_filtro_venda"
                )
                
                if usuario_filtro != "Todos":
                    login = usuario_filtro.split('(')[-1].replace(')', '')
                else:
                    login = None
            else:
                login = st.session_state.usuario_login
                st.info(f"Mostrando apenas suas vendas: {st.session_state.usuario_nome}")

        if st.button("🔍 Buscar Vendas", type="primary"):
            with st.spinner("Buscando vendas..."):
                df = self.vendas.listar_vendas_por_periodo(
                    data_inicio, 
                    data_fim,
                    usuario=login if login != "Todos" else None,
                    limit=500
                )

                if not df.empty:
                    st.session_state.vendas_gerenciar = df
                    UIComponents.show_success_message(f"Encontradas {len(df)} vendas")
                else:
                    UIComponents.show_warning_message("Nenhuma venda encontrada no período.")
                    st.session_state.vendas_gerenciar = None

        if st.session_state.get('vendas_gerenciar') is not None:
            self._render_tabela_vendas(st.session_state.vendas_gerenciar)
    
    def _calcular_periodo(self, periodo):
        """Calcula datas baseado no período selecionado"""
        hoje = date.today()
        
        if periodo == "Últimos 7 dias":
            return hoje - timedelta(days=7), hoje
        elif periodo == "Últimos 30 dias":
            return hoje - timedelta(days=30), hoje
        elif periodo == "Este mês":
            return date(hoje.year, hoje.month, 1), hoje
        elif periodo == "Mês anterior":
            if hoje.month == 1:
                return date(hoje.year - 1, 12, 1), date(hoje.year, hoje.month, 1) - timedelta(days=1)
            else:
                return date(hoje.year, hoje.month - 1, 1), date(hoje.year, hoje.month, 1) - timedelta(days=1)
        else:
            return hoje - timedelta(days=30), hoje
    
    def _render_tabela_vendas(self, df):
        """Renderiza tabela de vendas com opção de estorno"""
        st.subheader("📋 Vendas Encontradas")

        # Paginação
        items_per_page = 10
        total_items = len(df)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

        if 'page_gerenciar_vendas' not in st.session_state:
            st.session_state.page_gerenciar_vendas = 1

        if st.session_state.page_gerenciar_vendas > total_pages:
            st.session_state.page_gerenciar_vendas = total_pages

        col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 1, 2])
        
        with col1:
            st.write(f"Página {st.session_state.page_gerenciar_vendas} de {total_pages}")
        
        with col2:
            if st.button("◀️", disabled=st.session_state.page_gerenciar_vendas <= 1, key="prev_page_vendas"):
                st.session_state.page_gerenciar_vendas -= 1
                st.rerun()
        
        with col3:
            st.write(f"Mostrando {min(items_per_page, total_items)} vendas por página")
        
        with col4:
            if st.button("▶️", disabled=st.session_state.page_gerenciar_vendas >= total_pages, key="next_page_vendas"):
                st.session_state.page_gerenciar_vendas += 1
                st.rerun()
        
        with col5:
            go_to_page = st.number_input(
                "Ir para página",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.page_gerenciar_vendas,
                step=1,
                key="go_to_page_vendas",
                label_visibility="collapsed"
            )
            if go_to_page != st.session_state.page_gerenciar_vendas:
                st.session_state.page_gerenciar_vendas = go_to_page
                st.rerun()

        # Índices da página atual
        start_idx = (st.session_state.page_gerenciar_vendas - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)

        # Preparar DataFrame para exibição
        df_display = df.iloc[start_idx:end_idx].copy()
        df_display['data_venda'] = pd.to_datetime(df_display['data_venda']).dt.strftime('%d/%m/%Y %H:%M')
        df_display['valor_total'] = df_display['valor_total'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df_display['cliente_nome'] = df_display['cliente_nome'].fillna('Não identificado')

        # Exibir vendas da página
        for idx, row in df_display.iterrows():
            with st.container():
                st.markdown(f"""
                <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <strong>Venda #{row['id']}</strong> - {row['data_venda']}
                        </div>
                        <div>
                            <strong>Valor:</strong> {row['valor_total']}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col_info, col_action = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"""
                    **Cliente:** {row['cliente_nome']}
                    **Forma de pagamento:** {row['forma_pagamento']}
                    **Itens:** {row['total_itens']}
                    **Vendedor:** {row['usuario_registro']}
                    """)
                
                with col_action:
                    pode_estornar = (
                        st.session_state.nivel_acesso == 'ADMIN' or 
                        row['usuario_registro'] == st.session_state.usuario_nome
                    )
                    
                    if pode_estornar:
                        button_key = f"estornar_btn_{row['id']}_{idx}"
                        if st.button("↩️ Estornar", key=button_key, type="secondary"):
                            st.session_state.venda_estornar = {
                                'id': int(row['id']),
                                'valor': row['valor_total'],
                                'data': row['data_venda'],
                                'cliente': row['cliente_nome']
                            }
                            st.rerun()
                    else:
                        st.caption("🔒 Sem permissão")
                
                st.markdown("---")

        # Modal de confirmação de estorno
        if 'venda_estornar' in st.session_state:
            self._render_modal_estorno()
    
    def _render_modal_estorno(self):
        """Renderiza modal de confirmação de estorno"""
        venda = st.session_state.venda_estornar
        
        st.markdown("---")
        st.error("⚠️ **CONFIRMAÇÃO DE ESTORNO**")
        
        st.markdown(f"""
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; padding: 15px; margin: 10px 0;">
            <h4 style="color: #856404;">Você está prestes a estornar esta venda:</h4>
            <ul>
                <li><strong>Venda #:</strong> {venda['id']}</li>
                <li><strong>Data:</strong> {venda['data']}</li>
                <li><strong>Cliente:</strong> {venda['cliente']}</li>
                <li><strong>Valor:</strong> {venda['valor']}</li>
            </ul>
            <p style="color: #dc3545; font-weight: bold;">
                O estorno irá:
                - Remover a venda do sistema
                - Devolver os itens ao estoque
                - Esta ação é IRREVERSÍVEL
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        motivo = st.text_area(
            "Motivo do estorno (opcional, mas recomendado):",
            placeholder="Ex: Cliente desistiu, erro na venda, troca...",
            key="motivo_estorno",
            height=100
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✅ Confirmar Estorno", type="primary"):
                with st.spinner("Estornando venda..."):
                    # Verificar se a venda ainda existe
                    venda_exists = self.db.fetchone(
                        "SELECT id FROM vendas WHERE id = ?",
                        (venda['id'],)
                    )
                    
                    if not venda_exists:
                        UIComponents.show_error_message(f"Venda #{venda['id']} não encontrada. Pode ter sido estornada por outro usuário.")
                        del st.session_state.venda_estornar
                        st.rerun()
                    
                    sucesso, mensagem = self.vendas.estornar_venda(
                        venda_id=venda['id'],
                        usuario=st.session_state.usuario_login,
                        motivo=motivo
                    )
                    
                    if sucesso:
                        UIComponents.show_success_message(mensagem)
                        AccessibilityManager.announce_message(f"Venda #{venda['id']} estornada com sucesso")
                        del st.session_state.venda_estornar
                        if 'vendas_gerenciar' in st.session_state:
                            del st.session_state.vendas_gerenciar
                        st.session_state.page_gerenciar_vendas = 1
                        st.rerun()
                    else:
                        UIComponents.show_error_message(mensagem)
        
        with col2:
            if st.button("❌ Cancelar"):
                del st.session_state.venda_estornar
                st.rerun()
    
    def _render_estatisticas(self):
        """Renderiza estatísticas de vendas e estornos"""
        st.subheader("📊 Estatísticas de Vendas")

        # Total de vendas
        total = self.db.fetchone("SELECT COUNT(*) as total FROM vendas")
        total_vendas = total['total'] if total else 0

        # Vendas por vendedor
        df_por_vendedor = self.db.read_sql("""
            SELECT 
                usuario_registro as vendedor,
                COUNT(*) as total_vendas,
                SUM(valor_total) as valor_total,
                MIN(data_venda) as primeira_venda,
                MAX(data_venda) as ultima_venda
            FROM vendas
            WHERE usuario_registro IS NOT NULL
            GROUP BY usuario_registro
            ORDER BY total_vendas DESC
        """)

        # Vendas por mês
        df_por_mes = self.db.read_sql("""
            SELECT 
                strftime('%Y-%m', data_venda) as mes,
                COUNT(*) as total_vendas,
                SUM(valor_total) as faturamento
            FROM vendas
            GROUP BY mes
            ORDER BY mes DESC
            LIMIT 12
        """)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total de Vendas", f"{total_vendas:,}")

        with col2:
            vendedores_ativos = len(df_por_vendedor)
            st.metric("Vendedores Ativos", vendedores_ativos)

        with col3:
            if not df_por_mes.empty:
                media_mensal = df_por_mes['total_vendas'].mean()
                st.metric("Média Mensal", f"{media_mensal:.0f}")

        st.subheader("📋 Vendas por Vendedor")
        if not df_por_vendedor.empty:
            df_display = df_por_vendedor.copy()
            df_display['valor_total'] = df_display['valor_total'].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            df_display['primeira_venda'] = pd.to_datetime(df_display['primeira_venda']).dt.strftime('%d/%m/%Y')
            df_display['ultima_venda'] = pd.to_datetime(df_display['ultima_venda']).dt.strftime('%d/%m/%Y')
            
            st.dataframe(
                df_display,
                hide_index=True,
                column_config={
                    "vendedor": "Vendedor",
                    "total_vendas": "Total de Vendas",
                    "valor_total": "Faturamento",
                    "primeira_venda": "Primeira Venda",
                    "ultima_venda": "Última Venda"
                }
            )

        # Logs de estorno
        with st.expander("📝 Logs de Estornos (últimos 30 dias)"):
            logs = self.db.read_sql("""
                SELECT 
                    data_hora,
                    usuario,
                    detalhes
                FROM logs
                WHERE acao = 'Estornou venda'
                    AND data_hora >= datetime('now', '-30 days')
                ORDER BY data_hora DESC
                LIMIT 100
            """)

            if not logs.empty:
                logs['data_hora'] = pd.to_datetime(logs['data_hora']).dt.strftime('%d/%m/%Y %H:%M:%S')
                st.dataframe(logs, hide_index=True)
                st.info(f"Total de estornos nos últimos 30 dias: {len(logs)}")
            else:
                st.info("Nenhum estorno registrado nos últimos 30 dias.")