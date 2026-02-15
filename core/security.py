"""
security.py - Segurança e formatação (CORRIGIDO)
"""

import hashlib
import re
from datetime import date, datetime
from typing import Any, Optional, Tuple

import pandas as pd


class Security:
    @staticmethod
    def sha256_hex(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def clean_cpf(cpf: Any) -> str:
        """Remove todos os caracteres não numéricos do CPF"""
        if cpf is None:
            return ""
        # Converter para string e remover tudo que não é dígito
        return re.sub(r"[^\d]", "", str(cpf))

    @staticmethod
    def validar_cpf(cpf: Any) -> bool:
        """Valida CPF (apenas números, 11 dígitos, dígitos verificadores corretos)"""
        cpf_str = Security.clean_cpf(cpf)
        
        # Verificar tamanho
        if not cpf_str or len(cpf_str) != 11:
            return False
        
        # Verificar se todos os dígitos são iguais (CPF inválido)
        if cpf_str == cpf_str[0] * 11:
            return False

        # Calcular primeiro dígito verificador
        soma = sum(int(cpf_str[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10) % 11
        if digito1 == 10:
            digito1 = 0

        # Calcular segundo dígito verificador
        soma = sum(int(cpf_str[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10) % 11
        if digito2 == 10:
            digito2 = 0

        # Verificar dígitos
        return cpf_str[-2:] == f"{digito1}{digito2}"

    @staticmethod
    def formatar_cpf(cpf: Any) -> str:
        """Formata CPF no padrão 000.000.000-00"""
        cpf_str = Security.clean_cpf(cpf)
        if len(cpf_str) == 11:
            return f"{cpf_str[:3]}.{cpf_str[3:6]}.{cpf_str[6:9]}-{cpf_str[9:]}"
        return str(cpf or "")

    @staticmethod
    def formatar_telefone(telefone: Any) -> str:
        """Formata telefone (11) 99999-9999"""
        tel = re.sub(r"[^\d]", "", str(telefone or ""))
        if len(tel) == 11:
            return f"({tel[:2]}) {tel[2:7]}-{tel[7:]}"
        elif len(tel) == 10:
            return f"({tel[:2]}) {tel[2:6]}-{tel[6:]}"
        return str(telefone or "")

    @staticmethod
    def formatar_cep(cep: Any) -> str:
        """Formata CEP 00000-000"""
        cep_str = re.sub(r"[^\d]", "", str(cep or ""))
        if len(cep_str) == 8:
            return f"{cep_str[:5]}-{cep_str[5:]}"
        return str(cep or "")

    @staticmethod
    def formatar_moeda(valor: Any) -> str:
        """Formata valor monetário R$ 1.234,56"""
        try:
            valor_float = float(valor)
            return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "R$ 0,00"

    @staticmethod
    def safe_select_only(sql: str) -> Tuple[bool, str]:
        """
        Permite somente SELECT em consulta personalizada (admin).
        Bloqueia operações e funções comuns de exfiltração.
        """
        s = (sql or "").strip().lower()
        if not s.startswith("select"):
            return False, "Apenas consultas SELECT são permitidas."

        blocked = [
            "insert", "update", "delete", "drop", "alter", "create",
            "pragma", "attach", "detach", "vacuum", "reindex",
            "replace", "truncate",
        ]
        if any(re.search(rf"\b{kw}\b", s) for kw in blocked):
            return False, "Comando bloqueado por política de segurança (apenas SELECT)."
        return True, ""


class Formatters:
    @staticmethod
    def parse_date(data_val: Any) -> Optional[date]:
        """Converte diversos formatos para objeto date."""
        if pd.isna(data_val) or data_val is None:
            return None
        
        from datetime import date as date_type, datetime as datetime_type
        
        if isinstance(data_val, (date_type, datetime_type)):
            if isinstance(data_val, datetime_type):
                return data_val.date()
            return data_val
            
        if isinstance(data_val, str):
            data_str = data_val.strip()
            if not data_str:
                return None
            
            # Limpar parte de hora se houver
            if ' ' in data_str:
                data_str = data_str.split(' ')[0]
            
            # Tentar formatos comuns
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(data_str, fmt).date()
                except ValueError:
                    continue
        
        return None

    @staticmethod
    def formatar_data_br(data_val: Any) -> str:
        """Formata data para o padrão brasileiro DD/MM/YYYY."""
        dt = Formatters.parse_date(data_val)
        if dt:
            return dt.strftime("%d/%m/%Y")
        return str(data_val) if data_val and not pd.isna(data_val) else ""

    @staticmethod
    def formatar_data_hora(data_val: Any) -> str:
        """Formata data e hora DD/MM/YYYY HH:MM"""
        if isinstance(data_val, datetime):
            return data_val.strftime("%d/%m/%Y %H:%M")
        if isinstance(data_val, str):
            try:
                dt = datetime.fromisoformat(data_val.replace('Z', '+00:00'))
                return dt.strftime("%d/%m/%Y %H:%M")
            except:
                pass
        return str(data_val or "")
    
    @staticmethod
    def calcular_idade(data_nascimento: Any) -> Optional[int]:
        """Calcula a idade exata em anos."""
        from datetime import date
        
        if data_nascimento is None:
            return None
            
        nasc = Formatters.parse_date(data_nascimento)
        if not nasc:
            return None
            
        hoje = date.today()
        try:
            return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
        except Exception:
            return None