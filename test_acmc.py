"""
Simple test script to exercise ACMCModbusClient in mock mode.
This script is safe to run without pymodbus installed.
"""
from acmc_modbus import ACMCModbusClient


def run_tests():
    print("Starting ACMCModbusClient tests (mock mode)...")
    client = ACMCModbusClient(host='localhost', port=502, unit_id=1, use_mock=True)
    res = client.connect()
    print('connect ->', res)
    assert res.get('success'), 'connect failed in mock mode'

    # write a register and read it back
    w = client.write_register(10, 1234)
    print('write_register ->', w)
    assert w.get('success'), 'write_register failed'

    r = client.read_holding_registers(10, 1)
    print('read_holding_registers ->', r)
    assert r.get('success') and r.get('data')[0] == 1234, 'read_holding_registers mismatch'

    # write a coil and read it back
    wc = client.write_coil(5, True)
    print('write_coil ->', wc)
    assert wc.get('success'), 'write_coil failed'

    rc = client.read_coils(5, 1)
    print('read_coils ->', rc)
    assert rc.get('success') and rc.get('data')[0] is True, 'read_coils mismatch'

    client.close()
    print('All mock tests passed.')


if __name__ == '__main__':
    run_tests()
