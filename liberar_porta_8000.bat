@echo off
title Liberar Porta 8000 - UNIFACCAMP Eventos

:: Verifica privilégios de Administrador e solicita elevação automática se necessário
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ADMIN] Solicitando permissao de Administrador para liberar a porta 8000...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ==============================================================================
echo [PORTA 8000] Verificando e liberando processos concorrentes na porta 8000...
echo ==============================================================================
echo.

REM Procura e finaliza qualquer processo escutando na porta 8000 (ex: php.exe rodando acidentalmente)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Finalizando processo PID %%a escutando na porta 8000...
    taskkill /F /PID %%a 2>NUL
)

echo.
echo ==============================================================================
echo [SUCESSO] Porta 8000 liberada com exito!
echo.
echo Configuracao correta das duas aplicacoes:
echo  1. Portal de Eventos (UNIFACCAMP): Porta 8000 (INSTALADOR_LOCAL_WINDOWS.bat)
echo  2. Sistema de Farmacia (TCC):      Porta 8030 (RODAR_APLICACAO_WINDOWS.bat)
echo.
echo Agora voce pode reiniciar o Portal de Eventos na porta 8000!
echo ==============================================================================
echo.
pause
