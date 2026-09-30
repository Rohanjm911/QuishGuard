@echo off
title Building QuishGuard Standalone Executable
echo ============================================================
echo  QuishGuard Desktop - Standalone Windows Executable Builder
echo ============================================================
echo.

echo [1/3] Verifying and installing build dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [2/3] Compiling standalone executable via PyInstaller...
python -m PyInstaller --clean --noconsole --onefile --name="QuishGuard" --icon="assets/icon.ico" --add-data "assets;assets" --collect-all customtkinter --collect-all pyzbar --hidden-import=PIL --hidden-import=cv2 --hidden-import=numpy --hidden-import=tldextract --hidden-import=Levenshtein --hidden-import=requests --hidden-import=urllib3 --hidden-import=modules --hidden-import=modules.qr_engine --hidden-import=modules.network_tracer --hidden-import=modules.heuristics --hidden-import=modules.ui_widgets --hidden-import=modules.sound_manager --hidden-import=modules.report_generator --hidden-import=modules.history_manager main.py

echo.
echo [3/3] Build complete! Executable is located in the "dist" folder.
echo ============================================================
pause
