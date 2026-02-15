"""
test_config.py - Configuração para os testes
"""

import os
import tempfile
import shutil
import time
import gc
from pathlib import Path

# Configuração de teste
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "electrogest_test.db")
TEST_BACKUP_DIR = os.path.join(tempfile.gettempdir(), "test_backups")

# Dados de teste - CORREÇÃO: CPFs válidos (apenas números)
TEST_ADMIN = {
    "login": "admin_teste",
    "senha": "admin123",
    "nome": "Administrador Teste",
    "nivel_acesso": "ADMIN"
}

TEST_OPERADOR = {
    "login": "operador_teste",
    "senha": "operador123",
    "nome": "Operador Teste",
    "nivel_acesso": "OPERADOR"
}

TEST_VISUALIZADOR = {
    "login": "visualizador_teste",
    "senha": "visualizador123",
    "nome": "Visualizador Teste",
    "nivel_acesso": "VISUALIZADOR"
}

TEST_CLIENTE = {
    "nome": "CLIENTE TESTE SILVA",
    "cpf": "52998224725",  # CPF VÁLIDO (apenas números)
    "email": "cliente.teste@email.com",
    "telefone": "(11) 99999-9999",
    "data_nascimento": "1990-01-01",
    "endereco": "Rua Teste, 123",
    "cidade": "SAO PAULO",
    "estado": "SP",
    "cep": "01234-567"
}

TEST_CATEGORIA = {
    "nome": "ELETRONICOS",
    "descricao": "Produtos eletronicos em geral"
}

TEST_PRODUTO = {
    "codigo_barras": "7891234567890",
    "nome": "SMARTPHONE TESTE 128GB",
    "descricao": "Smartphone para testes",
    "fabricante": "TESTE INC",
    "preco_custo": 1500.00,
    "preco_venda": 2500.00,
    "quantidade_estoque": 50,
    "estoque_minimo": 10,
    "ativo": True
}

TEST_PROMOCAO = {
    "nome": "PROMOÇÃO TESTE",
    "descricao": "Promoção para testes",
    "tipo": "DESCONTO_PERCENTUAL",
    "valor_desconto": 15.0,
    "data_inicio": "2026-01-01",
    "data_fim": "2026-12-31",
    "status": "ATIVA"
}

# CPFs válidos para testes (apenas números) - TODOS VÁLIDOS
CPF_VALIDO_1 = "52998224725"  # CPF válido
CPF_VALIDO_2 = "34175632890"  # CPF válido
CPF_VALIDO_3 = "04536271081"  # CPF válido
CPF_VALIDO_4 = "12345678909"  # CPF válido (usado em outros testes)

# Utilitários para testes - VERSÃO CORRIGIDA
def limpar_arquivos_teste():
    """Remove arquivos de teste após os testes com tratamento de erros"""
    # Fechar possíveis conexões com o banco
    try:
        # Forçar coleta de lixo para liberar arquivos
        gc.collect()
        
        # Pequena pausa para liberar arquivos
        time.sleep(0.2)
    except:
        pass
    
    # Remover banco de teste
    if os.path.exists(TEST_DB_PATH):
        try:
            # Tentar remover com força bruta
            for i in range(3):  # Tentar 3 vezes
                try:
                    os.remove(TEST_DB_PATH)
                    break
                except PermissionError:
                    time.sleep(0.1 * (i + 1))
        except Exception:
            pass
    
    # Remover diretório de backup com tratamento
    if os.path.exists(TEST_BACKUP_DIR):
        try:
            # Tentar remover com shutil primeiro
            shutil.rmtree(TEST_BACKUP_DIR, ignore_errors=True)
        except:
            pass
        
        # Se ainda existir, tentar remover arquivo por arquivo
        if os.path.exists(TEST_BACKUP_DIR):
            try:
                for root, dirs, files in os.walk(TEST_BACKUP_DIR, topdown=False):
                    for name in files:
                        try:
                            os.remove(os.path.join(root, name))
                        except:
                            pass
                    for name in dirs:
                        try:
                            os.rmdir(os.path.join(root, name))
                        except:
                            pass
                # Tentar remover o diretório novamente
                if os.path.exists(TEST_BACKUP_DIR):
                    os.rmdir(TEST_BACKUP_DIR)
            except:
                pass