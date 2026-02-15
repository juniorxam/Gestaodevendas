"""
database.py - Camada de persistência (CORRIGIDO)
"""

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from config import CONFIG


class Database:
    """
    SQLite database manager com WAL mode e retry logic
    """
    
    _MAX_WRITE_RETRIES = 10  # Aumentado de 6 para 10
    _BASE_BACKOFF_SEC = 0.1  # Aumentado de 0.08 para 0.1

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @staticmethod
    def _is_busy_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return ("database is locked" in msg) or ("database is busy" in msg) or ("locked" in msg and "database" in msg)

    def _with_write_retry(self, fn):
        """Executa escrita com retry e backoff exponencial"""
        last_exc = None
        for attempt in range(self._MAX_WRITE_RETRIES):
            try:
                return fn()
            except sqlite3.OperationalError as e:
                if not self._is_busy_error(e):
                    raise
                last_exc = e
                wait_time = self._BASE_BACKOFF_SEC * (2 ** attempt)
                logging.warning(f"Database locked, retrying in {wait_time:.2f}s (attempt {attempt+1}/{self._MAX_WRITE_RETRIES})")
                time.sleep(wait_time)
        logging.error(f"Max retries ({self._MAX_WRITE_RETRIES}) exceeded for database operation")
        raise last_exc

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA busy_timeout=30000;")  # Aumentado para 30 segundos
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: Sequence[Any] = ()) -> int:
        def _run():
            with self.connect() as conn:
                cur = conn.execute(query, params)
                return cur.rowcount
        return int(self._with_write_retry(_run))

    def executemany(self, query: str, params_seq: Sequence[Sequence[Any]]) -> int:
        if not params_seq:
            return 0
        def _run():
            with self.connect() as conn:
                cur = conn.executemany(query, params_seq)
                return cur.rowcount
        return int(self._with_write_retry(_run))

    def fetchone(self, query: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            cur = conn.execute(query, params)
            return cur.fetchone()

    def fetchall(self, query: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self.connect() as conn:
            cur = conn.execute(query, params)
            return cur.fetchall()

    def read_sql(self, query: str, params: Sequence[Any] = ()) -> pd.DataFrame:
        with self.connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    def init_schema(self) -> None:
        """Inicializa o schema do banco de dados"""
        with self.connect() as conn:
            c = conn.cursor()
            
            # Tabela clientes
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT UNIQUE,
                    email TEXT,
                    telefone TEXT,
                    data_nascimento DATE,
                    endereco TEXT,
                    cidade TEXT,
                    estado TEXT,
                    cep TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_cadastro TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cpf ON clientes(cpf)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes(nome)")

            # Tabela categorias
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    descricao TEXT,
                    ativo INTEGER DEFAULT 1,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_categorias_nome ON categorias(nome)")

            # Tabela produtos
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_barras TEXT UNIQUE,
                    nome TEXT NOT NULL,
                    descricao TEXT,
                    categoria_id INTEGER,
                    fabricante TEXT,
                    preco_custo DECIMAL(10,2),
                    preco_venda DECIMAL(10,2) NOT NULL,
                    quantidade_estoque INTEGER DEFAULT 0,
                    estoque_minimo INTEGER DEFAULT 5,
                    ativo INTEGER DEFAULT 1,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_cadastro TEXT,
                    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_produtos_codigo ON produtos(codigo_barras)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos(nome)")

            # Tabela promocoes
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS promocoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    descricao TEXT,
                    tipo TEXT CHECK(tipo IN ('DESCONTO_PERCENTUAL', 'DESCONTO_FIXO', 'LEVE_MAIS')) NOT NULL,
                    valor_desconto DECIMAL(10,2),
                    data_inicio DATE NOT NULL,
                    data_fim DATE NOT NULL,
                    status TEXT DEFAULT 'PLANEJADA' CHECK(status IN ('PLANEJADA', 'ATIVA', 'CONCLUÍDA', 'CANCELADA')),
                    usuario_criacao TEXT,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_promocoes_periodo ON promocoes(data_inicio, data_fim)")

            # Tabela vendas
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS vendas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cliente_id INTEGER,
                    valor_total DECIMAL(10,2) NOT NULL,
                    forma_pagamento TEXT,
                    usuario_registro TEXT NOT NULL,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas(data_venda)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_vendas_cliente ON vendas(cliente_id)")

            # Tabela itens_venda
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS itens_venda (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venda_id INTEGER NOT NULL,
                    produto_id INTEGER NOT NULL,
                    quantidade INTEGER NOT NULL,
                    preco_unitario DECIMAL(10,2) NOT NULL,
                    promocao_id INTEGER,
                    FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE,
                    FOREIGN KEY (produto_id) REFERENCES produtos(id),
                    FOREIGN KEY (promocao_id) REFERENCES promocoes(id)
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_itens_venda ON itens_venda(venda_id)")

            # Tabela usuarios
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    login TEXT PRIMARY KEY,
                    senha TEXT,
                    nome TEXT,
                    nivel_acesso TEXT CHECK(nivel_acesso IN ('ADMIN', 'OPERADOR', 'VISUALIZADOR')),
                    ativo INTEGER DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Tabela logs
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario TEXT,
                    modulo TEXT,
                    acao TEXT,
                    detalhes TEXT,
                    ip_address TEXT
                )
                """
            )

    def ensure_seed_data(self) -> None:
        """Garante dados iniciais no banco"""
        from .security import Security
        
        # Criar usuário admin padrão
        admin_exists = self.fetchone("SELECT login FROM usuarios WHERE login = ?", (CONFIG.admin_login,))
        if not admin_exists:
            senha_hash = Security.sha256_hex(CONFIG.admin_password_default)
            self.execute(
                """
                INSERT INTO usuarios (login, senha, nome, nivel_acesso, ativo, data_criacao)
                VALUES (?, ?, ?, 'ADMIN', 1, CURRENT_TIMESTAMP)
                """,
                (CONFIG.admin_login, senha_hash, "Administrador"),
            )

        # Criar categorias padrão
        categorias_padrao = [
            ("Smartphones", "Celulares e smartphones"),
            ("Tablets", "Tablets e iPads"),
            ("Notebooks", "Notebooks e laptops"),
            ("Video Games", "Consoles e jogos"),
            ("Acessórios", "Acessórios em geral"),
            ("Áudio", "Fones, caixas de som"),
            ("TVs", "Televisores"),
            ("Informática", "Periféricos e componentes"),
        ]

        for nome, desc in categorias_padrao:
            self.execute(
                """
                INSERT OR IGNORE INTO categorias (nome, descricao, ativo)
                VALUES (?, ?, 1)
                """,
                (nome, desc)
            )


class OptimizedDatabase(Database):
    """Database com cache de consultas"""
    
    # Constantes para cache
    MAX_CACHE_SIZE = 50
    DEFAULT_TTL = 300  # 5 minutos
    
    def __init__(self, db_path: str) -> None:
        super().__init__(db_path)
        self._query_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def read_sql(self, query: str, params: Sequence[Any] = (), ttl: int = DEFAULT_TTL) -> pd.DataFrame:
        cache_key = f"{query}_{hash(str(params))}"
        
        if cache_key in self._query_cache:
            cached_time, data = self._query_cache[cache_key]
            if (datetime.now() - cached_time).seconds < ttl:
                self._cache_hits += 1
                return data.copy()
        
        self._cache_misses += 1
        with self._show_query_performance(query):
            result = super().read_sql(query, params)
        
        self._query_cache[cache_key] = (datetime.now(), result.copy())
        self._clean_old_cache(ttl)
        
        return result
    
    @contextmanager
    def _show_query_performance(self, query: str):
        start_time = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start_time
            if elapsed > 1.0:
                logging.warning(f"Query lenta ({elapsed:.2f}s): {query[:100]}...")
    
    def _clean_old_cache(self, ttl: int):
        """Limpa cache antigo e mantém tamanho controlado"""
        current_time = datetime.now()
        to_remove = []
        
        # Remover itens expirados
        for key, (cached_time, _) in self._query_cache.items():
            if (current_time - cached_time).seconds > ttl:
                to_remove.append(key)
        
        # Se ainda estiver muito grande, remover os mais antigos
        if len(self._query_cache) - len(to_remove) > self.MAX_CACHE_SIZE:
            # Ordenar por timestamp (mais antigos primeiro)
            items = sorted(self._query_cache.items(), key=lambda x: x[1][0])
            # Manter apenas os MAX_CACHE_SIZE mais recentes
            for key, _ in items[:len(items) - self.MAX_CACHE_SIZE]:
                if key not in to_remove:
                    to_remove.append(key)
        
        for key in to_remove:
            del self._query_cache[key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        total_requests = self._cache_hits + self._cache_misses
        return {
            "cache_size": len(self._query_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": self._cache_hits / max(1, total_requests),
        }
    
    def clear_cache(self):
        """Limpa todo o cache"""
        self._query_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0