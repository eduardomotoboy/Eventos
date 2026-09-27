@echo off
REM ==============================================================================
REM ARQUIVO: definicoes/scripts_teste/liberar_firewall_porta_8000.bat
REM PROJETO: Eventos (Módulo de Inscrição e Extensão Universitária - UNIFACCAMP)
REM DESCRIÇÃO: Libera a porta 8000 TCP no Firewall do Windows Defender
REM            para permitir que outros celulares e computadores na rede local
REM            acessem a aplicação no endereço http://192.168.0.23:8000.
REM
REM COMO USAR:
REM Clique com o botão direito neste arquivo e selecione "Executar como administrador".
REM ==============================================================================

echo [FIREWALL] Adicionando regra de permissao de entrada para a porta 8000 TCP...
netsh advfirewall firewall add rule name="Portal Eventos UNIFACCAMP (Porta 8000)" dir=in action=allow protocol=TCP localport=8000
if errorlevel 1 (
    echo.
    echo [ATENCAO] A adicao da regra falhou porque este script nao foi executado como Administrador.
    echo Por favor, clique com o botao direito no arquivo e escolha "Executar como Administrador".
) else (
    echo.
    echo [SUCESSO] Porta 8000 liberada com sucesso no Firewall do Windows!
    echo Aparelhos conectados no mesmo Wi-Fi podem acessar: http://192.168.0.23:8000
)
echo.
pause
