"""
test_security.py - Testes das funcionalidades de segurança
"""

import pytest
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security import Security, Formatters


class TestSecurity:
    """Testes para a classe Security"""
    
    def test_sha256_hex(self):
        """Testa geração de hash SHA256"""
        result = Security.sha256_hex("admin123")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex tem 64 caracteres
        assert result == Security.sha256_hex("admin123")  # Consistente
    
    def test_clean_cpf(self):
        """Testa limpeza de CPF"""
        assert Security.clean_cpf("123.456.789-09") == "12345678909"
        assert Security.clean_cpf("12345678909") == "12345678909"
        assert Security.clean_cpf("123.456.789-09 abc") == "12345678909"
        assert Security.clean_cpf(None) == ""
        assert Security.clean_cpf(12345678909) == "12345678909"
    
    def test_validar_cpf(self):
        """Testa validação de CPF"""
        # CPFs válidos
        assert Security.validar_cpf("52998224725") is True
        assert Security.validar_cpf(52998224725) is True
        assert Security.validar_cpf("12345678909") is True
        
        # CPFs inválidos
        assert Security.validar_cpf("11111111111") is False
        assert Security.validar_cpf("12345678900") is False
        assert Security.validar_cpf("") is False
        assert Security.validar_cpf(None) is False
        assert Security.validar_cpf("abc") is False
    
    def test_formatar_cpf(self):
        """Testa formatação de CPF"""
        assert Security.formatar_cpf("12345678909") == "123.456.789-09"
        assert Security.formatar_cpf("123.456.789-09") == "123.456.789-09"
        assert Security.formatar_cpf("123") == "123"  # Tamanho inválido
        assert Security.formatar_cpf(None) == ""
    
    def test_formatar_telefone(self):
        """Testa formatação de telefone"""
        # Celular 11 dígitos
        assert Security.formatar_telefone("11999999999") == "(11) 99999-9999"
        # Fixo 10 dígitos
        assert Security.formatar_telefone("1133334444") == "(11) 3333-4444"
        # Já formatado
        assert Security.formatar_telefone("(11) 99999-9999") == "(11) 99999-9999"
        # Tamanho inválido
        assert Security.formatar_telefone("123") == "123"
        assert Security.formatar_telefone(None) == ""
    
    def test_formatar_cep(self):
        """Testa formatação de CEP"""
        assert Security.formatar_cep("12345678") == "12345-678"
        assert Security.formatar_cep("12345-678") == "12345-678"
        assert Security.formatar_cep("123") == "123"
        assert Security.formatar_cep(None) == ""
    
    def test_formatar_moeda(self):
        """Testa formatação de valores monetários"""
        assert Security.formatar_moeda(1234.56) == "R$ 1.234,56"
        assert Security.formatar_moeda(1000) == "R$ 1.000,00"
        assert Security.formatar_moeda(0) == "R$ 0,00"
        assert Security.formatar_moeda(None) == "R$ 0,00"
        assert Security.formatar_moeda("abc") == "R$ 0,00"
    
    def test_safe_select_only(self):
        """Testa validação de SQL seguro"""
        # SELECTs válidos
        valid, msg = Security.safe_select_only("SELECT * FROM clientes")
        assert valid is True
        
        valid, msg = Security.safe_select_only("SELECT nome, cpf FROM clientes WHERE id = 1")
        assert valid is True
        
        valid, msg = Security.safe_select_only("SELECT COUNT(*) FROM vendas GROUP BY data")
        assert valid is True
        
        # Comandos inválidos
        invalid_queries = [
            "INSERT INTO clientes VALUES (1, 'teste')",
            "UPDATE clientes SET nome = 'teste'",
            "DELETE FROM clientes",
            "DROP TABLE clientes",
            "ALTER TABLE clientes ADD COLUMN teste",
            "CREATE TABLE teste (id INTEGER)",
            "PRAGMA table_info(clientes)",
            "ATTACH DATABASE 'teste.db' AS teste",
            "VACUUM",
        ]
        
        for query in invalid_queries:
            valid, msg = Security.safe_select_only(query)
            assert valid is False
            # CORREÇÃO: Verificar mensagem sem acentos e com caracteres especiais
            msg_lower = msg.lower()
            assert "apenas select" in msg_lower or "bloqueado" in msg_lower or "apenas consultas select" in msg_lower


class TestFormatters:
    """Testes para a classe Formatters"""
    
    def test_parse_date(self):
        """Testa parsing de datas"""
        from datetime import date, datetime
        
        # Vários formatos
        assert Formatters.parse_date("2026-02-14") == date(2026, 2, 14)
        assert Formatters.parse_date("14/02/2026") == date(2026, 2, 14)
        assert Formatters.parse_date("14-02-2026") == date(2026, 2, 14)
        assert Formatters.parse_date("2026/02/14") == date(2026, 2, 14)
        
        # Com hora
        assert Formatters.parse_date("2026-02-14 15:30:00") == date(2026, 2, 14)
        
        # Objeto date
        d = date(2026, 2, 14)
        assert Formatters.parse_date(d) == d
        
        # Objeto datetime
        dt = datetime(2026, 2, 14, 15, 30)
        assert Formatters.parse_date(dt) == date(2026, 2, 14)
        
        # Valores nulos
        assert Formatters.parse_date(None) is None
        assert Formatters.parse_date("") is None
        assert Formatters.parse_date("   ") is None
        
        # Formato inválido
        assert Formatters.parse_date("data inválida") is None
    
    def test_formatar_data_br(self):
        """Testa formatação de data no padrão brasileiro"""
        from datetime import date
        
        assert Formatters.formatar_data_br("2026-02-14") == "14/02/2026"
        assert Formatters.formatar_data_br(date(2026, 2, 14)) == "14/02/2026"
        assert Formatters.formatar_data_br(None) == ""
        assert Formatters.formatar_data_br("") == ""
    
    def test_formatar_data_hora(self):
        """Testa formatação de data e hora"""
        from datetime import datetime
        
        assert Formatters.formatar_data_hora("2026-02-14 15:30:00") == "14/02/2026 15:30"
        assert Formatters.formatar_data_hora(datetime(2026, 2, 14, 15, 30)) == "14/02/2026 15:30"
        assert Formatters.formatar_data_hora(None) == ""
    
    def test_calcular_idade(self):
        """Testa cálculo de idade"""
        from datetime import date, timedelta
        import unittest.mock as mock
        
        # Fixar data atual para teste consistente
        mock_date = date(2026, 2, 14)
        
        with mock.patch('core.security.date') as mock_date_class:
            mock_date_class.today.return_value = mock_date
            mock_date_class.side_effect = lambda *args, **kw: date(*args, **kw)
            
            # Idade exata
            assert Formatters.calcular_idade("1990-02-14") == 36
            
            # Aniversário ainda não ocorreu este ano
            assert Formatters.calcular_idade("1990-05-14") == 35
            
            # Aniversário já ocorreu este ano
            assert Formatters.calcular_idade("1990-01-14") == 36
            
            # Data nula
            assert Formatters.calcular_idade(None) is None