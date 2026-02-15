@echo off
title ElectroGest
echo ========================================
echo   INICIANDO ELECTROGEST
echo   Sistema de Gestão Comercial
echo ========================================

:: Verifica se o Python existe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O Python nao foi encontrado instalado neste computador.
    echo Por favor, instale o Python em python.org e marque a opcao "Add Python to PATH".
    pause
    exit
)

:: Instalar dependências se necessário
echo [INFO] Verificando dependencias...
pip install -r requirements.txt

:: Iniciar o sistema
echo [INFO] Iniciando o ElectroGest...
python -m streamlit run app.py

echo.
echo ========================================
echo [AVISO] O programa parou de rodar.
echo Verifique as mensagens de erro acima.
echo ========================================
pause