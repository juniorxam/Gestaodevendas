"""
dashboard.py - Página do painel de controle
"""

from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class DashboardPage:
    """Página do dashboard"""
    
    def __init__(self, db, relatorios, clientes, produtos, vendas):
        self.db = db
        self.relatorios = relatorios
        self.clientes = clientes
        self.produtos = produtos
        self.vendas = vendas
    
    def render(self):
        """Renderiza o dashboard"""
        st.markdown('<div id="main-content"></div>', unsafe_allow_html=True)
        st.title("📊 Painel de Controle - ElectroGest")
        UIComponents.breadcrumb("🏠 Início", "Dashboard")

        with UIComponents.show_loading_indicator("Carregando métricas..."):
            m = self.relatorios.get_metricas_gerais()

        # Cards de métricas
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            UIComponents.create_metric_card(
                "Clientes",
                m["total_clientes"],
                icon="👥",
                color="#3b82f6"
            )

        with col2:
            UIComponents.create_metric_card(
                "Vendas Hoje",
                m["vendas_hoje"],
                icon="💰",
                color="#10b981"
            )

        with col3:
            UIComponents.create_metric_card(
                "Faturamento Hoje",
                m["faturamento_hoje"],
                icon="📈",
                color="#8b5cf6"
            )

        with col4:
            UIComponents.create_metric_card(
                "Estoque Baixo",
                m["estoque_baixo"],
                icon="⚠️",
                color="#ef4444" if m["estoque_baixo"] > 0 else "#10b981"
            )

        # Abas de gráficos
        tab1, tab2, tab3 = st.tabs([
            "📈 Vendas e Faturamento",
            "🏆 Produtos Mais Vendidos",
            "💳 Formas de Pagamento"
        ])

        with tab1:
            with UIComponents.show_loading_indicator("Gerando gráfico..."):
                fig = self.relatorios.grafico_vendas_ultimos_30_dias()
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    UIComponents.show_info_message("Não há dados de vendas nos últimos 30 dias.")

        with tab2:
            with UIComponents.show_loading_indicator("Carregando dados..."):
                fig = self.relatorios.grafico_produtos_mais_vendidos(limite=10)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    UIComponents.show_info_message("Não há dados de produtos vendidos.")

        with tab3:
            with UIComponents.show_loading_indicator("Carregando dados..."):
                fig = self.relatorios.grafico_vendas_por_forma_pagamento()
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    UIComponents.show_info_message("Não há dados de formas de pagamento.")

        # Cards informativos
        st.markdown("---")
        col_info1, col_info2, col_info3 = st.columns(3)

        with col_info1:
            st.markdown("### 📦 Estoque")
            st.metric(
                "Total de Produtos",
                m["total_produtos"],
                delta=None
            )
            
            # Produtos em estoque baixo
            if m["estoque_baixo"] > 0:
                st.warning(f"⚠️ {m['estoque_baixo']} produtos com estoque baixo")
                
                # Link rápido para estoque - REMOVIDO width='stretch'
                if st.button("🔍 Ver estoque baixo", key="btn_estoque_baixo"):
                    st.session_state.pagina_atual = "estoque"
                    st.rerun()
            else:
                st.success("✅ Todos os produtos com estoque adequado")

        with col_info2:
            st.markdown("### 💰 Vendas")
            st.metric(
                "Ticket Médio (30 dias)",
                f"R$ {m['ticket_medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                delta=None
            )
            
            # Vendas hoje vs ontem
            ontem = (date.today() - timedelta(days=1)).isoformat()
            vendas_ontem = self.db.fetchone(
                "SELECT COUNT(*) as c, COALESCE(SUM(valor_total), 0) as total FROM vendas WHERE date(data_venda) = ?",
                (ontem,)
            )
            
            if vendas_ontem and vendas_ontem["c"] > 0:
                var_vendas = m["vendas_hoje"] - vendas_ontem["c"]
                var_faturamento = m["faturamento_hoje"] - vendas_ontem["total"]
                
                st.caption(f"Variação vs ontem: {var_vendas:+d} vendas | R$ {var_faturamento:+,.2f}")

        with col_info3:
            st.markdown("### 👥 Clientes")
            st.metric(
                "Total de Clientes",
                m["total_clientes"],
                delta=None
            )
            
            # Clientes com compras hoje
            clientes_hoje = self.db.fetchone(
                "SELECT COUNT(DISTINCT cliente_id) as c FROM vendas WHERE date(data_venda) = ? AND cliente_id IS NOT NULL",
                (date.today().isoformat(),)
            )
            
            if clientes_hoje and clientes_hoje["c"] > 0:
                st.caption(f"{clientes_hoje['c']} clientes compraram hoje")

        # Atalhos rápidos
        st.markdown("---")
        st.markdown("### ⚡ Atalhos Rápidos")
        
        col_atalho1, col_atalho2, col_atalho3, col_atalho4 = st.columns(4)
        
        with col_atalho1:
            # REMOVIDO width='stretch'
            if st.button("➕ Nova Venda", key="btn_nova_venda"):
                st.session_state.pagina_atual = "vendas"
                st.rerun()
        
        with col_atalho2:
            if st.button("📦 Novo Produto", key="btn_novo_produto"):
                st.session_state.pagina_atual = "produtos"
                st.rerun()
        
        with col_atalho3:
            if st.button("👤 Novo Cliente", key="btn_novo_cliente"):
                st.session_state.pagina_atual = "clientes"
                st.rerun()
        
        with col_atalho4:
            if st.button("📊 Relatórios", key="btn_relatorios"):
                st.session_state.pagina_atual = "relatorios"
                st.rerun()

        # Últimas vendas
        with st.expander("🔄 Últimas Vendas", expanded=False):
            ultimas_vendas = self.vendas.listar_vendas_por_periodo(
                data_inicio=date.today() - timedelta(days=7),
                data_fim=date.today(),
                limit=20
            )
            
            if not ultimas_vendas.empty:
                df_display = ultimas_vendas[['data_venda', 'cliente_nome', 'valor_total', 'forma_pagamento']].copy()
                df_display['data_venda'] = pd.to_datetime(df_display['data_venda']).dt.strftime('%d/%m/%Y %H:%M')
                df_display['valor_total'] = df_display['valor_total'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "data_venda": "Data/Hora",
                        "cliente_nome": "Cliente",
                        "valor_total": "Valor",
                        "forma_pagamento": "Pagamento"
                    }
                )
            else:
                st.info("Nenhuma venda nos últimos 7 dias.")