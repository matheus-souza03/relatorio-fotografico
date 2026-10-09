@echo off
rem Gera o relatorio fotografico. De dois cliques neste arquivo.
rem Na primeira vez, prepara o Python numa pasta do usuario (fora da pasta do projeto).
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if defined RELATORIO_VENV (set "VENV=%RELATORIO_VENV%") else (set "VENV=%LOCALAPPDATA%\relatorio_fotografico\venv")
if exist "%VENV%\Scripts\python.exe" goto instalar

echo Preparando o programa - somente na primeira vez, pode levar alguns minutos...
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto sem_python
%PY% -m venv --clear "%VENV%"
if errorlevel 1 goto erro_venv

:instalar
echo Verificando componentes...
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto erro_pip
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements-opcional.txt >nul 2>nul

echo.
"%VENV%\Scripts\python.exe" gerar_relatorio.py %*
echo.
pause
exit /b

:sem_python
echo ERRO: o Python 3 nao esta instalado. Instale pelo site https://www.python.org/downloads/
echo Durante a instalacao, marque a opcao "Add python.exe to PATH". Depois tente de novo.
echo.
pause
exit /b 1

:erro_venv
echo ERRO: nao foi possivel preparar o Python. Veja a secao "Problemas comuns" do LEIAME.md.
echo.
pause
exit /b 1

:erro_pip
echo ERRO: nao foi possivel instalar os componentes. Verifique a internet e tente de novo.
echo.
pause
exit /b 1
