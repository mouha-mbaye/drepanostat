@echo off
cd /d "%~dp0"

echo Installation de DrepanoStat...

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Installation terminee.
echo Vous pouvez maintenant lancer DrepanoStat avec lancer_drepanostat.bat.
pause

