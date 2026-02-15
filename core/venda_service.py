"""
venda_service.py - Serviço de vendas
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.auth_service import AuditLog
from core.security import Formatters


class VendaService:
    """Serviço para gerenciamento de vendas"""
    
    def __init__(self, db: "Database", audit: AuditLog, produto_service=None) -> None:
        self.db = db
        self.audit = audit
        self.produto_service = produto_service

    def registrar_venda(
        self,
        cliente_id: Optional[int],
        itens: List[Dict[str, Any]],
        forma_pagamento: str,
        usuario: str,
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Registra uma nova venda
        
        Args:
            cliente_id: ID do cliente (pode ser None para venda sem CPF)
            itens: Lista de itens da venda. Cada item deve ter:
                - produto_id: ID do produto
                - quantidade: Quantidade
                - preco_unitario: Preço unitário (opcional, se não informado usa o da tabela)
                - promocao_id: ID da promoção aplicada (opcional)
            forma_pagamento: Forma de pagamento
            usuario: Login do usuário
            
        Returns:
            Tuple[bool, str, int]: (sucesso, mensagem, id_venda)
        """
        try:
            if not itens:
                return False, "Nenhum item na venda", None

            with self.db.connect() as conn:
                # Calcular valor total e verificar estoque
                valor_total = 0
                itens_processados = []
                
                for item in itens:
                    produto_id = item["produto_id"]
                    quantidade = int(item.get("quantidade", 1))
                    
                    # Buscar preço do produto
                    produto = conn.execute(
                        "SELECT nome, preco_venda, quantidade_estoque FROM produtos WHERE id = ? AND ativo = 1",
                        (produto_id,)
                    ).fetchone()
                    
                    if not produto:
                        return False, f"Produto ID {produto_id} não encontrado", None
                    
                    # Verificar estoque
                    if produto["quantidade_estoque"] < quantidade:
                        return False, f"Estoque insuficiente para {produto['nome']}", None
                    
                    preco = float(item.get("preco_unitario", produto["preco_venda"]))
                    subtotal = preco * quantidade
                    valor_total += subtotal
                    
                    itens_processados.append({
                        "produto_id": produto_id,
                        "quantidade": quantidade,
                        "preco_unitario": preco,
                        "promocao_id": item.get("promocao_id"),
                        "subtotal": subtotal
                    })
                
                # Inserir venda
                cursor = conn.execute(
                    """
                    INSERT INTO vendas
                    (cliente_id, valor_total, forma_pagamento, usuario_registro)
                    VALUES (?, ?, ?, ?)
                    """,
                    (cliente_id, valor_total, forma_pagamento, usuario)
                )
                venda_id = cursor.lastrowid
                
                # Inserir itens e atualizar estoque
                for item in itens_processados:
                    conn.execute(
                        """
                        INSERT INTO itens_venda
                        (venda_id, produto_id, quantidade, preco_unitario, promocao_id)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            venda_id,
                            item["produto_id"],
                            item["quantidade"],
                            item["preco_unitario"],
                            item["promocao_id"]
                        )
                    )
                    
                    # Atualizar estoque
                    conn.execute(
                        "UPDATE produtos SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?",
                        (item["quantidade"], item["produto_id"])
                    )
                
                conn.commit()
            
            # Registrar no audit
            self.audit.registrar(
                usuario,
                "VENDAS",
                "Registrou venda",
                f"Venda #{venda_id} - R$ {valor_total:.2f} - {len(itens)} itens"
            )
            
            return True, f"Venda #{venda_id} registrada com sucesso!", venda_id
            
        except Exception as e:
            return False, f"Erro ao registrar venda: {str(e)}", None

    def listar_vendas_por_periodo(
        self,
        data_inicio: date,
        data_fim: date,
        cliente_id: Optional[int] = None,
        usuario: Optional[str] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Lista vendas em um período
        
        Args:
            data_inicio: Data inicial
            data_fim: Data final
            cliente_id: Filtrar por cliente (opcional)
            usuario: Filtrar por usuário (opcional)
            limit: Limite de resultados
            
        Returns:
            DataFrame com as vendas
        """
        params = [data_inicio.isoformat(), data_fim.isoformat()]
        where = "WHERE date(v.data_venda) BETWEEN ? AND ?"
        
        if cliente_id:
            where += " AND v.cliente_id = ?"
            params.append(cliente_id)
        
        if usuario:
            where += " AND v.usuario_registro = ?"
            params.append(usuario)
        
        query = f"""
            SELECT 
                v.id,
                v.data_venda,
                v.valor_total,
                v.forma_pagamento,
                v.usuario_registro,
                c.id as cliente_id,
                c.nome as cliente_nome,
                c.cpf as cliente_cpf,
                COUNT(i.id) as total_itens
            FROM vendas v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            LEFT JOIN itens_venda i ON v.id = i.venda_id
            {where}
            GROUP BY v.id
            ORDER BY v.data_venda DESC
            LIMIT ?
        """
        params.append(limit)
        
        return self.db.read_sql(query, params)

    def detalhes_venda(self, venda_id: int) -> Dict[str, Any]:
        """
        Retorna detalhes completos de uma venda
        
        Args:
            venda_id: ID da venda
            
        Returns:
            Dicionário com dados da venda e itens
        """
        # Dados da venda
        venda = self.db.fetchone(
            """
            SELECT 
                v.*,
                c.nome as cliente_nome,
                c.cpf as cliente_cpf,
                c.telefone as cliente_telefone
            FROM vendas v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            WHERE v.id = ?
            """,
            (venda_id,)
        )
        
        if not venda:
            return {}
        
        # Itens da venda
        itens = self.db.read_sql(
            """
            SELECT 
                i.*,
                p.nome as produto_nome,
                p.codigo_barras,
                pr.nome as promocao_nome
            FROM itens_venda i
            JOIN produtos p ON i.produto_id = p.id
            LEFT JOIN promocoes pr ON i.promocao_id = pr.id
            WHERE i.venda_id = ?
            ORDER BY i.id
            """,
            (venda_id,)
        )
        
        return {
            "venda": dict(venda),
            "itens": itens.to_dict('records') if not itens.empty else []
        }

    def historico_cliente(self, cliente_id: int, limit: int = 20) -> pd.DataFrame:
        """
        Retorna histórico de compras de um cliente
        
        Args:
            cliente_id: ID do cliente
            limit: Limite de resultados
            
        Returns:
            DataFrame com histórico
        """
        return self.db.read_sql(
            """
            SELECT 
                v.id,
                v.data_venda,
                v.valor_total,
                v.forma_pagamento,
                COUNT(i.id) as total_itens,
                v.usuario_registro
            FROM vendas v
            JOIN itens_venda i ON v.id = i.venda_id
            WHERE v.cliente_id = ?
            GROUP BY v.id
            ORDER BY v.data_venda DESC
            LIMIT ?
            """,
            (cliente_id, limit)
        )

    def estornar_venda(
        self,
        venda_id: int,
        usuario: str,
        motivo: str = ""
    ) -> Tuple[bool, str]:
        """
        Estorna (cancela) uma venda, devolvendo os itens ao estoque
        
        Args:
            venda_id: ID da venda
            usuario: Login do usuário
            motivo: Motivo do estorno
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            with self.db.connect() as conn:
                # Verificar se venda existe
                venda = conn.execute(
                    """
                    SELECT v.*, c.nome as cliente_nome
                    FROM vendas v
                    LEFT JOIN clientes c ON v.cliente_id = c.id
                    WHERE v.id = ?
                    """,
                    (venda_id,)
                ).fetchone()
                
                if not venda:
                    return False, f"Venda #{venda_id} não encontrada"
                
                # Buscar itens da venda
                itens = conn.execute(
                    "SELECT produto_id, quantidade FROM itens_venda WHERE venda_id = ?",
                    (venda_id,)
                ).fetchall()
                
                if not itens:
                    return False, f"Venda #{venda_id} não possui itens"
                
                # Devolver itens ao estoque
                for item in itens:
                    conn.execute(
                        "UPDATE produtos SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?",
                        (item["quantidade"], item["produto_id"])
                    )
                
                # Excluir itens e venda
                conn.execute("DELETE FROM itens_venda WHERE venda_id = ?", (venda_id,))
                conn.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
                
                conn.commit()
            
            # Registrar no audit
            detalhes = f"Venda #{venda_id} estornada"
            if motivo:
                detalhes += f" - Motivo: {motivo}"
            
            self.audit.registrar(
                usuario,
                "VENDAS",
                "Estornou venda",
                detalhes
            )
            
            return True, f"Venda #{venda_id} estornada com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao estornar venda: {str(e)}"

    def get_metricas_periodo(self, data_inicio: date, data_fim: date) -> Dict[str, Any]:
        """
        Retorna métricas de vendas para um período
        
        Args:
            data_inicio: Data inicial
            data_fim: Data final
            
        Returns:
            Dicionário com métricas
        """
        # Total de vendas e faturamento
        resumo = self.db.fetchone(
            """
            SELECT 
                COUNT(*) as total_vendas,
                SUM(valor_total) as faturamento_total,
                AVG(valor_total) as ticket_medio,
                COUNT(DISTINCT cliente_id) as clientes_unicos
            FROM vendas
            WHERE date(data_venda) BETWEEN ? AND ?
            """,
            (data_inicio.isoformat(), data_fim.isoformat())
        )
        
        # Formas de pagamento
        formas = self.db.read_sql(
            """
            SELECT 
                forma_pagamento,
                COUNT(*) as quantidade,
                SUM(valor_total) as valor_total
            FROM vendas
            WHERE date(data_venda) BETWEEN ? AND ?
            GROUP BY forma_pagamento
            ORDER BY valor_total DESC
            """,
            (data_inicio.isoformat(), data_fim.isoformat())
        )
        
        # Produtos mais vendidos
        produtos = self.db.read_sql(
            """
            SELECT 
                p.id,
                p.nome as produto,
                SUM(i.quantidade) as quantidade_vendida,
                SUM(i.quantidade * i.preco_unitario) as valor_total
            FROM itens_venda i
            JOIN vendas v ON i.venda_id = v.id
            JOIN produtos p ON i.produto_id = p.id
            WHERE date(v.data_venda) BETWEEN ? AND ?
            GROUP BY p.id
            ORDER BY quantidade_vendida DESC
            LIMIT 10
            """,
            (data_inicio.isoformat(), data_fim.isoformat())
        )
        
        return {
            "total_vendas": int(resumo["total_vendas"]) if resumo and resumo["total_vendas"] else 0,
            "faturamento_total": float(resumo["faturamento_total"]) if resumo and resumo["faturamento_total"] else 0,
            "ticket_medio": float(resumo["ticket_medio"]) if resumo and resumo["ticket_medio"] else 0,
            "clientes_unicos": int(resumo["clientes_unicos"]) if resumo and resumo["clientes_unicos"] else 0,
            "formas_pagamento": formas.to_dict('records') if not formas.empty else [],
            "produtos_mais_vendidos": produtos.to_dict('records') if not produtos.empty else []
        }