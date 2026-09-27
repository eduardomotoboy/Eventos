@echo off
REM ==============================================================================
REM ARQUIVO: run.bat
REM PROJETO: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
REM DESCRIÇÃO: Script executável para inicialização facilitada do servidor web local.
REM           Executa o uvicorn no host 0.0.0.0 permitindo acesso via rede local
REM           no endereço http://192.168.0.23:8000 a partir de outros dispositivos.
REM ==============================================================================

echo [UNIFACCAMP - Extensao Universitaria] Inicializando o Portal de Eventos...
echo Verificando integridade e dependencias do ambiente Python e MySQL...

python -c "import fastapi, uvicorn, jinja2, pymysql, qrcode" 2>NUL
if errorlevel 1 (
    echo Instalando dependencias ausentes via requirements.txt...
    pip install -r requirements.txt
)

echo.
echo ==============================================================================
echo Servidor pronto para atender conexoes locais e da rede:
echo   - Neste computador:        http://localhost:8000
echo   - Outros aparelhos na rede: http://192.168.0.23:8000
echo ==============================================================================
echo.

python app.py
pause
