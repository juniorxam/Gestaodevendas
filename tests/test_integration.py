"""
test_integration.py - Testes de integração entre serviços
"""

import os
import pytest
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database
from core.auth_service import AuditLog, Auth
from core.cliente_service import ClienteService
from core.produto_service import ProdutoService
from core.categoria_service import CategoriaService
from core.venda_service import VendaService
from core.estoque_service import EstoqueService
from core.promocao_service import PromocaoService
from core.relatorio_service import RelatorioService
from tests.test_config import (
    TEST_DB_PATH, limpar_arquivos_teste, 
    CPF_VALIDO_1, CPF_VALIDO_2, CPF_VALIDO_3, CPF_VALIDO_4
)


class TestIntegration:
    """Testes de integração entre serviços"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Configuração antes de cada teste"""
        self.db_path = TEST_DB_PATH
        limpar_arquivos_teste()
        
        self.db = Database(self.db_path)
        self.db.init_schema()
        self.db.ensure_seed_data()
        
        self.audit = AuditLog(self.db)
        self.auth = Auth(self.db)
        self.cliente_service = ClienteService(self.db, self.audit)
        self.categoria_service = CategoriaService(self.db, self.audit)
        self.produto_service = ProdutoService(self.db, self.audit)
        self.promocao_service = PromocaoService(self.db, self.audit)
        self.venda_service = VendaService(self.db, self.audit, self.produto_service)
        self.estoque_service = EstoqueService(self.db, self.audit, self.produto_service)
        self.relatorio_service = RelatorioService(self.db)
        
        # Dados base
        self._criar_dados_base()
        
        yield
        
        limpar_arquivos_teste()
    
    def _criar_dados_base(self):
        """Cria dados base para os testes"""
        # Categorias - SEM ACENTOS
        self.categoria_service.cadastrar_categoria(
            "ELETRONICOS", "Produtos eletronicos", "admin_teste"
        )
        self.categoria_service.cadastrar_categoria(
            "ACESSORIOS", "Acessorios em geral", "admin_teste"
        )
        
        # Clientes - CPFs VÁLIDOS (apenas números)
        sucesso, msg = self.cliente_service.cadastrar_individual({
            "nome": "CLIENTE INTEGRACAO 1",
            "cpf": CPF_VALIDO_1,  # 52998224725
            "email": "cliente1@teste.com",
            "telefone": "(11) 91111-1111",
        }, "admin_teste")
        assert sucesso, f"Falha ao cadastrar cliente 1: {msg}"
        
        sucesso, msg = self.cliente_service.cadastrar_individual({
            "nome": "CLIENTE INTEGRACAO 2",
            "cpf": CPF_VALIDO_4,  # Usar 12345678909 que é válido
            "email": "cliente2@teste.com",
            "telefone": "(11) 92222-2222",
        }, "admin_teste")
        assert sucesso, f"Falha ao cadastrar cliente 2: {msg}"
        
        # Produtos
        sucesso, msg = self.produto_service.cadastrar_produto({
            "nome": "NOTEBOOK TESTE",
            "codigo_barras": "7891111111111",
            "categoria": "ELETRONICOS",
            "preco_custo": 2000.00,
            "preco_venda": 3500.00,
            "quantidade_estoque": 20,
            "estoque_minimo": 5,
            "fabricante": "TESTE INC",
        }, "admin_teste")
        assert sucesso, f"Falha ao cadastrar notebook: {msg}"
        
        sucesso, msg = self.produto_service.cadastrar_produto({
            "nome": "SMARTPHONE TESTE",
            "codigo_barras": "7892222222222",
            "categoria": "ELETRONICOS",
            "preco_custo": 1200.00,
            "preco_venda": 2000.00,
            "quantidade_estoque": 30,
            "estoque_minimo": 10,
            "fabricante": "TESTE INC",
        }, "admin_teste")
        assert sucesso, f"Falha ao cadastrar smartphone: {msg}"
        
        sucesso, msg = self.produto_service.cadastrar_produto({
            "nome": "FONE DE OUVIDO",
            "codigo_barras": "7893333333333",
            "categoria": "ACESSORIOS",
            "preco_custo": 50.00,
            "preco_venda": 120.00,
            "quantidade_estoque": 100,
            "estoque_minimo": 20,
            "fabricante": "TESTE AUDIO",
        }, "admin_teste")
        assert sucesso, f"Falha ao cadastrar fone: {msg}"
        
        # Buscar IDs com segurança
        self.produtos = self.produto_service.listar_todos_produtos()
        
        # Buscar produtos pelo nome exato
        notebook = self.produtos[self.produtos["nome"] == "NOTEBOOK TESTE"]
        assert not notebook.empty, "Produto NOTEBOOK TESTE não encontrado"
        self.produto1_id = int(notebook.iloc[0]["id"])
        
        smartphone = self.produtos[self.produtos["nome"] == "SMARTPHONE TESTE"]
        assert not smartphone.empty, "Produto SMARTPHONE TESTE não encontrado"
        self.produto2_id = int(smartphone.iloc[0]["id"])
        
        fone = self.produtos[self.produtos["nome"] == "FONE DE OUVIDO"]
        assert not fone.empty, "Produto FONE DE OUVIDO não encontrado"
        self.produto3_id = int(fone.iloc[0]["id"])
        
        # Buscar clientes - USAR CPF para maior precisão
        cliente1 = self.cliente_service.obter_cliente_por_cpf(CPF_VALIDO_1)
        assert cliente1 is not None, "Cliente 1 não encontrado por CPF"
        self.cliente1_id = cliente1["id"]
        
        cliente2 = self.cliente_service.obter_cliente_por_cpf(CPF_VALIDO_4)
        assert cliente2 is not None, "Cliente 2 não encontrado por CPF"
        self.cliente2_id = cliente2["id"]
    
    def test_ciclo_venda_completo(self):
        """Testa ciclo completo de venda: cadastro -> venda -> relatório"""
        # Registrar venda
        itens = [
            {"produto_id": self.produto1_id, "quantidade": 1},
            {"produto_id": self.produto2_id, "quantidade": 2},
            {"produto_id": self.produto3_id, "quantidade": 3}
        ]
        
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente1_id,
            itens=itens,
            forma_pagamento="Cartão de Crédito",
            usuario="admin_teste"
        )
        
        assert sucesso, f"Falha ao registrar venda: {msg}"
        assert venda_id is not None
        
        # Verificar estoque após venda
        _, estoque1 = self.produto_service.verificar_estoque(self.produto1_id)
        assert estoque1 == 19  # 20 - 1
        
        _, estoque2 = self.produto_service.verificar_estoque(self.produto2_id)
        assert estoque2 == 28  # 30 - 2
        
        _, estoque3 = self.produto_service.verificar_estoque(self.produto3_id)
        assert estoque3 == 97  # 100 - 3
        
        # Obter detalhes da venda
        detalhes = self.venda_service.detalhes_venda(venda_id)
        assert detalhes["venda"]["cliente_id"] == self.cliente1_id
        assert len(detalhes["itens"]) == 3
        
        # Histórico do cliente
        historico = self.venda_service.historico_cliente(self.cliente1_id)
        assert len(historico) == 1
        assert historico.iloc[0]["id"] == venda_id
        
        # Métricas de vendas
        data_fim = date.today() + timedelta(days=1)
        data_inicio = data_fim - timedelta(days=30)
        
        metricas = self.venda_service.get_metricas_periodo(data_inicio, data_fim)
        assert metricas["total_vendas"] >= 1
        assert metricas["faturamento_total"] > 0
        
        # Relatório geral
        relatorio = self.relatorio_service.get_metricas_gerais()
        assert relatorio["vendas_hoje"] >= 1
        assert relatorio["faturamento_hoje"] > 0
    
    def test_fluxo_estoque_completo(self):
        """Testa fluxo completo de estoque: entrada -> saída -> ajuste -> relatório"""
        # Registrar entrada manual
        sucesso, msg = self.estoque_service.entrada_estoque(
            produto_id=self.produto1_id,
            quantidade=10,
            usuario="admin_teste",
            observacao="Compra de reposição"
        )
        
        assert sucesso
        
        _, estoque = self.produto_service.verificar_estoque(self.produto1_id)
        assert estoque == 30  # 20 + 10
        
        # Registrar saída manual
        sucesso, msg = self.estoque_service.saida_estoque(
            produto_id=self.produto1_id,
            quantidade=5,
            usuario="admin_teste",
            observacao="Amostra para cliente"
        )
        
        assert sucesso
        
        _, estoque = self.produto_service.verificar_estoque(self.produto1_id)
        assert estoque == 25  # 30 - 5
        
        # Ajuste de estoque
        sucesso, msg = self.estoque_service.ajuste_estoque(
            produto_id=self.produto1_id,
            nova_quantidade=22,
            usuario="admin_teste",
            motivo="Após contagem física"
        )
        
        assert sucesso
        
        _, estoque = self.produto_service.verificar_estoque(self.produto1_id)
        assert estoque == 22
        
        # Verificar logs de estoque
        logs = self.db.read_sql(
            "SELECT * FROM logs WHERE modulo = 'ESTOQUE' ORDER BY data_hora DESC LIMIT 10"
        )
        assert len(logs) >= 3
    
    def test_integracao_promocoes_vendas(self):
        """Testa integração entre promoções e vendas"""
        # Criar promoção
        from datetime import date, timedelta
        
        hoje = date.today()
        inicio = hoje - timedelta(days=1)
        fim = hoje + timedelta(days=30)
        
        sucesso, msg = self.promocao_service.criar_promocao(
            nome="PROMO TESTE 15%",
            descricao="15% de desconto em eletrônicos",
            tipo="DESCONTO_PERCENTUAL",
            valor_desconto=15.0,
            data_inicio=inicio,
            data_fim=fim,
            status="ATIVA",
            usuario="admin_teste"
        )
        
        assert sucesso, f"Falha ao criar promoção: {msg}"
        
        # Listar promoções ativas
        promocoes = self.promocao_service.listar_promocoes(ativas=True)
        assert len(promocoes) >= 1
        
        # Aplicar promoção a itens
        itens = [
            {"produto_id": self.produto1_id, "quantidade": 1, "preco_unitario": 3500.00},
            {"produto_id": self.produto2_id, "quantidade": 1, "preco_unitario": 2000.00},
        ]
        
        itens_com_promocao = self.promocao_service.aplicar_promocao(itens)
        
        # Verificar se algum item recebeu desconto (pode depender da regra)
        assert len(itens_com_promocao) == 2
    
    def test_relatorio_completo_clientes(self):
        """Testa geração de relatórios completos de clientes"""
        # Criar mais vendas para ter dados
        itens1 = [{"produto_id": self.produto1_id, "quantidade": 1}]
        itens2 = [{"produto_id": self.produto2_id, "quantidade": 2}]
        
        for i in range(3):
            self.venda_service.registrar_venda(
                cliente_id=self.cliente1_id,
                itens=itens1,
                forma_pagamento="Dinheiro",
                usuario="admin_teste"
            )
        
        for i in range(2):
            self.venda_service.registrar_venda(
                cliente_id=self.cliente2_id,
                itens=itens2,
                forma_pagamento="Cartão",
                usuario="admin_teste"
            )
        
        # Estatísticas de clientes
        stats = self.cliente_service.get_estatisticas()
        assert stats["total_clientes"] >= 2
        assert stats["clientes_com_cpf"] >= 2
        
        # Top clientes
        top_clientes = self.relatorio_service.relatorio_clientes_top(limite=5)
        assert len(top_clientes) >= 2
        
        # Verificar ordenação (maior gasto primeiro)
        if len(top_clientes) >= 2:
            assert top_clientes.iloc[0]["total_gasto"] >= top_clientes.iloc[1]["total_gasto"]
    
    def test_transacao_completa_com_rollback(self):
        """Testa transação completa com rollback em caso de erro"""
        # Estado inicial
        _, estoque1_inicial = self.produto_service.verificar_estoque(self.produto1_id)
        _, estoque2_inicial = self.produto_service.verificar_estoque(self.produto2_id)
        
        # Tentar venda que vai falhar (produto3 sem estoque)
        itens_invalidos = [
            {"produto_id": self.produto3_id, "quantidade": 999},  # Estoque insuficiente
        ]
        
        # Tentar registrar venda (deve falhar)
        sucesso, msg, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente1_id,
            itens=itens_invalidos,
            forma_pagamento="Cartão",
            usuario="admin_teste"
        )
        
        assert sucesso is False
        assert "insuficiente" in msg.lower() or "estoque" in msg.lower()
        
        # Verificar que estoque não mudou
        _, estoque1_final = self.produto_service.verificar_estoque(self.produto1_id)
        _, estoque2_final = self.produto_service.verificar_estoque(self.produto2_id)
        
        assert estoque1_final == estoque1_inicial
        assert estoque2_final == estoque2_inicial
    
    def test_fluxo_completo_auditoria(self):
        """Testa se todas as operações geram logs de auditoria"""
        # Operações
        self.cliente_service.cadastrar_individual({
            "nome": "CLIENTE AUDITORIA",
            "cpf": CPF_VALIDO_3
        }, "admin_teste")
        
        self.produto_service.cadastrar_produto({
            "nome": "PRODUTO AUDITORIA",
            "categoria": "ELETRONICOS",
            "preco_venda": 500.00
        }, "admin_teste")
        
        itens = [{"produto_id": self.produto1_id, "quantidade": 1}]
        sucesso, _, venda_id = self.venda_service.registrar_venda(
            cliente_id=self.cliente1_id,
            itens=itens,
            forma_pagamento="PIX",
            usuario="admin_teste"
        )
        assert sucesso
        
        sucesso, _ = self.venda_service.estornar_venda(venda_id, "admin_teste", "Teste")
        assert sucesso
        
        sucesso, _ = self.estoque_service.entrada_estoque(self.produto2_id, 5, "admin_teste", "Teste")
        assert sucesso
        
        # Verificar logs
        logs = self.db.read_sql("SELECT * FROM logs ORDER BY id")
        
        # Deve ter pelo menos 5 logs
        assert len(logs) >= 5
        
        # Verificar tipos de ação
        acoes = logs["acao"].tolist()
        assert any("Cadastrou cliente" in str(a) for a in acoes)
        assert any("Cadastrou produto" in str(a) for a in acoes)
        assert any("Registrou venda" in str(a) for a in acoes)
        assert any("Estornou venda" in str(a) for a in acoes)
        assert any("Movimentação" in str(a) or "Entrada" in str(a) for a in acoes)