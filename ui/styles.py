"""
styles.py - Estilos CSS personalizados com design compacto
"""

import streamlit as st


class Styles:
    """Classe para gerenciar estilos CSS da aplicação"""
    
    @staticmethod
    def inject():
        """Injeta CSS personalizado na aplicação com design compacto"""
        st.markdown("""
        <style>
        /* ===== REDUÇÃO DE ESPAÇAMENTO GLOBAL ===== */
        
        /* Reduzir padding do container principal */
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 100% !important;
        }
        
        /* Reduzir margem dos títulos */
        h1 {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
            padding-top: 0 !important;
            font-size: 2rem !important;
        }
        
        h2 {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
            font-size: 1.5rem !important;
        }
        
        h3 {
            margin-top: 0.15rem !important;
            margin-bottom: 0.15rem !important;
        }
        
        /* Reduzir espaçamento de todos os elementos */
        .stAlert, .stSuccess, .stError, .stWarning, .stInfo {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        /* Reduzir espaçamento de colunas */
        .row-widget {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
        }
        
        .element-container {
            margin-bottom: 0.1rem !important;
        }
        
        /* Reduzir espaçamento de abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem !important;
            margin-bottom: 0.25rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
        }
        
        /* Reduzir espaçamento de botões */
        .stButton button {
            margin-top: 0 !important;
            margin-bottom: 0.1rem !important;
        }
        
        /* Reduzir espaçamento de inputs */
        .stTextInput, .stSelectbox, .stDateInput, .stNumberInput {
            margin-bottom: 0.25rem !important;
        }
        
        /* Reduzir espaçamento de métricas */
        .stMetric {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        
        .stMetric label {
            margin-top: 0 !important;
        }
        
        .stMetric [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
        }
        
        /* Reduzir espaçamento de expanders */
        .streamlit-expanderHeader {
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
        }
        
        /* ===== SIDEBAR (MENU LATERAL) - DESIGN COMPACTO ===== */
        
        /* Estilos da sidebar compacta */
        [data-testid="stSidebar"] {
            padding-top: 0.5rem !important;
            width: 250px !important;
        }
        
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        [data-testid="stSidebar"] .stButton button {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
            font-size: 0.9rem !important;
        }
        
        [data-testid="stSidebar"] h1 {
            font-size: 1.3rem !important;
            margin-top: 0 !important;
            margin-bottom: 0.25rem !important;
        }
        
        [data-testid="stSidebar"] h2 {
            font-size: 1.1rem !important;
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
        }
        
        [data-testid="stSidebar"] h3 {
            font-size: 1rem !important;
            margin-top: 0.15rem !important;
            margin-bottom: 0.15rem !important;
        }
        
        [data-testid="stSidebar"] p {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            font-size: 0.9rem !important;
        }
        
        [data-testid="stSidebar"] hr {
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }
        
        /* Estilo para os botões da sidebar */
        [data-testid="stSidebar"] .stButton button {
            background-color: transparent;
            border: 1px solid rgba(49, 51, 63, 0.2);
            color: rgb(49, 51, 63);
            transition: all 0.3s;
        }
        
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: rgba(49, 51, 63, 0.05);
            border-color: rgba(49, 51, 63, 0.4);
        }
        
        [data-testid="stSidebar"] .stButton button[kind="primary"] {
            background-color: rgba(49, 51, 63, 0.1);
            border-color: rgba(49, 51, 63, 0.3);
            color: rgb(49, 51, 63);
        }
        
        [data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
            background-color: rgba(49, 51, 63, 0.15);
        }
        
        /* ===== CARDS DE MÉTRICAS ===== */
        
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            padding: 20px;
            color: white;
            text-align: center;
            margin-bottom: 10px;
        }
        
        .metric-card .metric-value {
            font-size: 2.5em;
            font-weight: bold;
        }
        
        .metric-card .metric-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        /* ===== DESTAQUE PARA ESTOQUE BAIXO ===== */
        .estoque-baixo {
            background-color: #ffebee !important;
            color: #c62828 !important;
            font-weight: bold;
        }
        
        /* ===== TABELAS RESPONSIVAS ===== */
        .stDataFrame {
            width: 100%;
            overflow-x: auto;
        }
        
        /* ===== BREADCRUMB ===== */
        .breadcrumb {
            padding: 0.2rem 0;
            margin-bottom: 0.3rem;
            border-bottom: 1px solid #eee;
        }
        
        .breadcrumb-item {
            display: inline-block;
            color: #666;
        }
        
        .breadcrumb-item:not(:last-child):after {
            content: " > ";
            margin: 0 5px;
            color: #999;
        }
        
        /* ===== FORM STEPS ===== */
        .form-step {
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #ddd;
            background-color: #f9f9f9;
        }
        
        .form-step.active {
            border-left-color: #4CAF50;
            background-color: #f1f8e9;
        }
        
        .form-step.completed {
            border-left-color: #2196F3;
            background-color: #e3f2fd;
        }
        
        /* ===== HOTKEY HINTS ===== */
        .hotkey-hint {
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 0.8em;
            color: #666;
        }
        
        /* ===== TOOLTIPS ===== */
        [data-tooltip] {
            position: relative;
            cursor: help;
        }
        
        [data-tooltip]:before {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #333;
            color: white;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            white-space: nowrap;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.2s;
            z-index: 1000;
        }
        
        [data-tooltip]:hover:before {
            opacity: 1;
            visibility: visible;
        }
        
        /* ===== RODAPÉ ===== */
        footer {
            visibility: hidden !important;
        }
        
        /* ===== TEMA ESCURO (RESPONSIVO) ===== */
        @media (prefers-color-scheme: dark) {
            [data-testid="stSidebar"] .stButton button {
                border-color: rgba(250, 250, 250, 0.2);
                color: rgb(250, 250, 250);
            }
            
            [data-testid="stSidebar"] .stButton button:hover {
                background-color: rgba(250, 250, 250, 0.05);
                border-color: rgba(250, 250, 250, 0.3);
            }
            
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] p {
                color: rgb(250, 250, 250);
            }
            
            .breadcrumb-item {
                color: #aaa;
            }
            
            .form-step {
                background-color: #2d2d2d;
                border-left-color: #555;
            }
            
            .form-step.active {
                background-color: #1e3a2e;
                border-left-color: #4CAF50;
            }
            
            .form-step.completed {
                background-color: #1a3a4a;
                border-left-color: #2196F3;
            }
        }
        
        /* ===== RESPONSIVIDADE ===== */
        @media (max-width: 768px) {
            .metric-card .metric-value {
                font-size: 1.8em;
            }
            
            .stButton button {
                width: 100%;
                margin: 5px 0;
            }
        }
        </style>
        """, unsafe_allow_html=True)
