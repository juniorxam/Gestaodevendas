"""
vendas.py - Página de registro de vendas
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from core.auth_service import AuditLog
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class VendasPage:
    """Página de vendas - PDV"""
    
    def __init__(self, db, vendas, clientes, produtos, promocoes, auth):
        self.db = db
        self.vendas = vendas
        self.clientes = clientes
        self.produtos = produtos
        self.promocoes = promocoes
        self.auth = auth
        
        # Cache
        self._carrinho_key = "carrinho_compras"
        self._cliente_selecionado_key = "cliente_venda_atual"
        
        # Inicializar carrinho na sessão
        if self._carrinho_key not in st.session_state:
            st.session_state[self._carrinho_key] = []
        
        if self._cliente_selecionado_key not in st.session_state:
            st.session_state[self._cliente_selecionado_key] = None
    
    def render(self):
        """Renderiza página de vendas"""
        st.title("💰 Ponto de Venda - PDV")
        UIComponents.breadcrumb("🏠 Início", "Vendas")

        tab1, tab2, tab3 = st.tabs([
            "💲 PDV",
            "👥 Venda para Cliente",
            "📁 Histórico"
        ])

        with tab1:
            self._render_pdv()

        with tab2:
            self._render_venda_cliente()

        with tab3:
            self._render_historico()
    
    def _render_pdv(self):
        """Renderiza o PDV (Ponto de Venda)"""
        st.subheader("💲 Ponto de Venda Rápido")
        
        # Layout do PDV
        col_esquerda, col_direita = st.columns([2, 1])
        
        with col_esquerda:
            self._render_secao_busca_produto()
            self._render_carrinho()
        
        with col_direita:
            self._render_secao_cliente()
            self._render_resumo_venda()
            self._render_finalizacao()
    
    def _render_secao_busca_produto(self):
        """Renderiza seção de busca de produtos"""
        st.markdown("### 🔍 Buscar Produto")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            busca = st.text_input(
                "Código de barras ou nome:",
                placeholder="Digite ou escaneie o código",
                key="busca_produto_pdv",
                label_visibility="collapsed"
            )
        
        with col2:
            if st.button("➕ Adicionar"):
                if busca:
                    self._adicionar_produto_ao_carrinho(busca)
        
        # Sugestões de produtos mais vendidos
        with st.expander("📦 Produtos mais vendidos"):
            produtos_top = self.db.read_sql("""
                SELECT 
                    p.id,
                    p.nome,
                    p.preco_venda,
                    SUM(i.quantidade) as total_vendido
                FROM produtos p
                JOIN itens_venda i ON p.id = i.produto_id
                GROUP BY p.id
                ORDER BY total_vendido DESC
                LIMIT 10
            """)
            
            if not produtos_top.empty:
                cols = st.columns(5)
                for i, (_, produto) in enumerate(produtos_top.iterrows()):
                    with cols[i % 5]:
                        if st.button(
                            f"{produto['nome'][:15]}...\nR$ {produto['preco_venda']:.2f}",
                            key=f"rapido_{produto['id']}"
                        ):
                            self._adicionar_produto_ao_carrinho(produto['id'], is_id=True)
    
    def _adicionar_produto_ao_carrinho(self, termo: str, is_id: bool = False):
        """Adiciona produto ao carrinho"""
        produto = None
        
        if is_id:
            # Buscar por ID
            row = self.db.fetchone(
                "SELECT id, nome, preco_venda, quantidade_estoque FROM produtos WHERE id = ? AND ativo = 1",
                (int(termo),)
            )
            if row:
                produto = dict(row)
        else:
            # Buscar por código de barras ou nome
            produto = self.produtos.buscar_produto_por_codigo(termo)
            
            if not produto:
                # Buscar por nome aproximado
                df = self.produtos.buscar_produtos(termo, limit=1)
                if not df.empty:
                    produto = df.iloc[0].to_dict()
        
        if produto:
            # Verificar estoque
            if produto['quantidade_estoque'] <= 0:
                UIComponents.show_error_message(f"Produto {produto['nome']} sem estoque!")
                return
            
            # Adicionar ao carrinho
            carrinho = st.session_state[self._carrinho_key]
            
            # Verificar se já existe no carrinho
            encontrado = False
            for item in carrinho:
                if item['produto_id'] == produto['id']:
                    if item['quantidade'] < produto['quantidade_estoque']:
                        item['quantidade'] += 1
                        item['subtotal'] = item['quantidade'] * item['preco_unitario']
                    else:
                        UIComponents.show_warning_message(f"Estoque insuficiente! Máximo: {produto['quantidade_estoque']}")
                    encontrado = True
                    break
            
            if not encontrado:
                carrinho.append({
                    'produto_id': produto['id'],
                    'nome': produto['nome'],
                    'preco_unitario': float(produto['preco_venda']),
                    'quantidade': 1,
                    'subtotal': float(produto['preco_venda'])
                })
            
            st.session_state[self._carrinho_key] = carrinho
            AccessibilityManager.announce_message(f"Produto {produto['nome']} adicionado ao carrinho")
            st.rerun()
        else:
            UIComponents.show_error_message("Produto não encontrado!")
    
    def _render_carrinho(self):
        """Renderiza o carrinho de compras"""
        st.markdown("### 🛒 Carrinho")
        
        carrinho = st.session_state[self._carrinho_key]
        
        if not carrinho:
            st.info("Carrinho vazio. Adicione produtos para começar.")
            return
        
        # Tabela do carrinho
        df_carrinho = pd.DataFrame(carrinho)
        
        # Colunas para exibição
        colunas = ['nome', 'quantidade', 'preco_unitario', 'subtotal']
        df_display = df_carrinho[colunas].copy()
        
        df_display['preco_unitario'] = df_display['preco_unitario'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        df_display['subtotal'] = df_display['subtotal'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        st.dataframe(
            df_display,
            hide_index=True,
            column_config={
                "nome": "Produto",
                "quantidade": "Qtd",
                "preco_unitario": "Preço Unit.",
                "subtotal": "Subtotal"
            }
        )
        
        # Controles de quantidade e remoção
        st.markdown("#### 🔧 Ajustar Quantidades")
        
        cols_ajuste = st.columns([3, 1, 1, 1])
        with cols_ajuste[0]:
            produto_ajuste = st.selectbox(
                "Selecione o produto:",
                options=[item['nome'] for item in carrinho],
                key="select_ajuste"
            )
        
        if produto_ajuste:
            item_idx = next(i for i, item in enumerate(carrinho) if item['nome'] == produto_ajuste)
            item = carrinho[item_idx]
            
            with cols_ajuste[1]:
                nova_qtd = st.number_input(
                    "Quantidade:",
                    min_value=1,
                    max_value=100,
                    value=item['quantidade'],
                    key="qtd_ajuste",
                    label_visibility="collapsed"
                )
            
            with cols_ajuste[2]:
                if st.button("✅ Atualizar", key="btn_atualizar_qtd"):
                    if nova_qtd != item['quantidade']:
                        carrinho[item_idx]['quantidade'] = nova_qtd
                        carrinho[item_idx]['subtotal'] = nova_qtd * item['preco_unitario']
                        st.session_state[self._carrinho_key] = carrinho
                        st.rerun()
            
            with cols_ajuste[3]:
                if st.button("🗑️ Remover", key="btn_remover_item"):
                    carrinho.pop(item_idx)
                    st.session_state[self._carrinho_key] = carrinho
                    st.rerun()
        
        # Botão para limpar carrinho
        if st.button("🗑️ Limpar Carrinho"):
            st.session_state[self._carrinho_key] = []
            st.session_state[self._cliente_selecionado_key] = None
            st.rerun()
    
    def _render_secao_cliente(self):
        """Renderiza seção de seleção de cliente"""
        st.markdown("### 👤 Cliente")
        
        if st.session_state[self._cliente_selecionado_key]:
            cliente = st.session_state[self._cliente_selecionado_key]
            st.success(f"Cliente: **{cliente['nome']}**")
            
            if st.button("🔄 Trocar Cliente"):
                st.session_state[self._cliente_selecionado_key] = None
                st.rerun()
        else:
            st.info("Cliente não identificado")
            
            opcao = st.radio(
                "Opções:",
                ["Continuar sem cliente", "Buscar cliente existente", "Cadastrar novo cliente"],
                key="opcao_cliente"
            )
            
            if opcao == "Buscar cliente existente":
                busca_cliente = st.text_input(
                    "Buscar por nome, CPF ou telefone:",
                    key="busca_cliente_pdv"
                )
                
                if busca_cliente:
                    clientes = self.clientes.buscar_clientes(busca_cliente, limit=10)
                    
                    if not clientes.empty:
                        opcoes = {}
                        for _, c in clientes.iterrows():
                            label = f"{c['nome']}"
                            if c.get('cpf'):
                                label += f" - CPF: {Security.formatar_cpf(c['cpf'])}"
                            opcoes[label] = c.to_dict()
                        
                        selecao = st.selectbox(
                            "Selecione o cliente:",
                            options=list(opcoes.keys()),
                            key="select_cliente_pdv"
                        )
                        
                        if selecao and st.button("✅ Selecionar Cliente"):
                            st.session_state[self._cliente_selecionado_key] = opcoes[selecao]
                            st.rerun()
                    else:
                        st.warning("Nenhum cliente encontrado.")
            
            elif opcao == "Cadastrar novo cliente":
                with st.form("form_cliente_rapido"):
                    nome = st.text_input("Nome:*", placeholder="Nome do cliente")
                    cpf = st.text_input("CPF:", placeholder="000.000.000-00")
                    telefone = st.text_input("Telefone:", placeholder="(00) 00000-0000")
                    
                    if st.form_submit_button("💾 Cadastrar e Selecionar"):
                        if nome.strip():
                            dados = {
                                "nome": nome.strip().upper(),
                                "cpf": cpf.strip() if cpf.strip() else None,
                                "telefone": telefone.strip() if telefone.strip() else None
                            }
                            
                            sucesso, msg = self.clientes.cadastrar_individual(
                                dados,
                                st.session_state.usuario_nome
                            )
                            
                            if sucesso:
                                # Buscar o cliente recém-cadastrado
                                novo_cliente = self.clientes.buscar_clientes(nome.strip(), limit=1)
                                if not novo_cliente.empty:
                                    st.session_state[self._cliente_selecionado_key] = novo_cliente.iloc[0].to_dict()
                                    UIComponents.show_success_message("Cliente cadastrado com sucesso!")
                                    st.rerun()
                            else:
                                UIComponents.show_error_message(msg)
    
    def _render_resumo_venda(self):
        """Renderiza resumo da venda"""
        st.markdown("### 📊 Resumo")
        
        carrinho = st.session_state[self._carrinho_key]
        
        if not carrinho:
            return
        
        # Calcular totais
        subtotal = sum(item['subtotal'] for item in carrinho)
        total_itens = sum(item['quantidade'] for item in carrinho)
        
        # Aplicar promoções (se houver)
        # Por simplicidade, não implementamos promoções automáticas aqui
        
        st.markdown(f"""
        **Itens:** {total_itens}
        **Subtotal:** R$ {subtotal:,.2f}
        """.replace(",", "X").replace(".", ",").replace("X", "."))
    
    def _render_finalizacao(self):
        """Renderiza seção de finalização da venda"""
        st.markdown("### 💳 Finalizar Venda")
        
        carrinho = st.session_state[self._carrinho_key]
        
        if not carrinho:
            return
        
        forma_pagamento = st.selectbox(
            "Forma de pagamento:*",
            ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Transferência", "Crediário"],
            key="forma_pagamento"
        )
        
        # Observações
        observacao = st.text_area(
            "Observações:",
            placeholder="Observações sobre a venda",
            key="obs_venda"
        )
        
        # Botão de finalização
        if st.button("✅ Finalizar Venda", type="primary"):
            self._finalizar_venda(forma_pagamento, observacao)
    
    def _finalizar_venda(self, forma_pagamento: str, observacao: str):
        """Finaliza a venda"""
        carrinho = st.session_state[self._carrinho_key]
        cliente = st.session_state[self._cliente_selecionado_key]
        
        # Preparar itens para o serviço
        itens = []
        for item in carrinho:
            itens.append({
                'produto_id': item['produto_id'],
                'quantidade': item['quantidade'],
                'preco_unitario': item['preco_unitario']
            })
        
        # Registrar venda
        cliente_id = cliente['id'] if cliente else None
        
        sucesso, msg, venda_id = self.vendas.registrar_venda(
            cliente_id=cliente_id,
            itens=itens,
            forma_pagamento=forma_pagamento,
            usuario=st.session_state.usuario_login
        )
        
        if sucesso:
            UIComponents.show_success_message(msg)
            AccessibilityManager.announce_message(f"Venda #{venda_id} finalizada com sucesso")
            
            # Limpar carrinho e cliente
            st.session_state[self._carrinho_key] = []
            st.session_state[self._cliente_selecionado_key] = None
            
            # Mostrar resumo da venda
            self._mostrar_comprovante(venda_id)
        else:
            UIComponents.show_error_message(msg)
    
    def _mostrar_comprovante(self, venda_id: int):
        """Mostra comprovante da venda"""
        with st.expander("🧾 Comprovante da Venda", expanded=True):
            detalhes = self.vendas.detalhes_venda(venda_id)
            
            if detalhes:
                venda = detalhes['venda']
                itens = detalhes['itens']
                
                st.markdown(f"""
                ### ElectroGest - Comprovante de Venda
                **Venda #{venda_id}**
                **Data:** {Formatters.formatar_data_hora(venda['data_venda'])}
                **Cliente:** {venda.get('cliente_nome', 'Não identificado')}
                **Forma de pagamento:** {venda['forma_pagamento']}
                
                **Itens:**
                """)
                
                for item in itens:
                    st.markdown(f"""
                    - {item['quantidade']}x {item['produto_nome']} - R$ {item['preco_unitario']:,.2f} = R$ {item['quantidade'] * item['preco_unitario']:,.2f}
                    """.replace(",", "X").replace(".", ",").replace("X", "."))
                
                st.markdown(f"""
                ---
                **Total:** R$ {venda['valor_total']:,.2f}
                
                *Obrigado pela preferência!*
                """.replace(",", "X").replace(".", ",").replace("X", "."))
    
    def _render_venda_cliente(self):
        """Renderiza venda para cliente específico"""
        st.subheader("👥 Venda para Cliente Específico")
        
        # Buscar cliente
        busca_cliente = st.text_input(
            "Buscar cliente por nome, CPF ou telefone:",
            key="busca_cliente_venda"
        )
        
        cliente_selecionado = None
        if busca_cliente:
            clientes = self.clientes.buscar_clientes(busca_cliente, limit=10)
            
            if not clientes.empty:
                opcoes = {}
                for _, c in clientes.iterrows():
                    label = f"{c['nome']}"
                    if c.get('cpf'):
                        label += f" - CPF: {Security.formatar_cpf(c['cpf'])}"
                    opcoes[label] = c.to_dict()
                
                selecao = st.selectbox(
                    "Selecione o cliente:",
                    options=list(opcoes.keys()),
                    key="select_cliente_venda"
                )
                
                if selecao:
                    cliente_selecionado = opcoes[selecao]
                    st.success(f"Cliente selecionado: **{cliente_selecionado['nome']}**")
        
        if cliente_selecionado:
            # Mostrar histórico do cliente
            with st.expander("📋 Histórico do Cliente"):
                historico = self.vendas.historico_cliente(int(cliente_selecionado['id']))
                
                if not historico.empty:
                    df_hist = historico.copy()
                    df_hist['data_venda'] = pd.to_datetime(df_hist['data_venda']).dt.strftime('%d/%m/%Y')
                    df_hist['valor_total'] = df_hist['valor_total'].apply(
                        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    )
                    
                    st.dataframe(df_hist[['data_venda', 'valor_total', 'total_itens']])
                else:
                    st.info("Cliente não possui histórico de compras.")
            
            # Carrinho para este cliente
            st.markdown("### 🛒 Carrinho")
            
            if self._carrinho_key not in st.session_state:
                st.session_state[self._carrinho_key] = []
            
            # Busca de produtos
            col1, col2 = st.columns([3, 1])
            with col1:
                busca_prod = st.text_input(
                    "Buscar produto:",
                    placeholder="Código de barras ou nome",
                    key="busca_prod_venda_cliente"
                )
            with col2:
                if st.button("➕ Adicionar", key="add_prod_cliente"):
                    if busca_prod:
                        self._adicionar_produto_ao_carrinho(busca_prod)
            
            # Exibir carrinho
            if st.session_state[self._carrinho_key]:
                df_carrinho = pd.DataFrame(st.session_state[self._carrinho_key])
                st.dataframe(
                    df_carrinho[['nome', 'quantidade', 'subtotal']]
                )
                
                # Total
                total = sum(item['subtotal'] for item in st.session_state[self._carrinho_key])
                st.metric("Total", f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                # Finalização
                forma_pagamento = st.selectbox(
                    "Forma de pagamento:",
                    ["Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX", "Transferência"],
                    key="forma_pag_cliente"
                )
                
                if st.button("✅ Finalizar Venda", type="primary"):
                    itens = []
                    for item in st.session_state[self._carrinho_key]:
                        itens.append({
                            'produto_id': item['produto_id'],
                            'quantidade': item['quantidade'],
                            'preco_unitario': item['preco_unitario']
                        })
                    
                    sucesso, msg, venda_id = self.vendas.registrar_venda(
                        cliente_id=int(cliente_selecionado['id']),
                        itens=itens,
                        forma_pagamento=forma_pagamento,
                        usuario=st.session_state.usuario_login
                    )
                    
                    if sucesso:
                        UIComponents.show_success_message(msg)
                        st.session_state[self._carrinho_key] = []
                        st.rerun()
                    else:
                        UIComponents.show_error_message(msg)
            else:
                st.info("Carrinho vazio. Adicione produtos para continuar.")
    
    def _render_historico(self):
        """Renderiza histórico de vendas"""
        st.subheader("📁 Histórico de Vendas")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            periodo = st.selectbox(
                "Período:",
                ["Hoje", "Ontem", "Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês anterior", "Personalizado"],
                key="periodo_historico"
            )
        
        with col2:
            if periodo == "Personalizado":
                data_inicio = st.date_input(
                    "Data inicial:",
                    value=date.today() - timedelta(days=30),
                    key="data_inicio_historico"
                )
                data_fim = st.date_input(
                    "Data final:",
                    value=date.today(),
                    key="data_fim_historico"
                )
            else:
                data_inicio, data_fim = self._calcular_periodo(periodo)
                st.text_input(
                    "Período:",
                    value=f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                    disabled=True,
                    key="periodo_display_historico"
                )
        
        with col3:
            filtro_pagamento = st.selectbox(
                "Forma de pagamento:",
                ["Todas", "Dinheiro", "Cartão de Crédito", "Cartão de Débito", "PIX"],
                key="filtro_pagamento"
            )
        
        if st.button("🔍 Buscar Vendas", type="primary", key="btn_buscar_vendas"):
            with st.spinner("Buscando vendas..."):
                vendas = self.vendas.listar_vendas_por_periodo(
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    limit=1000
                )
                
                if not vendas.empty:
                    # Aplicar filtro de pagamento
                    if filtro_pagamento != "Todas":
                        vendas = vendas[vendas['forma_pagamento'] == filtro_pagamento]
                    
                    st.session_state.vendas_historico = vendas
                    UIComponents.show_success_message(f"{len(vendas)} vendas encontradas")
        
        # Exibir resultados
        if st.session_state.get('vendas_historico') is not None:
            vendas = st.session_state.vendas_historico
            
            if not vendas.empty:
                # Métricas
                col_met1, col_met2, col_met3 = st.columns(3)
                
                with col_met1:
                    total_vendas = len(vendas)
                    st.metric("Total de Vendas", total_vendas)
                
                with col_met2:
                    faturamento = vendas['valor_total'].sum()
                    st.metric("Faturamento", f"R$ {faturamento:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                with col_met3:
                    ticket_medio = faturamento / total_vendas if total_vendas > 0 else 0
                    st.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
                # Tabela
                df_display = vendas.copy()
                df_display['data_venda'] = pd.to_datetime(df_display['data_venda']).dt.strftime('%d/%m/%Y %H:%M')
                df_display['valor_total'] = df_display['valor_total'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                df_display['cliente_nome'] = df_display['cliente_nome'].fillna('Não identificado')
                
                st.dataframe(
                    df_display[['data_venda', 'id', 'cliente_nome', 'valor_total', 'forma_pagamento', 'total_itens']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "data_venda": "Data/Hora",
                        "id": "Venda #",
                        "cliente_nome": "Cliente",
                        "valor_total": "Valor",
                        "forma_pagamento": "Pagamento",
                        "total_itens": "Itens"
                    }
                )
                
                # Detalhes de uma venda específica
                st.markdown("---")
                st.subheader("🔍 Detalhes da Venda")
                
                venda_selecionada = st.selectbox(
                    "Selecione o número da venda:",
                    options=vendas['id'].tolist(),
                    format_func=lambda x: f"Venda #{x}",
                    key="select_venda_detalhe"
                )
                
                if venda_selecionada:
                    detalhes = self.vendas.detalhes_venda(int(venda_selecionada))
                    
                    if detalhes:
                        venda = detalhes['venda']
                        itens = detalhes['itens']
                        
                        col_det1, col_det2 = st.columns(2)
                        
                        with col_det1:
                            st.markdown(f"""
                            **Data:** {Formatters.formatar_data_hora(venda['data_venda'])}
                            **Cliente:** {venda.get('cliente_nome', 'Não identificado')}
                            **CPF:** {Security.formatar_cpf(venda.get('cliente_cpf')) if venda.get('cliente_cpf') else 'N/I'}
                            """)
                        
                        with col_det2:
                            st.markdown(f"""
                            **Forma de pagamento:** {venda['forma_pagamento']}
                            **Valor total:** R$ {venda['valor_total']:,.2f}
                            **Vendedor:** {venda['usuario_registro']}
                            """.replace(",", "X").replace(".", ",").replace("X", "."))
                        
                        st.markdown("#### Itens da Venda")
                        
                        if itens:
                            df_itens = pd.DataFrame(itens)
                            
                            # CORREÇÃO: Converter preco_unitario para float
                            df_itens['preco_unitario'] = pd.to_numeric(df_itens['preco_unitario'], errors='coerce')
                            df_itens['quantidade'] = pd.to_numeric(df_itens['quantidade'], errors='coerce')
                            
                            # Calcular subtotal
                            df_itens['subtotal'] = df_itens['quantidade'] * df_itens['preco_unitario']
                            
                            # Formatar valores
                            df_itens['preco_unitario'] = df_itens['preco_unitario'].apply(
                                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "R$ 0,00"
                            )
                            df_itens['subtotal'] = df_itens['subtotal'].apply(
                                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "R$ 0,00"
                            )
                            
                            st.dataframe(
                                df_itens[['produto_nome', 'quantidade', 'preco_unitario', 'subtotal', 'promocao_nome']],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "produto_nome": "Produto",
                                    "quantidade": "Qtd",
                                    "preco_unitario": "Preço Unit.",
                                    "subtotal": "Subtotal",
                                    "promocao_nome": "Promoção"
                                }
                            )
                        else:
                            st.info("Nenhum item encontrado para esta venda.")
            else:
                st.info("Nenhuma venda encontrada no período.")
    
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