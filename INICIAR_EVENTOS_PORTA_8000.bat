@echo off
title Portal de Eventos UNIFACCAMP - Porta 8000
cd /d "%~dp0"

echo ==============================================================================
echo [UNIFACCAMP] Inicializando o Portal de Eventos e Extensao...
echo ==============================================================================
echo.

REM Verifica se as dependencias estao instaladas
python -c "import fastapi, uvicorn, jinja2, pymysql, qrcode" 2>NUL
if errorlevel 1 (
    echo Instalando dependencias ausentes via requirements.txt...
    pip install -r requirements.txt
)

REM Alerta se houver processo concorrente na porta 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [AVISO] Processo (PID %%a) detectado na porta 8000.
    echo Se nao for o Portal de Eventos, execute 'liberar_porta_8000.bat' como Administrador.
)

echo.
echo ==============================================================================
echo Servidor pronto para conexoes:
echo   - Localhost:             http://localhost:8000
echo   - IP Local direto:       http://127.0.0.1:8000
echo   - Outros aparelhos Wi-Fi: http://192.168.0.23:8000
echo   - Tunel Cloudflare:      https://eventos.emgvendas.com.br
echo ==============================================================================
echo.

python app.py
pause
