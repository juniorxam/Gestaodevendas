"""
relatorio_service.py - Serviços de relatórios e dashboards
"""

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from fpdf import FPDF

from core.security import Formatters, Security


class RelatorioService:
    """Serviço para geração de relatórios e dashboards"""
    
    def __init__(self, db: "Database") -> None:
        self.db = db

    def get_metricas_gerais(self) -> Dict[str, Any]:
        """
        Retorna métricas gerais para o dashboard
        
        Returns:
            Dicionário com métricas
        """
        metricas: Dict[str, Any] = {}
        
        # Total de clientes
        total_clientes = self.db.fetchone("SELECT COUNT(*) AS c FROM clientes")
        metricas["total_clientes"] = int(total_clientes["c"]) if total_clientes else 0

        # Total de vendas (hoje)
        hoje = date.today().isoformat()
        vendas_hoje = self.db.fetchone(
            "SELECT COUNT(*) AS c, COALESCE(SUM(valor_total), 0) AS total FROM vendas WHERE date(data_venda) = ?",
            (hoje,)
        )
        metricas["vendas_hoje"] = int(vendas_hoje["c"]) if vendas_hoje else 0
        metricas["faturamento_hoje"] = float(vendas_hoje["total"]) if vendas_hoje and vendas_hoje["total"] else 0.0

        # Total de produtos
        total_produtos = self.db.fetchone("SELECT COUNT(*) AS c FROM produtos WHERE ativo = 1")
        metricas["total_produtos"] = int(total_produtos["c"]) if total_produtos else 0

        # Produtos com estoque baixo
        estoque_baixo = self.db.fetchone(
            "SELECT COUNT(*) AS c FROM produtos WHERE quantidade_estoque <= estoque_minimo AND ativo = 1"
        )
        metricas["estoque_baixo"] = int(estoque_baixo["c"]) if estoque_baixo else 0

        # Ticket médio (últimos 30 dias)
        trinta_dias_atras = (date.today() - timedelta(days=30)).isoformat()
        ticket = self.db.fetchone(
            """
            SELECT AVG(valor_total) AS media 
            FROM vendas 
            WHERE date(data_venda) >= ?
            """,
            (trinta_dias_atras,)
        )
        metricas["ticket_medio"] = float(ticket["media"]) if ticket and ticket["media"] else 0.0

        return metricas

    def grafico_vendas_ultimos_30_dias(self) -> Optional[go.Figure]:
        """
        Gera gráfico de vendas dos últimos 30 dias
        
        Returns:
            Figura Plotly ou None se não houver dados
        """
        trinta_dias_atras = (date.today() - timedelta(days=30)).isoformat()
        
        df = self.db.read_sql(
            """
            SELECT 
                date(data_venda) as data,
                COUNT(*) as total_vendas,
                SUM(valor_total) as faturamento
            FROM vendas
            WHERE date(data_venda) >= ?
            GROUP BY date(data_venda)
            ORDER BY data
            """,
            (trinta_dias_atras,)
        )
        
        if df.empty:
            return None

        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name="Total de Vendas",
            x=df["data"],
            y=df["total_vendas"],
            yaxis="y",
            marker_color="#3b82f6"
        ))
        
        fig.add_trace(go.Scatter(
            name="Faturamento (R$)",
            x=df["data"],
            y=df["faturamento"],
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#10b981", width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title="Vendas e Faturamento - Últimos 30 Dias",
            xaxis=dict(title="Data"),
            yaxis=dict(title="Quantidade de Vendas", side="left"),
            yaxis2=dict(
                title="Faturamento (R$)",
                overlaying="y",
                side="right",
                tickprefix="R$ "
            ),
            hovermode="x unified",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        return fig

    def grafico_produtos_mais_vendidos(self, limite: int = 10) -> Optional[go.Figure]:
        """
        Gera gráfico de produtos mais vendidos
        
        Args:
            limite: Número de produtos a mostrar
            
        Returns:
            Figura Plotly ou None se não houver dados
        """
        df = self.db.read_sql(
            """
            SELECT 
                p.nome as produto,
                SUM(i.quantidade) as quantidade_vendida,
                SUM(i.quantidade * i.preco_unitario) as faturamento
            FROM itens_venda i
            JOIN produtos p ON i.produto_id = p.id
            GROUP BY p.id
            ORDER BY quantidade_vendida DESC
            LIMIT ?
            """,
            (limite,)
        )
        
        if df.empty:
            return None

        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df["quantidade_vendida"],
            y=df["produto"],
            orientation="h",
            marker=dict(
                color=df["faturamento"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Faturamento (R$)", tickprefix="R$ ")
            ),
            text=df["quantidade_vendida"].apply(lambda x: f"{x} unid"),
            textposition="outside"
        ))
        
        fig.update_layout(
            title=f"Top {limite} Produtos Mais Vendidos",
            xaxis=dict(title="Quantidade Vendida"),
            yaxis=dict(title="", autorange="reversed"),
            height=400,
            margin=dict(l=150)
        )
        
        return fig

    def grafico_vendas_por_forma_pagamento(self) -> Optional[go.Figure]:
        """
        Gera gráfico de vendas por forma de pagamento
        
        Returns:
            Figura Plotly ou None se não houver dados
        """
        df = self.db.read_sql(
            """
            SELECT 
                forma_pagamento,
                COUNT(*) as quantidade,
                SUM(valor_total) as valor_total
            FROM vendas
            WHERE forma_pagamento IS NOT NULL
            GROUP BY forma_pagamento
            ORDER BY valor_total DESC
            """
        )
        
        if df.empty:
            return None

        fig = px.pie(
            df,
            values="valor_total",
            names="forma_pagamento",
            title="Vendas por Forma de Pagamento",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Valor: R$ %{value:,.2f}<br>Percentual: %{percent}"
        )
        
        fig.update_layout(height=400)
        
        return fig

    def relatorio_vendas_periodo(
        self,
        data_inicio: date,
        data_fim: date,
        agrupar_por: str = "dia"
    ) -> pd.DataFrame:
        """
        Gera relatório detalhado de vendas por período
        
        Args:
            data_inicio: Data inicial
            data_fim: Data final
            agrupar_por: 'dia', 'semana', 'mes'
            
        Returns:
            DataFrame com vendas agregadas
        """
        group_by = {
            "dia": "date(v.data_venda)",
            "semana": "strftime('%Y-%W', v.data_venda)",
            "mes": "strftime('%Y-%m', v.data_venda)"
        }.get(agrupar_por, "date(v.data_venda)")
        
        df = self.db.read_sql(
            f"""
            SELECT 
                {group_by} as periodo,
                COUNT(*) as total_vendas,
                SUM(v.valor_total) as faturamento,
                AVG(v.valor_total) as ticket_medio,
                COUNT(DISTINCT v.cliente_id) as clientes_unicos,
                COUNT(i.id) as total_itens_vendidos
            FROM vendas v
            LEFT JOIN itens_venda i ON v.id = i.venda_id
            WHERE date(v.data_venda) BETWEEN ? AND ?
            GROUP BY periodo
            ORDER BY periodo
            """,
            (data_inicio.isoformat(), data_fim.isoformat())
        )
        
        return df

    def relatorio_clientes_top(self, limite: int = 20) -> pd.DataFrame:
        """
        Gera relatório dos melhores clientes
        
        Args:
            limite: Número de clientes a mostrar
            
        Returns:
            DataFrame com top clientes
        """
        return self.db.read_sql(
            """
            SELECT 
                c.id,
                c.nome,
                c.cpf,
                c.telefone,
                c.email,
                COUNT(v.id) as total_compras,
                SUM(v.valor_total) as total_gasto,
                AVG(v.valor_total) as ticket_medio,
                MAX(v.data_venda) as ultima_compra,
                MIN(v.data_venda) as primeira_compra
            FROM clientes c
            JOIN vendas v ON c.id = v.cliente_id
            GROUP BY c.id
            ORDER BY total_gasto DESC
            LIMIT ?
            """,
            (limite,)
        )

    def relatorio_estoque_completo(self) -> pd.DataFrame:
        """
        Gera relatório completo da situação do estoque
        
        Returns:
            DataFrame com análise do estoque
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
                p.preco_custo,
                p.preco_venda,
                (p.quantidade_estoque * p.preco_custo) as valor_estoque_custo,
                (p.quantidade_estoque * p.preco_venda) as valor_estoque_venda,
                CASE 
                    WHEN p.quantidade_estoque <= 0 THEN 'SEM ESTOQUE'
                    WHEN p.quantidade_estoque <= p.estoque_minimo THEN 'ESTOQUE BAIXO'
                    ELSE 'NORMAL'
                END as situacao,
                (SELECT COUNT(*) FROM itens_venda i WHERE i.produto_id = p.id) as total_vendido
            FROM produtos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.ativo = 1
            ORDER BY situacao, p.nome
            """
        )

    def relatorio_produtividade_vendedores(
        self,
        data_inicio: date,
        data_fim: date
    ) -> pd.DataFrame:
        """
        Gera relatório de produtividade por vendedor
        
        Args:
            data_inicio: Data inicial
            data_fim: Data final
            
        Returns:
            DataFrame com métricas por vendedor
        """
        return self.db.read_sql(
            """
            SELECT 
                u.nome as vendedor,
                u.login,
                COUNT(v.id) as total_vendas,
                SUM(v.valor_total) as valor_total_vendido,
                AVG(v.valor_total) as ticket_medio,
                COUNT(DISTINCT v.cliente_id) as clientes_atendidos,
                COUNT(i.id) as itens_vendidos,
                ROUND(AVG(CAST((julianday(v.data_venda) - julianday(?)) * 24 AS REAL)), 1) as media_horas_venda
            FROM usuarios u
            LEFT JOIN vendas v ON u.nome = v.usuario_registro 
                AND date(v.data_venda) BETWEEN ? AND ?
            LEFT JOIN itens_venda i ON v.id = i.venda_id
            WHERE u.ativo = 1
            GROUP BY u.id
            ORDER BY valor_total_vendido DESC
            """,
            (data_inicio.isoformat(), data_inicio.isoformat(), data_fim.isoformat())
        )


class RelatorioPDFService:
    """Serviço para geração de relatórios em PDF"""
    
    @staticmethod
    def gerar_cabecalho(pdf: FPDF, titulo: str, logo_path: str = ""):
        """Gera cabeçalho padrão para PDFs"""
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, 10, 8, 20)
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "ELECTROGEST", 0, 1, "C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, titulo, 0, 1, "C")
        pdf.ln(5)

    @staticmethod
    def gerar_rodape(pdf: FPDF):
        """Gera rodapé padrão para PDFs"""
        pdf.set_y(-30)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 5, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, "R")
        pdf.cell(0, 5, "Documento gerado eletronicamente pelo sistema ElectroGest.", 0, 1, "C")

    @staticmethod
    def gerar_relatorio_vendas_pdf(
        logo_path: str,
        dados: Dict[str, Any],
        periodo: str
    ) -> bytes:
        """
        Gera relatório de vendas em PDF
        
        Args:
            logo_path: Caminho do logo
            dados: Dicionário com dados do relatório
            periodo: Descrição do período
            
        Returns:
            Bytes do PDF gerado
        """
        pdf = FPDF()
        pdf.add_page()
        
        # Cabeçalho
        RelatorioPDFService.gerar_cabecalho(pdf, "Relatório de Vendas", logo_path)
        
        # Período
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, f"Período: {periodo}", 0, 1, "L")
        pdf.ln(5)
        
        # Métricas
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 7, "Métricas Gerais", 0, 1, "L", 1)
        pdf.ln(2)
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(60, 6, "Total de Vendas:", 0, 0)
        pdf.cell(0, 6, str(dados.get("total_vendas", 0)), 0, 1)
        
        pdf.cell(60, 6, "Faturamento Total:", 0, 0)
        pdf.cell(0, 6, f"R$ {dados.get('faturamento_total', 0):,.2f}", 0, 1)
        
        pdf.cell(60, 6, "Ticket Médio:", 0, 0)
        pdf.cell(0, 6, f"R$ {dados.get('ticket_medio', 0):,.2f}", 0, 1)
        
        pdf.cell(60, 6, "Clientes Atendidos:", 0, 0)
        pdf.cell(0, 6, str(dados.get('clientes_unicos', 0)), 0, 1)
        pdf.ln(5)
        
        # Formas de pagamento
        if dados.get("formas_pagamento"):
            pdf.set_font("Arial", "B", 12)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 7, "Formas de Pagamento", 0, 1, "L", 1)
            pdf.ln(2)
            
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(70, 6, "Forma", 1, 0, "C", 1)
            pdf.cell(40, 6, "Quantidade", 1, 0, "C", 1)
            pdf.cell(70, 6, "Valor Total", 1, 1, "C", 1)
            
            pdf.set_font("Arial", "", 9)
            for forma in dados["formas_pagamento"][:10]:
                pdf.cell(70, 6, forma.get("forma_pagamento", ""), 1)
                pdf.cell(40, 6, str(forma.get("quantidade", 0)), 1, 0, "C")
                pdf.cell(70, 6, f"R$ {forma.get('valor_total', 0):,.2f}", 1, 1, "R")
        
        # Produtos mais vendidos
        if dados.get("produtos_mais_vendidos"):
            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 7, "Produtos Mais Vendidos", 0, 1, "L", 1)
            pdf.ln(2)
            
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(80, 6, "Produto", 1, 0, "C", 1)
            pdf.cell(40, 6, "Quantidade", 1, 0, "C", 1)
            pdf.cell(60, 6, "Valor Total", 1, 1, "C", 1)
            
            pdf.set_font("Arial", "", 9)
            for prod in dados["produtos_mais_vendidos"][:15]:
                pdf.cell(80, 6, prod.get("produto", "")[:40], 1)
                pdf.cell(40, 6, str(prod.get("quantidade_vendida", 0)), 1, 0, "C")
                pdf.cell(60, 6, f"R$ {prod.get('valor_total', 0):,.2f}", 1, 1, "R")
        
        # Rodapé
        RelatorioPDFService.gerar_rodape(pdf)
        
        return bytes(pdf.output(dest="S"))

    @staticmethod
    def gerar_relatorio_estoque_pdf(
        logo_path: str,
        dados: Dict[str, Any]
    ) -> bytes:
        """
        Gera relatório de estoque em PDF
        
        Args:
            logo_path: Caminho do logo
            dados: Dicionário com dados do relatório
            
        Returns:
            Bytes do PDF gerado
        """
        pdf = FPDF()
        pdf.add_page()
        
        # Cabeçalho
        RelatorioPDFService.gerar_cabecalho(pdf, "Relatório de Estoque", logo_path)
        
        # Data
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Gerado em: {dados.get('data_geracao', '')}", 0, 1, "L")
        pdf.ln(5)
        
        # Métricas
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 7, "Resumo do Estoque", 0, 1, "L", 1)
        pdf.ln(2)
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(70, 6, "Valor Total do Estoque:", 0, 0)
        pdf.cell(0, 6, f"R$ {dados.get('valor_total_estoque', 0):,.2f}", 0, 1)
        
        pdf.cell(70, 6, "Total de Produtos Ativos:", 0, 0)
        pdf.cell(0, 6, str(dados.get('total_produtos_ativos', 0)), 0, 1)
        
        pdf.cell(70, 6, "Total de Itens em Estoque:", 0, 0)
        pdf.cell(0, 6, str(dados.get('total_itens_estoque', 0)), 0, 1)
        
        pdf.cell(70, 6, "Produtos com Estoque Baixo:", 0, 0)
        pdf.cell(0, 6, str(dados.get('produtos_estoque_baixo', 0)), 0, 1)
        
        pdf.cell(70, 6, "Produtos sem Estoque:", 0, 0)
        pdf.cell(0, 6, str(dados.get('produtos_sem_estoque', 0)), 0, 1)
        pdf.ln(5)
        
        # Produtos com estoque baixo
        if dados.get("estoque_baixo_detalhes"):
            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 7, "Produtos com Estoque Baixo", 0, 1, "L", 1)
            pdf.ln(2)
            
            pdf.set_font("Arial", "B", 8)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(60, 6, "Código", 1, 0, "C", 1)
            pdf.cell(60, 6, "Produto", 1, 0, "C", 1)
            pdf.cell(30, 6, "Estoque", 1, 0, "C", 1)
            pdf.cell(30, 6, "Mínimo", 1, 1, "C", 1)
            
            pdf.set_font("Arial", "", 8)
            for prod in dados["estoque_baixo_detalhes"][:20]:
                pdf.cell(60, 5, prod.get("codigo_barras", "")[:15], 1)
                pdf.cell(60, 5, prod.get("nome", "")[:25], 1)
                pdf.cell(30, 5, str(prod.get("quantidade_estoque", 0)), 1, 0, "C")
                pdf.cell(30, 5, str(prod.get("estoque_minimo", 0)), 1, 1, "C")
        
        # Categorias
        if dados.get("categorias"):
            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 7, "Estoque por Categoria", 0, 1, "L", 1)
            pdf.ln(2)
            
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(70, 6, "Categoria", 1, 0, "C", 1)
            pdf.cell(40, 6, "Produtos", 1, 0, "C", 1)
            pdf.cell(40, 6, "Itens", 1, 0, "C", 1)
            pdf.cell(40, 6, "Valor", 1, 1, "C", 1)
            
            pdf.set_font("Arial", "", 9)
            for cat in dados["categorias"]:
                pdf.cell(70, 6, cat.get("categoria", "")[:30], 1)
                pdf.cell(40, 6, str(cat.get("total_produtos", 0)), 1, 0, "C")
                pdf.cell(40, 6, str(cat.get("total_itens", 0)), 1, 0, "C")
                pdf.cell(40, 6, f"R$ {cat.get('valor_estoque', 0):,.2f}", 1, 1, "R")
        
        # Rodapé
        RelatorioPDFService.gerar_rodape(pdf)
        
        return bytes(pdf.output(dest="S"))