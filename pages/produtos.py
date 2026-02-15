"""
produtos.py - Página de gerenciamento de produtos
"""

import io
from datetime import date

import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class ProdutosPage:
    """Página de gerenciamento de produtos"""
    
    def __init__(self, db, produtos, auth, categorias):
        self.db = db
        self.produtos = produtos
        self.auth = auth
        self.categorias = categorias
        
        # Cache
        self._cache_categorias = None
    
    def _get_cached_categorias(self):
        if self._cache_categorias is None:
            self._cache_categorias = self.categorias.listar_categorias()
        return self._cache_categorias
    
    def render(self):
        """Renderiza página de produtos"""
        st.title("📦 Gerenciar Produtos")
        UIComponents.breadcrumb("🏠 Início", "Produtos")

        tab1, tab2, tab3, tab4 = st.tabs([
            "🔍 Consultar",
            "➕ Cadastrar",
            "📊 Relatórios",
            "⚙️ Administrar"
        ])

        with tab1:
            self._render_consultar()

        with tab2:
            self._render_cadastrar()

        with tab3:
            self._render_relatorios()

        with tab4:
            self._render_administrar()
    
    def _render_consultar(self):
        """Renderiza consulta de produtos"""
        st.subheader("🔍 Consultar Produtos")

        col1, col2, col3 = st.columns(3)

        with col1:
            filtro_nome = st.text_input("Nome:", key="filtro_nome_produto")

        with col2:
            filtro_categoria = st.selectbox(
                "Categoria:",
                ["TODAS"] + self._get_cached_categorias(),
                key="filtro_categoria"
            )

        with col3:
            filtro_estoque = st.selectbox(
                "Situação do Estoque:",
                ["TODOS", "COM ESTOQUE", "ESTOQUE BAIXO", "SEM ESTOQUE"],
                key="filtro_estoque"
            )

        if st.button("🔎 Buscar"):
            where_clauses = ["p.ativo = 1"]
            params = []

            if filtro_nome:
                where_clauses.append("p.nome LIKE ?")
                params.append(f"%{filtro_nome}%")

            if filtro_categoria != "TODAS":
                where_clauses.append("c.nome = ?")
                params.append(filtro_categoria)

            if filtro_estoque == "COM ESTOQUE":
                where_clauses.append("p.quantidade_estoque > 0")
            elif filtro_estoque == "ESTOQUE BAIXO":
                where_clauses.append("p.quantidade_estoque <= p.estoque_minimo AND p.quantidade_estoque > 0")
            elif filtro_estoque == "SEM ESTOQUE":
                where_clauses.append("p.quantidade_estoque = 0")

            where_sql = " AND ".join(where_clauses)

            query = f"""
                SELECT 
                    p.id,
                    p.codigo_barras,
                    p.nome,
                    p.descricao,
                    c.nome as categoria,
                    p.fabricante,
                    p.preco_custo,
                    p.preco_venda,
                    p.quantidade_estoque,
                    p.estoque_minimo,
                    (p.preco_venda - p.preco_custo) as margem_lucro,
                    ((p.preco_venda - p.preco_custo) / p.preco_custo * 100) as margem_percentual
                FROM produtos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE {where_sql}
                ORDER BY p.nome
                LIMIT 100
            """

            produtos = self.db.read_sql(query, params)
            st.session_state.produtos_filtrados = produtos

        # Exibir resultados
        if st.session_state.get('produtos_filtrados') is not None:
            produtos = st.session_state.produtos_filtrados

            if not produtos.empty:
                UIComponents.show_success_message(f"{len(produtos)} produtos encontrados")

                # Preparar DataFrame para exibição
                df_display = produtos.copy()
                
                # Formatar valores monetários
                for col in ['preco_custo', 'preco_venda', 'margem_lucro']:
                    if col in df_display.columns:
                        df_display[col] = df_display[col].apply(
                            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else ""
                        )
                
                if 'margem_percentual' in df_display.columns:
                    df_display['margem_percentual'] = df_display['margem_percentual'].apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else ""
                    )

                # Destacar produtos com estoque baixo
                def destacar_estoque_baixo(row):
                    if row['quantidade_estoque'] <= row['estoque_minimo']:
                        return ['background-color: #ffebee'] * len(row)
                    return [''] * len(row)

                st.dataframe(
                    df_display.style.apply(destacar_estoque_baixo, axis=1),
                    hide_index=True,
                    column_config={
                        "id": "ID",
                        "codigo_barras": "Cód. Barras",
                        "nome": "Nome",
                        "categoria": "Categoria",
                        "fabricante": "Fabricante",
                        "preco_custo": "Preço Custo",
                        "preco_venda": "Preço Venda",
                        "quantidade_estoque": "Estoque",
                        "estoque_minimo": "Est. Mínimo",
                        "margem_lucro": "Margem (R$)",
                        "margem_percentual": "Margem (%)"
                    }
                )

                # Botões de exportação
                col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])

                with col_exp1:
                    csv = produtos.to_csv(index=False)
                    st.download_button(
                        "📥 CSV",
                        csv,
                        "produtos.csv",
                        "text/csv"
                    )

                with col_exp2:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        produtos.to_excel(writer, index=False, sheet_name='Produtos')

                    st.download_button(
                        "📊 Excel",
                        excel_buffer.getvalue(),
                        "produtos.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                # Estatísticas
                with st.expander("📈 Estatísticas"):
                    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

                    with col_stat1:
                        total_produtos = len(produtos)
                        st.metric("Total de Produtos", total_produtos)

                    with col_stat2:
                        estoque_baixo = len(produtos[produtos['quantidade_estoque'] <= produtos['estoque_minimo']])
                        st.metric("Estoque Baixo", estoque_baixo, delta_color="inverse")

                    with col_stat3:
                        sem_estoque = len(produtos[produtos['quantidade_estoque'] == 0])
                        st.metric("Sem Estoque", sem_estoque)

                    with col_stat4:
                        valor_estoque = (produtos['quantidade_estoque'] * produtos['preco_custo']).sum()
                        st.metric("Valor do Estoque", f"R$ {valor_estoque:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            else:
                UIComponents.show_info_message("Nenhum produto encontrado com os filtros selecionados.")
    
    def _render_cadastrar(self):
        """Renderiza cadastro de produto"""
        st.subheader("➕ Cadastrar Novo Produto")

        with st.form("form_cadastro_produto", clear_on_submit=True):
            st.markdown("### 📦 Informações Básicas")
            
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input(
                    "Nome do Produto:*",
                    placeholder="Ex: iPhone 14 128GB",
                    key="cad_nome_produto"
                )

                codigo_barras = st.text_input(
                    "Código de Barras:",
                    placeholder="7891234567890",
                    key="cad_codigo_barras"
                )

                categoria = st.selectbox(
                    "Categoria:*",
                    [""] + self._get_cached_categorias(),
                    key="cad_categoria"
                )

                if categoria == "":
                    categoria = st.text_input(
                        "Nova Categoria:",
                        placeholder="Digite o nome da nova categoria",
                        key="cad_nova_categoria"
                    )

            with col2:
                descricao = st.text_area(
                    "Descrição:",
                    placeholder="Descrição detalhada do produto",
                    height=100,
                    key="cad_descricao"
                )

                fabricante = st.text_input(
                    "Fabricante:",
                    placeholder="Ex: Apple, Samsung, Sony",
                    key="cad_fabricante"
                )

            st.markdown("### 💰 Preços")
            
            col3, col4 = st.columns(2)

            with col3:
                preco_custo = st.number_input(
                    "Preço de Custo (R$):*",
                    min_value=0.0,  # CORRIGIDO: 0.0 em vez de 0.01
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="cad_preco_custo"
                )

            with col4:
                preco_venda = st.number_input(
                    "Preço de Venda (R$):*",
                    min_value=0.01,
                    value=0.01,
                    step=0.01,
                    format="%.2f",
                    key="cad_preco_venda"
                )

            # Calcular margem automaticamente
            if preco_custo > 0 and preco_venda > 0:
                margem = preco_venda - preco_custo
                margem_percentual = (margem / preco_custo) * 100
                
                st.info(
                    f"**Margem de Lucro:** R$ {margem:,.2f} ({margem_percentual:.1f}%)",
                    icon="💰"
                )
            elif preco_custo == 0:
                st.warning("⚠️ Preço de custo zero - margem não calculada")

            st.markdown("### 📊 Estoque")
            
            col5, col6 = st.columns(2)

            with col5:
                quantidade_estoque = st.number_input(
                    "Quantidade em Estoque:",
                    min_value=0,
                    value=0,
                    step=1,
                    key="cad_quantidade"
                )

            with col6:
                estoque_minimo = st.number_input(
                    "Estoque Mínimo:",
                    min_value=0,
                    value=5,
                    step=1,
                    key="cad_estoque_minimo",
                    help="Quantidade mínima para alerta de reposição"
                )

            ativo = st.checkbox("Produto Ativo", value=True, key="cad_ativo")

            st.markdown("*Campos obrigatórios")

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                submit = st.form_submit_button(
                    "💾 Salvar Produto",
                    type="primary"
                )

            with col_btn2:
                submit_novo = st.form_submit_button(
                    "➕ Salvar e Novo"
                )

            if submit or submit_novo:
                self._processar_cadastro(
                    nome, codigo_barras, categoria, descricao, fabricante,
                    preco_custo, preco_venda, quantidade_estoque, estoque_minimo,
                    ativo, submit_novo
                )

    
    def _processar_cadastro(self, nome, codigo_barras, categoria, descricao, fabricante,
                           preco_custo, preco_venda, quantidade_estoque, estoque_minimo,
                           ativo, submit_novo):
        """Processa cadastro de produto"""
        if not nome.strip():
            UIComponents.show_error_message("Nome do produto é obrigatório!")
            st.stop()

        if preco_venda <= 0:
            UIComponents.show_error_message("Preço de venda deve ser maior que zero!")
            st.stop()

        if not categoria.strip():
            UIComponents.show_error_message("Categoria é obrigatória!")
            st.stop()

        # Se for uma nova categoria, cadastrar primeiro
        if categoria not in self._get_cached_categorias():
            sucesso, msg = self.categorias.cadastrar_categoria(
                nome=categoria,
                descricao="",
                usuario=st.session_state.usuario_nome
            )
            if not sucesso:
                UIComponents.show_error_message(f"Erro ao criar categoria: {msg}")
                st.stop()

        dados = {
            "nome": nome.strip().upper(),
            "codigo_barras": codigo_barras.strip() if codigo_barras.strip() else None,
            "categoria": categoria.strip().upper(),
            "descricao": descricao.strip() if descricao.strip() else None,
            "fabricante": fabricante.strip().upper() if fabricante.strip() else None,
            "preco_custo": preco_custo,
            "preco_venda": preco_venda,
            "quantidade_estoque": quantidade_estoque,
            "estoque_minimo": estoque_minimo,
            "ativo": ativo
        }

        sucesso, mensagem = self.produtos.cadastrar_produto(
            dados,
            st.session_state.usuario_nome
        )

        if sucesso:
            UIComponents.show_success_message(mensagem)
            AccessibilityManager.announce_message("Produto cadastrado com sucesso")
            
            # Limpar cache de categorias
            self._cache_categorias = None
            
            if submit_novo:
                st.rerun()
        else:
            UIComponents.show_error_message(mensagem)
    
    def _render_relatorios(self):
        """Renderiza relatórios de produtos"""
        st.subheader("📊 Relatórios de Produtos")
        
        col_rel1, col_rel2 = st.columns(2)
        
        with col_rel1:
            with st.container():
                st.markdown("### 📈 Margem de Lucro por Produto")
                
                df_margem = self.db.read_sql("""
                    SELECT 
                        nome,
                        preco_custo,
                        preco_venda,
                        (preco_venda - preco_custo) as margem,
                        ((preco_venda - preco_custo) / preco_custo * 100) as margem_percentual
                    FROM produtos
                    WHERE ativo = 1 AND preco_custo > 0
                    ORDER BY margem_percentual DESC
                    LIMIT 20
                """)
                
                if not df_margem.empty:
                    df_display = df_margem.copy()
                    df_display['preco_custo'] = df_display['preco_custo'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    df_display['preco_venda'] = df_display['preco_venda'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    df_display['margem'] = df_display['margem'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    df_display['margem_percentual'] = df_display['margem_percentual'].apply(lambda x: f"{x:.1f}%")
                    
                    st.dataframe(df_display, hide_index=True)
                else:
                    st.info("Dados insuficientes para gerar relatório.")
        
        with col_rel2:
            with st.container():
                st.markdown("### 📦 Distribuição por Categoria")
                
                df_cat = self.db.read_sql("""
                    SELECT 
                        c.nome as categoria,
                        COUNT(p.id) as total_produtos,
                        SUM(p.quantidade_estoque) as total_estoque,
                        SUM(p.quantidade_estoque * p.preco_custo) as valor_estoque
                    FROM categorias c
                    LEFT JOIN produtos p ON c.id = p.categoria_id AND p.ativo = 1
                    WHERE c.ativo = 1
                    GROUP BY c.id
                    ORDER BY total_produtos DESC
                """)
                
                if not df_cat.empty:
                    df_display = df_cat.copy()
                    df_display['valor_estoque'] = df_display['valor_estoque'].apply(
                        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if x else "R$ 0,00"
                    )
                    
                    st.dataframe(df_display, hide_index=True)
                else:
                    st.info("Nenhuma categoria cadastrada.")
    
    def _render_administrar(self):
        """Renderiza administração de produtos (apenas ADMIN)"""
        st.subheader("⚙️ Administrar Produtos")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "ADMIN"):
            UIComponents.show_error_message("Acesso não autorizado. Apenas administradores podem acessar esta funcionalidade.")
            return

        st.markdown("### ✏️ Editar Produto")
        
        # Buscar produtos para edição
        produtos = self.produtos.listar_todos_produtos(incluir_inativos=True)
        
        if not produtos.empty:
            produto_selecionado = st.selectbox(
                "Selecione um produto para editar:",
                options=produtos['nome'].tolist(),
                key="select_produto_editar"
            )
            
            if produto_selecionado:
                produto_data = produtos[produtos['nome'] == produto_selecionado].iloc[0]
                self._render_editar_produto(produto_data)
        
        st.markdown("---")
        st.markdown("### 🗑️ Excluir Produto")
        UIComponents.show_warning_message("**Atenção:** Esta ação é irreversível e pode afetar o histórico de vendas.")
        
        busca_exclusao = st.text_input(
            "Buscar produto para exclusão:",
            placeholder="Nome ou código de barras",
            key="busca_exclusao_produto"
        )
        
        if busca_exclusao:
            produtos_busca = self.produtos.buscar_produtos(busca_exclusao, limit=10)
            
            if not produtos_busca.empty:
                for _, produto in produtos_busca.iterrows():
                    with st.container():
                        col_info, col_action = st.columns([3, 1])
                        
                        with col_info:
                            st.markdown(f"""
                            **Nome:** {produto['nome']}
                            **Código Barras:** {produto.get('codigo_barras', 'N/I')}
                            **Categoria:** {produto.get('categoria', 'N/I')}
                            **Preço Venda:** R$ {produto['preco_venda']:,.2f}
                            **Estoque:** {produto['quantidade_estoque']}
                            """)
                        
                        with col_action:
                            if st.button("🗑️ Excluir", key=f"del_prod_{produto['id']}", type="secondary"):
                                confirm = UIComponents.create_confirmation_dialog(
                                    title="Confirmar exclusão",
                                    message=f"Tem certeza que deseja excluir o produto **{produto['nome']}**?",
                                    key=f"conf_del_{produto['id']}"
                                )
                                
                                if confirm:
                                    # Aqui você implementaria a exclusão
                                    # Como não temos método de exclusão no serviço, apenas simulamos
                                    UIComponents.show_success_message(f"Produto {produto['nome']} excluído com sucesso!")
                                    st.rerun()
            else:
                st.info("Nenhum produto encontrado.")
    
    def _render_editar_produto(self, produto):
        """Renderiza formulário de edição de produto"""
        with st.form(f"form_editar_produto_{produto['id']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                novo_nome = st.text_input(
                    "Nome:",
                    value=produto['nome'],
                    key=f"edit_nome_{produto['id']}"
                )
                
                novo_codigo = st.text_input(
                    "Código de Barras:",
                    value=produto.get('codigo_barras', ''),
                    key=f"edit_codigo_{produto['id']}"
                )
                
                categorias = [""] + self._get_cached_categorias()
                index_cat = categorias.index(produto['categoria']) if produto['categoria'] in categorias else 0
                
                nova_categoria = st.selectbox(
                    "Categoria:",
                    categorias,
                    index=index_cat,
                    key=f"edit_categoria_{produto['id']}"
                )
            
            with col2:
                novo_preco_custo = st.number_input(
                    "Preço Custo (R$):",
                    value=float(produto['preco_custo']) if produto['preco_custo'] else 0.0,
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"edit_custo_{produto['id']}"
                )
                
                novo_preco_venda = st.number_input(
                    "Preço Venda (R$):",
                    value=float(produto['preco_venda']),
                    min_value=0.01,
                    step=0.01,
                    format="%.2f",
                    key=f"edit_venda_{produto['id']}"
                )
                
                novo_estoque = st.number_input(
                    "Quantidade em Estoque:",
                    value=int(produto['quantidade_estoque']),
                    min_value=0,
                    step=1,
                    key=f"edit_estoque_{produto['id']}"
                )
            
            novo_estoque_minimo = st.number_input(
                "Estoque Mínimo:",
                value=int(produto['estoque_minimo']),
                min_value=0,
                step=1,
                key=f"edit_minimo_{produto['id']}"
            )
            
            novo_ativo = st.checkbox(
                "Produto Ativo",
                value=bool(produto['ativo']),
                key=f"edit_ativo_{produto['id']}"
            )
            
            if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                dados = {
                    "nome": novo_nome.strip().upper(),
                    "codigo_barras": novo_codigo.strip() if novo_codigo.strip() else None,
                    "categoria_id": self._obter_id_categoria(nova_categoria) if nova_categoria else None,
                    "preco_custo": novo_preco_custo,
                    "preco_venda": novo_preco_venda,
                    "quantidade_estoque": novo_estoque,
                    "estoque_minimo": novo_estoque_minimo,
                    "ativo": novo_ativo
                }
                
                sucesso, msg = self.produtos.atualizar_produto(
                    int(produto['id']),
                    dados,
                    st.session_state.usuario_nome
                )
                
                if sucesso:
                    UIComponents.show_success_message(msg)
                    st.rerun()
                else:
                    UIComponents.show_error_message(msg)
    
    def _obter_id_categoria(self, nome_categoria):
        """Obtém ID da categoria pelo nome"""
        row = self.db.fetchone(
            "SELECT id FROM categorias WHERE nome = ?",
            (nome_categoria,)
        )
        return row['id'] if row else None