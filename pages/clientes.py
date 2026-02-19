"""
clientes.py - Página de gerenciamento de clientes
"""

import io
from datetime import date

import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager


class ClientesPage:
    """Página de gerenciamento de clientes"""
    
    def __init__(self, db, clientes, auth, vendas=None):
        self.db = db
        self.clientes = clientes
        self.auth = auth
        self.vendas = vendas
    
    def render(self):
        """Renderiza página de clientes"""
        st.title("👥 Gerenciar Clientes")
        UIComponents.breadcrumb("🏠 Início", "Clientes")

        tab1, tab2, tab3, tab4 = st.tabs([
            "🔍 Consultar",
            "➕ Cadastrar",
            "📥 Importar",
            "📊 Análise RFM"
        ])

        with tab1:
            self._render_consultar()

        with tab2:
            self._render_cadastrar()

        with tab3:
            self._render_importar()

        with tab4:
            self._render_analise_rfm()

        if 'cliente_editar' in st.session_state:
            self._render_editar_cliente(st.session_state.cliente_editar)

        if 'cliente_excluir' in st.session_state:
            self._render_modal_exclusao_cliente(st.session_state.cliente_excluir)
    
    def _render_consultar(self):
        """Renderiza consulta de clientes"""
        st.subheader("🔍 Consultar Clientes")

        col1, col2, col3 = st.columns(3)

        with col1:
            filtro_nome = st.text_input("Nome:", key="filtro_nome_cliente")

        with col2:
            filtro_cpf = st.text_input("CPF:", key="filtro_cpf_cliente")

        with col3:
            filtro_cidade = st.text_input("Cidade:", key="filtro_cidade_cliente")

        col_incluir = st.checkbox("Incluir clientes inativos", key="incluir_inativos")

        if st.button("🔎 Buscar"):
            where_clauses = []
            params = []

            if filtro_nome:
                where_clauses.append("nome LIKE ?")
                params.append(f"%{filtro_nome}%")

            if filtro_cpf:
                cpf_limpo = Security.clean_cpf(filtro_cpf)
                where_clauses.append("cpf LIKE ?")
                params.append(f"%{cpf_limpo}%")

            if filtro_cidade:
                where_clauses.append("cidade LIKE ?")
                params.append(f"%{filtro_cidade}%")

            if not col_incluir:
                where_clauses.append("ativo = 1")

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = f"""
                SELECT 
                    id, nome, cpf, email, telefone, 
                    cidade, estado, data_nascimento, data_cadastro, ativo
                FROM clientes
                WHERE {where_sql}
                ORDER BY nome
                LIMIT 200
            """

            clientes = self.db.read_sql(query, params)
            st.session_state.clientes_filtrados = clientes

        if st.session_state.get('clientes_filtrados') is not None:
            clientes = st.session_state.clientes_filtrados

            if not clientes.empty:
                st.success(f"{len(clientes)} clientes encontrados")

                for idx, row in clientes.iterrows():
                    col1, col2, col3, col4, col5, col6 = st.columns([2.5, 1, 1, 1, 1, 1])
                    
                    with col1:
                        nome_display = row['nome']
                        if row['ativo'] == 0:
                            nome_display += " (inativo)"
                        st.write(f"**{nome_display}**")
                        st.caption(f"CPF: {Security.formatar_cpf(row['cpf']) if row['cpf'] else 'N/I'} | Tel: {row['telefone'] or 'N/I'}")
                    
                    with col2:
                        st.write(f"Nasc: {Formatters.formatar_data_br(row['data_nascimento'])}")
                    
                    with col3:
                        st.write(f"Cidade: {row['cidade'] or 'N/I'}")
                    
                    with col4:
                        if st.button("✏️ Editar", key=f"edit_{row['id']}_{idx}"):
                            st.session_state.cliente_editar = row.to_dict()
                            st.rerun()
                    
                    with col5:
                        if st.button("🗑️ Excluir", key=f"del_{row['id']}_{idx}"):
                            st.session_state.cliente_excluir = row.to_dict()
                            st.rerun()
                    
                    with col6:
                        if st.button("📋 Detalhes", key=f"detail_{row['id']}_{idx}"):
                            st.session_state.cliente_detalhe = row.to_dict()
                            st.rerun()
                    
                    st.divider()

                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    csv = clientes.to_csv(index=False)
                    st.download_button("📥 CSV", csv, "clientes.csv", "text/csv")
                with col_exp2:
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        clientes.to_excel(writer, index=False, sheet_name='Clientes')
                    st.download_button(
                        "📊 Excel",
                        excel_buffer.getvalue(),
                        "clientes.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info("Nenhum cliente encontrado.")

        if 'cliente_detalhe' in st.session_state:
            self._render_cliente_detalhe(st.session_state.cliente_detalhe)

    def _render_cliente_detalhe(self, cliente):
        """Renderiza detalhes de um cliente específico"""
        st.markdown("---")
        st.subheader(f"📋 Detalhes do Cliente: {cliente['nome']}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **ID:** {cliente['id']}
            **Nome:** {cliente['nome']}
            **CPF:** {Security.formatar_cpf(cliente['cpf']) if cliente['cpf'] else 'Não informado'}
            **E-mail:** {cliente['email'] or 'Não informado'}
            **Telefone:** {Security.formatar_telefone(cliente['telefone']) if cliente['telefone'] else 'Não informado'}
            """)
        with col2:
            st.markdown(f"""
            **Data Nascimento:** {Formatters.formatar_data_br(cliente['data_nascimento'])}
            **Cidade/UF:** {cliente.get('cidade', '')}/{cliente.get('estado', '')}
            **Data Cadastro:** {Formatters.formatar_data_br(cliente['data_cadastro'])}
            **Status:** {'✅ Ativo' if cliente['ativo'] == 1 else '❌ Inativo'}
            """)

        if self.vendas:
            st.subheader("🛒 Histórico de Compras")
            historico = self.vendas.historico_cliente(int(cliente['id']))
            
            if not historico.empty:
                df_hist = historico.copy()
                df_hist['data_venda'] = pd.to_datetime(df_hist['data_venda']).dt.strftime('%d/%m/%Y %H:%M')
                df_hist['valor_total'] = df_hist['valor_total'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                
                st.dataframe(
                    df_hist[['data_venda', 'valor_total', 'forma_pagamento', 'total_itens']],
                    hide_index=True,
                    column_config={
                        "data_venda": "Data",
                        "valor_total": "Valor",
                        "forma_pagamento": "Pagamento",
                        "total_itens": "Itens"
                    }
                )
                
                total_compras = len(historico)
                total_gasto = historico['valor_total'].sum()
                st.info(f"**Total de compras:** {total_compras} | **Total gasto:** R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            else:
                st.info("Cliente ainda não realizou compras.")

        if st.button("🔙 Voltar", key="back_from_detail"):
            del st.session_state.cliente_detalhe
            st.rerun()

    def _render_editar_cliente(self, cliente):
        """Renderiza formulário de edição de cliente"""
        st.markdown("---")
        st.subheader(f"✏️ Editando: {cliente['nome']}")

        with st.form(f"form_editar_cliente_{cliente['id']}"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome*", value=cliente['nome'])
                cpf = st.text_input("CPF", value=Security.formatar_cpf(cliente['cpf']) if cliente['cpf'] else "")
                data_nasc = st.date_input(
                    "Data de Nascimento",
                    value=Formatters.parse_date(cliente['data_nascimento']) if cliente['data_nascimento'] else None,
                    max_value=date.today()
                )
            with col2:
                email = st.text_input("E-mail", value=cliente['email'] or "")
                telefone = st.text_input("Telefone", value=cliente['telefone'] or "")

            endereco = st.text_input("Endereço", value=cliente['endereco'] or "")
            col3, col4, col5 = st.columns(3)
            with col3:
                cidade = st.text_input("Cidade", value=cliente['cidade'] or "")
            with col4:
                estado = st.text_input("Estado", value=cliente['estado'] or "", max_chars=2)
            with col5:
                cep = st.text_input("CEP", value=cliente['cep'] or "")

            ativo = st.checkbox("Cliente Ativo", value=bool(cliente['ativo']))

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                    if not nome.strip():
                        st.error("Nome é obrigatório")
                        st.stop()
                    
                    dados = {
                        "nome": nome.strip().upper(),
                        "cpf": Security.clean_cpf(cpf) if cpf.strip() else None,
                        "email": email.strip() or None,
                        "telefone": telefone.strip() or None,
                        "data_nascimento": data_nasc.isoformat() if data_nasc else None,
                        "endereco": endereco.strip() or None,
                        "cidade": cidade.strip().upper() or None,
                        "estado": estado.strip().upper() or None,
                        "cep": cep.strip() or None,
                        "ativo": ativo
                    }
                    sucesso, msg = self.clientes.atualizar_cliente(
                        int(cliente['id']), dados, st.session_state.usuario_nome
                    )
                    if sucesso:
                        st.success(msg)
                        del st.session_state.cliente_editar
                        if 'clientes_filtrados' in st.session_state:
                            del st.session_state.clientes_filtrados
                        st.rerun()
                    else:
                        st.error(msg)
            with col_btn2:
                if st.form_submit_button("Cancelar"):
                    del st.session_state.cliente_editar
                    st.rerun()

    def _render_modal_exclusao_cliente(self, cliente):
        """Renderiza modal de confirmação de exclusão"""
        st.markdown("---")
        st.error("⚠️ **CONFIRMAÇÃO DE EXCLUSÃO**")
        st.markdown(f"""
        <div style="background-color: #fff3cd; border:1px solid #ffeeba; border-radius:5px; padding:15px; margin:10px 0;">
            <h4 style="color:#856404;">Tem certeza que deseja excluir este cliente?</h4>
            <ul>
                <li><strong>Nome:</strong> {cliente['nome']}</li>
                <li><strong>CPF:</strong> {Security.formatar_cpf(cliente['cpf']) if cliente['cpf'] else 'N/I'}</li>
            </ul>
            <p style="color:#dc3545; font-weight:bold;">Esta ação é IRREVERSÍVEL e só será permitida se o cliente não tiver vendas.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirmar Exclusão", type="primary"):
                sucesso, msg = self.clientes.excluir_cliente(
                    int(cliente['id']), st.session_state.usuario_nome
                )
                if sucesso:
                    st.success(msg)
                    del st.session_state.cliente_excluir
                    if 'clientes_filtrados' in st.session_state:
                        del st.session_state.clientes_filtrados
                    st.rerun()
                else:
                    st.error(msg)
        with col2:
            if st.button("❌ Cancelar"):
                del st.session_state.cliente_excluir
                st.rerun()

    def _render_cadastrar(self):
        """Renderiza cadastro individual"""
        st.subheader("➕ Cadastrar Novo Cliente")

        with st.form("form_cadastro_cliente", clear_on_submit=True):
            st.markdown("### 👤 Dados Pessoais")
            
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input(
                    "Nome Completo:*",
                    placeholder="Ex: JOÃO DA SILVA SANTOS",
                    key="cad_nome"
                )

                cpf = st.text_input(
                    "CPF:",
                    placeholder="000.000.000-00",
                    key="cad_cpf"
                )

                data_nascimento = st.date_input(
                    "Data de Nascimento:",
                    max_value=date.today(),
                    key="cad_nascimento"
                )

            with col2:
                email = st.text_input(
                    "E-mail:",
                    placeholder="exemplo@dominio.com",
                    key="cad_email"
                )

                telefone = st.text_input(
                    "Telefone:",
                    placeholder="(00) 00000-0000",
                    key="cad_telefone"
                )

            st.markdown("### 📍 Endereço")
            
            col3, col4 = st.columns(2)

            with col3:
                endereco = st.text_input(
                    "Endereço:",
                    placeholder="Rua, número, complemento",
                    key="cad_endereco"
                )

                cidade = st.text_input(
                    "Cidade:",
                    placeholder="São Paulo",
                    key="cad_cidade"
                )

            with col4:
                estado = st.text_input(
                    "Estado:",
                    placeholder="SP",
                    max_chars=2,
                    key="cad_estado"
                )

                cep = st.text_input(
                    "CEP:",
                    placeholder="00000-000",
                    key="cad_cep"
                )

            st.markdown("*Campos obrigatórios")

            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

            with col_btn1:
                submit = st.form_submit_button(
                    "💾 Salvar Cliente",
                    type="primary"
                )

            with col_btn2:
                submit_novo = st.form_submit_button(
                    "➕ Salvar e Novo"
                )

            with col_btn3:
                st.form_submit_button(
                    "🗑️ Cancelar",
                    type="secondary"
                )

            if submit or submit_novo:
                self._processar_cadastro(
                    nome, cpf, email, telefone, data_nascimento,
                    endereco, cidade, estado, cep, submit_novo
                )

    def _processar_cadastro(self, nome, cpf, email, telefone, data_nascimento,
                           endereco, cidade, estado, cep, submit_novo):
        """Processa cadastro de cliente"""
        if not nome.strip():
            UIComponents.show_error_message("Nome é obrigatório!")
            st.stop()

        if cpf.strip() and not Security.validar_cpf(cpf):
            UIComponents.show_error_message("CPF inválido!")
            st.stop()

        dados = {
            "nome": nome.strip().upper(),
            "cpf": cpf.strip() if cpf.strip() else None,
            "email": email.strip() if email.strip() else None,
            "telefone": telefone.strip() if telefone.strip() else None,
            "data_nascimento": data_nascimento.isoformat() if data_nascimento else None,
            "endereco": endereco.strip() if endereco.strip() else None,
            "cidade": cidade.strip().upper() if cidade.strip() else None,
            "estado": estado.strip().upper() if estado.strip() else None,
            "cep": cep.strip() if cep.strip() else None,
        }

        sucesso, mensagem = self.clientes.cadastrar_individual(
            dados,
            st.session_state.usuario_nome
        )

        if sucesso:
            UIComponents.show_success_message(mensagem)
            AccessibilityManager.announce_message("Cliente cadastrado com sucesso")
            
            if submit_novo:
                st.rerun()
        else:
            UIComponents.show_error_message(mensagem)

    def _render_importar(self):
        """Renderiza importação em lote"""
        st.subheader("📥 Importar Clientes em Lote")

        st.info("""
        **Instruções para importação:**
        1. Prepare um arquivo Excel ou CSV com os dados dos clientes
        2. Faça o upload do arquivo
        3. Mapeie as colunas do arquivo para os campos do sistema
        4. Configure as opções de importação
        5. Execute a importação
        
        **Colunas recomendadas:** NOME, CPF, EMAIL, TELEFONE, ENDERECO, CIDADE, ESTADO, CEP, DATA_NASCIMENTO
        """)

        uploaded_file = st.file_uploader(
            "Escolha um arquivo (CSV, Excel)",
            type=["csv", "xlsx", "xls"],
            key="upload_clientes"
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_raw = pd.read_csv(uploaded_file, dtype=str)
                else:
                    df_raw = pd.read_excel(uploaded_file, dtype=str)

                UIComponents.show_success_message(f"Arquivo carregado: {len(df_raw)} registros")

                colunas_detectadas = self.clientes.detectar_colunas_arquivo(df_raw)

                with st.expander("📋 Pré-visualização do arquivo"):
                    st.dataframe(df_raw.head(10))

                st.subheader("⚙️ Mapeamento de Colunas")
                st.caption("Selecione para cada campo do sistema qual coluna do arquivo corresponde")

                campos_obrigatorios = ["NOME"]
                campos_opcionais = ["CPF", "EMAIL", "TELEFONE", "DATA_NASCIMENTO",
                                   "ENDERECO", "CIDADE", "ESTADO", "CEP"]

                mapeamento = {}
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Campos obrigatórios:**")
                    for campo in campos_obrigatorios:
                        default = colunas_detectadas.get(campo, "")
                        options = [""] + list(df_raw.columns)
                        mapeamento[campo] = st.selectbox(
                            f"{campo}:",
                            options,
                            index=options.index(default) if default in options else 0,
                            key=f"map_{campo}"
                        )

                with col2:
                    st.markdown("**Campos opcionais:**")
                    for campo in campos_opcionais:
                        default = colunas_detectadas.get(campo, "")
                        options = [""] + list(df_raw.columns)
                        mapeamento[campo] = st.selectbox(
                            f"{campo}:",
                            options,
                            index=options.index(default) if default in options else 0,
                            key=f"map_opt_{campo}"
                        )

                campos_nao_mapeados = [campo for campo in campos_obrigatorios if not mapeamento.get(campo)]
                if campos_nao_mapeados:
                    st.error(f"❌ Campos obrigatórios não mapeados: {', '.join(campos_nao_mapeados)}")
                    return

                st.subheader("🔧 Opções de Importação")

                col_opt1, col_opt2 = st.columns(2)

                with col_opt1:
                    acao_duplicados = st.selectbox(
                        "Clientes já cadastrados (por CPF):",
                        ["Manter existente e ignorar novo", "Sobrescrever todos os dados", "Atualizar campos vazios"],
                        key="acao_duplicados"
                    )

                    criar_novos = st.checkbox(
                        "Criar novos clientes",
                        value=True,
                        key="criar_novos"
                    )

                with col_opt2:
                    atualizar_vazios = st.checkbox(
                        "Atualizar campos vazios",
                        value=True,
                        key="atualizar_vazios"
                    )

                    notificar_diferencas = st.checkbox(
                        "Notificar diferenças",
                        value=True,
                        key="notificar_diferencas"
                    )

                if st.button("🚀 Executar Importação", type="primary"):
                    with st.spinner("Processando importação..."):
                        try:
                            stats, erros, diferencas = self.clientes.importar_em_lote(
                                df_raw=df_raw,
                                mapeamento_final=mapeamento,
                                acao_duplicados=acao_duplicados,
                                criar_novos=criar_novos,
                                atualizar_vazios=atualizar_vazios,
                                notificar_diferencas=notificar_diferencas,
                                usuario=st.session_state.usuario_nome,
                            )

                            st.subheader("📊 Resultado da Importação")

                            col_res1, col_res2, col_res3, col_res4 = st.columns(4)

                            with col_res1:
                                st.metric("Inseridos", stats["inseridos"])

                            with col_res2:
                                st.metric("Atualizados", stats["atualizados"])

                            with col_res3:
                                st.metric("Ignorados", stats["ignorados"])

                            with col_res4:
                                st.metric("Erros", stats["erros"])

                            if stats["erros"] == 0 and stats["inseridos"] + stats["atualizados"] > 0:
                                UIComponents.show_success_message("Importação concluída com sucesso!")
                                AccessibilityManager.announce_message(
                                    f"Importação concluída. {stats['inseridos']} inseridos, {stats['atualizados']} atualizados."
                                )

                            if erros:
                                st.error(f"❌ {len(erros)} erros encontrados")
                                with st.expander("Ver erros"):
                                    for erro in erros[:20]:
                                        st.error(erro)

                        except Exception as e:
                            st.error(f"❌ Erro durante a importação: {str(e)}")

            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")

    def _render_analise_rfm(self):
        """Renderiza análise RFM de clientes com scoring robusto"""
        st.subheader("📊 Análise RFM de Clientes")
        
        st.info("""
        **O que é análise RFM?**
        - **R** (Recência): Clientes que compraram recentemente
        - **F** (Frequência): Clientes que compram com frequência
        - **M** (Valor): Clientes que gastam mais
        
        Esta análise ajuda a identificar seus melhores clientes e oportunidades de relacionamento.
        """)
        
        if not self.vendas:
            st.warning("Serviço de vendas não disponível para análise RFM.")
            return
        
        # Query melhorada para incluir apenas clientes com compras
        query = """
            SELECT 
                c.id,
                c.nome,
                c.cpf,
                c.telefone,
                c.email,
                COUNT(v.id) as frequencia,
                COALESCE(SUM(v.valor_total), 0) as valor_total,
                MAX(v.data_venda) as ultima_compra,
                MIN(v.data_venda) as primeira_compra,
                julianday('now') - julianday(COALESCE(MAX(v.data_venda), 'now')) as dias_ultima_compra
            FROM clientes c
            LEFT JOIN vendas v ON c.id = v.cliente_id
            WHERE c.ativo = 1
            GROUP BY c.id
            HAVING COUNT(v.id) > 0  -- Apenas clientes com compras
        """
        
        df_rfm = self.db.read_sql(query)
        
        if df_rfm.empty:
            st.info("Nenhum dado disponível para análise RFM. É necessário ter clientes com compras registradas.")
            return
        
        # Função para criar scores de forma segura
        def safe_rfm_scoring(df, column, q=5, reverse=False):
            """
            Cria scores RFM de forma segura, lidando com valores duplicados
            
            Args:
                df: DataFrame
                column: Coluna para calcular score
                q: Número de quantis desejados
                reverse: Se True, maiores valores recebem menores scores (para recência)
            """
            try:
                # Primeira tentativa: usar qcut com rank para evitar problemas com duplicatas
                if reverse:
                    # Para recência: menores valores = maiores scores
                    return pd.qcut(df[column].rank(method='first'), q=q, 
                                  labels=range(q, 0, -1))
                else:
                    # Para frequência e valor: maiores valores = maiores scores
                    return pd.qcut(df[column].rank(method='first'), q=q, 
                                  labels=range(1, q+1))
            except Exception as e:
                # Fallback: divisão baseada em percentis
                st.caption(f"Usando método alternativo para {column}: {str(e)[:50]}...")
                
                # Ordenar valores
                sorted_vals = df[column].sort_values().values
                n = len(sorted_vals)
                
                # Criar scores baseados em percentis
                scores = []
                for val in df[column]:
                    # Calcular percentil aproximado
                    position = sum(sorted_vals <= val) / n
                    
                    if reverse:
                        # Recência: menor valor = maior score
                        if position <= 0.2:
                            scores.append(5)
                        elif position <= 0.4:
                            scores.append(4)
                        elif position <= 0.6:
                            scores.append(3)
                        elif position <= 0.8:
                            scores.append(2)
                        else:
                            scores.append(1)
                    else:
                        # Frequência/Valor: maior valor = maior score
                        if position >= 0.8:
                            scores.append(5)
                        elif position >= 0.6:
                            scores.append(4)
                        elif position >= 0.4:
                            scores.append(3)
                        elif position >= 0.2:
                            scores.append(2)
                        else:
                            scores.append(1)
                
                return pd.Series(scores, index=df.index)
        
        # Aplicar scoring seguro
        df_rfm['R_score'] = safe_rfm_scoring(df_rfm, 'dias_ultima_compra', reverse=True)
        df_rfm['F_score'] = safe_rfm_scoring(df_rfm, 'frequencia', reverse=False)
        df_rfm['M_score'] = safe_rfm_scoring(df_rfm, 'valor_total', reverse=False)
        
        # Garantir que os scores são inteiros
        df_rfm['R_score'] = df_rfm['R_score'].astype(int)
        df_rfm['F_score'] = df_rfm['F_score'].astype(int)
        df_rfm['M_score'] = df_rfm['M_score'].astype(int)
        
        # Calcular score total
        df_rfm['RFM_score'] = df_rfm['R_score'] + df_rfm['F_score'] + df_rfm['M_score']
        
        # Classificar clientes
        def classificar_cliente(row):
            if row['RFM_score'] >= 13:
                return '🏆 CAMPEÃO'
            elif row['RFM_score'] >= 10:
                return '⭐ LEAL'
            elif row['RFM_score'] >= 7:
                return '📈 PROMISSOR'
            elif row['RFM_score'] >= 4:
                return '⚠️ EM RISCO'
            else:
                return '❌ INATIVO'
        
        df_rfm['classificacao'] = df_rfm.apply(classificar_cliente, axis=1)
        
        # Estatísticas resumidas
        col_rfm1, col_rfm2, col_rfm3, col_rfm4 = st.columns(4)
        
        with col_rfm1:
            campeoes = len(df_rfm[df_rfm['classificacao'] == '🏆 CAMPEÃO'])
            st.metric("🏆 Campeões", campeoes)
        
        with col_rfm2:
            leais = len(df_rfm[df_rfm['classificacao'] == '⭐ LEAL'])
            st.metric("⭐ Leais", leais)
        
        with col_rfm3:
            promissores = len(df_rfm[df_rfm['classificacao'] == '📈 PROMISSOR'])
            st.metric("📈 Promissores", promissores)
        
        with col_rfm4:
            risco = len(df_rfm[df_rfm['classificacao'].isin(['⚠️ EM RISCO', '❌ INATIVO'])])
            st.metric("⚠️ Em Risco", risco)
        
        # Tabela detalhada
        st.subheader("📋 Análise Detalhada")
        
        # Preparar DataFrame para exibição
        df_display = df_rfm[['nome', 'classificacao', 'frequencia', 'valor_total', 
                             'ultima_compra', 'R_score', 'F_score', 'M_score', 'RFM_score']].copy()
        
        # Formatação para exibição
        df_display['ultima_compra'] = pd.to_datetime(df_display['ultima_compra']).dt.strftime('%d/%m/%Y')
        df_display['valor_total'] = df_display['valor_total'].apply(
            lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        # Ordenar por score total (melhores primeiro)
        df_display = df_display.sort_values('RFM_score', ascending=False)
        
        # Exibir tabela
        st.dataframe(
            df_display,
            hide_index=True,
            use_container_width=True,
            column_config={
                "nome": "Cliente",
                "classificacao": "Classificação",
                "frequencia": "Compras",
                "valor_total": "Total Gasto",
                "ultima_compra": "Última Compra",
                "R_score": "R",
                "F_score": "F",
                "M_score": "M",
                "RFM_score": "Total"
            }
        )
        
        # Sugestões de ação
        st.subheader("💡 Sugestões de Ação")
        
        col_sug1, col_sug2 = st.columns(2)
        
        with col_sug1:
            st.markdown("**🏆 Clientes Campeões**")
            st.markdown("""
            - Enviar ofertas exclusivas
            - Programa de fidelidade
            - Pedir indicações
            - Atendimento prioritário
            """)
            
            # Listar campeões
            campeoes_lista = df_rfm[df_rfm['classificacao'] == '🏆 CAMPEÃO']['nome'].tolist()
            if campeoes_lista:
                with st.expander(f"Ver lista de campeões ({len(campeoes_lista)})"):
                    for nome in campeoes_lista[:20]:
                        st.markdown(f"- {nome}")
        
        with col_sug2:
            st.markdown("**⚠️ Clientes em Risco**")
            st.markdown("""
            - Enviar cupons de desconto
            - Pesquisa de satisfação
            - Ofertas personalizadas
            - Campanha de reativação
            """)
            
            # Listar em risco
            risco_lista = df_rfm[df_rfm['classificacao'].isin(['⚠️ EM RISCO', '❌ INATIVO'])]['nome'].tolist()
            if risco_lista:
                with st.expander(f"Ver clientes em risco ({len(risco_lista)})"):
                    for nome in risco_lista[:20]:
                        st.markdown(f"- {nome}")
        
        # Opção de exportar análise
        st.markdown("---")
        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])
        
        with col_exp1:
            csv_rfm = df_rfm.to_csv(index=False)
            st.download_button(
                "📥 Exportar CSV",
                csv_rfm,
                f"analise_rfm_{date.today().strftime('%Y%m%d')}.csv",
                "text/csv",
                key="download_rfm_csv"
            )
        
        with col_exp2:
            # Gráfico de distribuição
            import plotly.express as px
            fig = px.pie(
                df_rfm,
                names='classificacao',
                title='Distribuição por Classificação RFM',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
