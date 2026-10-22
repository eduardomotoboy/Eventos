@echo off
REM ==============================================================================
REM ARQUIVO: INSTALADOR_LOCAL_WINDOWS.bat
REM PROJETO: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
REM DESCRIÇÃO: Script executável para inicialização facilitada do servidor web local.
REM           Executa o uvicorn no host 0.0.0.0 permitindo acesso via rede local
REM           no endereço http://192.168.0.23:8000 e via Cloudflare na porta 8000.
REM ==============================================================================

title Portal de Eventos UNIFACCAMP - Porta 8000
cd /d "%~dp0"

echo [UNIFACCAMP - Extensao Universitaria] Inicializando o Portal de Eventos...
echo Verificando integridade e dependencias do ambiente Python e MySQL...

python -c "import fastapi, uvicorn, jinja2, pymysql, qrcode" 2>NUL
if errorlevel 1 (
    echo Instalando dependencias ausentes via requirements.txt...
    pip install -r requirements.txt
)

REM Verificação de conflito de porta 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    REM Se houver processo rodando na porta 8000 que não seja este python atual
    echo.
    echo [AVISO] Foi detectado um processo (PID %%a) escutando na porta 8000.
    echo Se este processo for de outra aplicacao (ex: php.exe da Farmacia),
    echo finalize-o primeiro ou execute 'liberar_porta_8000.bat' como Administrador.
    echo A aplicacao de Farmacia deve rodar na porta 8030.
    echo.
)

echo.
echo ==============================================================================
echo Servidor pronto para atender conexoes locais, rede e Cloudflare:
echo   - Neste computador:        http://localhost:8000
echo   - Link direto IPv4:        http://127.0.0.1:8000
echo   - Outros aparelhos na rede: http://192.168.0.23:8000
echo   - Cloudflare Tunnel:       https://eventos.emgvendas.com.br
echo ==============================================================================
echo.

python app.py
pause
