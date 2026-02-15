"""
admin.py - Página de administração do sistema
"""

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security
from core.auth_service import AuditLog
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager
from core.backup import BackupManager, BackupScheduler


class AdminPage:
    """Página de administração"""
    
    def __init__(self, db, auth, produtos, categorias):
        self.db = db
        self.auth = auth
        self.produtos = produtos
        self.categorias = categorias
    
    def render(self):
        """Renderiza página de administração"""
        st.title("⚙️ Administração do Sistema")
        UIComponents.breadcrumb("🏠 Início", "Administração")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "ADMIN"):
            UIComponents.show_error_message("Apenas administradores podem acessar esta página.")
            return

        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "👥 Usuários",
            "📦 Categorias",
            "💾 Backup",
            "🛠️ Utilitários",
            "📊 Sistema",
            "🔐 Gerenciar Usuários",
            "📝 Logs"
        ])

        with tab1:
            self._render_usuarios()

        with tab2:
            self._render_categorias()

        with tab3:
            self._render_backup()

        with tab4:
            self._render_utilitarios()

        with tab5:
            self._render_sistema()

        with tab6:
            self._render_gerenciar_usuarios()

        with tab7:
            self._render_logs_admin()
    
    def _render_usuarios(self):
        """Renderiza administração de usuários (visão geral)"""
        st.subheader("👥 Visão Geral de Usuários")

        usuarios = self.db.read_sql(
            "SELECT login, nome, nivel_acesso, ativo, data_criacao FROM usuarios ORDER BY nome"
        )

        if not usuarios.empty:
            UIComponents.show_success_message(f"{len(usuarios)} usuários cadastrados")

            df_usuarios = usuarios.copy()
            df_usuarios['data_criacao'] = pd.to_datetime(df_usuarios['data_criacao']).dt.strftime('%d/%m/%Y')

            st.dataframe(
                df_usuarios,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "login": "Login",
                    "nome": "Nome",
                    "nivel_acesso": "Nível",
                    "ativo": "Ativo",
                    "data_criacao": "Data Criação"
                }
            )

        st.subheader("➕ Novo Usuário")

        with st.form("form_novo_usuario"):
            col1, col2 = st.columns(2)

            with col1:
                login = st.text_input("Login:*", key="novo_usuario_login")
                nome = st.text_input("Nome:*", key="novo_usuario_nome")
                senha = st.text_input("Senha:*", type="password", key="novo_usuario_senha")

            with col2:
                nivel_acesso = st.selectbox(
                    "Nível de Acesso:*",
                    ["VISUALIZADOR", "OPERADOR", "ADMIN"],
                    key="novo_usuario_nivel"
                )
                ativo = st.checkbox("Ativo", value=True, key="novo_usuario_ativo")

            if st.form_submit_button("💾 Criar Usuário", type="primary"):
                if not login.strip():
                    UIComponents.show_error_message("Login é obrigatório!")
                    st.stop()

                if not nome.strip():
                    UIComponents.show_error_message("Nome é obrigatório!")
                    st.stop()

                if not senha.strip():
                    UIComponents.show_error_message("Senha é obrigatória!")
                    st.stop()

                existe = self.db.fetchone("SELECT login FROM usuarios WHERE login = ?", (login.strip(),))
                if existe:
                    UIComponents.show_error_message("Login já existe!")
                    st.stop()

                try:
                    senha_hash = Security.sha256_hex(senha)
                    self.db.execute(
                        """
                        INSERT INTO usuarios (login, senha, nome, nivel_acesso, ativo)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (login.strip(), senha_hash, nome.strip(), nivel_acesso, 1 if ativo else 0)
                    )

                    audit = AuditLog(self.db)
                    audit.registrar(
                        st.session_state.usuario_nome,
                        "ADMIN",
                        "Criou usuário",
                        f"Novo usuário: {login}"
                    )

                    UIComponents.show_success_message("Usuário criado com sucesso!")
                    AccessibilityManager.announce_message("Novo usuário criado")
                    st.rerun()

                except Exception as e:
                    UIComponents.show_error_message(f"Erro ao criar usuário: {str(e)}")
    
    def _render_gerenciar_usuarios(self):
        """Renderiza gerenciamento completo de usuários"""
        st.subheader("🔐 Gerenciar Usuários")
        
        usuarios = self.db.read_sql(
            "SELECT login, nome, nivel_acesso, ativo, data_criacao FROM usuarios ORDER BY nome"
        )
        
        if usuarios.empty:
            st.info("Nenhum usuário cadastrado.")
            return
        
        usuarios_lista = usuarios['nome'].tolist()
        usuario_selecionado = st.selectbox(
            "Selecione um usuário para gerenciar:",
            usuarios_lista,
            key="select_usuario_gerenciar"
        )
        
        if usuario_selecionado:
            usuario_data = usuarios[usuarios['nome'] == usuario_selecionado].iloc[0]
            login = usuario_data['login']
            
            st.markdown("---")
            st.subheader(f"📝 Editando: {usuario_selecionado}")
            
            tab_edit, tab_password, tab_status = st.tabs(["✏️ Editar Dados", "🔑 Resetar Senha", "🔄 Status"])
            
            with tab_edit:
                self._render_editar_usuario(login, usuario_data)
            
            with tab_password:
                self._render_resetar_senha(login, usuario_selecionado)
            
            with tab_status:
                self._render_alterar_status(login, usuario_data)
    
    def _render_editar_usuario(self, login, usuario_data):
        """Editar dados do usuário"""
        with st.form(f"form_editar_usuario_{login}"):
            st.markdown("### ✏️ Editar Dados do Usuário")
            
            col1, col2 = st.columns(2)
            
            with col1:
                novo_nome = st.text_input(
                    "Nome:",
                    value=usuario_data['nome'],
                    key=f"edit_nome_{login}"
                )
                
                st.text_input(
                    "Login:",
                    value=login,
                    disabled=True,
                    key=f"edit_login_{login}"
                )
                st.caption("⚠️ O login não pode ser alterado")
            
            with col2:
                novo_nivel = st.selectbox(
                    "Nível de Acesso:",
                    ["VISUALIZADOR", "OPERADOR", "ADMIN"],
                    index=["VISUALIZADOR", "OPERADOR", "ADMIN"].index(usuario_data['nivel_acesso']),
                    key=f"edit_nivel_{login}"
                )
            
            if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                try:
                    self.db.execute(
                        """
                        UPDATE usuarios 
                        SET nome = ?, nivel_acesso = ?
                        WHERE login = ?
                        """,
                        (novo_nome.strip(), novo_nivel, login)
                    )
                    
                    audit = AuditLog(self.db)
                    audit.registrar(
                        st.session_state.usuario_nome,
                        "ADMIN",
                        "Editou usuário",
                        f"Alterou dados de {login}"
                    )
                    
                    UIComponents.show_success_message(f"Dados do usuário {login} atualizados com sucesso!")
                    st.rerun()
                    
                except Exception as e:
                    UIComponents.show_error_message(f"Erro ao atualizar: {str(e)}")
    
    def _render_resetar_senha(self, login, nome):
        """Resetar senha do usuário"""
        with st.form(f"form_reset_senha_{login}"):
            st.markdown("### 🔑 Resetar Senha do Usuário")
            st.warning(f"Você está prestes a resetar a senha de **{nome}**")
            
            nova_senha = st.text_input(
                "Nova Senha:",
                type="password",
                placeholder="Digite a nova senha",
                key=f"nova_senha_{login}"
            )
            
            confirmar_senha = st.text_input(
                "Confirmar Nova Senha:",
                type="password",
                placeholder="Digite a nova senha novamente",
                key=f"confirm_senha_{login}"
            )
            
            if st.form_submit_button("🔑 Resetar Senha", type="primary"):
                if not nova_senha:
                    UIComponents.show_error_message("A nova senha é obrigatória!")
                    st.stop()
                
                if nova_senha != confirmar_senha:
                    UIComponents.show_error_message("As senhas não conferem!")
                    st.stop()
                
                if len(nova_senha) < 6:
                    UIComponents.show_error_message("A senha deve ter pelo menos 6 caracteres!")
                    st.stop()
                
                try:
                    senha_hash = Security.sha256_hex(nova_senha)
                    self.db.execute(
                        "UPDATE usuarios SET senha = ? WHERE login = ?",
                        (senha_hash, login)
                    )
                    
                    audit = AuditLog(self.db)
                    audit.registrar(
                        st.session_state.usuario_nome,
                        "ADMIN",
                        "Resetou senha",
                        f"Resetou senha de {login}"
                    )
                    
                    UIComponents.show_success_message(f"Senha do usuário {nome} resetada com sucesso!")
                    st.rerun()
                    
                except Exception as e:
                    UIComponents.show_error_message(f"Erro ao resetar senha: {str(e)}")
    
    def _render_alterar_status(self, login, usuario_data):
        """Ativar/Desativar/Excluir usuário"""
        st.markdown("### 🔄 Alterar Status do Usuário")
        
        status_atual = "ATIVO" if usuario_data['ativo'] == 1 else "INATIVO"
        st.info(f"Status atual: **{status_atual}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if usuario_data['ativo'] == 1:
                if st.button("🔴 Desativar Usuário", type="secondary", use_container_width=True, key=f"desativar_{login}"):
                    if login == st.session_state.usuario_login:
                        UIComponents.show_error_message("Você não pode desativar seu próprio usuário!")
                        st.stop()
                    
                    try:
                        self.db.execute(
                            "UPDATE usuarios SET ativo = 0 WHERE login = ?",
                            (login,)
                        )
                        
                        audit = AuditLog(self.db)
                        audit.registrar(
                            st.session_state.usuario_nome,
                            "ADMIN",
                            "Desativou usuário",
                            f"Desativou {login}"
                        )
                        
                        UIComponents.show_success_message(f"Usuário {login} desativado com sucesso!")
                        st.rerun()
                        
                    except Exception as e:
                        UIComponents.show_error_message(f"Erro ao desativar: {str(e)}")
            else:
                if st.button("🟢 Ativar Usuário", type="primary", use_container_width=True, key=f"ativar_{login}"):
                    try:
                        self.db.execute(
                            "UPDATE usuarios SET ativo = 1 WHERE login = ?",
                            (login,)
                        )
                        
                        audit = AuditLog(self.db)
                        audit.registrar(
                            st.session_state.usuario_nome,
                            "ADMIN",
                            "Ativou usuário",
                            f"Ativou {login}"
                        )
                        
                        UIComponents.show_success_message(f"Usuário {login} ativado com sucesso!")
                        st.rerun()
                        
                    except Exception as e:
                        UIComponents.show_error_message(f"Erro ao ativar: {str(e)}")
        
        with col2:
            if st.button("🗑️ Excluir Usuário", type="secondary", use_container_width=True, key=f"excluir_{login}"):
                st.session_state.usuario_excluir = {
                    'login': login,
                    'nome': usuario_data['nome']
                }
                st.rerun()
        
        if 'usuario_excluir' in st.session_state and st.session_state.usuario_excluir['login'] == login:
            self._render_modal_exclusao_usuario()
    
    def _render_modal_exclusao_usuario(self):
        """Renderiza modal de confirmação de exclusão de usuário"""
        usuario = st.session_state.usuario_excluir
        
        st.markdown("---")
        st.error("⚠️ **CONFIRMAÇÃO DE EXCLUSÃO DE USUÁRIO**")
        
        st.markdown(f"""
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; padding: 15px; margin: 10px 0;">
            <h4 style="color: #856404;">Você está prestes a excluir permanentemente este usuário:</h4>
            <ul>
                <li><strong>Login:</strong> {usuario['login']}</li>
                <li><strong>Nome:</strong> {usuario['nome']}</li>
            </ul>
            <p style="color: #dc3545; font-weight: bold;">Esta ação é IRREVERSÍVEL!</p>
        </div>
        """, unsafe_allow_html=True)
        
        registros = self.db.fetchone(
            "SELECT COUNT(*) as total FROM vendas WHERE usuario_registro = ?",
            (usuario['login'],)
        )
        total_registros = registros['total'] if registros else 0
        
        if total_registros > 0:
            st.warning(f"⚠️ Este usuário possui **{total_registros}** vendas associadas. Elas serão mantidas, mas o campo 'usuario_registro' será esvaziado.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Confirmar Exclusão", type="primary", use_container_width=True):
                try:
                    with self.db.connect() as conn:
                        conn.execute(
                            "UPDATE vendas SET usuario_registro = NULL WHERE usuario_registro = ?",
                            (usuario['login'],)
                        )
                        
                        conn.execute(
                            "DELETE FROM usuarios WHERE login = ?",
                            (usuario['login'],)
                        )
                    
                    audit = AuditLog(self.db)
                    audit.registrar(
                        st.session_state.usuario_nome,
                        "ADMIN",
                        "Excluiu usuário",
                        f"Excluiu {usuario['login']} - {total_registros} vendas desassociadas"
                    )
                    
                    UIComponents.show_success_message(f"Usuário {usuario['login']} excluído com sucesso!")
                    del st.session_state.usuario_excluir
                    st.rerun()
                    
                except Exception as e:
                    UIComponents.show_error_message(f"Erro ao excluir: {str(e)}")
        
        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                del st.session_state.usuario_excluir
                st.rerun()
    
    def _render_categorias(self):
        """Renderiza administração de categorias"""
        st.subheader("📦 Gerenciamento de Categorias")

        df_categorias = self.categorias.listar_todas(incluir_inativas=True)

        if not df_categorias.empty:
            UIComponents.show_success_message(f"{len(df_categorias)} categorias cadastradas")

            st.dataframe(
                df_categorias,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": "ID",
                    "nome": "Nome",
                    "descricao": "Descrição",
                    "total_produtos": "Produtos",
                    "ativo": "Ativa"
                }
            )

        st.subheader("➕ Nova Categoria")

        with st.form("form_nova_categoria"):
            nome = st.text_input("Nome da Categoria:*", key="nova_cat_nome")
            descricao = st.text_input("Descrição:", key="nova_cat_descricao")

            if st.form_submit_button("💾 Cadastrar Categoria", type="primary"):
                if not nome.strip():
                    UIComponents.show_error_message("Nome da categoria é obrigatório!")
                    st.stop()

                sucesso, msg = self.categorias.cadastrar_categoria(
                    nome=nome.strip(),
                    descricao=descricao.strip() if descricao else "",
                    usuario=st.session_state.usuario_nome
                )

                if sucesso:
                    UIComponents.show_success_message(msg)
                    st.rerun()
                else:
                    UIComponents.show_error_message(msg)
    
    def _render_backup(self):
        """Renderiza configurações de backup automático"""
        st.subheader("💾 Backup Automático do Banco de Dados")
        
        backup_manager = BackupManager(CONFIG.db_path, "backups")
        scheduler = BackupScheduler(backup_manager)
        
        schedule_config = scheduler.load_schedule()
        
        st.markdown("""
        ### Sobre o Backup Automático
        
        O sistema pode realizar backups automáticos do banco de dados em intervalos regulares.
        Os backups são armazenados na pasta `backups` e podem ser restaurados quando necessário.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⚙️ Configurações")
            
            enabled = st.toggle(
                "Ativar backup automático",
                value=schedule_config.get("enabled", False),
                help="Quando ativado, o sistema fará backups automaticamente"
            )
            
            interval = st.slider(
                "Intervalo entre backups (horas):",
                min_value=1,
                max_value=168,
                value=schedule_config.get("interval", 24),
                step=1
            )
            
            col_save1, col_save2 = st.columns(2)
            with col_save1:
                if st.button("💾 Salvar Configurações", use_container_width=True):
                    scheduler.save_schedule(interval, enabled)
                    
                    if enabled:
                        backup_manager.start_auto_backup(
                            interval_hours=interval,
                            callback=lambda x: st.toast(f"✅ Backup automático concluído: {os.path.basename(x)}")
                        )
                        UIComponents.show_success_message(f"Backup automático ativado! Intervalo: {interval} horas")
                    else:
                        backup_manager.stop_auto_backup()
                        UIComponents.show_info_message("Backup automático desativado")
                    
                    st.rerun()
            
            with col_save2:
                if st.button("🔄 Fazer Backup Agora", use_container_width=True, type="primary"):
                    with st.spinner("Criando backup..."):
                        backup_path = backup_manager.create_backup("manual")
                        if backup_path:
                            UIComponents.show_success_message(f"Backup criado: {os.path.basename(backup_path)}")
                            
                            with open(backup_path, 'rb') as f:
                                st.download_button(
                                    "📥 Baixar Backup",
                                    f.read(),
                                    os.path.basename(backup_path),
                                    "application/x-sqlite3",
                                    key="download_backup"
                                )
                        else:
                            UIComponents.show_error_message("Erro ao criar backup")
        
        with col2:
            st.markdown("### 📋 Backups Disponíveis")
            
            backups = backup_manager.list_backups()
            
            if backups:
                st.info(f"Total de {len(backups)} backups encontrados")
                
                for backup in backups[:10]:
                    with st.container():
                        col_b1, col_b2 = st.columns([3, 1])
                        
                        with col_b1:
                            st.markdown(f"**{backup['filename']}**")
                            st.caption(f"Criado: {backup['created'].strftime('%d/%m/%Y %H:%M:%S')} | Tamanho: {backup['size_mb']:.2f} MB")
                        
                        with col_b2:
                            if st.button("📥 Baixar", key=f"dl_{backup['filename']}"):
                                with open(backup['path'], 'rb') as f:
                                    st.download_button(
                                        "Download",
                                        f.read(),
                                        backup['filename'],
                                        "application/x-sqlite3",
                                        key=f"download_{backup['filename']}"
                                    )
                        
                        st.markdown("---")
            else:
                st.info("📭 Nenhum backup encontrado.")
    
    def _render_utilitarios(self):
        """Renderiza utilitários administrativos"""
        st.subheader("🛠️ Utilitários do Sistema")

        col1, col2 = st.columns(2)

        with col1:
            with st.container():
                st.markdown("### 🧹 Limpeza de Logs")
                st.markdown("Remova logs antigos do sistema.")

                dias_logs = st.number_input(
                    "Manter logs dos últimos (dias):",
                    min_value=30,
                    max_value=365,
                    value=90,
                    key="dias_manter_logs"
                )

                if st.button("Executar Limpeza", key="btn_limpeza", use_container_width=True):
                    with st.spinner("Executando limpeza..."):
                        try:
                            self.db.execute(
                                "DELETE FROM logs WHERE data_hora < datetime('now', '-' || ? || ' days')",
                                (str(dias_logs),)
                            )

                            logs_removidos = self.db.fetchone("SELECT changes() as c")['c']
                            UIComponents.show_success_message(f"Limpeza concluída: {logs_removidos} logs removidos")

                        except Exception as e:
                            UIComponents.show_error_message(f"Erro na limpeza: {str(e)}")

        with col2:
            with st.container():
                st.markdown("### 📊 Estatísticas do Banco")
                
                try:
                    db_size = os.path.getsize(CONFIG.db_path)
                    db_size_mb = db_size / (1024 * 1024)
                    st.metric("Tamanho do Banco", f"{db_size_mb:.2f} MB")
                    
                    total_tables = self.db.fetchone(
                        "SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'"
                    )['c']
                    st.metric("Tabelas", total_tables)
                    
                    if hasattr(self.db, 'get_cache_stats'):
                        cache_stats = self.db.get_cache_stats()
                        st.metric("Cache Hits", cache_stats['cache_hits'])
                        st.metric("Hit Rate", f"{cache_stats['hit_rate']*100:.1f}%")
                        
                except Exception as e:
                    st.error(f"Erro ao obter estatísticas: {str(e)}")

        st.subheader("🔍 Consulta SQL (Apenas SELECT)")

        sql_query = st.text_area(
            "Digite sua consulta SQL:",
            placeholder="SELECT * FROM vendas LIMIT 10",
            height=100,
            key="sql_query_admin"
        )

        if st.button("Executar Consulta", key="btn_exec_sql_admin", use_container_width=True):
            seguro, mensagem = Security.safe_select_only(sql_query)

            if not seguro:
                UIComponents.show_error_message(mensagem)
            else:
                try:
                    resultado = self.db.read_sql(sql_query)

                    if not resultado.empty:
                        UIComponents.show_success_message(f"Consulta executada: {len(resultado)} registros")
                        st.dataframe(resultado, use_container_width=True)

                        csv = resultado.to_csv(index=False)
                        st.download_button(
                            "📥 Exportar CSV",
                            csv,
                            "consulta.csv",
                            "text/csv",
                            key="download_consulta_csv"
                        )
                    else:
                        UIComponents.show_info_message("Nenhum resultado encontrado.")

                except Exception as e:
                    UIComponents.show_error_message(f"Erro na consulta: {str(e)}")
    
    def _render_sistema(self):
        """Renderiza informações do sistema"""
        st.subheader("📊 Informações do Sistema")

        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        with col_stat1:
            total_usuarios = self.db.fetchone("SELECT COUNT(*) as c FROM usuarios WHERE ativo = 1")['c']
            st.metric("Usuários Ativos", total_usuarios)

        with col_stat2:
            total_clientes = self.db.fetchone("SELECT COUNT(*) as c FROM clientes")['c']
            st.metric("Total Clientes", f"{total_clientes:,}")

        with col_stat3:
            total_produtos = self.db.fetchone("SELECT COUNT(*) as c FROM produtos WHERE ativo = 1")['c']
            st.metric("Produtos Ativos", f"{total_produtos:,}")

        with col_stat4:
            total_vendas = self.db.fetchone("SELECT COUNT(*) as c FROM vendas")['c']
            st.metric("Total Vendas", f"{total_vendas:,}")

        st.markdown("### 📦 Informações da Versão")

        info_cols = st.columns(2)

        with info_cols[0]:
            st.markdown(f"""
            **Versão do Sistema:** 1.0
            **Ano de Referência:** {CONFIG.ano_atual}
            **Banco de Dados:** SQLite
            **Framework:** Streamlit
            **Desenvolvido em:** Python 3.10+
            """)

        with info_cols[1]:
            st.markdown(f"""
            **Desenvolvedor:** ElectroGest
            **Última Atualização:** {datetime.now().strftime('%d/%m/%Y')}
            **Status:** 🟢 Online
            **Usuário Atual:** {st.session_state.usuario_nome}
            **Nível de Acesso:** {st.session_state.nivel_acesso}
            """)
    
    def _render_logs_admin(self):
        """Renderiza visualização rápida de logs"""
        st.subheader("📝 Últimos Logs do Sistema")
        
        logs = self.db.read_sql("""
            SELECT 
                data_hora,
                usuario,
                modulo,
                acao,
                detalhes
            FROM logs
            ORDER BY data_hora DESC
            LIMIT 100
        """)
        
        if not logs.empty:
            df_logs = logs.copy()
            
            # CORREÇÃO: Converter data_hora para datetime de forma segura
            try:
                # Tentar converter para datetime
                df_logs['data_hora_dt'] = pd.to_datetime(df_logs['data_hora'], errors='coerce')
                # Formatar para exibição
                df_logs['data_hora'] = df_logs['data_hora_dt'].dt.strftime('%d/%m/%Y %H:%M:%S')
            except Exception as e:
                # Se falhar, usar string original
                print(f"Erro ao converter datas: {e}")
                pass
            
            st.dataframe(
                df_logs[['data_hora', 'usuario', 'modulo', 'acao', 'detalhes']],
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("📥 Exportar Logs", key="btn_exportar_logs_admin"):
                csv = logs.to_csv(index=False)
                st.download_button(
                    "📥 Baixar CSV",
                    csv,
                    f"logs_completos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    key="download_logs_admin"
                )
        else:
            st.info("Nenhum log encontrado.")