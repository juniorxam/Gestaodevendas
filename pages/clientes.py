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

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = f"""
                SELECT 
                    id, nome, cpf, email, telefone, 
                    cidade, estado, data_nascimento, data_cadastro
                FROM clientes
                WHERE {where_sql}
                ORDER BY nome
                LIMIT 100
            """

            clientes = self.db.read_sql(query, params)
            st.session_state.clientes_filtrados = clientes

        # Exibir resultados
        if st.session_state.get('clientes_filtrados') is not None:
            clientes = st.session_state.clientes_filtrados

            if not clientes.empty:
                UIComponents.show_success_message(f"{len(clientes)} clientes encontrados")

                df_display = clientes.copy()
                df_display['cpf'] = df_display['cpf'].apply(lambda x: Security.formatar_cpf(x) if x else "")
                df_display['telefone'] = df_display['telefone'].apply(lambda x: Security.formatar_telefone(x) if x else "")
                df_display['data_nascimento'] = df_display['data_nascimento'].apply(Formatters.formatar_data_br)
                df_display['data_cadastro'] = pd.to_datetime(df_display['data_cadastro']).dt.strftime('%d/%m/%Y')

                UIComponents.create_data_table(
                    df_display,
                    key="clientes_table",
                    column_config={
                        "id": "ID",
                        "nome": "Nome",
                        "cpf": "CPF",
                        "email": "E-mail",
                        "telefone": "Telefone",
                        "cidade": "Cidade",
                        "estado": "UF",
                        "data_nascimento": "Nascimento",
                        "data_cadastro": "Cadastro"
                    }
                )

                # Botões de exportação
                col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])

                with col_exp1:
                    csv = clientes.to_csv(index=False)
                    st.download_button(
                        "📥 CSV",
                        csv,
                        "clientes.csv",
                        "text/csv"
                    )

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

                # Ver detalhes de um cliente
                st.markdown("---")
                st.subheader("📋 Detalhes do Cliente")
                
                cliente_selecionado = st.selectbox(
                    "Selecione um cliente para ver detalhes:",
                    options=clientes['nome'].tolist(),
                    key="select_cliente_detalhe"
                )
                
                if cliente_selecionado:
                    cliente_data = clientes[clientes['nome'] == cliente_selecionado].iloc[0]
                    self._render_cliente_detalhe(cliente_data)
            else:
                UIComponents.show_info_message("Nenhum cliente encontrado com os filtros selecionados.")
    
    def _render_cliente_detalhe(self, cliente):
        """Renderiza detalhes de um cliente específico"""
        col_detalhe1, col_detalhe2 = st.columns(2)
        
        with col_detalhe1:
            st.markdown(f"""
            **ID:** {cliente['id']}
            **Nome:** {cliente['nome']}
            **CPF:** {Security.formatar_cpf(cliente['cpf']) if cliente['cpf'] else 'Não informado'}
            **E-mail:** {cliente['email'] or 'Não informado'}
            **Telefone:** {Security.formatar_telefone(cliente['telefone']) if cliente['telefone'] else 'Não informado'}
            """)
        
        with col_detalhe2:
            st.markdown(f"""
            **Data Nascimento:** {cliente['data_nascimento'] or 'Não informado'}
            **Cidade/UF:** {cliente.get('cidade', '')}/{cliente.get('estado', '')}
            **Data Cadastro:** {cliente['data_cadastro']}
            """)
        
        # Histórico de compras
        if self.vendas:
            st.subheader("🛒 Histórico de Compras")
            
            historico = self.vendas.historico_cliente(int(cliente['id']))
            
            if not historico.empty:
                df_hist = historico.copy()
                df_hist['data_venda'] = pd.to_datetime(df_hist['data_venda']).dt.strftime('%d/%m/%Y %H:%M')
                df_hist['valor_total'] = df_hist['valor_total'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                
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
                
                # Totais
                total_compras = len(historico)
                total_gasto = historico['valor_total'].sum()
                
                st.info(f"**Total de compras:** {total_compras} | **Total gasto:** R$ {total_gasto:,.2f}")
            else:
                st.info("Cliente ainda não realizou compras.")
    
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
        """Renderiza análise RFM (Recência, Frequência, Valor)"""
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
        
        # Buscar dados para RFM
        query = """
            SELECT 
                c.id,
                c.nome,
                c.cpf,
                c.telefone,
                c.email,
                COUNT(v.id) as frequencia,
                SUM(v.valor_total) as valor_total,
                MAX(v.data_venda) as ultima_compra,
                MIN(v.data_venda) as primeira_compra,
                julianday('now') - julianday(MAX(v.data_venda)) as dias_ultima_compra
            FROM clientes c
            JOIN vendas v ON c.id = v.cliente_id
            GROUP BY c.id
            ORDER BY valor_total DESC
        """
        
        df_rfm = self.db.read_sql(query)
        
        if df_rfm.empty:
            st.info("Nenhum dado disponível para análise RFM.")
            return
        
        # Calcular scores RFM
        # Recência: quanto menor dias_ultima_compra, melhor
        df_rfm['R_score'] = pd.qcut(df_rfm['dias_ultima_compra'], q=5, labels=[5,4,3,2,1], duplicates='drop')
        
        # Frequência: quanto maior, melhor
        df_rfm['F_score'] = pd.qcut(df_rfm['frequencia'], q=5, labels=[1,2,3,4,5], duplicates='drop')
        
        # Valor: quanto maior, melhor
        df_rfm['M_score'] = pd.qcut(df_rfm['valor_total'], q=5, labels=[1,2,3,4,5], duplicates='drop')
        
        # Score total
        df_rfm['RFM_score'] = (
            df_rfm['R_score'].astype(int) + 
            df_rfm['F_score'].astype(int) + 
            df_rfm['M_score'].astype(int)
        )
        
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
        
        # Estatísticas
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
        
        # Tabela RFM
        st.subheader("📋 Análise Detalhada")
        
        df_display = df_rfm[['nome', 'classificacao', 'frequencia', 'valor_total', 'ultima_compra']].copy()
        df_display['ultima_compra'] = pd.to_datetime(df_display['ultima_compra']).dt.strftime('%d/%m/%Y')
        df_display['valor_total'] = df_display['valor_total'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        
        st.dataframe(
            df_display,
            hide_index=True,
            column_config={
                "nome": "Cliente",
                "classificacao": "Classificação",
                "frequencia": "Compras",
                "valor_total": "Total Gasto",
                "ultima_compra": "Última Compra"
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
        
        with col_sug2:
            st.markdown("**⚠️ Clientes em Risco**")
            st.markdown("""
            - Enviar cupons de desconto
            - Pesquisa de satisfação
            - Ofertas personalizadas
            - Campanha de reativação
            """)