"""
app.py - ElectroGest v1.0
Ponto de entrada principal da aplicação Streamlit com captura de IP dinâmico
"""

import streamlit as st

# Configuração da página DEVE ser a primeira chamada Streamlit
st.set_page_config(
    page_title="ElectroGest - Sistema de Gestão Comercial",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS para esconder navegação padrão do Streamlit completamente
st.markdown("""
<style>
    /* Esconde navegação automática de páginas */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    /* Esconde sidebar quando não logado */
    [data-testid="stSidebar"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Imports padrão
import os
import sys
from datetime import datetime

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports da aplicação
from config import CONFIG
from core.database import OptimizedDatabase
from core.security import Security, Formatters
from core.auth_service import AuditLog, Auth
from core.cliente_service import ClienteService
from core.produto_service import ProdutoService
from core.venda_service import VendaService
from core.promocao_service import PromocaoService
from core.categoria_service import CategoriaService
from core.relatorio_service import RelatorioService
from core.estoque_service import EstoqueService
from ui.styles import Styles
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager
from core.backup import BackupManager, BackupScheduler

# Imports das páginas usando import dinâmico
import importlib.util

pages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

def load_page_class(filename, class_name):
    """Carrega uma classe de página dinamicamente dos arquivos .py"""
    filepath = os.path.join(pages_dir, filename)
    spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[filename[:-3]] = module
    spec.loader.exec_module(module)
    return getattr(module, class_name)

# Carrega todas as páginas dinamicamente
LoginPage = load_page_class("login.py", "LoginPage")
DashboardPage = load_page_class("dashboard.py", "DashboardPage")
VendasPage = load_page_class("vendas.py", "VendasPage")
ClientesPage = load_page_class("clientes.py", "ClientesPage")
ProdutosPage = load_page_class("produtos.py", "ProdutosPage")
EstoquePage = load_page_class("estoque.py", "EstoquePage")
PromocoesPage = load_page_class("promocoes.py", "PromocoesPage")
RelatoriosPage = load_page_class("relatorios.py", "RelatoriosPage")
ProdutividadePage = load_page_class("produtividade.py", "ProdutividadePage")
AlterarSenhaPage = load_page_class("alterar_senha.py", "AlterarSenhaPage")
LogsPage = load_page_class("logs.py", "LogsPage")
AdminPage = load_page_class("admin.py", "AdminPage")
GerenciarVendasPage = load_page_class("gerenciar_vendas.py", "GerenciarVendasPage")


class ElectroGestApp:
    """
    Classe principal da aplicação ElectroGest.
    Gerencia estado, serviços, navegação e injeção de dependências.
    """
    
    def __init__(self):
        self.db = None
        self.auth = None
        self.audit = None
        self.clientes = None
        self.produtos = None
        self.vendas = None
        self.promocoes = None
        self.categorias = None
        self.relatorios = None
        self.estoque = None
        self.backup_manager = None
        
        # Inicializa serviços
        self._init_services()
        
        # Inicializa backup automático
        self._init_backup()
        
        # Inicializa estado da sessão
        self._init_session_state()
        
        # Registrar shutdown hook
        import atexit
        atexit.register(self._shutdown_backup)
    
    def _get_client_ip(self) -> str:
        """
        Captura o IP real do cliente baseado nos headers do Streamlit
        
        Returns:
            String com o IP do cliente ou '127.0.0.1' se não conseguir detectar
        """
        try:
            # Tentar obter headers do Streamlit
            headers = st.context.headers if hasattr(st, 'context') else {}
            
            # Lista de headers que podem conter o IP real (em ordem de prioridade)
            ip_headers = [
                'X-Forwarded-For',      # Header padrão de proxy
                'X-Real-IP',             # Header do Nginx
                'CF-Connecting-IP',       # Cloudflare
                'True-Client-IP',         # Cloudflare
                'X-Client-IP',           
                'X-Forwarded',
                'Forwarded-For',
                'Forwarded',
                'Remote-Addr'             # Fallback
            ]
            
            # Verificar cada header
            for header in ip_headers:
                if header in headers:
                    ip_value = headers[header]
                    # X-Forwarded-For pode conter múltiplos IPs (cliente, proxy1, proxy2)
                    if header == 'X-Forwarded-For' and ',' in ip_value:
                        # Pegar o primeiro IP (do cliente original)
                        return ip_value.split(',')[0].strip()
                    return ip_value.strip()
            
            # Tentar obter IP da sessão do Streamlit (se disponível)
            if hasattr(st, 'query_params') and 'client_ip' in st.query_params:
                return st.query_params['client_ip']
            
        except Exception as e:
            # Log do erro para debug (opcional)
            print(f"Erro ao capturar IP: {e}")
        
        # Fallback para localhost
        return "127.0.0.1"
    
    def _init_services(self):
        """Inicializa todos os serviços com injeção de dependências"""
        try:
            # Database
            self.db = OptimizedDatabase(CONFIG.db_path)
            
            # Garante schema e dados iniciais
            self.db.init_schema()
            self.db.ensure_seed_data()
            
            # Serviços core
            self.audit = AuditLog(self.db)
            self.auth = Auth(self.db)
            
            # Serviços de negócio
            self.clientes = ClienteService(self.db, self.audit)
            self.categorias = CategoriaService(self.db, self.audit)
            self.produtos = ProdutoService(self.db, self.audit)
            self.promocoes = PromocaoService(self.db, self.audit)
            self.vendas = VendaService(self.db, self.audit, self.produtos)
            self.estoque = EstoqueService(self.db, self.audit, self.produtos)
            self.relatorios = RelatorioService(self.db)
            
            # Conectar serviços que dependem uns dos outros
            self.vendas.produto_service = self.produtos
            self.estoque.produto_service = self.produtos
            
        except Exception as e:
            st.error(f"❌ Erro ao inicializar serviços: {str(e)}")
            st.stop()
    
    def _init_backup(self):
        """Inicializa o sistema de backup automático"""
        try:
            os.makedirs("backups", exist_ok=True)
            
            self.backup_manager = BackupManager(CONFIG.db_path, "backups")
            
            scheduler = BackupScheduler(self.backup_manager)
            schedule_config = scheduler.load_schedule()
            
            if schedule_config.get("enabled", False):
                interval = schedule_config.get("interval", 24)
                self.backup_manager.start_auto_backup(
                    interval_hours=interval,
                    callback=self._on_backup_completed
                )
                
                if hasattr(self, 'audit') and self.audit:
                    ip = self._get_client_ip()
                    self.audit.registrar(
                        "SISTEMA",
                        "BACKUP",
                        "Backup automático iniciado",
                        f"Intervalo: {interval} horas",
                        ip
                    )
        
        except Exception as e:
            print(f"⚠️ Erro ao inicializar backup automático: {str(e)}")
    
    def _on_backup_completed(self, backup_path):
        """Callback executado quando um backup automático é concluído"""
        try:
            if hasattr(self, 'audit') and self.audit:
                ip = self._get_client_ip()
                self.audit.registrar(
                    "SISTEMA",
                    "BACKUP",
                    "Backup automático concluído",
                    f"Arquivo: {os.path.basename(backup_path)}",
                    ip
                )
        except Exception as e:
            print(f"⚠️ Erro ao processar callback de backup: {str(e)}")
    
    def _shutdown_backup(self):
        """Finaliza o sistema de backup ao encerrar a aplicação"""
        if self.backup_manager:
            self.backup_manager.stop_auto_backup()
            
            if hasattr(self, 'audit') and self.audit:
                ip = self._get_client_ip()
                self.audit.registrar(
                    "SISTEMA",
                    "BACKUP",
                    "Backup automático encerrado",
                    "Aplicação finalizada",
                    ip
                )
    
    def _init_session_state(self):
        """Inicializa variáveis de estado da sessão"""
        defaults = {
            "logado": False,
            "usuario_login": "",
            "usuario_nome": "",
            "nivel_acesso": "VISUALIZADOR",
            "pagina_atual": "login",
            "ultima_busca": "",
            "clientes_filtrados": None,
            "produtos_filtrados": None,
            "vendas_historico": None,
            "relatorio_avancado": None,
            "carrinho_compras": [],
            "cliente_venda_atual": None,
            "page_gerenciar": 1,
            "page_gerenciar_vendas": 1,
            "senha_alterada": False,
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def _inject_styles(self):
        """Injeta CSS e JavaScript personalizado"""
        try:
            Styles.inject()
            AccessibilityManager.inject_accessibility_js()
        except Exception as e:
            st.warning(f"Não foi possível injetar estilos: {str(e)}")
    
    def _render_sidebar(self):
        """Renderiza menu lateral de navegação apenas para usuários logados"""
        if not st.session_state.get('logado', False):
            return
        
        st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: block !important; }
            
            /* ESTILOS COMPACTOS DO MENU */
            [data-testid="stSidebar"] {
                padding-top: 0.5rem !important;
                width: 250px !important;
            }
            
            [data-testid="stSidebar"] > div:first-child {
                padding-top: 0.5rem !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            
            [data-testid="stSidebar"] .stButton button {
                margin-top: 0.1rem !important;
                margin-bottom: 0.1rem !important;
                padding-top: 0.25rem !important;
                padding-bottom: 0.25rem !important;
                font-size: 0.9rem !important;
            }
            
            [data-testid="stSidebar"] h1 {
                font-size: 1.3rem !important;
                margin-top: 0 !important;
                margin-bottom: 0.25rem !important;
            }
            
            [data-testid="stSidebar"] h2 {
                font-size: 1.1rem !important;
                margin-top: 0.25rem !important;
                margin-bottom: 0.25rem !important;
            }
            
            [data-testid="stSidebar"] h3 {
                font-size: 1rem !important;
                margin-top: 0.15rem !important;
                margin-bottom: 0.15rem !important;
            }
            
            [data-testid="stSidebar"] p {
                margin-top: 0.1rem !important;
                margin-bottom: 0.1rem !important;
                font-size: 0.9rem !important;
            }
            
            [data-testid="stSidebar"] hr {
                margin-top: 0.3rem !important;
                margin-bottom: 0.3rem !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        with st.sidebar:
            st.markdown("### 📍 Menu")
            
            # Itens do menu principal
            menu_items = [
                ("🏠 Dashboard", "dashboard"),
                ("💰 Vendas", "vendas"),
                ("👥 Clientes", "clientes"),
                ("📦 Produtos", "produtos"),
                ("📊 Estoque", "estoque"),
                ("🎯 Promoções", "promocoes"),
                ("📋 Relatórios", "relatorios"),
            ]
            
            # Itens para ADMIN/OPERADOR
            if st.session_state.get('nivel_acesso') in ["ADMIN", "OPERADOR"]:
                menu_items.extend([
                    ("📋 Gerenciar Vendas", "gerenciar_vendas"),
                    ("📈 Produtividade", "produtividade"),
                ])
            
            # Itens apenas para ADMIN
            if st.session_state.get('nivel_acesso') == "ADMIN":
                menu_items.extend([
                    ("📝 Logs", "logs"),
                    ("⚙️ Administração", "admin"),
                ])
            
            # Renderizar botões do menu
            for label, page in menu_items:
                current_page = st.session_state.get('pagina_atual', 'login')
                btn_type = "primary" if current_page == page else "secondary"
                
                if st.button(label, use_container_width=True, type=btn_type, key=f"nav_{page}"):
                    st.session_state.pagina_atual = page
                    st.rerun()
            
            # Separador
            st.markdown("---")
            
            # Informações do usuário
            st.markdown(f"**👤 {st.session_state.get('usuario_nome', 'Usuário')}**")
            st.markdown(f"🔑 {st.session_state.get('nivel_acesso', 'VISUALIZADOR')}")
            
            # Botões de ações do usuário
            if st.button("🔐 Alterar Minha Senha", use_container_width=True, type="secondary", key="btn_alterar_senha"):
                st.session_state.pagina_atual = "alterar_senha"
                st.rerun()

            if st.button("🚪 Sair", use_container_width=True, type="secondary"):
                self._logout()
    
    def _logout(self):
        """Realiza logout do usuário"""
        ip = self._get_client_ip()
        
        if st.session_state.get('usuario_nome') and hasattr(self, 'audit') and self.audit:
            try:
                self.audit.registrar(
                    st.session_state.usuario_nome,
                    "AUTH",
                    "Logout",
                    "Usuário desconectou do sistema",
                    ip
                )
            except:
                pass
        
        keys_to_clear = [
            "logado", "usuario_login", "usuario_nome", "nivel_acesso",
            "pagina_atual", "ultima_busca", "clientes_filtrados",
            "produtos_filtrados", "vendas_historico", "carrinho_compras",
            "cliente_venda_atual", "page_gerenciar", "page_gerenciar_vendas",
            "venda_estornar", "cliente_excluir", "produto_excluir"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.pagina_atual = "login"
        st.rerun()
    
    def _route_page(self):
        """Roteia para a página atual"""
        page = st.session_state.get('pagina_atual', 'login')
        
        # TELA DE LOGIN
        if page == "login" or not st.session_state.get('logado', False):
            st.markdown("""
            <style>
                [data-testid="stSidebar"] {display: none !important;}
                section[data-testid="stSidebar"] {display: none !important;}
                .css-1cypcdb {display: none !important;}
            </style>
            """, unsafe_allow_html=True)
            
            login_page = LoginPage(self.auth, self.audit)
            login_page.render()
            return
        
        # PÁGINAS INTERNAS
        if not st.session_state.get('logado', False):
            st.session_state.pagina_atual = "login"
            st.rerun()
            return
        
        pages_map = {
            "dashboard": lambda: DashboardPage(
                self.db, self.relatorios, self.clientes, 
                self.produtos, self.vendas
            ),
            "vendas": lambda: VendasPage(
                self.db, self.vendas, self.clientes, 
                self.produtos, self.promocoes, self.auth
            ),
            "clientes": lambda: ClientesPage(
                self.db, self.clientes, self.auth, self.vendas
            ),
            "produtos": lambda: ProdutosPage(
                self.db, self.produtos, self.auth, self.categorias
            ),
            "estoque": lambda: EstoquePage(
                self.db, self.produtos, self.estoque, self.auth
            ),
            "promocoes": lambda: PromocoesPage(
                self.db, self.promocoes, self.auth
            ),
            "relatorios": lambda: RelatoriosPage(
                self.db, self.relatorios, self.clientes, 
                self.produtos, self.vendas
            ),
            "produtividade": lambda: ProdutividadePage(
                self.db, self.auth
            ),
            "alterar_senha": lambda: AlterarSenhaPage(
                self.db, self.auth, self.audit
            ),
            "logs": lambda: LogsPage(self.db, self.auth),
            "admin": lambda: AdminPage(
                self.db, self.auth, self.produtos, self.categorias
            ),
            "gerenciar_vendas": lambda: GerenciarVendasPage(
                self.db, self.vendas, self.auth, self.audit
            ),
        }
        
        if page in pages_map:
            try:
                page_instance = pages_map[page]()
                page_instance.render()
            except Exception as e:
                st.error(f"❌ Erro ao carregar página '{page}': {str(e)}")
                if st.session_state.get('nivel_acesso') == "ADMIN":
                    st.exception(e)
                st.info("Tente fazer login novamente ou contate o administrador.")
        else:
            st.error(f"❌ Página '{page}' não encontrada")
            st.session_state.pagina_atual = "dashboard"
            st.rerun()
    
    def run(self):
        """Método principal de execução da aplicação"""
        self._inject_styles()
        self._render_sidebar()
        self._route_page()


def main():
    """Função de entrada principal"""
    try:
        app = ElectroGestApp()
        app.run()
    except Exception as e:
        st.error(f"❌ Erro crítico na aplicação: {str(e)}")
        if os.getenv('STREAMLIT_ENV') == 'development':
            st.exception(e)


if __name__ == "__main__":
    main()
