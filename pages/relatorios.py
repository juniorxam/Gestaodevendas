"""
relatorios.py - Página de relatórios
"""

from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil.relativedelta import relativedelta

from config import CONFIG
from core.security import Security, Formatters
from core.relatorio_service import RelatorioPDFService
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class RelatoriosPage:
    """Página de relatórios"""
    
    def __init__(self, db, relatorios, clientes, produtos, vendas):
        self.db = db
        self.relatorios = relatorios
        self.clientes = clientes
        self.produtos = produtos
        self.vendas = vendas
    
    def render(self):
        """Renderiza página de relatórios"""
        st.title("📊 Relatórios")
        UIComponents.breadcrumb("🏠 Início", "Relatórios")

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Vendas",
            "👥 Clientes",
            "📦 Produtos",
            "💰 Financeiro",
            "📋 Personalizado"
        ])

        with tab1:
            self._render_relatorio_vendas()

        with tab2:
            self._render_relatorio_clientes()

        with tab3:
            self._render_relatorio_produtos()

        with tab4:
            self._render_relatorio_financeiro()

        with tab5:
            self._render_relatorio_personalizado()
    
    def _render_relatorio_vendas(self):
        """Renderiza relatório de vendas"""
        st.subheader("📈 Relatório de Vendas")

        col1, col2, col3 = st.columns(3)

        with col1:
            periodo = st.selectbox(
                "Período:",
                ["Hoje", "Ontem", "Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês anterior", "Personalizado"],
                key="rel_vendas_periodo"
            )

        with col2:
            if periodo == "Personalizado":
                data_inicio = st.date_input(
                    "Data inicial:",
                    value=date.today() - timedelta(days=30),
                    key="rel_vendas_inicio"
                )
                data_fim = st.date_input(
                    "Data final:",
                    value=date.today(),
                    key="rel_vendas_fim"
                )
            else:
                data_inicio, data_fim = self._calcular_periodo(periodo)
                st.text_input(
                    "Período:",
                    value=f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                    disabled=True,
                    key="rel_vendas_periodo_display"
                )

        with col3:
            agrupar_por = st.selectbox(
                "Agrupar por:",
                ["dia", "semana", "mes"],
                index=0,
                key="rel_vendas_agrupar"
            )

        if st.button("📊 Gerar Relatório", type="primary", key="btn_rel_vendas"):
            with st.spinner("Gerando relatório..."):
                metricas = self.vendas.get_metricas_periodo(data_inicio, data_fim)
                
                df_vendas = self.relatorios.relatorio_vendas_periodo(
                    data_inicio, data_fim, agrupar_por
                )
                
                df_produtos = self.db.read_sql("""
                    SELECT 
                        p.nome as produto,
                        SUM(i.quantidade) as quantidade,
                        SUM(i.quantidade * i.preco_unitario) as valor_total
                    FROM itens_venda i
                    JOIN vendas v ON i.venda_id = v.id
                    JOIN produtos p ON i.produto_id = p.id
                    WHERE date(v.data_venda) BETWEEN ? AND ?
                    GROUP BY p.id
                    ORDER BY quantidade DESC
                    LIMIT 20
                """, (data_inicio.isoformat(), data_fim.isoformat()))
                
                st.session_state.rel_vendas_dados = {
                    "metricas": metricas,
                    "vendas": df_vendas,
                    "produtos": df_produtos,
                    "periodo": f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
                }

        if st.session_state.get('rel_vendas_dados'):
            dados = st.session_state.rel_vendas_dados
            metricas = dados['metricas']
            
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            
            with col_met1:
                st.metric("Total de Vendas", metricas['total_vendas'])
            
            with col_met2:
                st.metric("Faturamento", f"R$ {metricas['faturamento_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            with col_met3:
                st.metric("Ticket Médio", f"R$ {metricas['ticket_medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            with col_met4:
                st.metric("Clientes", metricas['clientes_unicos'])
            
            if not dados['vendas'].empty:
                st.subheader("📈 Evolução das Vendas")
                
                fig = px.line(
                    dados['vendas'],
                    x='periodo',
                    y='faturamento',
                    title='Faturamento por Período',
                    markers=True
                )
                fig.update_layout(
                    xaxis_title="Período",
                    yaxis_title="Faturamento (R$)",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            if metricas['formas_pagamento']:
                st.subheader("💳 Formas de Pagamento")
                
                df_pag = pd.DataFrame(metricas['formas_pagamento'])
                
                col_pag1, col_pag2 = st.columns(2)
                
                with col_pag1:
                    st.dataframe(
                        df_pag,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "forma_pagamento": "Forma",
                            "quantidade": "Vendas",
                            "valor_total": "Valor Total"
                        }
                    )
                
                with col_pag2:
                    fig_pag = px.pie(
                        df_pag,
                        values='valor_total',
                        names='forma_pagamento',
                        title='Distribuição por Forma de Pagamento'
                    )
                    st.plotly_chart(fig_pag, use_container_width=True)
            
            if not dados['produtos'].empty:
                st.subheader("🏆 Produtos Mais Vendidos")
                
                df_prod = dados['produtos'].head(10)
                
                fig_prod = px.bar(
                    df_prod,
                    x='quantidade',
                    y='produto',
                    orientation='h',
                    title='Top 10 Produtos Mais Vendidos',
                    labels={'quantidade': 'Quantidade Vendida', 'produto': ''}
                )
                fig_prod.update_layout(yaxis={'autorange': 'reversed'})
                st.plotly_chart(fig_prod, use_container_width=True)
            
            st.markdown("---")
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                if st.button("📥 Exportar CSV", key="btn_vendas_csv"):
                    csv = dados['vendas'].to_csv(index=False)
                    st.download_button(
                        "📥 Baixar CSV",
                        csv,
                        f"relatorio_vendas_{date.today().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        key="download_vendas_csv"
                    )
            
            with col_exp2:
                if st.button("📊 Exportar Excel", key="btn_vendas_excel"):
                    import io
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        dados['vendas'].to_excel(writer, sheet_name='Vendas', index=False)
                        if not dados['produtos'].empty:
                            dados['produtos'].to_excel(writer, sheet_name='Produtos', index=False)
                    
                    st.download_button(
                        "📊 Baixar Excel",
                        output.getvalue(),
                        f"relatorio_vendas_{date.today().strftime('%Y%m%d')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_vendas_excel"
                    )
            
            with col_exp3:
                if st.button("📄 Gerar PDF", key="btn_vendas_pdf"):
                    with st.spinner("Gerando PDF..."):
                        try:
                            pdf_bytes = RelatorioPDFService.gerar_relatorio_vendas_pdf(
                                CONFIG.logo_path,
                                metricas,
                                dados['periodo']
                            )
                            
                            st.download_button(
                                "📥 Baixar PDF",
                                data=pdf_bytes,
                                file_name=f"relatorio_vendas_{date.today().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                key="download_vendas_pdf"
                            )
                        except Exception as e:
                            st.error(f"Erro ao gerar PDF: {str(e)}")
    
    def _render_relatorio_clientes(self):
        """Renderiza relatório de clientes"""
        st.subheader("👥 Relatório de Clientes")

        col1, col2 = st.columns(2)

        with col1:
            periodo = st.selectbox(
                "Período de análise:",
                ["Últimos 30 dias", "Últimos 90 dias", "Últimos 180 dias", "Todos"],
                key="rel_clientes_periodo"
            )

        with col2:
            limite = st.number_input(
                "Número de clientes:",
                min_value=5,
                max_value=100,
                value=20,
                step=5,
                key="rel_clientes_limite"
            )

        if st.button("📊 Gerar Relatório", type="primary", key="btn_rel_clientes"):
            with st.spinner("Gerando relatório..."):
                df_top = self.relatorios.relatorio_clientes_top(limite=int(limite))
                stats = self.clientes.get_estatisticas()
                
                st.session_state.rel_clientes_dados = {
                    "top_clientes": df_top,
                    "estatisticas": stats
                }

        if st.session_state.get('rel_clientes_dados'):
            dados = st.session_state.rel_clientes_dados
            stats = dados['estatisticas']
            
            col_met1, col_met2, col_met3 = st.columns(3)
            
            with col_met1:
                st.metric("Total de Clientes", stats['total_clientes'])
            
            with col_met2:
                st.metric("Clientes com CPF", stats['clientes_com_cpf'])
            
            with col_met3:
                st.metric("Clientes com E-mail", stats['clientes_com_email'])
            
            if not dados['top_clientes'].empty:
                st.subheader(f"🏆 Top {len(dados['top_clientes'])} Clientes")
                
                df_display = dados['top_clientes'].copy()
                df_display['total_gasto'] = df_display['total_gasto'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                df_display['ticket_medio'] = df_display['ticket_medio'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                df_display['cpf'] = df_display['cpf'].apply(lambda x: Security.formatar_cpf(x) if x else "")
                df_display['ultima_compra'] = pd.to_datetime(df_display['ultima_compra']).dt.strftime('%d/%m/%Y')
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "nome": "Cliente",
                        "cpf": "CPF",
                        "total_compras": "Compras",
                        "total_gasto": "Total Gasto",
                        "ticket_medio": "Ticket Médio",
                        "ultima_compra": "Última Compra"
                    }
                )
                
                fig = px.bar(
                    dados['top_clientes'].head(10),
                    x='total_gasto',
                    y='nome',
                    orientation='h',
                    title='Top 10 Clientes por Gasto',
                    labels={'total_gasto': 'Total Gasto (R$)', 'nome': ''}
                )
                fig.update_layout(yaxis={'autorange': 'reversed'})
                st.plotly_chart(fig, use_container_width=True)
    
    def _render_relatorio_produtos(self):
        """Renderiza relatório de produtos"""
        st.subheader("📦 Relatório de Produtos")

        col1, col2 = st.columns(2)

        with col1:
            incluir_inativos = st.checkbox(
                "Incluir produtos inativos",
                value=False,
                key="rel_prod_inativos"
            )

        with col2:
            ordenar_por = st.selectbox(
                "Ordenar por:",
                ["nome", "quantidade_estoque", "preco_venda", "margem_percentual"],
                format_func=lambda x: {
                    "nome": "Nome",
                    "quantidade_estoque": "Estoque",
                    "preco_venda": "Preço",
                    "margem_percentual": "Margem de Lucro"
                }[x],
                key="rel_prod_ordenar"
            )

        if st.button("📊 Gerar Relatório", type="primary", key="btn_rel_produtos"):
            with st.spinner("Gerando relatório..."):
                df_estoque = self.relatorios.relatorio_estoque_completo()
                
                if not incluir_inativos:
                    df_estoque = df_estoque[df_estoque['situacao'] != 'INATIVO']
                
                df_estoque = df_estoque.sort_values(ordenar_por)
                
                st.session_state.rel_produtos_dados = df_estoque

        if st.session_state.get('rel_produtos_dados') is not None:
            df = st.session_state.rel_produtos_dados
            
            if not df.empty:
                col_met1, col_met2, col_met3, col_met4 = st.columns(4)
                
                with col_met1:
                    st.metric("Total de Produtos", len(df))
                
                with col_met2:
                    valor_total = df['valor_estoque_custo'].sum()
                    st.metric("Valor do Estoque", f"R$ {valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                with col_met3:
                    estoque_baixo = len(df[df['situacao'] == 'ESTOQUE BAIXO'])
                    st.metric("Estoque Baixo", estoque_baixo)
                
                with col_met4:
                    sem_estoque = len(df[df['situacao'] == 'SEM ESTOQUE'])
                    st.metric("Sem Estoque", sem_estoque)
                
                df_display = df.copy()
                for col in ['preco_custo', 'preco_venda', 'valor_estoque_custo', 'valor_estoque_venda']:
                    df_display[col] = df_display[col].apply(
                        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else ""
                    )
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )
    
    def _render_relatorio_financeiro(self):
        """Renderiza relatório financeiro"""
        st.subheader("💰 Relatório Financeiro")

        col1, col2 = st.columns(2)

        with col1:
            ano = st.selectbox(
                "Ano:",
                [2024, 2025, 2026],
                index=0,
                key="rel_fin_ano"
            )

        with col2:
            mes = st.selectbox(
                "Mês (opcional):",
                ["Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
                key="rel_fin_mes"
            )

        if st.button("📊 Gerar Relatório", type="primary", key="btn_rel_financeiro"):
            with st.spinner("Gerando relatório..."):
                if mes != "Todos":
                    meses = {
                        "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
                        "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
                        "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
                    }
                    mes_num = meses[mes]
                    data_inicio = date(ano, mes_num, 1)
                    if mes_num == 12:
                        data_fim = date(ano + 1, 1, 1) - timedelta(days=1)
                    else:
                        data_fim = date(ano, mes_num + 1, 1) - timedelta(days=1)
                else:
                    data_inicio = date(ano, 1, 1)
                    data_fim = date(ano, 12, 31)
                
                metricas = self.vendas.get_metricas_periodo(data_inicio, data_fim)
                
                df_diario = self.db.read_sql("""
                    SELECT 
                        date(data_venda) as data,
                        COUNT(*) as vendas,
                        SUM(valor_total) as faturamento
                    FROM vendas
                    WHERE date(data_venda) BETWEEN ? AND ?
                    GROUP BY date(data_venda)
                    ORDER BY data
                """, (data_inicio.isoformat(), data_fim.isoformat()))
                
                st.session_state.rel_financeiro_dados = {
                    "metricas": metricas,
                    "diario": df_diario,
                    "periodo": f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
                }

        if st.session_state.get('rel_financeiro_dados'):
            dados = st.session_state.rel_financeiro_dados
            metricas = dados['metricas']
            
            col_met1, col_met2, col_met3, col_met4 = st.columns(4)
            
            with col_met1:
                st.metric("Faturamento Total", f"R$ {metricas['faturamento_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            with col_met2:
                st.metric("Total de Vendas", metricas['total_vendas'])
            
            with col_met3:
                st.metric("Ticket Médio", f"R$ {metricas['ticket_medio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            with col_met4:
                st.metric("Clientes Únicos", metricas['clientes_unicos'])
            
            if not dados['diario'].empty:
                fig = px.bar(
                    dados['diario'],
                    x='data',
                    y='faturamento',
                    title='Faturamento Diário',
                    labels={'faturamento': 'Faturamento (R$)', 'data': 'Data'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                if len(dados['diario']) > 7:
                    dados['diario']['media_movel'] = dados['diario']['faturamento'].rolling(window=7).mean()
                    
                    fig2 = px.line(
                        dados['diario'],
                        x='data',
                        y=['faturamento', 'media_movel'],
                        title='Faturamento com Média Móvel (7 dias)',
                        labels={'value': 'Faturamento (R$)', 'data': 'Data', 'variable': 'Tipo'}
                    )
                    st.plotly_chart(fig2, use_container_width=True)
    
    def _render_relatorio_personalizado(self):
        """Renderiza relatório personalizado (SQL)"""
        st.subheader("📋 Relatório Personalizado")
        
        st.info("""
        Crie seu próprio relatório usando consultas SQL.
        **Apenas consultas SELECT são permitidas.**
        """)
        
        sql_query = st.text_area(
            "Digite sua consulta SQL:",
            placeholder="SELECT * FROM vendas LIMIT 10",
            height=150,
            key="sql_personalizado"
        )
        
        if st.button("🔍 Executar Consulta", type="primary", key="btn_exec_sql"):
            seguro, mensagem = Security.safe_select_only(sql_query)
            
            if not seguro:
                st.error(mensagem)
            else:
                try:
                    resultado = self.db.read_sql(sql_query)
                    
                    if not resultado.empty:
                        st.success(f"Consulta executada: {len(resultado)} registros")
                        st.dataframe(resultado, use_container_width=True)
                        
                        csv = resultado.to_csv(index=False)
                        st.download_button(
                            "📥 Exportar CSV",
                            csv,
                            "consulta_personalizada.csv",
                            "text/csv",
                            key="download_consulta_csv"
                        )
                    else:
                        st.info("Nenhum resultado encontrado.")
                        
                except Exception as e:
                    st.error(f"Erro na consulta: {str(e)}")
    
    def _calcular_periodo(self, periodo):
        """Calcula datas baseado no período selecionado"""
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
            if hoje.month == 1:
                return date(hoje.year - 1, 12, 1), date(hoje.year, hoje.month, 1) - timedelta(days=1)
            else:
                return date(hoje.year, hoje.month - 1, 1), date(hoje.year, hoje.month, 1) - timedelta(days=1)
        else:
            return hoje - timedelta(days=30), hoje