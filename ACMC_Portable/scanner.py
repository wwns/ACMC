"""
Moduł skanujący jednostki Modbus (unit IDs) na danym hoście:port.
Funkcja scan_units(host, port, unit_range, timeout, use_mock) zwraca listę tupli (unit, ok, details)
Zapisuje wyniki do bazy danych przez db.save_scan_result
"""
from acmc_modbus import ACMCModbusClient
from typing import List, Tuple
import concurrent.futures
import logger
import db


def _probe_one(host: str, port: int, unit: int, timeout: float):
    # SKANOWANIE: zawsze używaj Mock (prawidłowy - zwraca errors dla real IP)
    client = ACMCModbusClient(host=host, port=port, unit_id=unit, timeout=timeout, use_mock=True)
    res = client.connect()
    if not res.get('success'):
        details = res.get('error', '')
        db.save_scan_result(host, port, unit, False, details)
        return (unit, False, details)
    # try a quick read of one holding register
    r = client.read_holding_registers(0, 1)
    client.close()
    if r.get('success'):
        details = str(r.get('data'))
        db.save_scan_result(host, port, unit, True, details)
        return (unit, True, details)
    else:
        details = r.get('error', '')
        db.save_scan_result(host, port, unit, False, details)
        return (unit, False, details)


def scan_units(host: str = '127.0.0.1', port: int = 502, unit_range: range = range(1, 11), timeout: float = 1.0, use_mock: bool = True) -> List[Tuple[int, bool, str]]:
    # SKANOWANIE ZAWSZE TESTUJE POŁĄCZENIE (przez prawidłowy MockClient)
    # - localhost:502 → OK (symulacja)
    # - Real IP → FAIL (symulacja: "brak nasłuchu")
    results = []
    logger.info(f"Rozpoczynam skanowanie {host}:{port} dla jednostek {unit_range.start}-{unit_range.stop-1}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
        futures = {ex.submit(_probe_one, host, port, unit, timeout): unit for unit in unit_range}
        for fut in concurrent.futures.as_completed(futures):
            try:
                res = fut.result()
            except Exception as e:
                unit = futures.get(fut)
                res = (unit, False, str(e))
            results.append(res)
    logger.info(f"Skanowanie zakończone, znaleziono: {sum(1 for r in results if r[1])} urządzeń")
    return sorted(results, key=lambda x: x[0])
