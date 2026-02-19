"""
auth_service.py - Serviços de autenticação e auditoria com IP dinâmico
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Optional

from .security import Security


class AuditLog:
    def __init__(self, db: "Database") -> None:
        self.db = db

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

    def registrar(self, usuario: str, modulo: str, acao: str, detalhes: str = "", ip_address: str = None) -> None:
        """
        Registra uma ação no log de auditoria
        
        Args:
            usuario: Nome do usuário
            modulo: Módulo do sistema
            acao: Ação realizada
            detalhes: Detalhes adicionais
            ip_address: IP do cliente (se None, tenta capturar automaticamente)
        """
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Se não forneceu IP, tenta capturar
        if ip_address is None:
            ip_address = self._get_client_ip()
        
        self.db.execute(
            """
            INSERT INTO logs (data_hora, usuario, modulo, acao, detalhes, ip_address)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agora, usuario, modulo, acao, detalhes, ip_address),
        )


class Auth:
    def __init__(self, db: "Database") -> None:
        self.db = db

    def login(self, login: str, senha: str) -> Optional[Dict[str, str]]:
        senha_hash = Security.sha256_hex(senha)
        row = self.db.fetchone(
            "SELECT nome, nivel_acesso FROM usuarios WHERE login = ? AND senha = ? AND ativo = 1",
            (login, senha_hash),
        )
        if not row:
            return None
        return {"nome": str(row["nome"]), "nivel_acesso": str(row["nivel_acesso"])}

    @staticmethod
    def verificar_permissoes(user_level: str, needed_level: str) -> bool:
        if user_level == "ADMIN":
            return True
        if user_level == "OPERADOR":
            return needed_level in ("OPERADOR", "VISUALIZADOR")
        if user_level == "VISUALIZADOR":
            return needed_level == "VISUALIZADOR"
        return False
