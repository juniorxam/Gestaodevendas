"""
test_services.py - Testes dos serviços de negócio (CORRIGIDO)
"""

import os
import pytest
import sys
from datetime import date, timedelta
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database
from core.security import Security
from core.auth_service import AuditLog, Auth
from core.cliente_service import ClienteService
from core.produto_service import ProdutoService
from core.categoria_service import CategoriaService
from core.venda_service import VendaService
from core.estoque_service import EstoqueService
from core.promocao_service import PromocaoService
from tests.test_config import (
    TEST_DB_PATH, TEST_ADMIN, TEST_CLIENTE, TEST_CATEGORIA,
    TEST_PRODUTO, TEST_PROMOCAO, CPF_VALIDO_1, CPF_VALIDO_2, CPF_VALIDO_3, CPF_VALIDO_4,
    limpar_arquivos_teste
)


class TestAuthService:
    """Testes para os serviços de autenticação"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        # Criar usuário de teste
        senha_hash = Security.sha256_hex(TEST_ADMIN["senha"])
        self.db.execute(
            "INSERT INTO usuarios (login, senha, nome, nivel_acesso, ativo) VALUES (?, ?, ?, ?, 1)",
            (TEST_ADMIN["login"], senha_hash, TEST_ADMIN["nome"], TEST_ADMIN["nivel_acesso"])
        )
        
        self.audit = AuditLog(self.db)
        self.auth = Auth(self.db)
        
        yield
        
        limpar_arquivos_teste()
    
    def test_login_success(self):
        """Testa login bem-sucedido"""
        result = self.auth.login(TEST_ADMIN["login"], TEST_ADMIN["senha"])
        
        assert result is not None
        assert result["nome"] == TEST_ADMIN["nome"]
        assert result["nivel_acesso"] == TEST_ADMIN["nivel_acesso"]
    
    def test_login_failure_wrong_password(self):
        """Testa login com senha errada"""
        result = self.auth.login(TEST_ADMIN["login"], "senha_errada")
        assert result is None
    
    def test_login_failure_wrong_user(self):
        """Testa login com usuário errado"""
        result = self.auth.login("usuario_inexistente", TEST_ADMIN["senha"])
        assert result is None
    
    def test_verificar_permissoes_admin(self):
        """Testa verificação de permissões para ADMIN"""
        assert Auth.verificar_permissoes("ADMIN", "ADMIN") is True
        assert Auth.verificar_permissoes("ADMIN", "OPERADOR") is True
        assert Auth.verificar_permissoes("ADMIN", "VISUALIZADOR") is True
    
    def test_verificar_permissoes_operador(self):
        """Testa verificação de permissões para OPERADOR"""
        assert Auth.verificar_permissoes("OPERADOR", "ADMIN") is False
        assert Auth.verificar_permissoes("OPERADOR", "OPERADOR") is True
        assert Auth.verificar_permissoes("OPERADOR", "VISUALIZADOR") is True
    
    def test_verificar_permissoes_visualizador(self):
        """Testa verificação de permissões para VISUALIZADOR"""
        assert Auth.verificar_permissoes("VISUALIZADOR", "ADMIN") is False
        assert Auth.verificar_permissoes("VISUALIZADOR", "OPERADOR") is False
        assert Auth.verificar_permissoes("VISUALIZADOR", "VISUALIZADOR") is True
    
    def test_audit_registrar(self):
        """Testa registro de log de auditoria"""
        self.audit.registrar(
            TEST_ADMIN["login"],
            "TESTE",
            "Ação de teste",
            "Detalhes do teste",
            "127.0.0.1"
        )
        
        # Verificar se o log foi criado
        log = self.db.fetchone("SELECT * FROM logs WHERE usuario = ?", (TEST_ADMIN["login"],))
        
        assert log is not None
        assert log["modulo"] == "TESTE"
        assert log["acao"] == "Ação de teste"
        assert log["detalhes"] == "Detalhes do teste"


class TestClienteService:
    """Testes para o serviço de clientes"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        self.audit = AuditLog(self.db)
        self.cliente_service = ClienteService(self.db, self.audit)
        
        yield
        
        limpar_arquivos_teste()
    
    def test_cadastrar_cliente_success(self):
        """Testa cadastro de cliente com sucesso"""
        dados = TEST_CLIENTE.copy()
        dados["cpf"] = CPF_VALIDO_1
        
        sucesso, msg = self.cliente_service.cadastrar_individual(
            dados,
            "admin_teste"
        )
        
        assert sucesso is True
        assert "sucesso" in msg.lower()
    
    def test_cadastrar_cliente_sem_nome(self):
        """Testa cadastro sem nome"""
        dados = TEST_CLIENTE.copy()
        dados["nome"] = ""
        
        sucesso, msg = self.cliente_service.cadastrar_individual(dados, "admin_teste")
        
        assert sucesso is False
        assert "nome" in msg.lower()
    
    def test_cadastrar_cliente_cpf_invalido(self):
        """Testa cadastro com CPF inválido"""
        dados = TEST_CLIENTE.copy()
        dados["cpf"] = "11111111111"  # CPF inválido
        
        sucesso, msg = self.cliente_service.cadastrar_individual(dados, "admin_teste")
        
        assert sucesso is False
        assert "cpf" in msg.lower()
    
    def test_cadastrar_cliente_cpf_duplicado(self):
        """Testa cadastro com CPF duplicado"""
        dados1 = TEST_CLIENTE.copy()
        dados1["cpf"] = CPF_VALIDO_1
        
        dados2 = TEST_CLIENTE.copy()
        dados2["cpf"] = CPF_VALIDO_1  # Mesmo CPF
        
        # Primeiro cadastro
        sucesso, _ = self.cliente_service.cadastrar_individual(dados1, "admin_teste")
        assert sucesso, "Falha no primeiro cadastro"
        
        # Segundo cadastro com mesmo CPF
        sucesso, msg = self.cliente_service.cadastrar_individual(dados2, "admin_teste")
        
        assert sucesso is False
        assert "cpf já cadastrado" in msg.lower()
    
    def test_buscar_clientes_por_nome(self):
        """Testa busca de clientes por nome"""
        # Limpar clientes existentes
        self.db.execute("DELETE FROM clientes")
        
        # Cadastrar clientes com CPFs únicos e válidos
        cpfs = [CPF_VALIDO_1, CPF_VALIDO_2, CPF_VALIDO_3]
        
        for i in range(3):
            dados = TEST_CLIENTE.copy()
            dados["nome"] = f"TESTE BUSCA {i}"
            dados["cpf"] = cpfs[i]
            sucesso, msg = self.cliente_service.cadastrar_individual(dados, "admin_teste")
            assert sucesso, f"Falha ao cadastrar cliente {i}: {msg}"
        
        # Buscar
        resultados = self.cliente_service.buscar_clientes("TESTE BUSCA", limit=10)
        
        assert len(resultados) == 3, f"Esperado 3 clientes, encontrado {len(resultados)}"
        assert all("TESTE BUSCA" in nome for nome in resultados["nome"].tolist())
    
    def test_obter_cliente_por_id(self):
        """Testa obtenção de cliente por ID"""
        # Cadastrar
        dados = TEST_CLIENTE.copy()
        dados["cpf"] = CPF_VALIDO_1
        
        sucesso, msg = self.cliente_service.cadastrar_individual(dados, "admin_teste")
        assert sucesso, f"Falha ao cadastrar cliente: {msg}"
        
        # Buscar pelo nome para obter ID
        resultados = self.cliente_service.buscar_clientes(dados["nome"], limit=1)
        assert not resultados.empty, "Cliente não encontrado na busca"
        cliente_id = int(resultados.iloc[0]["id"])
        
        # Obter por ID
        cliente = self.cliente_service.obter_cliente_por_id(cliente_id)
        
        assert cliente is not None, "Cliente não encontrado por ID"
        assert cliente["nome"] == dados["nome"]
        assert cliente["cpf"] == dados["cpf"]
    
    def test_obter_cliente_por_cpf(self):
        """Testa obtenção de cliente por CPF"""
        # Cadastrar
        dados = TEST_CLIENTE.copy()
        dados["cpf"] = CPF_VALIDO_1
        
        self.cliente_service.cadastrar_individual(dados, "admin_teste")
        
        # Obter por CPF
        cliente = self.cliente_service.obter_cliente_por_cpf(dados["cpf"])
        
        assert cliente is not None
        assert cliente["nome"] == dados["nome"]
    
    def test_atualizar_cliente(self):
        """Testa atualização de cliente"""
        # Cadastrar
        dados = TEST_CLIENTE.copy()
        dados["cpf"] = CPF_VALIDO_1
        
        sucesso, msg = self.cliente_service.cadastrar_individual(dados, "admin_teste")
        assert sucesso, f"Falha ao cadastrar cliente: {msg}"
        
        # Buscar ID
        resultados = self.cliente_service.buscar_clientes(dados["nome"], limit=1)
        assert not resultados.empty, "Cliente não encontrado na busca"
        cliente_id = int(resultados.iloc[0]["id"])
        
        # Atualizar
        novos_dados = {"email": "novo.email@teste.com", "telefone": "(11) 98888-7777"}
        sucesso, msg = self.cliente_service.atualizar_cliente(
            cliente_id, novos_dados, "admin_teste"
        )
        
        assert sucesso is True, f"Falha ao atualizar cliente: {msg}"
        
        # Verificar
        cliente = self.cliente_service.obter_cliente_por_id(cliente_id)
        assert cliente is not None
        assert cliente["email"] == "novo.email@teste.com"
        assert cliente["telefone"] == "(11) 98888-7777"
        # Nome não deve ter mudado
        assert cliente["nome"] == dados["nome"]


class TestCategoriaService:
    """Testes para o serviço de categorias"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        self.audit = AuditLog(self.db)
        self.categoria_service = CategoriaService(self.db, self.audit)
        
        yield
        
        limpar_arquivos_teste()
    
    def test_cadastrar_categoria_success(self):
        """Testa cadastro de categoria com sucesso"""
        sucesso, msg = self.categoria_service.cadastrar_categoria(
            TEST_CATEGORIA["nome"],
            TEST_CATEGORIA["descricao"],
            "admin_teste"
        )
        
        assert sucesso is True
        assert "sucesso" in msg.lower()
    
    def test_cadastrar_categoria_duplicada(self):
        """Testa cadastro de categoria duplicada"""
        # Primeiro cadastro
        self.categoria_service.cadastrar_categoria(
            TEST_CATEGORIA["nome"],
            TEST_CATEGORIA["descricao"],
            "admin_teste"
        )
        
        # Segundo cadastro
        sucesso, msg = self.categoria_service.cadastrar_categoria(
            TEST_CATEGORIA["nome"],
            TEST_CATEGORIA["descricao"],
            "admin_teste"
        )
        
        assert sucesso is False
        assert "já existe" in msg.lower()
    
    def test_listar_categorias(self):
        """Testa listagem de categorias"""
        # Limpar categorias existentes
        self.db.execute("DELETE FROM categorias")
        
        # Cadastrar algumas
        for i in range(3):
            self.categoria_service.cadastrar_categoria(
                f"CATEGORIA TESTE {i}",
                f"Descrição {i}",
                "admin_teste"
            )
        
        # Listar
        categorias = self.categoria_service.listar_categorias()
        
        assert len(categorias) == 3  # Apenas as 3 que criamos
    
    def test_listar_todas_com_produtos(self):
        """Testa listagem com contagem de produtos"""
        # Limpar dados
        self.db.execute("DELETE FROM produtos")
        self.db.execute("DELETE FROM categorias")
        
        # Cadastrar categoria
        self.categoria_service.cadastrar_categoria(
            "CATEGORIA PRODUTOS",
            "Teste",
            "admin_teste"
        )
        
        # Buscar ID da categoria
        df_cat = self.categoria_service.listar_todas()
        cat_row = df_cat[df_cat["nome"] == "CATEGORIA PRODUTOS"]
        assert not cat_row.empty
        cat_id = int(cat_row.iloc[0]["id"])
        
        # Cadastrar alguns produtos
        self.db.execute(
            """
            INSERT INTO produtos (nome, categoria_id, preco_venda, ativo)
            VALUES (?, ?, ?, 1)
            """,
            ("PRODUTO TESTE 1", cat_id, 100.00)
        )
        self.db.execute(
            """
            INSERT INTO produtos (nome, categoria_id, preco_venda, ativo)
            VALUES (?, ?, ?, 1)
            """,
            ("PRODUTO TESTE 2", cat_id, 200.00)
        )
        
        # Listar com contagem
        df = self.categoria_service.listar_todas()
        
        # Encontrar a categoria
        cat_row = df[df["nome"] == "CATEGORIA PRODUTOS"]
        assert not cat_row.empty
        assert cat_row.iloc[0]["total_produtos"] == 2
    
    def test_atualizar_categoria(self):
        """Testa atualização de categoria"""
        # Limpar dados
        self.db.execute("DELETE FROM categorias")
        
        # Cadastrar
        self.categoria_service.cadastrar_categoria(
            "CATEGORIA ANTIGA",
            "Descrição antiga",
            "admin_teste"
        )
        
        # Buscar ID
        df = self.categoria_service.listar_todas(incluir_inativas=True)
        cat_row = df[df["nome"] == "CATEGORIA ANTIGA"]
        assert not cat_row.empty, "Categoria não encontrada"
        cat_id = int(cat_row.iloc[0]["id"])
        
        # Atualizar
        sucesso, msg = self.categoria_service.atualizar_categoria(
            cat_id,
            {"nome": "CATEGORIA NOVA", "descricao": "Nova descrição"},
            "admin_teste"
        )
        
        assert sucesso is True, f"Falha ao atualizar: {msg}"
        
        # Verificar
        df_atualizada = self.categoria_service.listar_todas(incluir_inativas=True)
        cat = df_atualizada[df_atualizada["id"] == cat_id].iloc[0]
        assert cat["nome"] == "CATEGORIA NOVA"
        assert cat["descricao"] == "Nova descrição"
    
    def test_excluir_categoria_sem_produtos(self):
        """Testa exclusão de categoria sem produtos"""
        # Limpar dados
        self.db.execute("DELETE FROM categorias")
        
        # Cadastrar
        self.categoria_service.cadastrar_categoria(
            "CATEGORIA EXCLUIR",
            "Será excluída",
            "admin_teste"
        )
        
        # Buscar ID
        df = self.categoria_service.listar_todas(incluir_inativas=True)
        cat_row = df[df["nome"] == "CATEGORIA EXCLUIR"]
        assert not cat_row.empty, "Categoria não encontrada"
        cat_id = int(cat_row.iloc[0]["id"])
        
        # Excluir
        sucesso, msg = self.categoria_service.excluir_categoria(cat_id, "admin_teste")
        assert sucesso is True, f"Falha ao excluir: {msg}"
        
        # Verificar se foi removida
        df_apos = self.categoria_service.listar_todas(incluir_inativas=True)
        assert cat_id not in df_apos["id"].values
    
    def test_excluir_categoria_com_produtos(self):
        """Testa exclusão de categoria com produtos associados"""
        # Limpar dados
        self.db.execute("DELETE FROM produtos")
        self.db.execute("DELETE FROM categorias")
        
        # Cadastrar categoria
        self.categoria_service.cadastrar_categoria(
            "CATEGORIA COM PRODUTOS",
            "Tem produtos",
            "admin_teste"
        )
        
        # Buscar ID
        df = self.categoria_service.listar_todas()
        cat_row = df[df["nome"] == "CATEGORIA COM PRODUTOS"]
        assert not cat_row.empty
        cat_id = int(cat_row.iloc[0]["id"])
        
        # Cadastrar produto na categoria
        self.db.execute(
            """
            INSERT INTO produtos (nome, categoria_id, preco_venda, ativo)
            VALUES (?, ?, ?, 1)
            """,
            ("PRODUTO ASSOCIADO", cat_id, 100.00)
        )
        
        # Tentar excluir
        sucesso, msg = self.categoria_service.excluir_categoria(cat_id, "admin_teste")
        
        assert sucesso is False
        assert "produtos" in msg.lower()


class TestProdutoService:
    """Testes para o serviço de produtos"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        self.audit = AuditLog(self.db)
        self.produto_service = ProdutoService(self.db, self.audit)
        
        # Criar categoria para testes
        self.categoria_service = CategoriaService(self.db, self.audit)
        self.categoria_service.cadastrar_categoria(
            TEST_CATEGORIA["nome"],
            TEST_CATEGORIA["descricao"],
            "admin_teste"
        )
        
        yield
        
        limpar_arquivos_teste()
    
    def test_cadastrar_produto_success(self):
        """Testa cadastro de produto com sucesso"""
        dados = TEST_PRODUTO.copy()
        dados["categoria"] = TEST_CATEGORIA["nome"]
        dados["codigo_barras"] = "7891111111111"
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados, "admin_teste")
        
        assert sucesso is True
        assert "sucesso" in msg.lower()
    
    def test_cadastrar_produto_sem_nome(self):
        """Testa cadastro sem nome"""
        dados = TEST_PRODUTO.copy()
        dados["nome"] = ""
        dados["categoria"] = TEST_CATEGORIA["nome"]
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados, "admin_teste")
        
        assert sucesso is False
        assert "nome" in msg.lower()
    
    def test_cadastrar_produto_preco_zero(self):
        """Testa cadastro com preço zero"""
        dados = TEST_PRODUTO.copy()
        dados["preco_venda"] = 0
        dados["categoria"] = TEST_CATEGORIA["nome"]
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados, "admin_teste")
        
        assert sucesso is False
        assert "preço" in msg.lower() or "zero" in msg.lower()
    
    def test_cadastrar_produto_codigo_duplicado(self):
        """Testa cadastro com código de barras duplicado"""
        dados = TEST_PRODUTO.copy()
        dados["categoria"] = TEST_CATEGORIA["nome"]
        dados["codigo_barras"] = "7891111111111"
        
        # Primeiro cadastro
        sucesso, _ = self.produto_service.cadastrar_produto(dados, "admin_teste")
        assert sucesso, "Falha no primeiro cadastro"
        
        # Segundo cadastro com mesmo código
        sucesso, msg = self.produto_service.cadastrar_produto(dados, "admin_teste")
        
        assert sucesso is False
        assert "código de barras" in msg.lower()
    
    def test_buscar_produto_por_codigo(self):
        """Testa busca de produto por código de barras"""
        # Cadastrar
        dados = TEST_PRODUTO.copy()
        dados["categoria"] = TEST_CATEGORIA["nome"]
        dados["codigo_barras"] = "7891111111111"
        
        self.produto_service.cadastrar_produto(dados, "admin_teste")
        
        # Buscar
        produto = self.produto_service.buscar_produto_por_codigo(dados["codigo_barras"])
        
        assert produto is not None
        assert produto["nome"] == dados["nome"]
    
    def test_buscar_produtos_por_termo(self):
        """Testa busca de produtos por termo"""
        # Limpar produtos existentes
        self.db.execute("DELETE FROM produtos")
        
        # Cadastrar
        for i in range(3):
            dados = TEST_PRODUTO.copy()
            dados["nome"] = f"PRODUTO BUSCA {i}"
            dados["codigo_barras"] = f"789{i}{i}{i}123"
            dados["categoria"] = TEST_CATEGORIA["nome"]
            self.produto_service.cadastrar_produto(dados, "admin_teste")
        
        # Buscar
        resultados = self.produto_service.buscar_produtos("BUSCA", limit=10)
        
        assert len(resultados) == 3
        assert all("BUSCA" in nome for nome in resultados["nome"].tolist())
    
    def test_verificar_estoque(self):
        """Testa verificação de estoque"""
        # Cadastrar com estoque 50
        dados = TEST_PRODUTO.copy()
        dados["categoria"] = TEST_CATEGORIA["nome"]
        dados["quantidade_estoque"] = 50
        dados["codigo_barras"] = "7891111111111"
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto: {msg}"
        
        # Buscar ID
        produtos = self.produto_service.listar_todos_produtos()
        produto_row = produtos[produtos["nome"] == dados["nome"]]
        assert not produto_row.empty, f"Produto {dados['nome']} não encontrado após cadastro"
        produto_id = int(produto_row.iloc[0]["id"])
        
        # Verificar estoque
        disponivel, estoque = self.produto_service.verificar_estoque(produto_id, 30)
        assert disponivel is True
        assert estoque == 50
        
        disponivel, estoque = self.produto_service.verificar_estoque(produto_id, 60)
        assert disponivel is False
        assert estoque == 50
    
    def test_atualizar_estoque(self):
        """Testa atualização de estoque"""
        # Cadastrar com estoque 50
        dados = TEST_PRODUTO.copy()
        dados["categoria"] = TEST_CATEGORIA["nome"]
        dados["quantidade_estoque"] = 50
        dados["codigo_barras"] = "7891111111111"
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto: {msg}"
        
        # Buscar ID
        produtos = self.produto_service.listar_todos_produtos()
        produto_row = produtos[produtos["nome"] == dados["nome"]]
        assert not produto_row.empty, "Produto não encontrado após cadastro"
        produto_id = int(produto_row.iloc[0]["id"])
        
        # Atualizar estoque (entrada)
        sucesso, msg = self.produto_service.atualizar_estoque(
            produto_id, 10, "ENTRADA", "admin_teste"
        )
        
        assert sucesso is True, f"Falha na entrada: {msg}"
        
        # Verificar
        disponivel, estoque = self.produto_service.verificar_estoque(produto_id)
        assert estoque == 60
        
        # Saída
        sucesso, msg = self.produto_service.atualizar_estoque(
            produto_id, -20, "SAIDA", "admin_teste"
        )
        
        assert sucesso is True, f"Falha na saída: {msg}"
        disponivel, estoque = self.produto_service.verificar_estoque(produto_id)
        assert estoque == 40
    
    def test_atualizar_estoque_negativo(self):
        """Testa tentativa de estoque negativo"""
        # Cadastrar com estoque 5
        dados = TEST_PRODUTO.copy()
        dados["quantidade_estoque"] = 5
        dados["categoria"] = TEST_CATEGORIA["nome"]
        dados["codigo_barras"] = "7891111111111"
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto: {msg}"
        
        # Buscar ID
        produtos = self.produto_service.listar_todos_produtos()
        produto_row = produtos[produtos["nome"] == dados["nome"]]
        assert not produto_row.empty, "Produto não encontrado após cadastro"
        produto_id = int(produto_row.iloc[0]["id"])
        
        # Tentar sair mais do que tem
        sucesso, msg = self.produto_service.atualizar_estoque(
            produto_id, -10, "SAIDA", "admin_teste"
        )
        
        assert sucesso is False
        assert "negativo" in msg.lower() or "insuficiente" in msg.lower()
    
    def test_get_produtos_estoque_baixo(self):
        """Testa listagem de produtos com estoque baixo"""
        # Limpar produtos existentes
        self.db.execute("DELETE FROM produtos")
        
        # Cadastrar produtos com códigos de barras únicos
        dados1 = TEST_PRODUTO.copy()
        dados1["nome"] = "PRODUTO ESTOQUE BAIXO 1"
        dados1["codigo_barras"] = "7891111111111"
        dados1["quantidade_estoque"] = 5
        dados1["estoque_minimo"] = 10
        dados1["categoria"] = TEST_CATEGORIA["nome"]
        
        dados2 = TEST_PRODUTO.copy()
        dados2["nome"] = "PRODUTO ESTOQUE BAIXO 2"
        dados2["codigo_barras"] = "7892222222222"
        dados2["quantidade_estoque"] = 2
        dados2["estoque_minimo"] = 8
        dados2["categoria"] = TEST_CATEGORIA["nome"]
        
        dados3 = TEST_PRODUTO.copy()
        dados3["nome"] = "PRODUTO ESTOQUE NORMAL"
        dados3["codigo_barras"] = "7893333333333"
        dados3["quantidade_estoque"] = 20
        dados3["estoque_minimo"] = 10
        dados3["categoria"] = TEST_CATEGORIA["nome"]
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados1, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto 1: {msg}"
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados2, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto 2: {msg}"
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados3, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto 3: {msg}"
        
        # Listar estoque baixo
        estoque_baixo = self.produto_service.get_produtos_estoque_baixo()
        
        assert len(estoque_baixo) >= 2
        nomes_baixo = estoque_baixo["nome"].tolist()
        assert "PRODUTO ESTOQUE BAIXO 1" in nomes_baixo
        assert "PRODUTO ESTOQUE BAIXO 2" in nomes_baixo


class TestVendaService:
    """Testes para o serviço de vendas"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        self.db = Database(self.db_path)
        self.db.init_schema()
        
        self.audit = AuditLog(self.db)
        self.cliente_service = ClienteService(self.db, self.audit)
        self.categoria_service = CategoriaService(self.db, self.audit)
        self.produto_service = ProdutoService(self.db, self.audit)
        self.venda_service = VendaService(self.db, self.audit, self.produto_service)
        self.estoque_service = EstoqueService(self.db, self.audit, self.produto_service)
        
        # Dados de teste
        self.categoria_service.cadastrar_categoria("ELETRONICOS", "Teste", "admin_teste")
        
        # Cadastrar cliente
        cliente_dados = TEST_CLIENTE.copy()
        cliente_dados["cpf"] = CPF_VALIDO_1
        sucesso, msg = self.cliente_service.cadastrar_individual(cliente_dados, "admin_teste")
        assert sucesso, f"Falha ao cadastrar cliente: {msg}"
        
        # Cadastrar produtos com códigos únicos
        dados_prod1 = {
            "nome": "PRODUTO VENDA 1",
            "codigo_barras": "7891111111111",
            "categoria": "ELETRONICOS",
            "preco_venda": 100.00,
            "quantidade_estoque": 50,
            "ativo": True
        }
        dados_prod2 = {
            "nome": "PRODUTO VENDA 2",
            "codigo_barras": "7892222222222",
            "categoria": "ELETRONICOS",
            "preco_venda": 200.00,
            "quantidade_estoque": 30,
            "ativo": True
        }
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados_prod1, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto 1: {msg}"
        
        sucesso, msg = self.produto_service.cadastrar_produto(dados_prod2, "admin_teste")
        assert sucesso, f"Falha ao cadastrar produto 2: {msg}"
        
        # Buscar IDs
        self.produtos_df = self.produto_service.listar_todos_produtos()
        self.produto1_id = int(self.produtos_df[self.produtos_df["nome"] == "PRODUTO VENDA 1"].iloc[0]["id"])
        self.produto2_id = int(self.produtos_df[self.produtos_df["nome"] == "PRODUTO VENDA 2"].iloc[0]["id"])
        
        self.clientes_df = self.cliente_service.buscar_clientes(TEST_CLIENTE["nome"])
        self.cliente_id = int(self.clientes_df.iloc[0]["id"])
        
        yield
        
        limpar_arquivos_teste()
    
    def test_registrar_venda_success(self):
        """Testa registro de venda com sucesso"""
        # Guardar estoque antes
        _, estoque1_antes = self.produto_service.verificar_estoque(self.produto1_id)
        _, estoque2_antes = self.produto_service.verificar_estoque(self.produto2_id)
        
        itens = [
            {"produto_id": self.produto1_id, "quantidade": 2},
            {"produto_id": self.produto2_id, "quantidade": 1}
        ]
        
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente_id,
            itens=itens,
            forma_pagamento="Cartão de Crédito",
            usuario="admin_teste"
        )
        
        assert sucesso is True, f"Falha ao registrar venda: {msg}"
        assert venda_id is not None
        
        # Verificar se o estoque foi atualizado
        _, estoque1_depois = self.produto_service.verificar_estoque(self.produto1_id)
        _, estoque2_depois = self.produto_service.verificar_estoque(self.produto2_id)
        
        assert estoque1_depois == estoque1_antes - 2
        assert estoque2_depois == estoque2_antes - 1
    
    def test_registrar_venda_sem_cliente(self):
        """Testa venda sem cliente"""
        # Guardar estoque antes
        _, estoque1_antes = self.produto_service.verificar_estoque(self.produto1_id)
        
        itens = [
            {"produto_id": self.produto1_id, "quantidade": 1}
        ]
        
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=None,
            itens=itens,
            forma_pagamento="Dinheiro",
            usuario="admin_teste"
        )
        
        assert sucesso is True, f"Falha ao registrar venda sem cliente: {msg}"
        assert venda_id is not None
        
        # Verificar estoque
        _, estoque1_depois = self.produto_service.verificar_estoque(self.produto1_id)
        assert estoque1_depois == estoque1_antes - 1
    
    def test_registrar_venda_estoque_insuficiente(self):
        """Testa venda com estoque insuficiente"""
        # Verificar estoque atual
        _, estoque_atual = self.produto_service.verificar_estoque(self.produto1_id)
        
        itens = [
            {"produto_id": self.produto1_id, "quantidade": estoque_atual + 10}  # Mais que o disponível
        ]
        
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente_id,
            itens=itens,
            forma_pagamento="Cartão",
            usuario="admin_teste"
        )
        
        assert sucesso is False
        assert "estoque" in msg.lower() or "insuficiente" in msg.lower()
    
    def test_registrar_venda_sem_itens(self):
        """Testa venda sem itens"""
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente_id,
            itens=[],
            forma_pagamento="PIX",
            usuario="admin_teste"
        )
        
        assert sucesso is False
        assert "item" in msg.lower()
    
    def test_listar_vendas_por_periodo(self):
        """Testa listagem de vendas por período"""
        # Registrar algumas vendas
        itens = [{"produto_id": self.produto1_id, "quantidade": 1}]
        
        for i in range(3):
            sucesso, msg, venda_id = self.venda_service.registrar_venda(
                cliente_id=self.cliente_id if i % 2 == 0 else None,
                itens=itens,
                forma_pagamento="Dinheiro",
                usuario="admin_teste"
            )
            assert sucesso, f"Falha ao registrar venda {i}: {msg}"
        
        # Listar
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=7)
        
        vendas = self.venda_service.listar_vendas_por_periodo(data_inicio, data_fim)
        
        assert len(vendas) >= 3
    
    def test_detalhes_venda(self):
        """Testa obtenção de detalhes de uma venda"""
        # Registrar venda
        itens = [
            {"produto_id": self.produto1_id, "quantidade": 2},
            {"produto_id": self.produto2_id, "quantidade": 1}
        ]
        
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente_id,
            itens=itens,
            forma_pagamento="Cartão de Crédito",
            usuario="admin_teste"
        )
        
        assert sucesso, f"Falha ao registrar venda: {msg}"
        
        # Obter detalhes
        detalhes = self.venda_service.detalhes_venda(venda_id)
        
        assert "venda" in detalhes
        assert "itens" in detalhes
        assert len(detalhes["itens"]) == 2
        assert detalhes["venda"]["cliente_id"] == self.cliente_id
        assert detalhes["venda"]["forma_pagamento"] == "Cartão de Crédito"
    
    def test_historico_cliente(self):
        """Testa histórico de compras de um cliente"""
        # Registrar vendas para o cliente
        itens = [{"produto_id": self.produto1_id, "quantidade": 1}]
        
        for i in range(3):
            sucesso, msg, venda_id = self.venda_service.registrar_venda(
                cliente_id=self.cliente_id,
                itens=itens,
                forma_pagamento="Dinheiro",
                usuario="admin_teste"
            )
            assert sucesso, f"Falha ao registrar venda {i}: {msg}"
        
        # Histórico
        historico = self.venda_service.historico_cliente(self.cliente_id)
        
        assert len(historico) == 3
    
    def test_estornar_venda(self):
        """Testa estorno de venda"""
        # Registrar venda
        itens = [
            {"produto_id": self.produto1_id, "quantidade": 2},
            {"produto_id": self.produto2_id, "quantidade": 1}
        ]
        
        # Guardar estoque antes
        _, estoque1_antes = self.produto_service.verificar_estoque(self.produto1_id)
        _, estoque2_antes = self.produto_service.verificar_estoque(self.produto2_id)
        
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente_id,
            itens=itens,
            forma_pagamento="Cartão",
            usuario="admin_teste"
        )
        
        assert sucesso, f"Falha ao registrar venda: {msg}"
        assert venda_id is not None
        
        # Verificar estoque após venda
        _, estoque1_meio = self.produto_service.verificar_estoque(self.produto1_id)
        _, estoque2_meio = self.produto_service.verificar_estoque(self.produto2_id)
        assert estoque1_meio == estoque1_antes - 2
        assert estoque2_meio == estoque2_antes - 1
        
        # Estornar
        sucesso, msg = self.venda_service.estornar_venda(
            venda_id=venda_id,
            usuario="admin_teste",
            motivo="Teste de estorno"
        )
        
        assert sucesso is True, f"Falha ao estornar venda: {msg}"
        
        # Verificar estoque retornou
        _, estoque1_depois = self.produto_service.verificar_estoque(self.produto1_id)
        _, estoque2_depois = self.produto_service.verificar_estoque(self.produto2_id)
        
        assert estoque1_depois == estoque1_antes
        assert estoque2_depois == estoque2_antes
    
    def test_estornar_venda_inexistente(self):
        """Testa estorno de venda inexistente"""
        sucesso, msg = self.venda_service.estornar_venda(
            venda_id=99999,
            usuario="admin_teste"
        )
        
        assert sucesso is False
        assert "não encontrada" in msg.lower()
    
    def test_get_metricas_periodo(self):
        """Testa obtenção de métricas por período"""
        # Registrar vendas
        itens = [{"produto_id": self.produto1_id, "quantidade": 1}]
        
        for i in range(5):
            sucesso, msg, venda_id = self.venda_service.registrar_venda(
                cliente_id=self.cliente_id,
                itens=itens,
                forma_pagamento="Dinheiro",
                usuario="admin_teste"
            )
            assert sucesso, f"Falha ao registrar venda {i}: {msg}"
        
        # Métricas
        data_fim = date.today()
        data_inicio = data_fim - timedelta(days=7)
        
        metricas = self.venda_service.get_metricas_periodo(data_inicio, data_fim)
        
        assert metricas["total_vendas"] >= 5
        assert metricas["faturamento_total"] >= 500  # 5 * 100
        assert "formas_pagamento" in metricas
        assert "produtos_mais_vendidos" in metricas