"""
Moduł testujący 'splity' (jednostki Modbus). Pozwala wykonać zestaw testów na danej jednostce.
Udostępnia funkcję test_unit(host, port, unit, tests) gdzie tests to lista testów (nazw) - implementujemy kilka podstawowych testów:
- read_registers: czy można odczytać zakres rejestrów
- write_read_register: zapis i odczyt pojedynczego rejestru
- read_coils: czy można odczytać cewki

Zapisuje wyniki do bazy danych.
"""
from acmc_modbus import ACMCModbusClient
from typing import List, Dict
import db
import logger


def test_unit(host: str, port: int, unit: int, tests: List[str] = None, timeout: float = 2.0, use_mock: bool = True) -> Dict[str, Dict]:
    if tests is None:
        tests = ['read_registers', 'write_read_register', 'read_coils']
    results = {}
    client = ACMCModbusClient(host=host, port=port, unit_id=unit, timeout=timeout, use_mock=use_mock)
    c_res = client.connect()
    if not c_res.get('success'):
        for t in tests:
            results[t] = {'success': False, 'details': 'connect failed: ' + str(c_res.get('error'))}
            db.save_test_result(host, port, unit, t, False, c_res.get('error', ''))
        logger.error(f"Test {unit} - connect failed: {c_res.get('error')}")
        return results

    # compute base register for this unit (each unit occupies 7 registers)
    base = (unit - 1) * 7 + 1  # registers for unit: base .. base+6 (1-based addressing in doc)

    # test: read_registers (read status/input registers for the unit)
    if 'read_registers' in tests:
        r = client.read_input_registers(base, 7)
        ok = r.get('success', False)
        details = str(r.get('data')) if ok else str(r.get('error', ''))
        results['read_registers'] = {'success': ok, 'details': details}
        db.save_test_result(host, port, unit, 'read_registers', ok, details)

    # test: write_read_register (write set temperature and read back)
    if 'write_read_register' in tests:
        # ST (Set Temperature) is at register base+3 (for first unit it's register 4)
        temp_val = 25  # test value within allowed range (18..30)
        st_reg = base + 3
        w = client.write_register(st_reg, temp_val)
        okw = w.get('success', False)
        details_w = '' if okw else str(w.get('error', ''))
        # read back from input registers (status) — ST should reflect set value
        rr = client.read_input_registers(st_reg, 1)
        okr = rr.get('success', False) and rr.get('data') and rr.get('data')[0] == temp_val
        details_r = str(rr.get('data')) if rr.get('success') else str(rr.get('error', ''))
        ok = okw and okr
        details = f"write:{details_w}; read:{details_r}"
        results['write_read_register'] = {'success': ok, 'details': details}
        db.save_test_result(host, port, unit, 'write_read_register', ok, details)

    # test: read_coils
    if 'read_coils' in tests:
        rc = client.read_coils(0, 8)
        ok = rc.get('success', False)
        details = str(rc.get('data')) if ok else str(rc.get('error', ''))
        results['read_coils'] = {'success': ok, 'details': details}
        db.save_test_result(host, port, unit, 'read_coils', ok, details)

    client.close()
    logger.info(f"Zakończono testy jednostki {unit}")
    return results


def read_unit_registers(host: str, port: int, unit: int, timeout: float = 2.0, use_mock: bool = True) -> dict:
    """Odczytuje blok 7 rejestrów dla danej jednostki i zwraca surowe dane jako listę.
    Zwraca {'success': bool, 'data': [...]}"""
    client = ACMCModbusClient(host=host, port=port, unit_id=unit, timeout=timeout, use_mock=use_mock)
    c_res = client.connect()
    if not c_res.get('success'):
        return {'success': False, 'error': c_res.get('error')}
    base = (unit - 1) * 7 + 1
    r = client.read_input_registers(base, 7)
    client.close()
    if r.get('success'):
        return {'success': True, 'data': r.get('data')}
    else:
        return {'success': False, 'error': r.get('error')}


def test_gateway_pc(host: str, port: int, timeout: float = 2.0) -> dict:
    """Sprawdza podstawową łączność TCP do bramki (host:port)."""
    import socket
    try:
        sock = socket.create_connection((host, port), timeout)
        sock.close()
        logger.info(f'gateway_pc: TCP connect to {host}:{port} OK')
        return {'success': True, 'details': 'TCP connect OK'}
    except Exception as e:
        logger.error(f'gateway_pc: connect failed {e}')
        return {'success': False, 'details': str(e)}


def test_gateway_plate(host: str, port: int, unit: int, timeout: float = 2.0, use_mock: bool = True) -> dict:
    """Sprawdza komunikację bramka <-> płyta (odczyt diagnostycznego rejestru)."""
    client = ACMCModbusClient(host=host, port=port, unit_id=unit, timeout=timeout, use_mock=use_mock)
    c_res = client.connect()
    if not c_res.get('success'):
        logger.error(f'gateway_plate: connect failed for unit {unit}: {c_res.get("error")}')
        return {'success': False, 'details': 'connect failed: ' + str(c_res.get('error'))}
    # read unit's status/input registers (base .. base+6)
    base = (unit - 1) * 7 + 1
    r = client.read_input_registers(base, 7)
    client.close()
    if r.get('success'):
        logger.info(f'gateway_plate: read OK for unit {unit}: {r.get("data")}')
        return {'success': True, 'details': str(r.get('data'))}
    else:
        logger.error(f'gateway_plate: read failed for unit {unit}: {r.get("error")}')
        return {'success': False, 'details': str(r.get('error'))}


def write_unit_params(host: str, port: int, unit: int, fs_code: int = 0, md_code: int = 0, st_val: int = 22, flags: int = 0, timeout: float = 2.0, use_mock: bool = True) -> dict:
    """Zapisuje parametry jednostki: FS, MD, ST i FLAGS (pojedyncze rejestry)."""
    client = ACMCModbusClient(host=host, port=port, unit_id=unit, timeout=timeout, use_mock=use_mock)
    c_res = client.connect()
    if not c_res.get('success'):
        logger.error(f'write_unit_params: connect failed for unit {unit}: {c_res.get("error")}')
        db.log_event('ERROR', f'write_unit_params connect failed {host}:{port} unit={unit} {c_res.get("error")}')
        return {'success': False, 'details': 'connect failed: ' + str(c_res.get('error'))}
    try:
        base = (unit - 1) * 7 + 1
        fan_reg = base + 1
        md_reg = base + 2
        st_reg = base + 3
        flags_reg = base + 4
        w1 = client.write_register(fan_reg, int(fs_code))
        w2 = client.write_register(md_reg, int(md_code))
        w3 = client.write_register(st_reg, int(st_val))
        w4 = client.write_register(flags_reg, int(flags))
        client.close()
        ok = all(bool(w.get('success', True)) for w in (w1, w2, w3, w4))
        details = f'fan_reg:{fan_reg} {w1}; md_reg:{md_reg} {w2}; st_reg:{st_reg} {w3}; flags_reg:{flags_reg} {w4}'
        db.log_event('INFO', f'write_unit_params unit={unit} fs={fs_code} md={md_code} st={st_val} flags={flags} -> {details}')
        logger.info(f'write_unit_params for unit {unit}: {details}')
        return {'success': ok, 'details': details}
    except Exception as e:
        client.close()
        logger.error(f'write_unit_params exception for unit {unit}: {e}')
        db.log_event('ERROR', f'write_unit_params exception {e}')
        return {'success': False, 'details': str(e)}


def send_control(host: str, port: int, unit: int, fan_speed: int = 50, temp_setpoint: float = 22.0, timeout: float = 2.0, use_mock: bool = True) -> dict:
    """Wysyła wartości sterujące do jednostki:
    - fan_speed -> rejestr 200 (0..100)
    - temp_setpoint -> rejestr 201 (wartość * 10, aby zachować jedną cyfrę po przecinku)
    Zwraca słownik z kluczem success i details.
    """
    client = ACMCModbusClient(host=host, port=port, unit_id=unit, timeout=timeout, use_mock=use_mock)
    c_res = client.connect()
    if not c_res.get('success'):
        logger.error(f'send_control: connect failed for unit {unit}: {c_res.get("error")}')
        db.log_event('ERROR', f'send_control connect failed {host}:{port} unit={unit} {c_res.get("error")}')
        return {'success': False, 'details': 'connect failed: ' + str(c_res.get('error'))}
    try:
        # map percentage (0..100) to FS codes: 0=AUTO, 1=VERY LOW, 2=LOW, 3=MIDDLE, 4=HIGH, 5=VERY HIGH
        perc = int(max(0, min(100, int(fan_speed))))
        if perc == 0:
            fs_code = 0
        elif perc <= 10:
            fs_code = 1
        elif perc <= 30:
            fs_code = 2
        elif perc <= 60:
            fs_code = 3
        elif perc <= 85:
            fs_code = 4
        else:
            fs_code = 5
        # ST (Set Temperature) is an integer degrees (18..30)
        st_val = int(round(float(temp_setpoint)))
        base = (unit - 1) * 7 + 1
        fan_reg = base + 1  # FS register
        st_reg = base + 3   # ST register
        w1 = client.write_register(fan_reg, fs_code)
        w2 = client.write_register(st_reg, st_val)
        client.close()
        ok = bool(w1.get('success', True)) and bool(w2.get('success', True))
        details = f'fan_reg:{fan_reg} write:{w1}; st_reg:{st_reg} write:{w2}'
        db.log_event('INFO', f'send_control unit={unit} fan={fs_code} temp={st_val} -> {details}')
        logger.info(f'send_control for unit {unit}: {details}')
        return {'success': ok, 'details': details}
    except Exception as e:
        client.close()
        logger.error(f'send_control exception for unit {unit}: {e}')
        db.log_event('ERROR', f'send_control exception {e}')
        return {'success': False, 'details': str(e)}
