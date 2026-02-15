"""
produto_service.py - Serviço de gerenciamento de produtos (CORRIGIDO)
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from core.auth_service import AuditLog
from core.security import Formatters


class ProdutoService:
    """Serviço para gerenciamento de produtos"""
    
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit

    def listar_produtos_ativos(self) -> List[str]:
        """Lista nomes de produtos ativos para seleção"""
        df = self.db.read_sql(
            "SELECT nome FROM produtos WHERE ativo = 1 ORDER BY nome"
        )
        if df.empty:
            return []
        return df["nome"].astype(str).tolist()

    def listar_todos_produtos(self, incluir_inativos: bool = False) -> pd.DataFrame:
        """
        Lista todos os produtos com informações completas
        
        Args:
            incluir_inativos: Se True, inclui produtos inativos
            
        Returns:
            DataFrame com produtos
        """
        where = "" if incluir_inativos else "WHERE p.ativo = 1"
        
        query = f"""
            SELECT 
                p.id,
                p.codigo_barras,
                p.nome,
                p.descricao,
                c.nome as categoria,
                p.fabricante,
                p.preco_custo,
                p.preco_venda,
                p.quantidade_estoque,
                p.estoque_minimo,
                p.ativo,
                p.data_cadastro,
                p.usuario_cadastro
            FROM produtos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            {where}
            ORDER BY p.nome
        """
        return self.db.read_sql(query)

    def buscar_produto_por_codigo(self, codigo_barras: str) -> Optional[Dict[str, Any]]:
        """
        Busca um produto pelo código de barras
        
        Args:
            codigo_barras: Código de barras do produto
            
        Returns:
            Dicionário com dados do produto ou None
        """
        if not codigo_barras:
            return None
            
        row = self.db.fetchone(
            """
            SELECT 
                p.*,
                c.nome as categoria_nome
            FROM produtos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.codigo_barras = ? AND p.ativo = 1
            """,
            (codigo_barras.strip(),)
        )
        return dict(row) if row else None

    def buscar_produtos(self, termo: str, limit: int = 20) -> pd.DataFrame:
        """
        Busca produtos por nome, código de barras ou descrição
        
        Args:
            termo: Termo de busca
            limit: Limite de resultados
            
        Returns:
            DataFrame com produtos encontrados
        """
        termo = (termo or "").strip()
        if not termo:
            return pd.DataFrame()
            
        like = f"%{termo}%"
        
        return self.db.read_sql(
            """
            SELECT 
                p.id,
                p.codigo_barras,
                p.nome,
                p.descricao,
                c.nome as categoria,
                p.preco_venda,
                p.quantidade_estoque,
                p.estoque_minimo
            FROM produtos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE (p.nome LIKE ? 
               OR p.codigo_barras LIKE ? 
               OR p.descricao LIKE ?)
               AND p.ativo = 1
            ORDER BY p.nome
            LIMIT ?
            """,
            (like, like, like, int(limit))
        )

    def cadastrar_produto(
        self,
        dados: Dict[str, Any],
        usuario: str
    ) -> Tuple[bool, str]:
        """
        Cadastra um novo produto
        
        Args:
            dados: Dicionário com dados do produto
            usuario: Login do usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Validar campos obrigatórios
            nome = str(dados.get("nome", "")).strip().upper()
            if not nome:
                return False, "Nome do produto é obrigatório"

            preco_venda = float(dados.get("preco_venda", 0))
            if preco_venda <= 0:
                return False, "Preço de venda deve ser maior que zero"

            # Validar código de barras único se informado
            codigo_barras = dados.get("codigo_barras", "").strip()
            if codigo_barras:
                existe = self.db.fetchone(
                    "SELECT id FROM produtos WHERE codigo_barras = ?",
                    (codigo_barras,)
                )
                if existe:
                    return False, "Código de barras já cadastrado"

            # Obter categoria_id
            categoria_id = None
            if dados.get("categoria"):
                # Buscar categoria pelo nome
                cat_row = self.db.fetchone(
                    "SELECT id FROM categorias WHERE nome = ?",
                    (dados["categoria"],)
                )
                if cat_row:
                    categoria_id = cat_row["id"]
                else:
                    # Criar categoria automaticamente se não existir
                    from core.categoria_service import CategoriaService
                    cat_service = CategoriaService(self.db, self.audit)
                    sucesso, msg = cat_service.cadastrar_categoria(
                        dados["categoria"], 
                        f"Categoria criada automaticamente para {nome}",
                        usuario
                    )
                    if sucesso:
                        cat_row = self.db.fetchone(
                            "SELECT id FROM categorias WHERE nome = ?",
                            (dados["categoria"],)
                        )
                        categoria_id = cat_row["id"] if cat_row else None

            # Inserir produto
            self.db.execute(
                """
                INSERT INTO produtos
                (codigo_barras, nome, descricao, categoria_id, fabricante,
                 preco_custo, preco_venda, quantidade_estoque, estoque_minimo,
                 ativo, usuario_cadastro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    codigo_barras or None,
                    nome,
                    dados.get("descricao"),
                    categoria_id,
                    dados.get("fabricante"),
                    float(dados.get("preco_custo", 0)) if dados.get("preco_custo") else None,
                    preco_venda,
                    int(dados.get("quantidade_estoque", 0)),
                    int(dados.get("estoque_minimo", 5)),
                    1 if dados.get("ativo", True) else 0,
                    usuario,
                )
            )

            self.audit.registrar(
                usuario,
                "PRODUTOS",
                "Cadastrou produto",
                f"{nome} - {codigo_barras or 'sem código'}"
            )
            
            return True, "Produto cadastrado com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao cadastrar: {str(e)}"

    def atualizar_produto(
        self,
        produto_id: int,
        dados: Dict[str, Any],
        usuario: str
    ) -> Tuple[bool, str]:
        """
        Atualiza dados de um produto
        
        Args:
            produto_id: ID do produto
            dados: Dicionário com novos dados
            usuario: Login do usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Verificar se produto existe
            produto = self.db.fetchone(
                "SELECT nome FROM produtos WHERE id = ?",
                (produto_id,)
            )
            if not produto:
                return False, "Produto não encontrado"

            # Construir query dinâmica
            campos = []
            params = []
            
            mapeamento = {
                "codigo_barras": "codigo_barras",
                "nome": "nome",
                "descricao": "descricao",
                "categoria_id": "categoria_id",
                "fabricante": "fabricante",
                "preco_custo": "preco_custo",
                "preco_venda": "preco_venda",
                "quantidade_estoque": "quantidade_estoque",
                "estoque_minimo": "estoque_minimo",
                "ativo": "ativo",
            }
            
            for campo_db, campo_dados in mapeamento.items():
                if campo_dados in dados:
                    valor = dados[campo_dados]
                    if valor is not None:
                        if campo_db == "nome":
                            valor = str(valor).strip().upper()
                        elif campo_db in ["preco_custo", "preco_venda"]:
                            valor = float(valor)
                        elif campo_db in ["quantidade_estoque", "estoque_minimo"]:
                            valor = int(valor)
                        elif campo_db == "ativo":
                            valor = 1 if valor else 0
                    
                    campos.append(f"{campo_db} = ?")
                    params.append(valor)

            if not campos:
                return False, "Nenhum dado para atualizar"

            params.append(produto_id)
            query = f"UPDATE produtos SET {', '.join(campos)} WHERE id = ?"
            
            self.db.execute(query, params)
            
            self.audit.registrar(
                usuario,
                "PRODUTOS",
                "Atualizou produto",
                f"ID: {produto_id} - {produto['nome']}"
            )
            
            return True, "Produto atualizado com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao atualizar: {str(e)}"

    def verificar_estoque(self, produto_id: int, quantidade: int = 1) -> Tuple[bool, int]:
        """
        Verifica se há estoque disponível para um produto
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade desejada
            
        Returns:
            Tuple[bool, int]: (disponível, estoque_atual)
        """
        row = self.db.fetchone(
            "SELECT quantidade_estoque FROM produtos WHERE id = ? AND ativo = 1",
            (produto_id,)
        )
        
        if not row:
            return False, 0
            
        estoque = int(row["quantidade_estoque"])
        return estoque >= quantidade, estoque

    def atualizar_estoque(
        self,
        produto_id: int,
        quantidade: int,
        operacao: str,
        usuario: str,
        observacao: str = ""
    ) -> Tuple[bool, str]:
        """
        Atualiza o estoque de um produto
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade (positiva para entrada, negativa para saída)
            operacao: Tipo de operação ('ENTRADA', 'SAIDA', 'AJUSTE')
            usuario: Login do usuário
            observacao: Observação sobre a movimentação
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            with self.db.connect() as conn:
                # Obter estoque atual com lock
                row = conn.execute(
                    "SELECT nome, quantidade_estoque FROM produtos WHERE id = ?",
                    (produto_id,)
                ).fetchone()
                
                if not row:
                    return False, "Produto não encontrado"
                
                estoque_atual = int(row["quantidade_estoque"])
                novo_estoque = estoque_atual + quantidade
                
                if novo_estoque < 0:
                    return False, "Estoque não pode ficar negativo"
                
                # Atualizar estoque
                conn.execute(
                    "UPDATE produtos SET quantidade_estoque = ? WHERE id = ?",
                    (novo_estoque, produto_id)
                )
            
            # Registrar no audit
            self.audit.registrar(
                usuario,
                "ESTOQUE",
                f"Movimentação de estoque - {operacao}",
                f"Produto: {row['nome']} | Qtd: {abs(quantidade)} | Novo estoque: {novo_estoque} | Obs: {observacao}"
            )
            
            return True, f"Estoque atualizado com sucesso. Novo estoque: {novo_estoque}"
            
        except Exception as e:
            return False, f"Erro ao atualizar estoque: {str(e)}"

    def get_produtos_estoque_baixo(self, limite: int = 50) -> pd.DataFrame:
        """
        Retorna produtos com estoque abaixo do mínimo
        
        Args:
            limite: Limite de resultados
            
        Returns:
            DataFrame com produtos em estoque baixo
        """
        return self.db.read_sql(
            """
            SELECT 
                p.id,
                p.codigo_barras,
                p.nome,
                c.nome as categoria,
                p.quantidade_estoque,
                p.estoque_minimo,
                (p.estoque_minimo - p.quantidade_estoque) as quantidade_faltante
            FROM produtos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.quantidade_estoque <= p.estoque_minimo
              AND p.ativo = 1
            ORDER BY (p.estoque_minimo - p.quantidade_estoque) DESC
            LIMIT ?
            """,
            (limite,)
        )

    def get_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de produtos
        
        Returns:
            Dicionário com estatísticas
        """
        total = self.db.fetchone("SELECT COUNT(*) as total FROM produtos WHERE ativo = 1")
        total_inativos = self.db.fetchone("SELECT COUNT(*) as total FROM produtos WHERE ativo = 0")
        estoque_baixo = self.db.fetchone(
            "SELECT COUNT(*) as total FROM produtos WHERE quantidade_estoque <= estoque_minimo AND ativo = 1"
        )
        
        valor_estoque = self.db.fetchone(
            "SELECT SUM(quantidade_estoque * preco_custo) as total FROM produtos WHERE ativo = 1"
        )
        
        return {
            "total_produtos": int(total["total"]) if total else 0,
            "total_inativos": int(total_inativos["total"]) if total_inativos else 0,
            "estoque_baixo": int(estoque_baixo["total"]) if estoque_baixo else 0,
            "valor_estoque": float(valor_estoque["total"]) if valor_estoque and valor_estoque["total"] else 0,
        }