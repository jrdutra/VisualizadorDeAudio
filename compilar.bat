@echo off
setlocal

cd /d "%~dp0"

python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --clean ^
  --name va ^
  tela.py

if errorlevel 1 (
  echo.
  echo Erro ao compilar. Verifique se o PyInstaller esta instalado:
  echo python -m pip install pyinstaller
  pause
  exit /b 1
)

echo.
echo Compilacao concluida.
echo Arquivo gerado em: dist\va.exe
pause
