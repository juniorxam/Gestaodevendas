"""
estoque_service.py - Serviço de gestão de estoque
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.auth_service import AuditLog
from core.security import Formatters


class EstoqueService:
    """Serviço para gestão de estoque e movimentações"""
    
    def __init__(self, db: "Database", audit: AuditLog, produto_service=None) -> None:
        self.db = db
        self.audit = audit
        self.produto_service = produto_service

    def registrar_movimentacao(
        self,
        produto_id: int,
        tipo: str,
        quantidade: int,
        usuario: str,
        observacao: str = "",
        origem: str = "MANUAL"
    ) -> Tuple[bool, str]:
        """
        Registra uma movimentação de estoque
        
        Args:
            produto_id: ID do produto
            tipo: Tipo ('ENTRADA', 'SAIDA', 'AJUSTE')
            quantidade: Quantidade (positiva)
            usuario: Usuário
            observacao: Observação
            origem: Origem da movimentação ('VENDA', 'COMPRA', 'MANUAL', 'AJUSTE')
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Validar quantidade
            if quantidade <= 0:
                return False, "Quantidade deve ser maior que zero"
            
            with self.db.connect() as conn:
                # Obter produto
                produto = conn.execute(
                    "SELECT nome, quantidade_estoque FROM produtos WHERE id = ?",
                    (produto_id,)
                ).fetchone()
                
                if not produto:
                    return False, "Produto não encontrado"
                
                # Calcular novo estoque
                estoque_atual = int(produto["quantidade_estoque"])
                
                if tipo in ["SAIDA", "AJUSTE_NEGATIVO"]:
                    novo_estoque = estoque_atual - quantidade
                    if novo_estoque < 0:
                        return False, f"Estoque insuficiente. Disponível: {estoque_atual}"
                else:
                    novo_estoque = estoque_atual + quantidade
                
                # Atualizar estoque
                conn.execute(
                    "UPDATE produtos SET quantidade_estoque = ? WHERE id = ?",
                    (novo_estoque, produto_id)
                )
                
                # Registrar em tabela de movimentações (se existir)
                # Você pode criar uma tabela `movimentacoes_estoque` para histórico
                
                conn.commit()
            
            # Registrar no audit
            detalhes = (
                f"Produto: {produto['nome']} | "
                f"Tipo: {tipo} | "
                f"Quantidade: {quantidade} | "
                f"Estoque anterior: {estoque_atual} | "
                f"Novo estoque: {novo_estoque}"
            )
            if observacao:
                detalhes += f" | Obs: {observacao}"
            
            self.audit.registrar(
                usuario,
                "ESTOQUE",
                f"Movimentação - {tipo}",
                detalhes
            )
            
            return True, f"Movimentação registrada. Novo estoque: {novo_estoque}"
            
        except Exception as e:
            return False, f"Erro ao registrar movimentação: {str(e)}"

    def entrada_estoque(
        self,
        produto_id: int,
        quantidade: int,
        usuario: str,
        observacao: str = ""
    ) -> Tuple[bool, str]:
        """
        Registra entrada de estoque (compra)
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade
            usuario: Usuário
            observacao: Observação
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        return self.registrar_movimentacao(
            produto_id=produto_id,
            tipo="ENTRADA",
            quantidade=quantidade,
            usuario=usuario,
            observacao=observacao,
            origem="COMPRA"
        )

    def saida_estoque(
        self,
        produto_id: int,
        quantidade: int,
        usuario: str,
        observacao: str = ""
    ) -> Tuple[bool, str]:
        """
        Registra saída de estoque (venda manual)
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade
            usuario: Usuário
            observacao: Observação
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        return self.registrar_movimentacao(
            produto_id=produto_id,
            tipo="SAIDA",
            quantidade=quantidade,
            usuario=usuario,
            observacao=observacao,
            origem="MANUAL"
        )

    def ajuste_estoque(
        self,
        produto_id: int,
        nova_quantidade: int,
        usuario: str,
        motivo: str = ""
    ) -> Tuple[bool, str]:
        """
        Ajusta o estoque para uma quantidade específica
        
        Args:
            produto_id: ID do produto
            nova_quantidade: Nova quantidade em estoque
            usuario: Usuário
            motivo: Motivo do ajuste
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            with self.db.connect() as conn:
                produto = conn.execute(
                    "SELECT nome, quantidade_estoque FROM produtos WHERE id = ?",
                    (produto_id,)
                ).fetchone()
                
                if not produto:
                    return False, "Produto não encontrado"
                
                estoque_atual = int(produto["quantidade_estoque"])
                diferenca = nova_quantidade - estoque_atual
                
                if diferenca == 0:
                    return True, "Estoque já está na quantidade informada"
                
                conn.execute(
                    "UPDATE produtos SET quantidade_estoque = ? WHERE id = ?",
                    (nova_quantidade, produto_id)
                )
                
                conn.commit()
            
            # Registrar no audit
            detalhes = (
                f"Produto: {produto['nome']} | "
                f"Ajuste: {estoque_atual} → {nova_quantidade} | "
                f"Diferença: {diferenca:+d}"
            )
            if motivo:
                detalhes += f" | Motivo: {motivo}"
            
            self.audit.registrar(
                usuario,
                "ESTOQUE",
                "Ajuste de estoque",
                detalhes
            )
            
            return True, f"Estoque ajustado de {estoque_atual} para {nova_quantidade}"
            
        except Exception as e:
            return False, f"Erro ao ajustar estoque: {str(e)}"

    def get_relatorio_estoque(self) -> Dict[str, Any]:
        """
        Gera relatório completo da situação do estoque
        
        Returns:
            Dicionário com informações do estoque
        """
        # Valor total do estoque
        valor_total = self.db.fetchone(
            "SELECT SUM(quantidade_estoque * preco_custo) as total FROM produtos WHERE ativo = 1"
        )
        
        # Produtos em estoque baixo
        estoque_baixo = self.produto_service.get_produtos_estoque_baixo() if self.produto_service else pd.DataFrame()
        
        # Produtos sem estoque
        sem_estoque = self.db.read_sql(
            """
            SELECT 
                id,
                codigo_barras,
                nome,
                preco_venda
            FROM produtos
            WHERE quantidade_estoque = 0 AND ativo = 1
            ORDER BY nome
            """
        )
        
        # Categorias com estoque
        categorias = self.db.read_sql(
            """
            SELECT 
                c.nome as categoria,
                COUNT(DISTINCT p.id) as total_produtos,
                SUM(p.quantidade_estoque) as total_itens,
                SUM(p.quantidade_estoque * p.preco_custo) as valor_estoque
            FROM categorias c
            LEFT JOIN produtos p ON c.id = p.categoria_id AND p.ativo = 1
            WHERE c.ativo = 1
            GROUP BY c.id
            ORDER BY valor_estoque DESC
            """
        )
        
        return {
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "valor_total_estoque": float(valor_total["total"]) if valor_total and valor_total["total"] else 0,
            "total_produtos_ativos": int(self.db.fetchone("SELECT COUNT(*) as total FROM produtos WHERE ativo = 1")["total"]),
            "total_itens_estoque": int(self.db.fetchone("SELECT SUM(quantidade_estoque) as total FROM produtos WHERE ativo = 1")["total"] or 0),
            "produtos_estoque_baixo": len(estoque_baixo),
            "produtos_sem_estoque": len(sem_estoque),
            "estoque_baixo_detalhes": estoque_baixo.to_dict('records') if not estoque_baixo.empty else [],
            "sem_estoque_detalhes": sem_estoque.to_dict('records') if not sem_estoque.empty else [],
            "categorias": categorias.to_dict('records') if not categorias.empty else []
        }

    def get_sugestoes_reposicao(self) -> pd.DataFrame:
        """
        Gera sugestões de reposição baseadas no estoque mínimo
        
        Returns:
            DataFrame com sugestões de compra
        """
        return self.db.read_sql(
            """
            SELECT 
                id,
                codigo_barras,
                nome,
                quantidade_estoque,
                estoque_minimo,
                (estoque_minimo - quantidade_estoque) as quantidade_recomendada,
                preco_custo,
                (estoque_minimo - quantidade_estoque) * preco_custo as valor_total_estimado
            FROM produtos
            WHERE quantidade_estoque < estoque_minimo
              AND ativo = 1
            ORDER BY (estoque_minimo - quantidade_estoque) DESC
            """
        )