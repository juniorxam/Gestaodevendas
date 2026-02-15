"""
styles.py - Estilos CSS personalizados
"""

import streamlit as st


class Styles:
    """Classe para gerenciar estilos CSS da aplicação"""
    
    @staticmethod
    def inject():
        """Injeta CSS personalizado na aplicação"""
        st.markdown("""
        <style>
        /* Remove a cor de fundo padrão da sidebar */
        [data-testid="stSidebar"] {
            background-color: transparent !important;
            border-right: 1px solid rgba(49, 51, 63, 0.1);
        }
        
        /* Remove o background do conteúdo da sidebar */
        [data-testid="stSidebar"] > div:first-child {
            background-color: transparent !important;
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
        
        /* Cards de métricas */
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
        
        /* Estoque baixo - destaque vermelho */
        .estoque-baixo {
            background-color: #ffebee !important;
            color: #c62828 !important;
            font-weight: bold;
        }
        
        /* Tabelas responsivas */
        .stDataFrame {
            width: 100%;
            overflow-x: auto;
        }
        
        /* Breadcrumb */
        .breadcrumb {
            padding: 10px 0;
            margin-bottom: 20px;
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
        
        /* Form steps */
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
        
        /* Hotkey hints */
        .hotkey-hint {
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 2px 6px;
            font-size: 0.8em;
            color: #666;
        }
        
        /* Tooltips */
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
        
        /* Responsividade */
        @media (max-width: 768px) {
            .metric-card .metric-value {
                font-size: 1.8em;
            }
            
            .stButton button {
                width: 100%;
                margin: 5px 0;
            }
        }
        
        /* Tema escuro (prefers-color-scheme) */
        @media (prefers-color-scheme: dark) {
            [data-testid="stSidebar"] .stButton button {
                border-color: rgba(250, 250, 250, 0.2);
                color: rgb(250, 250, 250);
            }
            
            [data-testid="stSidebar"] .stButton button:hover {
                background-color: rgba(250, 250, 250, 0.05);
                border-color: rgba(250, 250, 250, 0.3);
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
        </style>
        """, unsafe_allow_html=True)