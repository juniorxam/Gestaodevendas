"""
cliente_service.py - Serviço de gerenciamento de clientes
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.auth_service import AuditLog
from core.security import Security, Formatters


class ClienteService:
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit

    def cadastrar_individual(self, dados: Dict[str, Any], usuario_cadastro: str) -> Tuple[bool, str]:
        """
        Cadastra um cliente individual
        """
        try:
            nome = str(dados.get("nome", "")).strip().upper()
            if not nome:
                return False, "Nome é obrigatório"

            cpf_limpo = None
            if dados.get("cpf"):
                cpf_limpo = Security.clean_cpf(dados.get("cpf"))
                if not Security.validar_cpf(cpf_limpo):
                    return False, "CPF inválido"
                
                existe = self.db.fetchone(
                    "SELECT id FROM clientes WHERE cpf = ?",
                    (cpf_limpo,)
                )
                if existe:
                    return False, "CPF já cadastrado"

            self.db.execute(
                """
                INSERT INTO clientes
                (nome, cpf, email, telefone, data_nascimento, endereco, cidade, estado, cep, usuario_cadastro, ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    nome,
                    cpf_limpo,
                    dados.get("email", "").lower().strip() if dados.get("email") else None,
                    dados.get("telefone"),
                    Formatters.parse_date(dados.get("data_nascimento")).isoformat() if Formatters.parse_date(dados.get("data_nascimento")) else None,
                    dados.get("endereco"),
                    dados.get("cidade"),
                    dados.get("estado"),
                    dados.get("cep"),
                    usuario_cadastro,
                ),
            )

            self.audit.registrar(
                usuario_cadastro, 
                "CLIENTES", 
                "Cadastrou cliente", 
                f"{nome} - {cpf_limpo or 'sem CPF'}"
            )
            return True, "Cliente cadastrado com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao cadastrar: {str(e)}"

    def buscar_clientes(self, termo: str, limit: int = 10, incluir_inativos: bool = False) -> pd.DataFrame:
        """
        Busca clientes por nome, CPF ou email
        """
        termo = (termo or "").strip()
        if not termo:
            return pd.DataFrame()
            
        like = f"%{termo}%"
        cpf_limpo = Security.clean_cpf(termo) if len(termo) > 3 else None
        
        query = """
            SELECT *
            FROM clientes
            WHERE (nome LIKE ? OR email LIKE ? OR telefone LIKE ?)
        """
        params = [like, like, like]
        
        if not incluir_inativos:
            query += " AND ativo = 1"
        
        if cpf_limpo and len(cpf_limpo) > 3:
            query += " OR cpf LIKE ?"
            params.append(f"%{cpf_limpo}%")
        
        query += " ORDER BY nome LIMIT ?"
        params.append(int(limit))
        
        return self.db.read_sql(query, params)

    def obter_cliente_por_id(self, cliente_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém um cliente pelo ID
        """
        row = self.db.fetchone(
            "SELECT * FROM clientes WHERE id = ?",
            (cliente_id,)
        )
        return dict(row) if row else None

    def obter_cliente_por_cpf(self, cpf: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um cliente pelo CPF
        """
        cpf_limpo = Security.clean_cpf(cpf)
        if not cpf_limpo:
            return None
            
        row = self.db.fetchone(
            "SELECT * FROM clientes WHERE cpf = ? AND ativo = 1",
            (cpf_limpo,)
        )
        return dict(row) if row else None

    def atualizar_cliente(self, cliente_id: int, dados: Dict[str, Any], usuario: str) -> Tuple[bool, str]:
        """
        Atualiza dados de um cliente
        """
        try:
            cliente = self.obter_cliente_por_id(cliente_id)
            if not cliente:
                return False, "Cliente não encontrado"

            campos = []
            params = []
            
            mapeamento = {
                "nome": "nome",
                "email": "email",
                "telefone": "telefone",
                "data_nascimento": "data_nascimento",
                "endereco": "endereco",
                "cidade": "cidade",
                "estado": "estado",
                "cep": "cep",
                "ativo": "ativo"
            }
            
            for campo_db, campo_dados in mapeamento.items():
                if campo_dados in dados and dados[campo_dados] is not None:
                    valor = dados[campo_dados]
                    if campo_db == "nome":
                        valor = str(valor).strip().upper()
                    elif campo_db == "email":
                        valor = str(valor).lower().strip()
                    elif campo_db == "data_nascimento":
                        valor = Formatters.parse_date(valor).isoformat() if Formatters.parse_date(valor) else None
                    elif campo_db == "ativo":
                        valor = 1 if valor else 0
                    
                    campos.append(f"{campo_db} = ?")
                    params.append(valor)

            if not campos:
                return False, "Nenhum dado para atualizar"

            params.append(cliente_id)
            query = f"UPDATE clientes SET {', '.join(campos)} WHERE id = ?"
            
            self.db.execute(query, params)
            
            self.audit.registrar(
                usuario,
                "CLIENTES",
                "Atualizou cliente",
                f"ID: {cliente_id} - {cliente['nome']}"
            )
            
            return True, "Cliente atualizado com sucesso!"
            
        except Exception as e:
            return False, f"Erro ao atualizar: {str(e)}"

    def excluir_cliente(self, cliente_id: int, usuario: str) -> Tuple[bool, str]:
        """
        Exclui logicamente um cliente (marca como inativo)
        """
        try:
            cliente = self.obter_cliente_por_id(cliente_id)
            if not cliente:
                return False, "Cliente não encontrado."

            vendas = self.db.fetchone(
                "SELECT COUNT(*) as total FROM vendas WHERE cliente_id = ?",
                (cliente_id,)
            )
            if vendas and vendas["total"] > 0:
                return False, f"Não é possível excluir: cliente possui {vendas['total']} venda(s) vinculada(s)."

            self.db.execute(
                "UPDATE clientes SET ativo = 0 WHERE id = ?",
                (cliente_id,)
            )

            self.audit.registrar(
                usuario,
                "CLIENTES",
                "Excluiu cliente",
                f"ID: {cliente_id} - {cliente['nome']}"
            )

            return True, "Cliente excluído com sucesso!"

        except Exception as e:
            return False, f"Erro ao excluir cliente: {str(e)}"

    @staticmethod
    def detectar_colunas_arquivo(df: pd.DataFrame) -> Dict[str, str]:
        """
        Detecta automaticamente as colunas em um arquivo de importação
        """
        m: Dict[str, str] = {}
        for col in df.columns:
            col_upper = str(col).upper().strip()

            if any(term in col_upper for term in ["NOME", "CLIENTE"]):
                m["NOME"] = col
            elif "CPF" in col_upper:
                m["CPF"] = col
            elif any(term in col_upper for term in ["EMAIL", "E-MAIL"]):
                m["EMAIL"] = col
            elif any(term in col_upper for term in ["TELEFONE", "FONE", "CELULAR", "TEL"]):
                m["TELEFONE"] = col
            elif any(term in col_upper for term in ["NASCIMENTO", "NASC", "DATANASC"]):
                m["DATA_NASCIMENTO"] = col
            elif "ENDERECO" in col_upper or "ENDEREÇO" in col_upper:
                m["ENDERECO"] = col
            elif "CIDADE" in col_upper:
                m["CIDADE"] = col
            elif "ESTADO" in col_upper or "UF" in col_upper:
                m["ESTADO"] = col
            elif "CEP" in col_upper:
                m["CEP"] = col

        return m

    def importar_em_lote(
        self,
        df_raw: pd.DataFrame,
        mapeamento_final: Dict[str, str],
        acao_duplicados: str,
        criar_novos: bool,
        atualizar_vazios: bool,
        notificar_diferencas: bool,
        usuario: str,
    ) -> Tuple[Dict[str, int], List[str], List[Dict[str, Any]]]:
        """
        Importa clientes em lote a partir de um DataFrame
        """
        stats = {"inseridos": 0, "atualizados": 0, "ignorados": 0, "erros": 0, "diferencas_detectadas": 0}
        erros: List[str] = []
        diferencas: List[Dict[str, Any]] = []

        required = ["NOME"]
        for r in required:
            if not mapeamento_final.get(r):
                raise ValueError(f"Campo obrigatório não mapeado: {r}")

        df = df_raw.copy()

        staging_cols: Dict[str, str] = {k: v for k, v in mapeamento_final.items() if v}
        stg = pd.DataFrame({k: df[v] for k, v in staging_cols.items()}).copy()

        for col in stg.columns:
            stg[col] = stg[col].astype(str).str.strip()

        mask_min = stg["NOME"].notna() & (stg["NOME"].str.upper().isin(["NAN", "NULL", "NONE"]) == False) & (stg["NOME"] != "")
        stg = stg[mask_min].copy()
        
        if stg.empty:
            return stats, ["Nenhuma linha com dados mínimos válidos."], diferencas

        if "CPF" in stg.columns:
            stg["CPF_LIMPO"] = stg["CPF"].map(Security.clean_cpf)
            stg["CPF_VALIDO"] = stg["CPF_LIMPO"].map(Security.validar_cpf)

            invalid_rows = stg[~stg["CPF_VALIDO"]]
            for idx, r in invalid_rows.head(200).iterrows():
                erros.append(f"Linha ~{int(idx)+2}: CPF inválido {r.get('CPF')}")
            stats["erros"] += int((~stg["CPF_VALIDO"]).sum())

        stg["NOME"] = stg["NOME"].astype(str).str.upper()

        existentes = self.db.read_sql(
            "SELECT id, cpf, nome, email, telefone, endereco, cidade, estado, cep, ativo FROM clientes"
        )
        if existentes.empty:
            existentes = pd.DataFrame(columns=["id", "cpf"])

        if "CPF_LIMPO" in stg.columns:
            stg = stg.merge(
                existentes[existentes['cpf'].notna()], 
                left_on="CPF_LIMPO", 
                right_on="cpf", 
                how="left", 
                suffixes=("", "_EX")
            )
            stg["EXISTE"] = stg["id"].notna()
        else:
            stg["EXISTE"] = False

        campos_opcionais = {
            "EMAIL": "email",
            "TELEFONE": "telefone",
            "DATA_NASCIMENTO": "data_nascimento",
            "ENDERECO": "endereco",
            "CIDADE": "cidade",
            "ESTADO": "estado",
            "CEP": "cep",
        }

        update_rows = stg[stg["EXISTE"]].copy()
        updates: List[Tuple[str, List[Any]]] = []
        updated_count = 0
        ignored_count = 0

        if not update_rows.empty:
            if acao_duplicados == "Manter existente e ignorar novo":
                ignored_count += len(update_rows)
            else:
                for _, r in update_rows.iterrows():
                    data_to_set: Dict[str, Any] = {}
                    
                    for src, dbcol in campos_opcionais.items():
                        if src not in r:
                            continue
                        
                        new_val = r.get(src)
                        if pd.isna(new_val) or new_val is None:
                            continue
                        
                        if acao_duplicados == "Sobrescrever todos os dados":
                            if dbcol == "data_nascimento":
                                dt = Formatters.parse_date(new_val)
                                if dt:
                                    data_to_set[dbcol] = dt.isoformat()
                            else:
                                data_to_set[dbcol] = str(new_val).strip()
                            continue

                        old_val = r.get(f"{dbcol}_EX")
                        if old_val is None or (atualizar_vazios and (pd.isna(old_val) or old_val == "")):
                            if dbcol == "data_nascimento":
                                dt = Formatters.parse_date(new_val)
                                if dt:
                                    data_to_set[dbcol] = dt.isoformat()
                            else:
                                data_to_set[dbcol] = str(new_val).strip()

                    if not data_to_set:
                        ignored_count += 1
                        continue

                    set_clause = ", ".join([f"{k} = ?" for k in data_to_set.keys()])
                    params = list(data_to_set.values())
                    params.append(int(r["id"]))
                    
                    q = f"UPDATE clientes SET {set_clause} WHERE id = ?"
                    updates.append((q, params))
                    updated_count += 1

        insert_rows = stg[~stg["EXISTE"]].copy()
        inserts_params: List[Tuple[Any, ...]] = []

        if not insert_rows.empty:
            if not criar_novos:
                ignored_count += len(insert_rows)
            else:
                for _, r in insert_rows.iterrows():
                    nome = str(r.get("NOME", "")).upper()
                    cpf = str(r.get("CPF_LIMPO")) if "CPF_LIMPO" in r and r.get("CPF_LIMPO") else None
                    email = r.get("EMAIL") if "EMAIL" in r else None
                    telefone = r.get("TELEFONE") if "TELEFONE" in r else None
                    
                    data_nascimento = None
                    if "DATA_NASCIMENTO" in r:
                        dt = Formatters.parse_date(r.get("DATA_NASCIMENTO"))
                        if dt:
                            data_nascimento = dt.isoformat()
                    
                    endereco = r.get("ENDERECO") if "ENDERECO" in r else None
                    cidade = r.get("CIDADE") if "CIDADE" in r else None
                    estado = r.get("ESTADO") if "ESTADO" in r else None
                    cep = r.get("CEP") if "CEP" in r else None

                    inserts_params.append((
                        nome,
                        cpf,
                        email,
                        telefone,
                        data_nascimento,
                        endereco,
                        cidade,
                        estado,
                        cep,
                        usuario,
                    ))

        if updates:
            with self.db.connect() as conn:
                for q, p in updates:
                    try:
                        conn.execute(q, p)
                    except Exception as e:
                        erros.append(f"Erro ao atualizar cliente {p[-1]}: {str(e)}")
                        stats["erros"] += 1
        
        if inserts_params:
            try:
                self.db.executemany(
                    """
                    INSERT INTO clientes
                    (nome, cpf, email, telefone, data_nascimento, endereco, cidade, estado, cep, usuario_cadastro, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    inserts_params,
                )
                stats["inseridos"] += len(inserts_params)
            except Exception as e:
                erros.append(f"Erro em lote, tentando linha por linha: {str(e)}")
                stats["inseridos"] = 0
                with self.db.connect() as conn:
                    for params in inserts_params:
                        try:
                            conn.execute(
                                """
                                INSERT INTO clientes
                                (nome, cpf, email, telefone, data_nascimento, endereco, cidade, estado, cep, usuario_cadastro, ativo)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                                """,
                                params,
                            )
                            stats["inseridos"] += 1
                        except Exception as row_error:
                            erros.append(f"Erro ao inserir {params[0]}: {str(row_error)}")
                            stats["erros"] += 1

        stats["atualizados"] += updated_count
        stats["ignorados"] += ignored_count

        self.audit.registrar(
            usuario,
            "CLIENTES",
            "Importação em massa",
            f"{stats['inseridos']} novos, {stats['atualizados']} atualizados, {stats['erros']} erros",
        )

        return stats, erros, diferencas

    def get_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de clientes
        """
        total = self.db.fetchone("SELECT COUNT(*) as total FROM clientes")
        ativos = self.db.fetchone("SELECT COUNT(*) as total FROM clientes WHERE ativo = 1")
        com_cpf = self.db.fetchone("SELECT COUNT(*) as total FROM clientes WHERE cpf IS NOT NULL")
        com_email = self.db.fetchone("SELECT COUNT(*) as total FROM clientes WHERE email IS NOT NULL")
        
        return {
            "total_clientes": int(total["total"]) if total else 0,
            "clientes_ativos": int(ativos["total"]) if ativos else 0,
            "clientes_com_cpf": int(com_cpf["total"]) if com_cpf else 0,
            "clientes_com_email": int(com_email["total"]) if com_email else 0,
        }
