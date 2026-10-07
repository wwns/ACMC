# PowerShell build script: zainstaluje zależności, wygeneruje ikonę i zbuduje .exe przy pomocy PyInstaller

# zainstaluj wymagane biblioteki
pip install --upgrade pip
pip install pyinstaller pillow matplotlib

# wygeneruj ikonę (użyje generate_icon.py)
python generate_icon.py

# buduj exe
pyinstaller --onefile --windowed --icon=acmc_icon.ico --name ACMC_AC acmc_app_pl.py

Write-Output 'Kompilacja zakończona. Plik EXE znajduje się w dist\ACMC_AC.exe'