# ACMC

ACMC to aplikacja desktopowa do monitorowania i sterowania układem klimatyzacji / bramką ACMC po protokole Modbus TCP. Projekt został stworzony do obsługi jednostek HVAC/AC z poziomu prostego interfejsu graficznego w systemie Windows, z możliwością skanowania urządzeń, odczytu parametrów, testów komunikacji oraz wysyłania poleceń sterujących.

## Czym jest ten projekt?

Aplikacja pozwala na:
- wykrywanie urządzeń ACMC w sieci lokalnej,
- odczyt danych z rejestrów Modbus,
- sprawdzanie statusu bramki,
- monitorowanie stanu jednostek (temperatura, tryb, przepływ, flagi),
- wysyłanie poleceń sterujących do konkretnej jednostki,
- przeprowadzanie testów komunikacji i diagnostyki,
- zapisywanie zdarzeń i danych do lokalnej bazy SQLite.

Aplikacja ma przede wszystkim służyć jako narzędzie diagnostyczne i kontrolne dla instalacji z wykorzystaniem bramek ACMC i jednostek AC.

## Do czego służy?

Projekt jest przydatny w scenariuszach takich jak:
- testowanie i diagnozowanie sieci Modbus TCP,
- konfiguracja i kontrola jednostek klimatyzacyjnych,
- sprawdzanie poprawności połączeń z bramką,
- weryfikacja parametrów jednostek (FS, MD, ST, AT, ON, ER),
- szybkie sterowanie urządzeniami bez potrzeby korzystania z dedykowanego narzędzia producenta.

## Główne funkcje

- skanowanie urządzeń w określonym zakresie adresów IP / portów,
- wyświetlanie listy odnalezionych jednostek,
- podgląd szczegółowych parametrów każdej jednostki,
- sterowanie nawiewem, temperaturą zadana, trybem pracy i stanem ON/OFF,
- wizualizacja parametrów i historii,
- logowanie zdarzeń do bazy SQLite,
- wsparcie dla trybu mock/testowego przy pracy bez fizycznego urządzenia,
- gotowy plik EXE do uruchamiania na Windows.

## Technologie i architektura

Projekt wykorzystuje:
- Python,
- Tkinter do tworzenia interfejsu graficznego,
- Modbus TCP do komunikacji z bramką,
- SQLite do przechowywania danych diagnostycznych,
- Matplotlib do wizualizacji,
- PyInstaller do tworzenia wersji desktopowej .exe.

## Struktura projektu

- `acmc_app_pl.py` — główny interfejs użytkownika,
- `acmc_modbus.py` — komunikacja Modbus oraz mock mode,
- `scanner.py` — skanowanie urządzeń,
- `tester.py` — testy i komendy sterujące,
- `visual.py` — wizualizacja danych,
- `db.py` — warstwa bazy danych,
- `logger.py` — logowanie,
- `acmc_registers.py` — mapowanie rejestrów i parametrów,
- `dist/ACMC_AC.exe` — zbudowana wersja aplikacji dla Windows.

## Wymagania

### Wersja Python
- Python 3.8+

### Zależności
- tkinter
- pymodbus
- matplotlib
- pillow

Można je zainstalować np.:

```bash
pip install pymodbus matplotlib pillow
```

## Uruchomienie

### 1. Uruchomienie ze źródła

```bash
cd C:\Users\wiesl\ACMC
python acmc_app_pl.py
```

### 2. Uruchomienie wykonawczego pliku EXE

```bash
C:\Users\wiesl\ACMC\dist\ACMC_AC.exe
```

## Jak używać aplikacji

1. Podaj adres IP bramki ACMC oraz port Modbus (domyślnie 502).
2. Kliknij „Skanuj jednostki”.
3. Wybierz jednostkę z listy.
4. Odczytaj szczegóły i parametry urządzenia.
5. W razie potrzeby wykonaj test komunikacji lub wyślij polecenia sterujące.
6. Dla testów bez fizycznego urządzenia można użyć trybu mock.

## Tryb mock vs tryb real

### Tryb mock
- przeznaczony do testów lokalnych,
- emuluje działanie urządzeń,
- przydatny do sprawdzania interfejsu GUI bez podłączonej bramki.

### Tryb real
- wykorzystuje prawdziwą komunikację Modbus TCP,
- wymaga aktywnego urządzenia ACMC w sieci lokalnej.

## Ograniczenia

- Aplikacja jest zorientowana na środowisko Windows,
- do prawdziwego działania w sieci wymagany jest zgodny sprzęt ACMC i poprawna topologia sieci,
- niektóre elementy UI i konfiguracji zależą od konkretnego modelu bramki wykonawczej,
- dla pełnej diagnostyki najlepiej sprawdzić dokumentację Modbus konkretnego urządzenia.

## Rozwój i status projektu

Projekt jest aktywnie rozwijany jako narzędzie pomocnicze do pracy z urządzeniami ACMC. Aktualnie obejmuje podstawową diagnostykę, skanowanie, sterowanie oraz wizualizację parametrów. W przyszłości można rozbudować go o:
- eksport danych do CSV,
- większy zestaw alarmów i diagnostyki,
- integrację z historią z wielu bramek,
- obsługę większej liczby modeli urządzeń.

## Licencja

Ten projekt jest udostępniany jako narzędzie lokalne i eksperymentalne. Przed publicznym wdrożeniem w środowisku produkcyjnym zaleca się sprawdzenie zgodności z politykami bezpieczeństwa, dokumentacją sprzętu oraz procedurami instalacji.

## Linki

- [Releases](https://github.com/wwns/ACMC/releases)

## Screenshot

![ACMC GUI](https://raw.githubusercontent.com/wwns/ACMC/main/screenshot.png)

## Status

- Repozytorium: GitHub
- Główna gałąź: `main`
- Wersja startowa: `v1.0.0`
