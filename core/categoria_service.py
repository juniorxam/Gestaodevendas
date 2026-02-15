"""
categoria_service.py - Serviço de categorias de produtos
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from core.auth_service import AuditLog


class CategoriaService:
    """Serviço para gerenciamento de categorias de produtos"""
    
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit

    def listar_categorias(self, apenas_ativas: bool = True) -> List[str]:
        """
        Lista nomes das categorias para seleção
        
        Args:
            apenas_ativas: Se True, lista apenas categorias ativas
            
        Returns:
            Lista de nomes das categorias
        """
        where = "WHERE ativo = 1" if apenas_ativas else ""
        df = self.db.read_sql(
            f"SELECT nome FROM categorias {where} ORDER BY nome"
        )
        if df.empty:
            return []
        return df["nome"].astype(str).tolist()

    def listar_todas(self, incluir_inativas: bool = False) -> pd.DataFrame:
        """
        Lista todas as categorias com detalhes
        
        Args:
            incluir_inativas: Se True, inclui categorias inativas
            
        Returns:
            DataFrame com categorias
        """
        # CORREÇÃO: Usar c.ativo no WHERE para evitar ambiguidade
        where = "" if incluir_inativas else "WHERE c.ativo = 1"
        
        # Incluir contagem de produtos
        return self.db.read_sql(
            f"""
            SELECT 
                c.id,
                c.nome,
                c.descricao,
                c.ativo,
                c.data_cadastro,
                COUNT(p.id) as total_produtos
            FROM categorias c
            LEFT JOIN produtos p ON c.id = p.categoria_id AND p.ativo = 1
            {where}
            GROUP BY c.id
            ORDER BY c.nome
            """
        )

    def cadastrar_categoria(
        self,
        nome: str,
        descricao: str,
        usuario: str
    ) -> Tuple[bool, str]:
        """
        Cadastra uma nova categoria
        
        Args:
            nome: Nome da categoria
            descricao: Descrição
            usuario: Usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            nome = nome.strip().upper()
            if not nome:
                return False, "Nome da categoria é obrigatório"
            
            # Verificar se já existe
            existe = self.db.fetchone(
                "SELECT id FROM categorias WHERE nome = ?",
                (nome,)
            )
            if existe:
                return False, "Categoria já existe"
            
            self.db.execute(
                """
                INSERT INTO categorias (nome, descricao, ativo)
                VALUES (?, ?, 1)
                """,
                (nome, descricao.strip() if descricao else None)
            )
            
            self.audit.registrar(
                usuario,
                "CATEGORIAS",
                "Cadastrou categoria",
                nome
            )
            
            return True, "Categoria cadastrada com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao cadastrar: {str(e)}"

    def atualizar_categoria(
        self,
        categoria_id: int,
        dados: Dict[str, Any],
        usuario: str
    ) -> Tuple[bool, str]:
        """
        Atualiza uma categoria
        
        Args:
            categoria_id: ID da categoria
            dados: Dicionário com novos dados
            usuario: Usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            categoria = self.db.fetchone(
                "SELECT nome FROM categorias WHERE id = ?",
                (categoria_id,)
            )
            if not categoria:
                return False, "Categoria não encontrada"

            campos = []
            params = []
            
            if "nome" in dados and dados["nome"]:
                campos.append("nome = ?")
                params.append(dados["nome"].strip().upper())
            
            if "descricao" in dados:
                campos.append("descricao = ?")
                params.append(dados["descricao"].strip() if dados["descricao"] else None)
            
            if "ativo" in dados:
                campos.append("ativo = ?")
                params.append(1 if dados["ativo"] else 0)

            if not campos:
                return False, "Nenhum dado para atualizar"

            params.append(categoria_id)
            query = f"UPDATE categorias SET {', '.join(campos)} WHERE id = ?"
            
            self.db.execute(query, params)
            
            self.audit.registrar(
                usuario,
                "CATEGORIAS",
                "Atualizou categoria",
                f"ID: {categoria_id} - {categoria['nome']}"
            )
            
            return True, "Categoria atualizada com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao atualizar: {str(e)}"

    def excluir_categoria(self, categoria_id: int, usuario: str) -> Tuple[bool, str]:
        """
        Exclui uma categoria
        
        Args:
            categoria_id: ID da categoria
            usuario: Usuário
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Verificar se há produtos nesta categoria
            produtos = self.db.fetchone(
                "SELECT COUNT(*) as total FROM produtos WHERE categoria_id = ? AND ativo = 1",
                (categoria_id,)
            )
            
            if produtos and produtos["total"] > 0:
                return False, f"Não é possível excluir: categoria possui {produtos['total']} produtos ativos"
            
            categoria = self.db.fetchone(
                "SELECT nome FROM categorias WHERE id = ?",
                (categoria_id,)
            )
            
            self.db.execute(
                "DELETE FROM categorias WHERE id = ?",
                (categoria_id,)
            )
            
            self.audit.registrar(
                usuario,
                "CATEGORIAS",
                "Excluiu categoria",
                f"ID: {categoria_id} - {categoria['nome'] if categoria else 'desconhecida'}"
            )
            
            return True, "Categoria excluída com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao excluir categoria: {str(e)}"