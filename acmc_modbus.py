"""
ACMC Modbus TCP - klient niskiego poziomu (pymodbus 3.x).

Bramka ACMC to POJEDYNCZY serwer/slave Modbus TCP. Zgodnie z dokumentacją:
"Urządzenie odpowie na zapytanie Modbus niezależnie od podanego adresu
docelowego (unit/device id). Zgodnie ze specyfikacją, powinien być
w takim przypadku stosowany adres 0xFF."

Bramka obsługuje wyłącznie dwie funkcje Modbus:
  - 0x04 Read Input Registers  (odczyt statusu bramki i jednostek)
  - 0x10 Write Multiple Registers (zapis parametrów jednostki)

Wszystkie metody zwracają dict: {"success": bool, "data"/"error": ...}
"""
from typing import Optional

try:
    from pymodbus.client import ModbusTcpClient
    HAVE_PYMODBUS = True
except Exception:
    HAVE_PYMODBUS = False

DEFAULT_DEVICE_ID = 0xFF  # bramka ignoruje adres docelowy, ale spec zaleca 0xFF


class MockResponse:
    def __init__(self, registers=None):
        self.registers = registers or []

    def isError(self):
        return False


class MockClient:
    """Prosty symulator bramki ACMC - używany WYŁĄCZNIE jako fallback,
    gdy biblioteka pymodbus nie jest zainstalowana. Nigdy nie jest domyślnym
    trybem pracy aplikacji (nie ma przełącznika 'tryb testowy' w GUI)."""

    def __init__(self, host, port=502, timeout=3):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connected = False
        # symulacja: rejestr statusu (RDY=1) + jedna przykładowa jednostka
        self._regs = {0: 0b0000000000000001}
        self._regs[1] = (1 << 15) | 0x01   # AC=1, GN=0, UN=1
        self._regs[2] = 0                  # FS
        self._regs[3] = 1                  # MD (chłodzenie)
        self._regs[4] = 24                 # ST
        self._regs[5] = 1                  # flagi: ON=1
        self._regs[6] = 26                 # AT
        self._regs[7] = 0                  # ER

    def connect(self):
        if self.host not in ('127.0.0.1', 'localhost'):
            self.connected = False
            return False
        self.connected = True
        return True

    def close(self):
        self.connected = False

    def read_input_registers(self, address, count=1, device_id=1, **kw):
        if not self.connected:
            raise ConnectionError('Symulator: brak połączenia')
        return MockResponse([self._regs.get(address + i, 0) for i in range(count)])

    def write_registers(self, address, values, device_id=1, **kw):
        if not self.connected:
            raise ConnectionError('Symulator: brak połączenia')
        for i, v in enumerate(values):
            self._regs[address + i] = v & 0xFFFF
        return MockResponse()


class ACMCModbusClient:
    """Klient Modbus TCP dla bramki ACMC (device_id domyślnie = 0xFF)."""

    def __init__(self, host: str = '127.0.0.1', port: int = 502,
                 device_id: int = DEFAULT_DEVICE_ID, timeout: float = 3.0,
                 use_mock: Optional[bool] = None):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.timeout = timeout
        if use_mock is None:
            use_mock = not HAVE_PYMODBUS
        self._use_mock = use_mock
        self._client = None

    def connect(self) -> dict:
        try:
            if self._use_mock:
                self._client = MockClient(self.host, self.port, self.timeout)
            else:
                self._client = ModbusTcpClient(self.host, port=self.port, timeout=self.timeout)
            ok = self._client.connect()
            if not ok:
                return {"success": False, "error": f"Nie można połączyć się z {self.host}:{self.port}"}
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self):
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass

    def read_input_registers(self, address: int, count: int) -> dict:
        """Read Input Registers (0x04)."""
        try:
            resp = self._client.read_input_registers(address, count=count, device_id=self.device_id)
            if hasattr(resp, 'isError') and resp.isError():
                return {"success": False, "error": str(resp)}
            return {"success": True, "data": list(resp.registers)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_registers(self, address: int, values) -> dict:
        """Write Multiple Registers (0x10)."""
        try:
            resp = self._client.write_registers(address, list(values), device_id=self.device_id)
            if hasattr(resp, 'isError') and resp.isError():
                return {"success": False, "error": str(resp)}
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
