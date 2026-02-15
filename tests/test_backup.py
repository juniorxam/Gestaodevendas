"""
test_backup.py - Testes do sistema de backup (CORRIGIDO)
"""

import os
import pytest
import sys
import tempfile
import shutil
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backup import BackupManager, BackupScheduler
from core.database import Database
from tests.test_config import TEST_DB_PATH, TEST_BACKUP_DIR, limpar_arquivos_teste


class TestBackupManager:
    """Testes para o BackupManager"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        self.backup_dir = TEST_BACKUP_DIR
        
        limpar_arquivos_teste()
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Criar banco de dados de teste com alguns dados
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        # Inserir alguns dados usando transação
        with self.db.connect() as conn:
            for i in range(5):
                conn.execute(
                    "INSERT INTO clientes (nome) VALUES (?)",
                    (f"CLIENTE BACKUP {i}",)
                )
        
        self.backup_manager = BackupManager(self.db_path, self.backup_dir)
        
        yield
        
        limpar_arquivos_teste()
    
    def test_create_backup(self):
        """Testa criação de backup"""
        backup_path = self.backup_manager.create_backup()
        
        assert backup_path is not None
        assert os.path.exists(backup_path)
        assert backup_path.startswith(self.backup_dir)
        assert backup_path.endswith(".db")
        
        # Verificar se o backup contém dados
        backup_db = Database(backup_path)
        clientes = backup_db.read_sql("SELECT * FROM clientes")
        assert len(clientes) == 5
    
    def test_create_backup_with_suffix(self):
        """Testa criação de backup com sufixo"""
        backup_path = self.backup_manager.create_backup(suffix="manual")
        
        assert backup_path is not None
        assert "manual" in backup_path
    
    def test_list_backups(self):
        """Testa listagem de backups"""
        # Criar backups com nomes únicos (adicionar sleep para timestamps diferentes)
        time.sleep(0.1)
        self.backup_manager.create_backup(suffix="test1")
        time.sleep(0.2)
        self.backup_manager.create_backup(suffix="test2")
        time.sleep(0.1)
        
        backups = self.backup_manager.list_backups()
        
        # Filtrar apenas os backups de teste
        backup_files = [b for b in backups if b["filename"].endswith(".db") and "test" in b["filename"]]
        assert len(backup_files) >= 2, f"Esperado >=2 backups, encontrado {len(backup_files)}"
    
    def test_restore_backup(self):
        """Testa restauração de backup"""
        # Criar backup
        backup_path = self.backup_manager.create_backup(suffix="before_alter")
        
        # Modificar banco original
        self.db.execute(
            "INSERT INTO clientes (nome) VALUES (?)",
            ("NOVO CLIENTE",)
        )
        
        # Verificar que modificação foi feita
        clientes_antes = self.db.read_sql("SELECT * FROM clientes")
        assert len(clientes_antes) == 6
        
        # Restaurar backup
        success = self.backup_manager.restore_backup(backup_path)
        assert success is True
        
        # Verificar que restaurou
        self.db = Database(self.db_path)  # Recriar conexão
        clientes_depois = self.db.read_sql("SELECT * FROM clientes")
        assert len(clientes_depois) == 5
    
    def test_restore_backup_invalid(self):
        """Testa restauração de backup inválido"""
        success = self.backup_manager.restore_backup("caminho/inexistente.db")
        assert success is False
    
    def test_cleanup_old_backups(self):
        """Testa limpeza de backups antigos"""
        # Criar backups com datas simuladas
        for i in range(5):
            backup_path = os.path.join(self.backup_dir, f"backup_{i}.db")
            with open(backup_path, 'w') as f:
                f.write("teste")
            
            # Simular data antiga para alguns
            if i < 3:
                os.utime(backup_path, (time.time() - 40*24*3600, time.time() - 40*24*3600))  # 40 dias atrás
        
        # Executar limpeza com cutoff de 30 dias
        self.backup_manager._cleanup_old_backups(days_to_keep=30)
        
        # Verificar que apenas os mais recentes (menos de 30 dias) permanecem
        remaining = [f for f in os.listdir(self.backup_dir) if f.startswith("backup_")]
        assert len(remaining) == 2  # 2 recentes
    
    def test_backup_integrity(self):
        """Testa integridade dos dados no backup"""
        with self.db.connect() as conn:
            # Limpar dados existentes
            conn.execute("DELETE FROM itens_venda")
            conn.execute("DELETE FROM vendas")
            conn.execute("DELETE FROM clientes")
            conn.execute("DELETE FROM produtos")
            
            # Inserir categoria primeiro (para FOREIGN KEY)
            conn.execute(
                "INSERT INTO categorias (nome, descricao, ativo) VALUES (?, ?, ?)",
                ("CATEGORIA TESTE", "Teste", 1)
            )
            categoria_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
            
            # Inserir produto
            conn.execute(
                """
                INSERT INTO produtos (nome, preco_venda, quantidade_estoque, ativo, categoria_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("PRODUTO BACKUP TESTE", 100.00, 50, 1, categoria_id)
            )
            produto_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
            
            # Inserir cliente
            conn.execute(
                "INSERT INTO clientes (nome, cpf, email) VALUES (?, ?, ?)",
                ("INTEGRIDADE TESTE", "52998224725", "integ@teste.com")
            )
            cliente_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
            
            # Criar venda
            conn.execute(
                "INSERT INTO vendas (cliente_id, valor_total, forma_pagamento, usuario_registro) VALUES (?, ?, ?, ?)",
                (cliente_id, 500.00, "Dinheiro", "admin_teste")
            )
            venda_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()["id"]
            
            # Inserir itens
            conn.execute(
                "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (venda_id, produto_id, 2, 250.00)
            )
        
        # Criar backup
        backup_path = self.backup_manager.create_backup(suffix="integrity_test")
        assert backup_path is not None
        
        # Verificar backup
        backup_db = Database(backup_path)
        clientes = backup_db.read_sql("SELECT * FROM clientes WHERE nome = ?", ("INTEGRIDADE TESTE",))
        assert len(clientes) == 1
        
        # Verificar relações
        vendas = backup_db.read_sql("SELECT * FROM vendas WHERE cliente_id = ?", (cliente_id,))
        assert len(vendas) == 1
        
        itens = backup_db.read_sql("SELECT * FROM itens_venda WHERE venda_id = ?", (venda_id,))
        assert len(itens) == 1
    
    def test_auto_backup_thread(self):
        """Testa thread de backup automático"""
        # Iniciar backup automático
        callback_called = [False]
        
        def callback(backup_path):
            callback_called[0] = True
        
        self.backup_manager.start_auto_backup(interval_hours=0.01, callback=callback)
        
        # Aguardar um pouco para o backup executar
        time.sleep(2)
        
        # Verificar se pelo menos um backup foi criado
        backups = self.backup_manager.list_backups()
        assert len(backups) >= 1
        
        # Parar backup
        self.backup_manager.stop_auto_backup()
    
    def test_stop_auto_backup(self):
        """Testa parada do backup automático"""
        self.backup_manager.start_auto_backup(interval_hours=0.01)
        
        # Verificar que está rodando
        assert self.backup_manager.running is True
        assert self.backup_manager.backup_thread is not None
        assert self.backup_manager.backup_thread.is_alive() is True
        
        # Parar
        self.backup_manager.stop_auto_backup()
        
        # Verificar que parou
        assert self.backup_manager.running is False


class TestBackupScheduler:
    """Testes para o BackupScheduler"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        self.backup_dir = TEST_BACKUP_DIR
        
        limpar_arquivos_teste()
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Criar banco de dados de teste
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        self.backup_manager = BackupManager(self.db_path, self.backup_dir)
        self.scheduler = BackupScheduler(self.backup_manager)
        
        yield
        
        limpar_arquivos_teste()
    
    def test_save_and_load_schedule(self):
        """Testa salvar e carregar configuração de agendamento"""
        # Salvar configuração
        self.scheduler.save_schedule(interval_hours=12, enabled=True)
        
        # Carregar
        config = self.scheduler.load_schedule()
        
        assert config["enabled"] is True
        assert config["interval"] == 12
        assert "updated" in config
    
    def test_load_schedule_default(self):
        """Testa carregar configuração padrão quando arquivo não existe"""
        config = self.scheduler.load_schedule()
        
        assert config["enabled"] is False
        assert config["interval"] == 24
    
    def test_load_schedule_corrupted(self):
        """Testa carregar configuração corrompida"""
        # Criar arquivo corrompido
        with open(self.scheduler.schedule_file, 'w') as f:
            f.write("dados corrompidos sem formato")
        
        # Carregar deve retornar padrão
        config = self.scheduler.load_schedule()
        
        assert config.get("enabled", False) is False
        assert config.get("interval", 24) == 24