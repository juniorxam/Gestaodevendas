"""
config.py - ElectroGest v1.0
Configurações da aplicação
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    app_title: str = "ElectroGest - Sistema de Gestão Comercial"
    page_icon: str = "🛒"
    layout: str = "wide"
    initial_sidebar_state: str = "expanded"

    # Ano exibido
    ano_atual: int = 2026

    # DB
    db_path: str = "electrogest.db"

    # Logo
    logo_path: str = "LOGO.png"

    # Segurança: senha padrão do admin
    admin_login: str = "admin"
    admin_password_default: str = "admin123"


CONFIG = AppConfig()