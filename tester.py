"""
Testy i sterowanie jednostkami LG podłączonymi do bramki ACMC.

Bramka to JEDEN serwer Modbus TCP (patrz acmc_modbus.py / acmc_registers.py).
"Jednostka" = numer slotu w tabeli rejestrów (1..250), NIE unit/device id Modbus.
"""
from typing import Dict
import socket

from acmc_modbus import ACMCModbusClient
from acmc_registers import (
    unit_base, decode_unit_block, decode_gateway_status, encode_unit_write_block,
    fan_percent_to_fs, REGS_PER_UNIT,
)
import db
import logger


def test_gateway_pc(host: str, port: int, timeout: float = 2.0) -> dict:
    """Test komunikacji: bramka ACMC <-> komputer (na którym działa aplikacja).
    Sprawdza połączenie TCP oraz odczyt rejestru statusu ogólnego (0x04, adres 0)."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
    except Exception as e:
        logger.error(f'test_gateway_pc: brak połączenia TCP {host}:{port}: {e}')
        db.log_event('ERROR', f'test_gateway_pc TCP fail {host}:{port} {e}')
        return {'success': False, 'details': f'Brak połączenia TCP z {host}:{port}: {e}'}

    client = ACMCModbusClient(host=host, port=port, timeout=timeout)
    c = client.connect()
    if not c.get('success'):
        return {'success': False, 'details': f'TCP OK, ale Modbus nie odpowiada: {c.get("error")}'}

    r = client.read_input_registers(0, 1)
    client.close()
    if not r.get('success'):
        db.log_event('ERROR', f'test_gateway_pc Modbus read fail {r.get("error")}')
        return {'success': False, 'details': f'Brak odpowiedzi Modbus (rejestr statusu): {r.get("error")}'}

    status = decode_gateway_status(r['data'][0])
    details = (f'Połączenie komp <-> bramka OK. '
               f'RDY={status["rdy"]}, BSY={status["bsy"]}, SCN={status["scn"]}, '
               f'błąd bramki: {status["error_text"]}')
    db.log_event('INFO', f'test_gateway_pc OK {host}:{port} {details}')
    logger.info(f'test_gateway_pc: {details}')
    return {'success': True, 'details': details, 'status': status}


def test_gateway_plate(host: str, port: int, unit_index: int, timeout: float = 2.0) -> dict:
    """Test komunikacji: bramka ACMC <-> płyta sterująca jednostki LG (magistrala RS485).
    Odczytuje rejestr błędu (ER) konkretnej jednostki - to on odzwierciedla stan
    komunikacji bramki z płytą tej konkretnej jednostki (kody błędów wg dokumentacji)."""
    client = ACMCModbusClient(host=host, port=port, timeout=timeout)
    c = client.connect()
    if not c.get('success'):
        return {'success': False, 'details': f'Brak połączenia: {c.get("error")}'}

    base = unit_base(unit_index)
    r = client.read_input_registers(base, REGS_PER_UNIT)
    client.close()
    if not r.get('success'):
        db.log_event('ERROR', f'test_gateway_plate unit={unit_index} fail {r.get("error")}')
        return {'success': False, 'details': f'Błąd odczytu rejestrów: {r.get("error")}'}

    info = decode_unit_block(r['data'])
    if not info['present']:
        details = f'Slot {unit_index}: brak podłączonej jednostki (AC=0, VENT=0)'
        db.log_event('ERROR', f'test_gateway_plate {details}')
        return {'success': False, 'details': details}

    ok = info['er'] == 0
    details = (f'Jednostka {unit_index} (grupa {info["gn"]}, nr {info["un"]}): '
               f'ER={info["er"]} ({info["er_text"]})')
    db.log_event('INFO' if ok else 'ERROR', f'test_gateway_plate {details}')
    logger.info(f'test_gateway_plate: {details}')
    return {'success': ok, 'details': details, 'unit': info}


def read_unit_registers(host: str, port: int, unit_index: int, timeout: float = 2.0) -> dict:
    """Odczytuje i dekoduje blok 7 rejestrów danej jednostki."""
    client = ACMCModbusClient(host=host, port=port, timeout=timeout)
    c = client.connect()
    if not c.get('success'):
        return {'success': False, 'error': c.get('error')}
    base = unit_base(unit_index)
    r = client.read_input_registers(base, REGS_PER_UNIT)
    client.close()
    if not r.get('success'):
        return {'success': False, 'error': r.get('error')}
    info = decode_unit_block(r['data'])
    info['index'] = unit_index
    info['base'] = base
    return {'success': True, 'data': info}


def write_unit_params(host: str, port: int, unit_index: int, fs: int, md: int, st: int,
                       pf: bool = False, pl: bool = False, auto_swing: bool = False,
                       on: bool = True, timeout: float = 2.0) -> dict:
    """Zapisuje pełny blok parametrów jednostki (Write Multiple Registers, 0x10).
    Zgodnie z dokumentacją: przed zapisem sprawdzana jest flaga gotowości (RDY)
    rejestru statusu ogólnego bramki."""
    if not (18 <= st <= 30):
        return {'success': False, 'details': 'Temperatura zadana poza zakresem 18-30°C'}
    if not (0 <= fs <= 5):
        return {'success': False, 'details': 'Nieprawidłowy kod intensywności nawiewu (0-5)'}
    if not (0 <= md <= 4):
        return {'success': False, 'details': 'Nieprawidłowy kod trybu pracy (0-4)'}

    client = ACMCModbusClient(host=host, port=port, timeout=timeout)
    c = client.connect()
    if not c.get('success'):
        return {'success': False, 'details': f'Brak połączenia: {c.get("error")}'}

    # sprawdź gotowość bramki (RDY) przed zapisem - wymóg z dokumentacji
    rstat = client.read_input_registers(0, 1)
    if rstat.get('success'):
        status = decode_gateway_status(rstat['data'][0])
        if not status['rdy']:
            client.close()
            msg = f'Bramka nie jest gotowa do zapisu (RDY=0, BSY={status["bsy"]}, SCN={status["scn"]})'
            logger.error(f'write_unit_params: {msg}')
            db.log_event('ERROR', f'write_unit_params abort unit={unit_index} {msg}')
            return {'success': False, 'details': msg}

    base = unit_base(unit_index)
    values = encode_unit_write_block(fs, md, st, pf=pf, pl=pl, auto_swing=auto_swing, on=on)
    w = client.write_registers(base, values)
    client.close()

    details = (f'Zapisano blok jednostki {unit_index} (adres {base}): '
               f'FS={fs} MD={md} ST={st} PF={pf} PL={pl} AS={auto_swing} ON={on}')
    if w.get('success'):
        db.log_event('INFO', f'write_unit_params OK {details}')
        logger.info(details)
        return {'success': True, 'details': details}
    else:
        err = f'{details} -> BŁĄD: {w.get("error")}'
        db.log_event('ERROR', err)
        logger.error(err)
        return {'success': False, 'details': err}


def send_control(host: str, port: int, unit_index: int, fan_speed_percent: int = 50,
                  temp_setpoint: float = 22.0, mode: int = 0, on: bool = True,
                  timeout: float = 2.0) -> dict:
    """Szybkie sterowanie: nawiew w % (0-100, mapowany na kod FS) + temperatura w °C."""
    fs = fan_percent_to_fs(fan_speed_percent)
    st = int(round(float(temp_setpoint)))
    return write_unit_params(host, port, unit_index, fs=fs, md=mode, st=st, on=on, timeout=timeout)


def test_unit(host: str, port: int, unit_index: int, timeout: float = 2.0) -> Dict[str, Dict]:
    """Pełny test danej jednostki: odczyt rejestrów, obecność, błąd jednostki (ER)."""
    results = {}
    r = read_unit_registers(host, port, unit_index, timeout=timeout)
    if not r.get('success'):
        results['read_registers'] = {'success': False, 'details': str(r.get('error'))}
        db.save_test_result(host, port, unit_index, 'read_registers', False, str(r.get('error')))
        return results

    info = r['data']
    results['read_registers'] = {'success': True, 'details': str(info['raw'])}
    db.save_test_result(host, port, unit_index, 'read_registers', True, str(info['raw']))

    present_ok = info['present']
    results['obecnosc'] = {'success': present_ok, 'details': f'AC={info["ac"]} VENT={info["vent"]}'}
    db.save_test_result(host, port, unit_index, 'obecnosc', present_ok, str(info))

    error_ok = info['er'] == 0
    results['blad_jednostki'] = {'success': error_ok, 'details': info['er_text']}
    db.save_test_result(host, port, unit_index, 'blad_jednostki', error_ok, info['er_text'])

    logger.info(f'test_unit {unit_index}: {results}')
    return results
