"""
Skanowanie jednostek LG podłączonych do bramki ACMC.

WAŻNE (zgodnie z dokumentacją): Bramka ACMC to JEDEN serwer Modbus TCP -
odpowiada niezależnie od podanego adresu docelowego (device/unit id).
"Jednostki" (indoor units LG) NIE są oddzielnymi urządzeniami Modbus -
są blokami po 7 rejestrów (adresy 1-1750) w ramach TEGO SAMEGO połączenia.

Dlatego skanowanie = JEDNO połączenie TCP + odczyt całej tabeli rejestrów
funkcją Read Input Registers (0x04), a NIE próba łączenia się z różnymi
"unit_id" jak z osobnymi urządzeniami (poprzedni, błędny model zawsze
zwracał komplet "OK" niezależnie od realnego adresu IP).
"""
from acmc_modbus import ACMCModbusClient
from acmc_registers import (
    decode_unit_block, decode_gateway_status, REGS_PER_UNIT, MAX_UNITS, MAX_READ_REGS,
)
from typing import Dict
import logger
import db


def scan_units(host: str = '127.0.0.1', port: int = 502, max_units: int = MAX_UNITS,
                timeout: float = 3.0) -> Dict:
    """
    Łączy się RAZ z bramką pod adresem host:port i odczytuje tabelę rejestrów.

    Zwraca:
        {
            'success': bool,
            'error': str | None,
            'gateway_status': {...} | None,   # dekodowany rejestr 0
            'units': [ {...decode_unit_block(), 'index': i, 'base': addr}, ... ]
        }
    Lista 'units' zawiera WYŁĄCZNIE sloty z podłączoną jednostką (present=True).
    """
    client = ACMCModbusClient(host=host, port=port, timeout=timeout)
    c = client.connect()
    if not c.get('success'):
        logger.error(f"Skanowanie: brak połączenia z {host}:{port}: {c.get('error')}")
        db.log_event('ERROR', f'scan_units connect fail {host}:{port} {c.get("error")}')
        return {'success': False, 'error': c.get('error'), 'units': [], 'gateway_status': None}

    logger.info(f"Skanowanie {host}:{port} - łączenie OK, odczyt rejestru statusu ogólnego...")

    # 1. status ogólny bramki (adres 0)
    gateway_status = None
    r0 = client.read_input_registers(0, 1)
    if r0.get('success'):
        gateway_status = decode_gateway_status(r0['data'][0])
        logger.info(f"Status bramki: RDY={gateway_status['rdy']} BSY={gateway_status['bsy']} "
                    f"SCN={gateway_status['scn']} błąd={gateway_status['error_text']}")
    else:
        logger.error(f"Nie udało się odczytać rejestru statusu: {r0.get('error')}")

    # 2. tabela jednostek - czytana w kawałkach (limit protokołu: max 125 rej. na zapytanie)
    units_found = []
    chunk_units = max(1, MAX_READ_REGS // REGS_PER_UNIT)   # np. 17 jednostek = 119 rejestrów
    chunk_regs = chunk_units * REGS_PER_UNIT

    addr = 1
    idx = 1
    remaining_units = max_units
    read_error = None
    while remaining_units > 0:
        units_this_read = min(chunk_units, remaining_units)
        n = units_this_read * REGS_PER_UNIT
        r = client.read_input_registers(addr, n)
        if not r.get('success'):
            read_error = r.get('error')
            logger.error(f"Skanowanie: błąd odczytu rejestrów od adresu {addr}: {read_error}")
            break
        regs = r['data']
        for off in range(0, len(regs), REGS_PER_UNIT):
            block = regs[off: off + REGS_PER_UNIT]
            if len(block) < REGS_PER_UNIT:
                break
            info = decode_unit_block(block)
            if info['present']:
                info['index'] = idx
                info['base'] = addr + off
                units_found.append(info)
                db.save_scan_result(
                    host, port, idx, True,
                    f"GN={info['gn']} UN={info['un']} FS={info['fs']} MD={info['md']} "
                    f"ST={info['st']} AT={info['at']} ON={info['on']} ER={info['er']}"
                )
            idx += 1
        addr += n
        remaining_units -= units_this_read

    client.close()

    if not units_found and read_error:
        logger.error(f"Skanowanie zakończone błędem: {read_error}")
        return {'success': False, 'error': read_error, 'units': [], 'gateway_status': gateway_status}

    logger.info(f"Skanowanie {host}:{port} zakończone. Znaleziono {len(units_found)} jednostek "
                f"(sprawdzono {max_units} slotów).")
    db.log_event('INFO', f'scan_units {host}:{port} znaleziono {len(units_found)} jednostek')
    return {'success': True, 'error': None, 'units': units_found, 'gateway_status': gateway_status}
