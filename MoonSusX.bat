@echo off
REM MoonSusX - abre el launcher (main.py) con Python en Windows
REM Si Python no esta instalado, descargalo de python.org (marca "Add to PATH")
cd /d "%~dp0"
python main.py
if errorlevel 1 (
  echo.
  echo No se pudo abrir MoonSusX. Revisa que Python este instalado y en el PATH.
  pause
)
