╔════════════════════════════════════════════════════════════╗
║          ACMC - Bramka Modbus LG (PORTABLE)               ║
║              Wersja przenośna bez instalacji              ║
╚════════════════════════════════════════════════════════════╝

URUCHOMIENIE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Kliknij dwukrotnie: ACMC_AC.exe
  2. Lub: Kliknij shortcut "ACMC Portable" na Desktop

WYMAGANIA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Windows 7+ (32 lub 64-bit)
  ✗ Nie wymaga instalacji Pythona
  ✗ Nie wymaga Visual C++
  ✗ Nie wymaga innych zależności
  ✓ Folder może być na USB stick, Desktop, Downloads

FUNKCJE APLIKACJI:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Skanowanie jednostek Modbus TCP
  ✓ Sterowanie: fan speed (0-100%), temperatura (18-30°C)
  ✓ Testy komunikacji:
    - Bramka ↔ Komputer
    - Bramka ↔ Płyta w agregacie LG
  ✓ Baza danych SQLite z logowaniem
  ✓ Wizualizacja wykresów (matplotlib)
  ✓ Panel szczegółów jednostki
  ✓ Interfejs w języku POLSKIM

SZYBKI TEST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Uruchom ACMC_AC.exe
  2. Wpisz:
     - Host: 127.0.0.1 (lub IP bramki ACMC)
     - Port: 502
     - Zakres: 1 do 10
  3. Kliknij "Skanuj jednostki"
     → Dla localhost: powinno znaleźć 10 x OK
     → Dla real IP: OK = jednostka dostępna, FAIL = brak

RZECZYWISTA BRAMKA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Zanotuj IP bramki ACMC (np. 192.168.1.50)
  2. Wpisz w aplikacji
  3. Skanuj - zobaczysz które jednostki są dostępne
  4. Zaznacz jednostkę
  5. Zmień fan speed, temperaturę
  6. Kliknij "Wyślij sterowanie"
  7. Sprawdź czy zmiany trafiły na urządzenie

BAZA DANYCH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Plik: acmc.db (SQLite)
  • Lokalizacja: w folderze ACMC_Portable
  • Zawiera: logi skanowania, sterowania, testów
  • Można otworzyć: DB Browser for SQLite

STRUKTURA PLIKÓW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ACMC_Portable/
  ├── ACMC_AC.exe          ← GŁÓWNY PROGRAM
  ├── acmc_app_pl.py       ← GUI (Python)
  ├── acmc_modbus.py       ← Komunikacja Modbus
  ├── scanner.py           ← Skanowanie jednostek
  ├── tester.py            ← Testy i sterowanie
  ├── visual.py            ← Wykresy
  ├── db.py                ← Baza danych
  ├── logger.py            ← Logowanie
  ├── acmc.db              ← Dane (tworzy się automatycznie)
  ├── LG.png               ← Ikona aplikacji
  ├── acmc_icon.ico        ← Ikona (ICO format)
  └── README.txt           ← Ten plik

ROZWIĄZYWANIE PROBLEMÓW:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Q: Aplikacja się nie uruchamia
  A: Sprawdź czy wszystkie pliki .py są w folderze

  Q: "Host not found" / "Connection refused"
  A: Sprawdź IP bramki ACMC, port powinien być 502

  Q: Baza danych pokazuje stare dane
  A: Usuń acmc.db, aplikacja utworzy nową

  Q: Ikona to niebieski kwadrat
  A: To ograniczenie Tkinter na Windowsie (znane)

AUTOR: Copilot CLI
DATA: 2026-08-19
WERSJA: 1.0 Portable
