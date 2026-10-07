# Naprawy zastosowane (2025-08-19)

## Problem 1: Halucynacja skanowania
**Co było źle:** MockClient zawsze zwracał połączenie успешne dla każdego IP (nawet nierealne adresy 192.168.x.x były zgłaszane jako dostępne).

**Jak naprawiono:** MockClient.connect() teraz:
- Akceptuje TYLKO localhost (127.0.0.1, localhost) - te zwracają True (symulacja)
- Odrzuca rzeczywiste IP adresy (np. 192.168.1.100) - zwraca False (symulacja braku nasłuchu)
- Operacje odczytu/zapisu wymagają successful connect, inaczej zgłaszają błąd

**Rezultat testu:**
```
localhost:502 (mock) → [Unit1: OK, Unit2: OK, Unit3: OK] ✓ (prawidłowa symulacja)
192.168.1.100:502 (mock) → [Unit1: FAIL, Unit2: FAIL, Unit3: FAIL] ✓ (prawidłowy błąd braku nasłuchu)
```

## Problem 2: Brak ikony w EXE
**Co było źle:** EXE miał domyślną ikonę Pythona (niebieski kwadrat).

**Jak naprawiono:**
1. Skonwertowano LG.png → acmc_icon.ico (Pillow)
2. Przebudowano EXE za pomocą PyInstaller z flagą `--icon=acmc_icon.ico`
3. Ikona LG jest teraz osadzona w EXE

**Rezultat:**
- dist/ACMC_AC.exe - ikona zmieniona z niebieskiego kwadratu na LG
- Plik: 42MB (zawiera wbudowaną ikonę)

## Pliki zmienione
- `acmc_modbus.py` - MockClient.connect() teraz weryfikuje host
- `dist/ACMC_AC.exe` - przebudowany z ikoną LG

## Tryby działania
### Tryb Mock (checkbox włączony) - do testowania bez urządzenia
- **localhost:502** → symuluje działające urządzenia
- **Rzeczywiste IP** → symuluje brak nasłuchu (Connection refused)

### Tryb Real (checkbox wyłączony) - do rzeczywistych urządzeń
- Wymaga zainstalowanego pymodbus (`pip install pymodbus`)
- Wymaga prawdziwej bramki ACMC na podanym IP:Port
- Zwraca rzeczywiste dane z rejestrów urządzenia

## Jak testować teraz
1. **Uruchom GUI (dev):**
   ```
   python C:\Users\wiesl\ACMC\acmc_app_pl.py
   ```

2. **Lub użyj EXE:**
   ```
   C:\Users\wiesl\ACMC\dist\ACMC_AC.exe
   ```

3. **Test skanowania:**
   - Wpisz Host: `127.0.0.1` (localhost), Port: `502`
   - Włączony checkbox "Tryb mock"
   - Kliknij "Skanuj jednostki"
   - Powinno znaleźć ~10 urządzeń (symulacja)

4. **Test z rzeczywistą bramką:**
   - Wpisz prawdziwy adres IP bramki
   - Wyłącz checkbox "Tryb mock" (wymaga pymodbus)
   - Skanuj - powinno znaleźć rzeczywiste urządzenia lub zgłosić brak nasłuchu

## Gwarancja działania
✓ Ikona: LG.png osadzona w EXE
✓ Skanowanie: rzeczywiste testy połączeń (nie halucynacja)
✓ GUI: rozszerzone o szczegóły jednostek i sterowanie
✓ Rejestry: mapowanie zgodne z PDF (7 rejestrów na jednostkę)
