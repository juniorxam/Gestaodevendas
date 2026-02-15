"""
conftest.py - Fixtures compartilhadas para os testes
"""

import os
import sys
import pytest
import tempfile
import shutil
from datetime import date, timedelta

# Garantir que o diretório raiz está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import Database
from core.auth_service import AuditLog, Auth
from core.cliente_service import ClienteService
from core.produto_service import ProdutoService
from core.categoria_service import CategoriaService
from core.venda_service import VendaService
from core.estoque_service import EstoqueService
from core.promocao_service import PromocaoService
from core.relatorio_service import RelatorioService
from core.backup import BackupManager


def pytest_addoption(parser):
    """Adiciona opções de linha de comando para o pytest"""
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    """Configura marcadores personalizados"""
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    """Pula testes lentos por padrão, a menos que --runslow seja especificado"""
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture(scope="function")
def temp_db_path():
    """Fixture que fornece um caminho temporário para banco de dados"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture(scope="function")
def temp_backup_dir():
    """Fixture que fornece um diretório temporário para backups"""
    path = tempfile.mkdtemp()
    yield path
    if os.path.exists(path):
        shutil.rmtree(path)


@pytest.fixture(scope="function")
def empty_db(temp_db_path):
    """Fixture que fornece um banco de dados vazio"""
    db = Database(temp_db_path)
    db.init_schema()
    yield db


@pytest.fixture(scope="function")
def populated_db(empty_db):
    """Fixture que fornece um banco com dados básicos"""
    db = empty_db
    
    # Criar serviços
    audit = AuditLog(db)
    cliente_service = ClienteService(db, audit)
    categoria_service = CategoriaService(db, audit)
    produto_service = ProdutoService(db, audit)
    
    # Categorias
    categoria_service.cadastrar_categoria("ELETRÔNICOS", "Teste", "admin")
    categoria_service.cadastrar_categoria("ACESSÓRIOS", "Teste", "admin")
    
    # Clientes
    cliente_service.cadastrar_individual({
        "nome": "CLIENTE TESTE 1",
        "cpf": "11122233344",
        "email": "teste1@email.com",
        "telefone": "(11) 91111-1111"
    }, "admin")
    
    cliente_service.cadastrar_individual({
        "nome": "CLIENTE TESTE 2",
        "cpf": "55566677788",
        "email": "teste2@email.com",
        "telefone": "(11) 92222-2222"
    }, "admin")
    
    # Produtos
    produto_service.cadastrar_produto({
        "nome": "NOTEBOOK TESTE",
        "codigo_barras": "7891111111111",
        "categoria": "ELETRÔNICOS",
        "preco_custo": 2000.00,
        "preco_venda": 3500.00,
        "quantidade_estoque": 20,
        "estoque_minimo": 5
    }, "admin")
    
    produto_service.cadastrar_produto({
        "nome": "SMARTPHONE TESTE",
        "codigo_barras": "7892222222222",
        "categoria": "ELETRÔNICOS",
        "preco_custo": 1200.00,
        "preco_venda": 2000.00,
        "quantidade_estoque": 30,
        "estoque_minimo": 10
    }, "admin")
    
    yield db


@pytest.fixture(scope="function")
def services(populated_db):
    """Fixture que fornece todos os serviços inicializados"""
    db = populated_db
    audit = AuditLog(db)
    produto_service = ProdutoService(db, audit)
    
    return {
        "db": db,
        "audit": audit,
        "auth": Auth(db),
        "clientes": ClienteService(db, audit),
        "categorias": CategoriaService(db, audit),
        "produtos": produto_service,
        "vendas": VendaService(db, audit, produto_service),
        "estoque": EstoqueService(db, audit, produto_service),
        "promocoes": PromocaoService(db, audit),
        "relatorios": RelatorioService(db)
    }


@pytest.fixture(scope="function")
def backup_manager(temp_db_path, temp_backup_dir):
    """Fixture que fornece um BackupManager configurado"""
    # Criar banco com dados
    db = Database(temp_db_path)
    db.init_schema()
    for i in range(5):
        db.execute("INSERT INTO clientes (nome) VALUES (?)", (f"CLIENTE {i}",))
    
    manager = BackupManager(temp_db_path, temp_backup_dir)
    yield manager
    manager.stop_auto_backup()