@echo off
REM ==== Compila el Gestor de Certificados en un unico .exe ====
cd /d "%~dp0"
echo Compilando... (puede tardar varios minutos)
python -m PyInstaller --noconfirm --onefile --windowed --name GestorCertificados ^
  --icon "gestor\assets\icono.ico" ^
  --splash "gestor\assets\splash.png" ^
  --collect-all customtkinter ^
  --collect-all anthropic ^
  --collect-all tkinterdnd2 ^
  --add-data "gestor\assets;gestor\assets" ^
  --add-data "gestor\seed_data.json;." ^
  run.py
echo.
echo ============================================================
echo  Listo. El ejecutable esta en:  dist\GestorCertificados.exe
echo ============================================================
pause
