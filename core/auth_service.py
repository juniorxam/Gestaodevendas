"""
auth_service.py - Serviços de autenticação e auditoria
"""

from datetime import datetime
from typing import Dict, Optional

from .security import Security


class AuditLog:
    def __init__(self, db: "Database") -> None:
        self.db = db

    def registrar(self, usuario: str, modulo: str, acao: str, detalhes: str = "", ip_address: str = "127.0.0.1") -> None:
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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