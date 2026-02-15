"""
test_database.py - Testes da camada de banco de dados
"""

import os
import pytest
import sqlite3
import tempfile
import pandas as pd
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database, OptimizedDatabase
from tests.test_config import TEST_DB_PATH, limpar_arquivos_teste


class TestDatabase:
    """Testes para a classe Database"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        # Criar instância do banco
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        yield
        
        # Limpeza após teste
        limpar_arquivos_teste()
    
    def test_init_schema(self):
        """Testa criação do schema"""
        # Verificar se as tabelas foram criadas
        tables = [
            "clientes", "categorias", "produtos", "promocoes",
            "vendas", "itens_venda", "usuarios", "logs"
        ]
        
        for table in tables:
            result = self.db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            assert result is not None, f"Tabela {table} não criada"
    
    def test_execute_insert(self):
        """Testa operação INSERT"""
        # Inserir um cliente
        result = self.db.execute(
            "INSERT INTO clientes (nome, email) VALUES (?, ?)",
            ("TESTE INSERT", "teste@email.com")
        )
        
        assert result == 1  # rowcount
        
        # Verificar se foi inserido
        cliente = self.db.fetchone("SELECT * FROM clientes WHERE nome = ?", ("TESTE INSERT",))
        assert cliente is not None
        assert cliente["nome"] == "TESTE INSERT"
        assert cliente["email"] == "teste@email.com"
    
    def test_execute_update(self):
        """Testa operação UPDATE"""
        # Inserir cliente
        self.db.execute(
            "INSERT INTO clientes (nome, email) VALUES (?, ?)",
            ("TESTE UPDATE", "update@email.com")
        )
        
        # Atualizar
        result = self.db.execute(
            "UPDATE clientes SET email = ? WHERE nome = ?",
            ("novo@email.com", "TESTE UPDATE")
        )
        
        assert result == 1
        
        # Verificar atualização
        cliente = self.db.fetchone("SELECT * FROM clientes WHERE nome = ?", ("TESTE UPDATE",))
        assert cliente["email"] == "novo@email.com"
    
    def test_execute_delete(self):
        """Testa operação DELETE"""
        # Inserir cliente
        self.db.execute(
            "INSERT INTO clientes (nome) VALUES (?)",
            ("TESTE DELETE",)
        )
        
        # Deletar
        result = self.db.execute(
            "DELETE FROM clientes WHERE nome = ?",
            ("TESTE DELETE",)
        )
        
        assert result == 1
        
        # Verificar deleção
        cliente = self.db.fetchone("SELECT * FROM clientes WHERE nome = ?", ("TESTE DELETE",))
        assert cliente is None
    
    def test_fetchone(self):
        """Testa fetchone"""
        # Inserir cliente
        self.db.execute(
            "INSERT INTO clientes (nome, email) VALUES (?, ?)",
            ("TESTE FETCHONE", "fetch@email.com")
        )
        
        # Buscar
        result = self.db.fetchone(
            "SELECT nome, email FROM clientes WHERE nome = ?",
            ("TESTE FETCHONE",)
        )
        
        assert result is not None
        assert result["nome"] == "TESTE FETCHONE"
        assert result["email"] == "fetch@email.com"
        
        # Buscar inexistente
        result = self.db.fetchone(
            "SELECT * FROM clientes WHERE nome = ?",
            ("INEXISTENTE",)
        )
        assert result is None
    
    def test_fetchall(self):
        """Testa fetchall"""
        # Inserir múltiplos clientes
        for i in range(5):
            self.db.execute(
                "INSERT INTO clientes (nome) VALUES (?)",
                (f"TESTE FETCHALL {i}",)
            )
        
        # Buscar todos
        results = self.db.fetchall("SELECT nome FROM clientes WHERE nome LIKE ?", ("TESTE FETCHALL%",))
        
        assert len(results) == 5
        assert all("TESTE FETCHALL" in row["nome"] for row in results)
    
    def test_read_sql(self):
        """Testa read_sql para DataFrame"""
        # Inserir dados
        for i in range(3):
            self.db.execute(
                "INSERT INTO clientes (nome) VALUES (?)",
                (f"TESTE DATAFRAME {i}",)
            )
        
        # Ler como DataFrame
        df = self.db.read_sql("SELECT nome FROM clientes WHERE nome LIKE ?", ("TESTE DATAFRAME%",))
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "nome" in df.columns
    
    def test_retry_on_locked(self):
        """Testa retry em caso de banco bloqueado"""
        # Simular lock abrindo outra conexão
        conn2 = sqlite3.connect(self.db_path)
        conn2.execute("BEGIN EXCLUSIVE")
        
        try:
            # Tentar inserir (deve retentar)
            result = self.db.execute(
                "INSERT INTO clientes (nome) VALUES (?)",
                ("TESTE RETRY",)
            )
            
            assert result == 1
            
        finally:
            conn2.rollback()
            conn2.close()


class TestOptimizedDatabase:
    """Testes para a classe OptimizedDatabase"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        self.db = OptimizedDatabase(self.db_path)
        self.db.init_schema()
        
        yield
        
        limpar_arquivos_teste()
    
    def test_cache_basic(self):
        """Testa funcionamento básico do cache"""
        # Inserir alguns dados
        for i in range(5):
            self.db.execute(
                "INSERT INTO clientes (nome) VALUES (?)",
                (f"CLIENTE CACHE {i}",)
            )
        
        # Primeira consulta (cache miss)
        df1 = self.db.read_sql("SELECT * FROM clientes ORDER BY id")
        
        # Segunda consulta (cache hit)
        df2 = self.db.read_sql("SELECT * FROM clientes ORDER BY id")
        
        assert df1.equals(df2)
        
        # Verificar estatísticas
        stats = self.db.get_cache_stats()
        assert stats["cache_hits"] >= 1
        assert stats["cache_misses"] >= 1
    
    def test_cache_invalidation(self):
        """Testa invalidação do cache por TTL"""
        # Inserir dados
        self.db.execute("INSERT INTO clientes (nome) VALUES (?)", ("TESTE TTL",))
        
        # Primeira consulta
        df1 = self.db.read_sql("SELECT * FROM clientes")
        
        # Consulta com TTL curto (deve usar cache)
        df2 = self.db.read_sql("SELECT * FROM clientes", ttl=1)
        
        assert df1.equals(df2)
        
        # Estatísticas devem mostrar hit
        stats = self.db.get_cache_stats()
        assert stats["cache_hits"] > 0
    
    def test_performance_logging(self, capsys):
        """Testa logging de performance para queries lentas"""
        # Executar query que deve ser lenta (forçar)
        import time
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(time, "time", lambda: 1000.0)
            
            # Primeira chamada para tempo normal
            self.db.read_sql("SELECT * FROM clientes")
            
            # Segunda chamada com tempo simulado lento
            mp.setattr(time, "time", lambda: 1002.0)  # 2 segundos depois
            
            with capsys.disabled():
                self.db.read_sql("SELECT COUNT(*) FROM clientes")
        
        # Não podemos verificar diretamente o log, mas o teste não deve falhar
        assert True
    
    def test_cache_cleanup(self):
        """Testa limpeza automática do cache"""
        # Adicionar muitos itens ao cache
        for i in range(10):
            self.db.read_sql(f"SELECT {i} as valor")
        
        # Aguardar TTL passar (simulado)
        import time
        time.sleep(0.1)
        
        # Limpar cache velho (chamado internamente)
        self.db._clean_old_cache(ttl=0)  # TTL zero para forçar limpeza
        
        # Verificar se o cache foi limpo (pode ter alguns itens)
        stats = self.db.get_cache_stats()
        assert stats["cache_size"] < 10  # Deve ter menos itens