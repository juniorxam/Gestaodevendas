"""
promocao_service.py - Serviço de promoções
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.auth_service import AuditLog
from core.security import Formatters


class PromocaoService:
    """Serviço para gerenciamento de promoções"""
    
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit

    def criar_promocao(
        self,
        nome: str,
        descricao: str,
        tipo: str,
        valor_desconto: float,
        data_inicio: date,
        data_fim: date,
        status: str,
        usuario: str,
    ) -> Tuple[bool, str]:
        """
        Cria uma nova promoção
        
        Args:
            nome: Nome da promoção
            descricao: Descrição
            tipo: Tipo ('DESCONTO_PERCENTUAL', 'DESCONTO_FIXO', 'LEVE_MAIS')
            valor_desconto: Valor do desconto
            data_inicio: Data de início
            data_fim: Data de fim
            status: Status ('PLANEJADA', 'ATIVA', 'CONCLUÍDA', 'CANCELADA')
            usuario: Usuário que está criando
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            if not nome.strip():
                return False, "Nome da promoção é obrigatório"
            
            if data_fim < data_inicio:
                return False, "Data de término deve ser posterior à data de início"
            
            if valor_desconto <= 0:
                return False, "Valor do desconto deve ser maior que zero"
            
            self.db.execute(
                """
                INSERT INTO promocoes
                (nome, descricao, tipo, valor_desconto, data_inicio, data_fim, status, usuario_criacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nome.strip(),
                    descricao.strip(),
                    tipo,
                    valor_desconto,
                    data_inicio.isoformat(),
                    data_fim.isoformat(),
                    status,
                    usuario,
                )
            )
            
            self.audit.registrar(
                usuario,
                "PROMOCOES",
                "Criou promoção",
                f"{nome} - {tipo} - R$ {valor_desconto}"
            )
            
            return True, "Promoção criada com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao criar promoção: {str(e)}"

    def listar_promocoes(
        self,
        status: Optional[str] = None,
        ativas: bool = False,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Lista promoções
        
        Args:
            status: Filtrar por status (opcional)
            ativas: Se True, filtra apenas promoções ativas (dentro do período)
            limit: Limite de resultados
            
        Returns:
            DataFrame com promoções
        """
        params = []
        where_clauses = []
        
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if ativas:
            hoje = date.today().isoformat()
            where_clauses.append("data_inicio <= ?")
            where_clauses.append("data_fim >= ?")
            where_clauses.append("status = 'ATIVA'")
            params.extend([hoje, hoje])
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        return self.db.read_sql(
            f"""
            SELECT 
                *,
                julianday('now') - julianday(data_fim) as dias_restantes
            FROM promocoes
            WHERE {where_sql}
            ORDER BY 
                CASE status 
                    WHEN 'ATIVA' THEN 1
                    WHEN 'PLANEJADA' THEN 2
                    WHEN 'CONCLUÍDA' THEN 3
                    WHEN 'CANCELADA' THEN 4
                END,
                data_inicio DESC
            LIMIT ?
            """,
            params + [limit]
        )

    def obter_promocao(self, promocao_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém uma promoção pelo ID
        
        Args:
            promocao_id: ID da promoção
            
        Returns:
            Dicionário com dados da promoção ou None
        """
        row = self.db.fetchone(
            "SELECT * FROM promocoes WHERE id = ?",
            (promocao_id,)
        )
        return dict(row) if row else None

    def atualizar_promocao(
        self,
        promocao_id: int,
        dados: Dict[str, Any],
        usuario: str
    ) -> Tuple[bool, str]:
        """
        Atualiza uma promoção
        
        Args:
            promocao_id: ID da promoção
            dados: Dicionário com novos dados
            usuario: Usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Verificar se promoção existe
            promocao = self.db.fetchone(
                "SELECT nome FROM promocoes WHERE id = ?",
                (promocao_id,)
            )
            if not promocao:
                return False, "Promoção não encontrada"

            # Construir query dinâmica
            campos = []
            params = []
            
            mapeamento = {
                "nome": "nome",
                "descricao": "descricao",
                "tipo": "tipo",
                "valor_desconto": "valor_desconto",
                "data_inicio": "data_inicio",
                "data_fim": "data_fim",
                "status": "status",
            }
            
            for campo_db, campo_dados in mapeamento.items():
                if campo_dados in dados and dados[campo_dados] is not None:
                    valor = dados[campo_dados]
                    if campo_db in ["data_inicio", "data_fim"]:
                        valor = Formatters.parse_date(valor).isoformat() if Formatters.parse_date(valor) else None
                    
                    campos.append(f"{campo_db} = ?")
                    params.append(valor)

            if not campos:
                return False, "Nenhum dado para atualizar"

            params.append(promocao_id)
            query = f"UPDATE promocoes SET {', '.join(campos)} WHERE id = ?"
            
            self.db.execute(query, params)
            
            self.audit.registrar(
                usuario,
                "PROMOCOES",
                "Atualizou promoção",
                f"ID: {promocao_id} - {promocao['nome']}"
            )
            
            return True, "Promoção atualizada com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao atualizar: {str(e)}"

    def excluir_promocao(self, promocao_id: int, usuario: str) -> Tuple[bool, str]:
        """
        Exclui uma promoção
        
        Args:
            promocao_id: ID da promoção
            usuario: Usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Verificar se promoção tem vendas associadas
            vendas = self.db.fetchone(
                "SELECT COUNT(*) as total FROM itens_venda WHERE promocao_id = ?",
                (promocao_id,)
            )
            
            if vendas and vendas["total"] > 0:
                return False, f"Não é possível excluir: promoção utilizada em {vendas['total']} vendas"
            
            # Buscar nome para audit
            promocao = self.db.fetchone(
                "SELECT nome FROM promocoes WHERE id = ?",
                (promocao_id,)
            )
            
            self.db.execute(
                "DELETE FROM promocoes WHERE id = ?",
                (promocao_id,)
            )
            
            self.audit.registrar(
                usuario,
                "PROMOCOES",
                "Excluiu promoção",
                f"ID: {promocao_id} - {promocao['nome'] if promocao else 'desconhecida'}"
            )
            
            return True, "Promoção excluída com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao excluir promoção: {str(e)}"

    def aplicar_promocao(self, itens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aplica promoções ativas a uma lista de itens
        
        Args:
            itens: Lista de itens com produto_id, quantidade, preco_unitario
            
        Returns:
            Lista de itens com promoções aplicadas e novos preços
        """
        # Buscar promoções ativas
        promocoes_ativas = self.listar_promocoes(ativas=True)
        
        if promocoes_ativas.empty:
            return itens
        
        itens_com_promocao = []
        
        for item in itens:
            item_copy = item.copy()
            melhor_desconto = 0
            promocao_aplicada = None
            
            # Para cada promoção ativa, verificar se aplica
            for _, promocao in promocoes_ativas.iterrows():
                # Aqui você pode implementar regras mais complexas
                # como promoções por categoria, produtos específicos, etc.
                
                if promocao["tipo"] == "DESCONTO_PERCENTUAL":
                    desconto = item["preco_unitario"] * (promocao["valor_desconto"] / 100)
                    if desconto > melhor_desconto:
                        melhor_desconto = desconto
                        promocao_aplicada = promocao["id"]
                        
                elif promocao["tipo"] == "DESCONTO_FIXO":
                    if promocao["valor_desconto"] > melhor_desconto:
                        melhor_desconto = promocao["valor_desconto"]
                        promocao_aplicada = promocao["id"]
            
            if promocao_aplicada:
                item_copy["preco_unitario"] = item["preco_unitario"] - melhor_desconto
                item_copy["promocao_id"] = promocao_aplicada
                item_copy["desconto_aplicado"] = melhor_desconto
            
            itens_com_promocao.append(item_copy)
        
        return itens_com_promocao