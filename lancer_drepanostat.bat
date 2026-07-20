@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo L'environnement virtuel .venv est introuvable.
    echo Veuillez d'abord lancer installer_drepanostat.bat ou installer les dependances.
    pause
    exit /b
)

call .venv\Scripts\activate.bat
python -m streamlit run app.py
pause

