"""
Mapowanie rejestrów bramki ACMC (AC Mobile Control) zgodnie z dokumentacją
"Integracja z BMS" (Modbus TCP).

REJESTR OGÓLNEGO STATUSU (adres 0, Read Input Registers 0x04):
  bity 15-8: kod błędu (0x00-0xFF)
  bit 6: SCN (skanowanie magistrali LG w toku)
  bit 3: BSY (urządzenie zajęte, np. trwa zapis ustawień)
  bit 0: RDY (gotowość do przyjęcia zapisu rejestrów Modbus)

Każda znaleziona przez bramkę jednostka LG zajmuje blok 7 rejestrów.
Adres pierwszego rejestru bloku (base) dla danego slotu (index = 1..250):
    base = (index - 1) * 7 + 1

BLOK JEDNOSTKI - ODCZYT (Read Input Registers 0x04), adresy base..base+6:
  base+0: AC(bit15) VENT(bit14) GN(bity7-4) UN(bity3-0)
  base+1: FS (bity7-0)  - intensywność nawiewu (0..5)
  base+2: MD (bity7-0)  - tryb pracy (0..4)
  base+3: ST (bity7-0)  - temperatura zadana (18..30 st.C)
  base+4: FA(bit4) PF(bit3) PL(bit2) AS(bit1) ON(bit0)
  base+5: AT (bity7-0)  - temperatura zmierzona (10..40 st.C), tylko odczyt
  base+6: ER (bity7-0)  - kod błędu jednostki, tylko odczyt

BLOK JEDNOSTKI - ZAPIS (Write Multiple Registers 0x10), adresy base..base+6:
  base+0: ZAREZERWOWANE (0)
  base+1: FS
  base+2: MD
  base+3: ST
  base+4: PF(bit3) PL(bit2) AS(bit1) ON(bit0)   [FA nie jest zapisywalne]
  base+5: ZAREZERWOWANE (0)
  base+6: ZAREZERWOWANE (0)

WAŻNE (z dokumentacji):
  - Bramka odpowiada na Modbus niezależnie od podanego adresu docelowego
    (device/unit id) - zalecany adres to 0xFF.
  - Przed zapisem rejestrów jednostki NALEŻY sprawdzić flagę RDY rejestru
    statusu ogólnego.
  - Każdy zapis parametrów jednostki powinien obejmować pełny zestaw
    7 rejestrów w jednym zapytaniu Write Multiple Registers.
"""

REGS_PER_UNIT = 7
MAX_UNITS = 250            # 1750 rejestrów / 7 na jednostkę
MAX_READ_REGS = 125        # limit protokołu Modbus na jedno zapytanie 0x04/0x03

FS_NAMES = {0: 'AUTO', 1: 'BARDZO NISKI', 2: 'NISKI', 3: 'ŚREDNI', 4: 'WYSOKI', 5: 'BARDZO WYSOKI'}
MD_NAMES = {0: 'AUTO', 1: 'CHŁODZENIE', 2: 'NAWIEW', 3: 'GRZANIE', 4: 'OSUSZANIE'}

ERROR_CODES = {
    0x00: 'BRAK_BŁĘDU',
    0x01: 'BŁĄD_CRC_LG (błąd sumy kontrolnej odpowiedzi jednostki)',
    0x02: 'BRAK_ODPOWIEDZI_LG (jednostka nie odpowiada)',
    0x03: 'ZŁA_TMP_ZADANA (poza zakresem 18-30)',
    0x04: 'ZŁA_TMP_ZMIERZONA (poza zakresem 10-40)',
    0x06: 'ZŁY_PARAMETR_FAN (poza zakresem 0-5)',
    0x07: 'ZŁY_PARAMETR_MODE (poza zakresem 0-4)',
}


def unit_base(index: int) -> int:
    """Adres pierwszego rejestru 7-rejestrowego bloku jednostki (index: 1..250)."""
    return (index - 1) * REGS_PER_UNIT + 1


def error_text(code: int) -> str:
    return ERROR_CODES.get(code, f'NIEZNANY_BŁĄD (0x{code:02X})')


def decode_gateway_status(reg: int) -> dict:
    """Dekoduje rejestr statusu ogólnego bramki (adres 0)."""
    error_code = (reg >> 8) & 0xFF
    return {
        'error_code': error_code,
        'error_text': error_text(error_code),
        'scn': bool(reg & (1 << 6)),
        'bsy': bool(reg & (1 << 3)),
        'rdy': bool(reg & (1 << 0)),
        'raw': reg,
    }


def decode_unit_block(regs) -> dict:
    """Dekoduje 7 rejestrów (base..base+6) odczytanych funkcją Read Input Registers."""
    regs = list(regs) + [0] * 7
    r0, fs, md, st, flags, at, er = regs[:7]
    ac = bool(r0 & (1 << 15))
    vent = bool(r0 & (1 << 14))
    gn = (r0 >> 4) & 0x0F
    un = r0 & 0x0F
    return {
        'present': ac or vent,
        'ac': ac,
        'vent': vent,
        'gn': gn,
        'un': un,
        'fs': fs,
        'fs_text': FS_NAMES.get(fs, str(fs)),
        'md': md,
        'md_text': MD_NAMES.get(md, str(md)),
        'st': st,
        'fa': bool(flags & (1 << 4)),
        'pf': bool(flags & (1 << 3)),
        'pl': bool(flags & (1 << 2)),
        'auto_swing': bool(flags & (1 << 1)),
        'on': bool(flags & (1 << 0)),
        'at': at,
        'er': er,
        'er_text': error_text(er),
        'raw': regs[:7],
    }


def encode_unit_write_block(fs: int, md: int, st: int, pf: bool = False,
                             pl: bool = False, auto_swing: bool = False,
                             on: bool = True) -> list:
    """Buduje listę 7 wartości do zapisu (Write Multiple Registers) dla jednostki."""
    flags = 0
    if pf:
        flags |= (1 << 3)
    if pl:
        flags |= (1 << 2)
    if auto_swing:
        flags |= (1 << 1)
    if on:
        flags |= (1 << 0)
    return [0, int(fs) & 0xFF, int(md) & 0xFF, int(st) & 0xFF, flags, 0, 0]


def fan_percent_to_fs(percent: int) -> int:
    """Mapuje intensywność nawiewu w % (0-100) na kod FS (0-5)."""
    p = max(0, min(100, int(percent)))
    if p == 0:
        return 0
    if p <= 10:
        return 1
    if p <= 30:
        return 2
    if p <= 60:
        return 3
    if p <= 85:
        return 4
    return 5
