"""
estoque.py - Página de gestão de estoque
"""

from datetime import date, datetime
import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from core.relatorio_service import RelatorioPDFService
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class EstoquePage:
    """Página de gestão de estoque"""
    
    def __init__(self, db, produtos, estoque, auth):
        self.db = db
        self.produtos = produtos
        self.estoque = estoque
        self.auth = auth
    
    def render(self):
        """Renderiza página de estoque"""
        st.title("📦 Gestão de Estoque")
        UIComponents.breadcrumb("🏠 Início", "Estoque")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Visão Geral",
            "📥 Entrada",
            "📤 Saída",
            "⚖️ Ajuste"
        ])

        with tab1:
            self._render_visao_geral()

        with tab2:
            self._render_entrada()

        with tab3:
            self._render_saida()

        with tab4:
            self._render_ajuste()
    
    def _render_visao_geral(self):
        """Renderiza visão geral do estoque"""
        st.subheader("📊 Situação Atual do Estoque")

        # Estatísticas rápidas
        stats = self.produtos.get_estatisticas()
        
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total de Produtos",
                stats["total_produtos"],
                help="Produtos ativos no cadastro"
            )

        with col2:
            st.metric(
                "Valor do Estoque",
                f"R$ {stats['valor_estoque']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                help="Valor total baseado no preço de custo"
            )

        with col3:
            st.metric(
                "Estoque Baixo",
                stats["estoque_baixo"],
                delta=None,
                delta_color="inverse",
                help="Produtos com quantidade abaixo do mínimo"
            )

        with col4:
            st.metric(
                "Produtos Inativos",
                stats["total_inativos"],
                help="Produtos desativados"
            )

        st.markdown("---")

        # Produtos com estoque baixo
        st.subheader("⚠️ Produtos com Estoque Baixo")
        
        estoque_baixo = self.produtos.get_produtos_estoque_baixo()
        
        if not estoque_baixo.empty:
            df_display = estoque_baixo.copy()
            
            # Verificar se a coluna preco_custo existe
            if 'preco_custo' not in df_display.columns:
                # Buscar preços dos produtos
                precos = {}
                for idx, row in df_display.iterrows():
                    produto = self.db.fetchone(
                        "SELECT preco_custo FROM produtos WHERE id = ?",
                        (int(row['id']),)
                    )
                    if produto:
                        precos[idx] = produto['preco_custo']
                    else:
                        precos[idx] = 0.0
                
                df_display['preco_custo'] = pd.Series(precos)
            
            # Formatar valores
            df_display['quantidade_faltante'] = df_display.apply(
                lambda row: int(row['estoque_minimo'] - row['quantidade_estoque']) 
                if row['estoque_minimo'] > row['quantidade_estoque'] else 0,
                axis=1
            )
            
            # Aplicar estilo de destaque
            def destacar_urgente(row):
                if row['quantidade_estoque'] == 0:
                    return ['background-color: #ffebee'] * len(row)
                elif row['quantidade_estoque'] <= row['estoque_minimo'] / 2:
                    return ['background-color: #fff3e0'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                df_display.style.apply(destacar_urgente, axis=1),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": "ID",
                    "codigo_barras": "Cód. Barras",
                    "nome": "Produto",
                    "categoria": "Categoria",
                    "quantidade_estoque": "Estoque Atual",
                    "estoque_minimo": "Est. Mínimo",
                    "quantidade_faltante": "Necessário",
                    "preco_custo": "Preço Custo"
                }
            )
            
            # Sugestão de compra
            st.subheader("🛒 Sugestão de Compra")
            
            total_comprar = df_display['quantidade_faltante'].sum()
            
            # Calcular valor estimado com segurança
            valor_estimado = 0
            for idx, row in df_display.iterrows():
                if 'preco_custo' in row and pd.notna(row['preco_custo']):
                    valor_estimado += row['quantidade_faltante'] * float(row['preco_custo'])
            
            col_compra1, col_compra2 = st.columns(2)
            
            with col_compra1:
                st.info(f"**Total a comprar:** {int(total_comprar)} unidades")
            
            with col_compra2:
                st.info(f"**Valor estimado:** R$ {valor_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
            # Botão para exportar sugestão
            if st.button("📥 Exportar Sugestão de Compra", key="btn_exportar_compra"):
                csv_data = df_display[['nome', 'codigo_barras', 'quantidade_estoque', 'estoque_minimo', 'quantidade_faltante']].copy()
                if 'preco_custo' in df_display.columns:
                    csv_data['preco_custo'] = df_display['preco_custo']
                
                csv = csv_data.to_csv(index=False)
                st.download_button(
                    "📥 Baixar CSV",
                    csv,
                    f"sugestao_compra_{date.today().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key="download_sugestao_csv"
                )
        else:
            UIComponents.show_success_message("✅ Todos os produtos estão com estoque adequado!")

        st.markdown("---")

        # Últimas movimentações
        st.subheader("🔄 Últimas Movimentações")
        
        # Buscar logs de movimentação
        movimentacoes = self.db.read_sql("""
            SELECT 
                data_hora,
                usuario,
                acao,
                detalhes
            FROM logs
            WHERE modulo = 'ESTOQUE'
            ORDER BY data_hora DESC
            LIMIT 50
        """)
        
        if not movimentacoes.empty:
            df_mov = movimentacoes.copy()
            df_mov['data_hora'] = pd.to_datetime(df_mov['data_hora']).dt.strftime('%d/%m/%Y %H:%M:%S')
            
            st.dataframe(
                df_mov,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "data_hora": "Data/Hora",
                    "usuario": "Usuário",
                    "acao": "Ação",
                    "detalhes": "Detalhes"
                }
            )
        else:
            st.info("Nenhuma movimentação registrada.")

        # Relatório completo
        st.markdown("---")
        st.subheader("📊 Relatório Completo de Estoque")
        
        if st.button("📄 Gerar Relatório PDF", key="btn_relatorio_pdf"):
            with st.spinner("Gerando relatório..."):
                relatorio = self.estoque.get_relatorio_estoque()
                
                # Garantir que os dados estão no formato correto
                if 'data_geracao' not in relatorio:
                    relatorio['data_geracao'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                
                try:
                    pdf_bytes = RelatorioPDFService.gerar_relatorio_estoque_pdf(
                        CONFIG.logo_path,
                        relatorio
                    )
                    
                    st.download_button(
                        "📥 Baixar Relatório PDF",
                        data=pdf_bytes,
                        file_name=f"relatorio_estoque_{date.today().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        key="download_relatorio_pdf"
                    )
                    
                    st.success("✅ PDF gerado com sucesso!")
                    
                except Exception as e:
                    UIComponents.show_error_message(f"Erro ao gerar PDF: {str(e)}")
                    # Log para debug
                    import traceback
                    st.error(traceback.format_exc())
    
    def _render_entrada(self):
        """Renderiza formulário de entrada de estoque"""
        st.subheader("📥 Registrar Entrada de Estoque")
        
        st.info("""
        Use este formulário para registrar entradas de estoque (compras, devoluções, etc.).
        A quantidade será **adicionada** ao estoque atual.
        """)
        
        with st.form("form_entrada_estoque"):
            # Buscar produto
            busca_produto = st.text_input(
                "Buscar produto:",
                placeholder="Digite nome ou código de barras",
                key="busca_produto_entrada"
            )
            
            produto_selecionado = None
            if busca_produto:
                produtos = self.produtos.buscar_produtos(busca_produto, limit=10)
                
                if not produtos.empty:
                    opcoes = {}
                    for _, p in produtos.iterrows():
                        label = f"{p['nome']} - Estoque: {p['quantidade_estoque']}"
                        if p.get('codigo_barras'):
                            label += f" | Cód: {p['codigo_barras']}"
                        opcoes[label] = p['id']
                    
                    selecao = st.selectbox(
                        "Selecione o produto:",
                        options=list(opcoes.keys()),
                        key="select_produto_entrada"
                    )
                    
                    if selecao:
                        produto_id = opcoes[selecao]
                        produto_selecionado = produtos[produtos['id'] == produto_id].iloc[0]
            
            if produto_selecionado is not None:
                st.markdown(f"""
                **Produto selecionado:** {produto_selecionado['nome']}
                **Estoque atual:** {produto_selecionado['quantidade_estoque']} unidades
                **Preço de custo:** R$ {produto_selecionado['preco_custo']:,.2f}
                """)
                
                quantidade = st.number_input(
                    "Quantidade a adicionar:*",
                    min_value=1,
                    value=1,
                    step=1,
                    key="qtd_entrada"
                )
                
                observacao = st.text_area(
                    "Observação:",
                    placeholder="Ex: Nota fiscal 123456, fornecedor XYZ",
                    key="obs_entrada"
                )
                
                if st.form_submit_button("✅ Registrar Entrada", type="primary"):
                    sucesso, msg = self.estoque.entrada_estoque(
                        produto_id=int(produto_selecionado['id']),
                        quantidade=quantidade,
                        usuario=st.session_state.usuario_login,
                        observacao=observacao
                    )
                    
                    if sucesso:
                        UIComponents.show_success_message(msg)
                        AccessibilityManager.announce_message(f"Entrada de {quantidade} unidades registrada")
                        st.rerun()
                    else:
                        UIComponents.show_error_message(msg)
    
    def _render_saida(self):
        """Renderiza formulário de saída de estoque"""
        st.subheader("📤 Registrar Saída de Estoque")
        
        st.info("""
        Use este formulário para registrar saídas manuais de estoque (avarias, amostras, etc.).
        **Para vendas, utilize o módulo de Vendas.**
        A quantidade será **subtraída** do estoque atual.
        """)
        
        with st.form("form_saida_estoque"):
            # Buscar produto
            busca_produto = st.text_input(
                "Buscar produto:",
                placeholder="Digite nome ou código de barras",
                key="busca_produto_saida"
            )
            
            produto_selecionado = None
            if busca_produto:
                produtos = self.produtos.buscar_produtos(busca_produto, limit=10)
                
                if not produtos.empty:
                    opcoes = {}
                    for _, p in produtos.iterrows():
                        label = f"{p['nome']} - Estoque: {p['quantidade_estoque']}"
                        if p.get('codigo_barras'):
                            label += f" | Cód: {p['codigo_barras']}"
                        opcoes[label] = p['id']
                    
                    selecao = st.selectbox(
                        "Selecione o produto:",
                        options=list(opcoes.keys()),
                        key="select_produto_saida"
                    )
                    
                    if selecao:
                        produto_id = opcoes[selecao]
                        produto_selecionado = produtos[produtos['id'] == produto_id].iloc[0]
            
            if produto_selecionado is not None:
                estoque_atual = int(produto_selecionado['quantidade_estoque'])
                
                st.markdown(f"""
                **Produto selecionado:** {produto_selecionado['nome']}
                **Estoque atual:** {estoque_atual} unidades
                """)
                
                quantidade = st.number_input(
                    "Quantidade a retirar:*",
                    min_value=1,
                    max_value=estoque_atual if estoque_atual > 0 else 1,
                    value=min(1, estoque_atual) if estoque_atual > 0 else 0,
                    step=1,
                    key="qtd_saida"
                )
                
                motivo = st.selectbox(
                    "Motivo da saída:*",
                    ["Avaria", "Perda", "Amostra", "Devolução ao fornecedor", "Outro"],
                    key="motivo_saida"
                )
                
                observacao = st.text_area(
                    "Observação:",
                    placeholder="Detalhes adicionais sobre a saída",
                    key="obs_saida"
                )
                
                if st.form_submit_button("✅ Registrar Saída", type="primary"):
                    sucesso, msg = self.estoque.saida_estoque(
                        produto_id=int(produto_selecionado['id']),
                        quantidade=quantidade,
                        usuario=st.session_state.usuario_login,
                        observacao=f"{motivo} - {observacao}" if observacao else motivo
                    )
                    
                    if sucesso:
                        UIComponents.show_success_message(msg)
                        AccessibilityManager.announce_message(f"Saída de {quantidade} unidades registrada")
                        st.rerun()
                    else:
                        UIComponents.show_error_message(msg)
    
    def _render_ajuste(self):
        """Renderiza formulário de ajuste de estoque"""
        st.subheader("⚖️ Ajuste de Estoque")
        
        st.warning("""
        **Atenção:** Use esta função apenas para corrigir discrepâncias após contagem física.
        O ajuste define uma quantidade **exata** para o estoque, independente do valor atual.
        """)
        
        with st.form("form_ajuste_estoque"):
            # Buscar produto
            busca_produto = st.text_input(
                "Buscar produto:",
                placeholder="Digite nome ou código de barras",
                key="busca_produto_ajuste"
            )
            
            produto_selecionado = None
            if busca_produto:
                produtos = self.produtos.buscar_produtos(busca_produto, limit=10)
                
                if not produtos.empty:
                    opcoes = {}
                    for _, p in produtos.iterrows():
                        label = f"{p['nome']} - Estoque: {p['quantidade_estoque']}"
                        if p.get('codigo_barras'):
                            label += f" | Cód: {p['codigo_barras']}"
                        opcoes[label] = p['id']
                    
                    selecao = st.selectbox(
                        "Selecione o produto:",
                        options=list(opcoes.keys()),
                        key="select_produto_ajuste"
                    )
                    
                    if selecao:
                        produto_id = opcoes[selecao]
                        produto_selecionado = produtos[produtos['id'] == produto_id].iloc[0]
            
            if produto_selecionado is not None:
                estoque_atual = int(produto_selecionado['quantidade_estoque'])
                
                st.markdown(f"""
                **Produto selecionado:** {produto_selecionado['nome']}
                **Estoque atual:** {estoque_atual} unidades
                """)
                
                nova_quantidade = st.number_input(
                    "Nova quantidade em estoque:*",
                    min_value=0,
                    value=estoque_atual,
                    step=1,
                    key="nova_qtd_ajuste"
                )
                
                if nova_quantidade != estoque_atual:
                    diferenca = nova_quantidade - estoque_atual
                    if diferenca > 0:
                        st.info(f"Serão **adicionadas** {diferenca} unidades ao estoque.")
                    else:
                        st.warning(f"Serão **removidas** {abs(diferenca)} unidades do estoque.")
                
                motivo = st.text_area(
                    "Motivo do ajuste:*",
                    placeholder="Ex: Após contagem física, diferença identificada",
                    key="motivo_ajuste"
                )
                
                if st.form_submit_button("✅ Realizar Ajuste", type="primary"):
                    if not motivo.strip():
                        UIComponents.show_error_message("Motivo do ajuste é obrigatório!")
                        st.stop()
                    
                    sucesso, msg = self.estoque.ajuste_estoque(
                        produto_id=int(produto_selecionado['id']),
                        nova_quantidade=nova_quantidade,
                        usuario=st.session_state.usuario_login,
                        motivo=motivo
                    )
                    
                    if sucesso:
                        UIComponents.show_success_message(msg)
                        AccessibilityManager.announce_message(f"Estoque ajustado para {nova_quantidade} unidades")
                        st.rerun()
                    else:
                        UIComponents.show_error_message(msg)
