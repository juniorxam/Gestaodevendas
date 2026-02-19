"""
produtividade.py - Página de relatório de produtividade por vendedor
"""

from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil.relativedelta import relativedelta

from config import CONFIG
from core.security import Formatters
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class ProdutividadePage:
    """Página de relatório de produtividade por vendedor"""

    def __init__(self, db, auth):
        self.db = db
        self.auth = auth

    def render(self):
        """Renderiza página de produtividade"""
        st.title("📊 Relatório de Produtividade - Vendedores")
        UIComponents.breadcrumb("🏠 Início", "Produtividade")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "OPERADOR"):
            UIComponents.show_error_message("Apenas operadores e administradores podem acessar este relatório.")
            return

        col1, col2, col3 = st.columns(3)

        with col1:
            periodo = st.selectbox(
                "Período:",
                ["Hoje", "Ontem", "Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês anterior", "Personalizado"],
                key="filtro_periodo_prod"
            )

        with col2:
            if periodo == "Personalizado":
                data_inicio = st.date_input(
                    "Data inicial:",
                    value=date.today() - timedelta(days=30),
                    key="data_inicio_prod"
                )
                data_fim = st.date_input(
                    "Data final:",
                    value=date.today(),
                    key="data_fim_prod"
                )
            else:
                data_inicio, data_fim = self._calcular_periodo(periodo)
                st.text_input(
                    "Período:",
                    value=f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                    disabled=True,
                    key="periodo_display"
                )

        with col3:
            incluir_inativos = st.checkbox(
                "Incluir vendedores sem vendas",
                value=False,
                key="incluir_inativos_prod"
            )

        if st.button("📊 Gerar Relatório", type="primary", key="btn_gerar_relatorio"):
            with st.spinner("Gerando relatório de produtividade..."):
                self._gerar_relatorio(data_inicio, data_fim, incluir_inativos)

    def _calcular_periodo(self, periodo):
        """Calcula a data de início baseada no período selecionado"""
        hoje = date.today()

        if periodo == "Hoje":
            return hoje, hoje
        elif periodo == "Ontem":
            ontem = hoje - timedelta(days=1)
            return ontem, ontem
        elif periodo == "Últimos 7 dias":
            return hoje - timedelta(days=7), hoje
        elif periodo == "Últimos 30 dias":
            return hoje - timedelta(days=30), hoje
        elif periodo == "Este mês":
            return date(hoje.year, hoje.month, 1), hoje
        elif periodo == "Mês anterior":
            ultimo_mes = hoje - relativedelta(months=1)
            return date(ultimo_mes.year, ultimo_mes.month, 1), date(hoje.year, hoje.month, 1) - timedelta(days=1)
        else:
            return hoje - timedelta(days=30), hoje

    def _gerar_relatorio(self, data_inicio, data_fim, incluir_inativos):
        """Gera o relatório de produtividade"""
        
        # CORREÇÃO: Query corrigida - usando u.login para juntar com vendas
        query = """
            SELECT 
                u.nome as vendedor,
                u.login,
                u.nivel_acesso,
                COUNT(DISTINCT v.id) as total_vendas,
                COALESCE(SUM(v.valor_total), 0) as valor_total_vendido,
                COALESCE(AVG(v.valor_total), 0) as ticket_medio,
                COUNT(DISTINCT v.cliente_id) as clientes_atendidos,
                COUNT(i.id) as itens_vendidos,
                MIN(v.data_venda) as primeira_venda,
                MAX(v.data_venda) as ultima_venda
            FROM usuarios u
            LEFT JOIN vendas v ON u.login = v.usuario_registro 
                AND date(v.data_venda) BETWEEN ? AND ?
            LEFT JOIN itens_venda i ON v.id = i.venda_id
            WHERE u.ativo = 1
            GROUP BY u.login, u.nome, u.nivel_acesso
        """
        
        params = [data_inicio.isoformat(), data_fim.isoformat()]
        
        # Aplicar filtro HAVING depois do GROUP BY
        if not incluir_inativos:
            query += " HAVING total_vendas > 0"
        
        query += " ORDER BY valor_total_vendido DESC"
        
        df = self.db.read_sql(query, params)

        if df.empty or (df['total_vendas'].sum() == 0 and not incluir_inativos):
            UIComponents.show_warning_message(
                f"Nenhum registro encontrado no período de "
                f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
            )
            return

        # Métricas gerais
        st.subheader("📈 Métricas Gerais do Período")

        total_vendas = int(df['total_vendas'].sum())
        total_valor = float(df['valor_total_vendido'].sum())
        vendedores_ativos = len(df[df['total_vendas'] > 0])
        ticket_medio_geral = total_valor / total_vendas if total_vendas > 0 else 0

        col_met1, col_met2, col_met3, col_met4 = st.columns(4)

        with col_met1:
            st.metric("Total de Vendas", f"{total_vendas:,}")

        with col_met2:
            st.metric("Faturamento Total", f"R$ {total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        with col_met3:
            st.metric("Vendedores Ativos", vendedores_ativos)

        with col_met4:
            st.metric("Ticket Médio Geral", f"R$ {ticket_medio_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        st.markdown("---")

        # Ranking de produtividade
        st.subheader("🏆 Ranking de Vendas por Vendedor")

        if not df.empty:
            df_ranking = df[df['total_vendas'] > 0].copy()

            if not df_ranking.empty:
                # Adicionar coluna de participação percentual
                df_ranking['participacao'] = (df_ranking['valor_total_vendido'] / total_valor * 100).round(1)
                df_ranking['posicao'] = range(1, len(df_ranking) + 1)

                # Formatar valores
                df_display = df_ranking.copy()
                df_display['valor_total_vendido'] = df_display['valor_total_vendido'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                df_display['ticket_medio'] = df_display['ticket_medio'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                df_display['participacao'] = df_display['participacao'].apply(lambda x: f"{x}%")

                # Gráfico de barras - Top 10
                fig = px.bar(
                    df_ranking.head(10),
                    x='vendedor',
                    y='valor_total_vendido',
                    title='Top 10 Vendedores por Faturamento',
                    labels={'valor_total_vendido': 'Faturamento (R$)', 'vendedor': 'Vendedor'},
                    color='valor_total_vendido',
                    color_continuous_scale='viridis',
                    text=df_ranking.head(10)['total_vendas'].apply(lambda x: f"{x} vendas")
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

                # Tabela completa
                st.dataframe(
                    df_display[[
                        'posicao', 'vendedor', 'login', 'nivel_acesso',
                        'total_vendas', 'valor_total_vendido', 'clientes_atendidos',
                        'itens_vendidos', 'ticket_medio', 'participacao'
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "posicao": "🏆 Pos.",
                        "vendedor": "Vendedor",
                        "login": "Login",
                        "nivel_acesso": "Nível",
                        "total_vendas": "Vendas",
                        "valor_total_vendido": "Faturamento",
                        "clientes_atendidos": "Clientes",
                        "itens_vendidos": "Itens",
                        "ticket_medio": "Ticket Médio",
                        "participacao": "Part. (%)"
                    }
                )

                # Vendedores sem vendas
                df_inativos = df[df['total_vendas'] == 0]
                if not df_inativos.empty and incluir_inativos:
                    with st.expander(f"👤 Vendedores sem vendas no período ({len(df_inativos)})"):
                        st.dataframe(
                            df_inativos[['vendedor', 'login', 'nivel_acesso']],
                            use_container_width=True,
                            hide_index=True
                        )

            # Detalhamento por vendedor
            st.markdown("---")
            st.subheader("📋 Detalhamento por Vendedor")

            vendedores_lista = df_ranking['vendedor'].tolist() if not df_ranking.empty else []
            if vendedores_lista:
                vendedor_selecionado = st.selectbox(
                    "Selecione um vendedor para ver detalhes:",
                    vendedores_lista,
                    key="select_vendedor_detalhe"
                )

                if vendedor_selecionado:
                    vendedor_data = df_ranking[df_ranking['vendedor'] == vendedor_selecionado].iloc[0]

                    # Detalhamento das vendas do vendedor - CORREÇÃO: usar login
                    query_detalhe = """
                        SELECT 
                            v.id,
                            v.data_venda,
                            v.valor_total,
                            v.forma_pagamento,
                            c.nome as cliente_nome,
                            COUNT(i.id) as total_itens
                        FROM vendas v
                        LEFT JOIN clientes c ON v.cliente_id = c.id
                        LEFT JOIN itens_venda i ON v.id = i.venda_id
                        WHERE v.usuario_registro = ? 
                            AND date(v.data_venda) BETWEEN ? AND ?
                        GROUP BY v.id
                        ORDER BY v.data_venda DESC
                    """

                    df_detalhe = self.db.read_sql(
                        query_detalhe,
                        (vendedor_data['login'], data_inicio.isoformat(), data_fim.isoformat())
                    )

                    if not df_detalhe.empty:
                        df_detalhe['data_venda'] = pd.to_datetime(df_detalhe['data_venda']).dt.strftime('%d/%m/%Y %H:%M')
                        df_detalhe['valor_total'] = df_detalhe['valor_total'].apply(
                            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        )

                        st.dataframe(
                            df_detalhe,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "id": "Venda #",
                                "data_venda": "Data",
                                "cliente_nome": "Cliente",
                                "valor_total": "Valor",
                                "forma_pagamento": "Pagamento",
                                "total_itens": "Itens"
                            }
                        )

                        # Gráfico de atividades por dia
                        df_detalhe['data'] = pd.to_datetime(df_detalhe['data_venda'], format='%d/%m/%Y %H:%M').dt.date
                        atividades_por_dia = df_detalhe.groupby('data').size().reset_index(name='quantidade')

                        if not atividades_por_dia.empty:
                            fig_dia = px.bar(
                                atividades_por_dia,
                                x='data',
                                y='quantidade',
                                title=f'Vendas por Dia - {vendedor_selecionado}',
                                labels={'quantidade': 'Número de Vendas', 'data': 'Data'},
                                text='quantidade'
                            )
                            fig_dia.update_traces(textposition='outside')
                            st.plotly_chart(fig_dia, use_container_width=True)

            # Exportar relatório
            st.markdown("---")
            st.subheader("📥 Exportar Relatório")

            col_exp1, col_exp2 = st.columns(2)

            with col_exp1:
                csv = df_ranking.to_csv(index=False)
                st.download_button(
                    "📥 CSV - Ranking",
                    csv,
                    f"produtividade_ranking_{date.today().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key="download_csv_ranking"
                )

            with col_exp2:
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_ranking.to_excel(writer, sheet_name='Ranking', index=False)
                    if 'df_detalhe' in locals() and not df_detalhe.empty:
                        df_detalhe.to_excel(writer, sheet_name='Detalhes', index=False)

                st.download_button(
                    "📊 Excel Completo",
                    output.getvalue(),
                    f"produtividade_completa_{date.today().strftime('%Y%m%d')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_completo"
                )
