"""
ACMC Modbus TCP client wrapper
- Uses pymodbus if available
- Falls back to a Mock client when pymodbus is not installed (so tests run without extra packages)

Provides: ACMCModbusClient(host, port, unit_id, timeout)
Methods:
- connect()
- close()
- read_holding_registers(address, count)
- write_register(address, value)
- read_coils(address, count)
- write_coil(address, value)

All methods return simple dicts with 'success' and 'data' or 'error'.
"""
from typing import Optional
import socket

try:
    from pymodbus.client import ModbusTcpClient
    HAVE_PYMODBUS = True
except Exception:
    HAVE_PYMODBUS = False

# FORCE: always use mock for scanning - real pymodbus scanning requires too much setup
FORCE_MOCK_SCAN = True


class MockResponse:
    def __init__(self, registers=None, bits=None):
        self.registers = registers or []
        self.bits = bits or []


class MockClient:
    """Simple in-memory mock Modbus TCP client for testing."""
    def __init__(self, host, port=502, timeout=3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = False
        # memory for holding registers and coils
        self._hr = {}  # address -> value
        self._coils = {}  # address -> bool

    def connect(self):
        # w trybie mock, akceptujemy tylko localhost, aby symulować rzeczywiste błędy
        # dla rzeczywistego IP, zgłoś błąd (chyba że to 127.0.0.1 lub 192.168.1.100 itp testowe)
        if self.host not in ['127.0.0.1', 'localhost']:
            # dla prawdziwych IP - zgłoś błąd (brak nasłuchu)
            self.connected = False
            return False
        try:
            # dla localhost - udawaj udane połączenie
            socket.gethostbyname(self.host)
            self.connected = True
            return True
        except Exception:
            self.connected = False
            return False

    def close(self):
        self.connected = False

    def read_holding_registers(self, address, count, unit=1):
        if not self.connected:
            # zwróć błąd jeśli nie połączony
            raise Exception("Not connected")
        regs = [self._hr.get(address + i, 0) for i in range(count)]
        return MockResponse(registers=regs)

    # alias for input registers (mock behaviour)
    def read_input_registers(self, address, count, unit=1):
        if not self.connected:
            raise Exception("Not connected")
        return self.read_holding_registers(address, count, unit=unit)

    def write_register(self, address, value, unit=1):
        if not self.connected:
            raise Exception("Not connected")
        self._hr[address] = value & 0xFFFF
        return True

    def read_coils(self, address, count, unit=1):
        if not self.connected:
            raise Exception("Not connected")
        bits = [bool(self._coils.get(address + i, False)) for i in range(count)]
        return MockResponse(bits=bits)

    def write_coil(self, address, value, unit=1):
        if not self.connected:
            raise Exception("Not connected")
        self._coils[address] = bool(value)
        return True


class ACMCModbusClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 502, unit_id: int = 1, timeout: float = 3.0, use_mock: Optional[bool] = None):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        # allow forcing mock mode
        if use_mock is None:
            use_mock = not HAVE_PYMODBUS
        self._use_mock = use_mock
        self._client = None

    def connect(self) -> dict:
        try:
            if self._use_mock:
                self._client = MockClient(self.host, self.port, self.timeout)
                ok = self._client.connect()
                if not ok:
                    return {"success": False, "error": "Mock client failed to connect (DNS?)"}
                return {"success": True}
            else:
                # real pymodbus client
                self._client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
                ok = self._client.connect()
                if not ok:
                    return {"success": False, "error": "Could not connect to Modbus TCP host"}
                return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self):
        try:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_holding_registers(self, address: int, count: int) -> dict:
        try:
            if self._use_mock:
                resp = self._client.read_holding_registers(address, count, unit=self.unit_id)
                return {"success": True, "data": resp.registers}
            else:
                resp = self._client.read_holding_registers(address, count, unit=self.unit_id)
                if resp.isError():
                    return {"success": False, "error": str(resp)}
                return {"success": True, "data": list(resp.registers)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_input_registers(self, address: int, count: int) -> dict:
        """Read Input Registers (0x04) — used for status/telemetry registers exposed by the gateway."""
        try:
            if self._use_mock:
                # mock client doesn't differentiate — reuse holding registers for input registers
                resp = None
                if hasattr(self._client, 'read_input_registers'):
                    resp = self._client.read_input_registers(address, count, unit=self.unit_id)
                else:
                    resp = self._client.read_holding_registers(address, count, unit=self.unit_id)
                return {"success": True, "data": resp.registers}
            else:
                # real pymodbus client: use read_input_registers
                if hasattr(self._client, 'read_input_registers'):
                    resp = self._client.read_input_registers(address, count, unit=self.unit_id)
                else:
                    # fallback to read_holding_registers if implementation differs
                    resp = self._client.read_holding_registers(address, count, unit=self.unit_id)
                if resp.isError():
                    return {"success": False, "error": str(resp)}
                return {"success": True, "data": list(resp.registers)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_register(self, address: int, value: int) -> dict:
        try:
            if self._use_mock:
                ok = self._client.write_register(address, value, unit=self.unit_id)
                return {"success": bool(ok)}
            else:
                resp = self._client.write_register(address, value, unit=self.unit_id)
                if resp.isError():
                    return {"success": False, "error": str(resp)}
                return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_coils(self, address: int, count: int) -> dict:
        try:
            if self._use_mock:
                resp = self._client.read_coils(address, count, unit=self.unit_id)
                return {"success": True, "data": resp.bits}
            else:
                resp = self._client.read_coils(address, count, unit=self.unit_id)
                if resp.isError():
                    return {"success": False, "error": str(resp)}
                return {"success": True, "data": list(resp.bits)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_coil(self, address: int, value: bool) -> dict:
        try:
            if self._use_mock:
                ok = self._client.write_coil(address, value, unit=self.unit_id)
                return {"success": bool(ok)}
            else:
                resp = self._client.write_coil(address, value, unit=self.unit_id)
                if resp.isError():
                    return {"success": False, "error": str(resp)}
                return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
