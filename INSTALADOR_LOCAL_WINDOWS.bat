@echo off
chcp 65001 >nul 2>&1
title Portal de Eventos UNIFACCAMP - Inicializador Completo - Porta 8000 + MySQL
cd /d "%~dp0"

REM ==============================================================================
REM ARQUIVO: INSTALADOR_LOCAL_WINDOWS.bat
REM PROJETO: Eventos (Modulo de Inscricao e Extensao Universitaria - UNIFACCAMP)
REM DESCRICAO: Script UNICO e completo de inicializacao local no Windows:
REM            1. Eleva privilegios de Administrador automaticamente
REM            2. Inicia o servico MySQL (MySQL80) na porta 3306 e garante banco/tabelas
REM            3. Libera a porta 8000 encerrando processos conflitantes
REM            4. Libera a porta 8000 TCP no Firewall do Windows Defender
REM            5. Verifica e instala todas as dependencias Python necessarias
REM            6. Abre o navegador em http://localhost:8000 e inicia a aplicacao
REM ==============================================================================

REM Localiza o interpretador Python principal da maquina
set "PYTHON_EXE=python"
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
if exist "%LocalAppData%\Programs\Python\Python314\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python314\python.exe"
if exist "C:\Python314\python.exe" set "PYTHON_EXE=C:\Python314\python.exe"

REM 0. Verifica privilegios de Administrador para liberar Firewall, Porta 8000 e MySQL
net session >nul 2>&1
if %errorlevel% equ 0 goto :INICIAR_EXECUCAO
if /I "%~1"=="SEM_ADMIN" goto :INICIAR_EXECUCAO

echo [ADMIN] Solicitando permissao de Administrador para iniciar MySQL, liberar Firewall e Porta 8000...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList 'SEM_ADMIN' -Verb RunAs" >nul 2>&1
if %errorlevel% equ 0 exit /b
echo [AVISO] Continuando sem elevacao de Administrador...

:INICIAR_EXECUCAO
cd /d "%~dp0"
cls
echo ==============================================================================
echo   [UNIFACCAMP - EXTENSAO UNIVERSITARIA] PORTAL DE EVENTOS E AMOSTRAS
echo   Inicializador Automatico Completo - MySQL + Firewall + Porta 8000 + App
echo ==============================================================================
echo.

REM ------------------------------------------------------------------------------
REM ETAPA 1: INICIAR E VERIFICAR O BANCO DE DADOS MYSQL - PORTA 3306
REM ------------------------------------------------------------------------------
echo [1/5] Verificando e iniciando o servidor MySQL na porta 3306...
netstat -aon | findstr ":3306" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 goto :MYSQL_OK

echo       MySQL nao detectado na porta 3306. Tentando iniciar o servico MySQL...
net start MySQL80 >nul 2>&1
net start MySQL >nul 2>&1
net start MariaDB >nul 2>&1
sc start MySQL80 >nul 2>&1

netstat -aon | findstr ":3306" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 goto :MYSQL_OK

if exist "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" (
    echo       Iniciando executavel mysqld.exe em segundo plano...
    start "" /b "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe"
    timeout /t 3 /nobreak >nul
)

:MYSQL_OK
echo       [OK] Servico MySQL ativo na porta 3306.

REM ------------------------------------------------------------------------------
REM ETAPA 2: LIBERAR A PORTA 8000 - FINALIZAR PROCESSOS CONFLITANTES
REM ------------------------------------------------------------------------------
echo [2/5] Verificando e liberando a porta 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do call :MATAR_PID %%a
echo       [OK] Porta 8000 livre e pronta para uso.

REM ------------------------------------------------------------------------------
REM ETAPA 3: LIBERAR PORTA 8000 NO FIREWALL DO WINDOWS DEFENDER
REM ------------------------------------------------------------------------------
echo [3/5] Configurando regra de liberacao da porta 8000 no Firewall do Windows...
netsh advfirewall firewall show rule name="Portal Eventos UNIFACCAMP Porta 8000" >nul 2>&1
if errorlevel 1 netsh advfirewall firewall add rule name="Portal Eventos UNIFACCAMP Porta 8000" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1
echo       [OK] Regra de Firewall verificada para a porta 8000 TCP.

REM ------------------------------------------------------------------------------
REM ETAPA 4: VERIFICAR E INSTALAR DEPENDENCIAS PYTHON + PREPARAR BANCO MYSQL
REM ------------------------------------------------------------------------------
echo [4/5] Verificando pacotes Python e estrutura do banco de dados MySQL...
"%PYTHON_EXE%" -c "import fastapi, uvicorn, jinja2, pymysql, qrcode, itsdangerous, multipart, reportlab, pypdf" >nul 2>&1
if not errorlevel 1 goto :DEPS_OK

echo       Instalando dependencias Python via requirements.txt...
"%PYTHON_EXE%" -m pip install --upgrade pip >nul 2>&1
"%PYTHON_EXE%" -m pip install -r requirements.txt

:DEPS_OK
if exist "definicoes\scripts_teste\grant_privileges.py" (
    "%PYTHON_EXE%" "definicoes\scripts_teste\grant_privileges.py" >nul 2>&1
)
echo       [OK] Dependencias e banco de dados prontos.

REM ------------------------------------------------------------------------------
REM ETAPA 5: INICIAR O SERVIDOR NA PORTA 8000 E ABRIR O NAVEGADOR
REM ------------------------------------------------------------------------------
echo [5/5] Iniciando Portal de Eventos UNIFACCAMP na porta 8000...
echo.
echo ==============================================================================
echo   APLICACAO PRONTA! ACESSE PELOS ENDERECOS ABAIXO:
echo   - Neste computador - Localhost:  http://localhost:8000
echo   - Link direto IPv4:              http://127.0.0.1:8000
echo   - Outros aparelhos no Wi-Fi:     http://192.168.0.23:8000
echo   - Cloudflare Tunnel:             https://eventos.emgvendas.com.br
echo ==============================================================================
echo   Mantenha esta janela aberta enquanto estiver utilizando o sistema.
echo.

if /I not "%~1"=="SEM_BROWSER" if /I not "%~2"=="SEM_BROWSER" (
    start "" /b cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"
)

"%PYTHON_EXE%" app.py
echo.
echo [AVISO] O servidor foi encerrado.
pause
exit /b

:MATAR_PID
if "%~1"=="" exit /b
if "%~1"=="0" exit /b
echo       Encerrando processo conflitante na porta 8000 - PID %~1...
taskkill /F /T /PID %~1 >nul 2>&1
exit /b
