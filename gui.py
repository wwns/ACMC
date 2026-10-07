"""
Simple Tkinter GUI for interacting with the ACMC gateway via Modbus TCP.
Uses ACMCModbusClient from acmc_modbus.py

Features:
- Connect / Disconnect
- Read holding registers
- Write single register
- Read coils
- Write single coil
- Simple log area

This GUI is intentionally lightweight and uses standard library only (tkinter).
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from acmc_modbus import ACMCModbusClient
import threading
import queue


class ACMCGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ACMC Modbus TCP Client")
        self.geometry("820x520")

        self.client = None
        self._worker_thread = None
        self._q = queue.Queue()

        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Connection frame
        conn_frame = ttk.Labelframe(frame, text="Connection")
        conn_frame.grid(row=0, column=0, sticky=tk.EW, padx=4, pady=4)

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(conn_frame, textvariable=self.host_var, width=18).grid(row=0, column=1)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky=tk.W)
        self.port_var = tk.IntVar(value=502)
        ttk.Entry(conn_frame, textvariable=self.port_var, width=8).grid(row=0, column=3)

        ttk.Label(conn_frame, text="Unit ID:").grid(row=0, column=4, sticky=tk.W)
        self.unit_var = tk.IntVar(value=1)
        ttk.Entry(conn_frame, textvariable=self.unit_var, width=6).grid(row=0, column=5)

        self.mock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(conn_frame, text="Use Mock (no pymodbus)", variable=self.mock_var).grid(row=0, column=6, padx=8)

        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self._connect)
        self.connect_btn.grid(row=0, column=7, padx=6)

        # Operations frame
        ops_frame = ttk.Labelframe(frame, text="Operations")
        ops_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=4, pady=4)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(ops_frame, text="Read HR Address:").grid(row=0, column=0, sticky=tk.W)
        self.read_addr_var = tk.IntVar(value=0)
        ttk.Entry(ops_frame, textvariable=self.read_addr_var, width=8).grid(row=0, column=1)

        ttk.Label(ops_frame, text="Count:").grid(row=0, column=2, sticky=tk.W)
        self.read_count_var = tk.IntVar(value=4)
        ttk.Entry(ops_frame, textvariable=self.read_count_var, width=6).grid(row=0, column=3)

        ttk.Button(ops_frame, text="Read Holding Registers", command=self._read_holding).grid(row=0, column=4, padx=6)

        ttk.Label(ops_frame, text="Write HR Addr:").grid(row=1, column=0, sticky=tk.W)
        self.write_addr_var = tk.IntVar(value=0)
        ttk.Entry(ops_frame, textvariable=self.write_addr_var, width=8).grid(row=1, column=1)

        ttk.Label(ops_frame, text="Value:").grid(row=1, column=2, sticky=tk.W)
        self.write_val_var = tk.IntVar(value=0)
        ttk.Entry(ops_frame, textvariable=self.write_val_var, width=8).grid(row=1, column=3)

        ttk.Button(ops_frame, text="Write Register", command=self._write_register).grid(row=1, column=4, padx=6)

        ttk.Separator(ops_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=8, sticky=tk.EW, pady=6)

        ttk.Label(ops_frame, text="Read Coil Addr:").grid(row=3, column=0, sticky=tk.W)
        self.read_coil_addr = tk.IntVar(value=0)
        ttk.Entry(ops_frame, textvariable=self.read_coil_addr, width=8).grid(row=3, column=1)

        ttk.Label(ops_frame, text="Count:").grid(row=3, column=2, sticky=tk.W)
        self.read_coil_count = tk.IntVar(value=8)
        ttk.Entry(ops_frame, textvariable=self.read_coil_count, width=6).grid(row=3, column=3)

        ttk.Button(ops_frame, text="Read Coils", command=self._read_coils).grid(row=3, column=4, padx=6)

        ttk.Label(ops_frame, text="Write Coil Addr:").grid(row=4, column=0, sticky=tk.W)
        self.write_coil_addr = tk.IntVar(value=0)
        ttk.Entry(ops_frame, textvariable=self.write_coil_addr, width=8).grid(row=4, column=1)

        ttk.Label(ops_frame, text="On/Off:").grid(row=4, column=2, sticky=tk.W)
        self.write_coil_val = tk.BooleanVar(value=False)
        ttk.Checkbutton(ops_frame, variable=self.write_coil_val).grid(row=4, column=3)

        ttk.Button(ops_frame, text="Write Coil", command=self._write_coil).grid(row=4, column=4, padx=6)

        # Log area
        log_frame = ttk.Labelframe(frame, text="Log")
        log_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=4, pady=4)
        frame.rowconfigure(2, weight=1)

        self.log = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=12)
        self.log.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg: str):
        self.log.insert(tk.END, msg + '\n')
        self.log.see(tk.END)

    def _connect(self):
        if self.client:
            # disconnect
            self._log("Closing connection...")
            self.client.close()
            self.client = None
            self.connect_btn.config(text="Connect")
            self._log("Disconnected")
            return

        host = self.host_var.get()
        port = int(self.port_var.get())
        unit = int(self.unit_var.get())
        use_mock = bool(self.mock_var.get())
        self.client = ACMCModbusClient(host=host, port=port, unit_id=unit, use_mock=use_mock)
        self._log(f"Connecting to {host}:{port} (unit {unit}) (mock={use_mock})...")

        def do_connect():
            res = self.client.connect()
            self._q.put(("connect_result", res))

        threading.Thread(target=do_connect, daemon=True).start()
        self.connect_btn.config(text="Disconnect")

    def _read_holding(self):
        if not self.client:
            messagebox.showwarning("Not connected", "Connect to the gateway first")
            return
        addr = int(self.read_addr_var.get())
        cnt = int(self.read_count_var.get())
        self._log(f"Reading holding registers at {addr} (count {cnt})...")

        def do_read():
            res = self.client.read_holding_registers(addr, cnt)
            self._q.put(("read_hr", (addr, cnt, res)))

        threading.Thread(target=do_read, daemon=True).start()

    def _write_register(self):
        if not self.client:
            messagebox.showwarning("Not connected", "Connect to the gateway first")
            return
        addr = int(self.write_addr_var.get())
        val = int(self.write_val_var.get())
        self._log(f"Writing register {addr} = {val}...")

        def do_write():
            res = self.client.write_register(addr, val)
            self._q.put(("write_hr", (addr, val, res)))

        threading.Thread(target=do_write, daemon=True).start()

    def _read_coils(self):
        if not self.client:
            messagebox.showwarning("Not connected", "Connect to the gateway first")
            return
        addr = int(self.read_coil_addr.get())
        cnt = int(self.read_coil_count.get())
        self._log(f"Reading coils at {addr} (count {cnt})...")

        def do_read():
            res = self.client.read_coils(addr, cnt)
            self._q.put(("read_coils", (addr, cnt, res)))

        threading.Thread(target=do_read, daemon=True).start()

    def _write_coil(self):
        if not self.client:
            messagebox.showwarning("Not connected", "Connect to the gateway first")
            return
        addr = int(self.write_coil_addr.get())
        val = bool(self.write_coil_val.get())
        self._log(f"Writing coil {addr} = {val}...")

        def do_write():
            res = self.client.write_coil(addr, val)
            self._q.put(("write_coil", (addr, val, res)))

        threading.Thread(target=do_write, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                item = self._q.get_nowait()
                kind = item[0]
                data = item[1]
                if kind == "connect_result":
                    res = data
                    if res.get("success"):
                        self._log("Connected successfully")
                    else:
                        self._log("Connect failed: " + str(res.get("error")))
                        self.client = None
                        self.connect_btn.config(text="Connect")
                elif kind == "read_hr":
                    addr, cnt, res = data
                    if res.get("success"):
                        vals = res.get("data")
                        self._log(f"HR @ {addr} [{cnt}]: {vals}")
                    else:
                        self._log("Read HR failed: " + str(res.get("error")))
                elif kind == "write_hr":
                    addr, val, res = data
                    if res.get("success"):
                        self._log(f"Write HR OK @ {addr} = {val}")
                    else:
                        self._log("Write HR failed: " + str(res.get("error")))
                elif kind == "read_coils":
                    addr, cnt, res = data
                    if res.get("success"):
                        vals = res.get("data")
                        self._log(f"Coils @ {addr} [{cnt}]: {vals}")
                    else:
                        self._log("Read coils failed: " + str(res.get("error")))
                elif kind == "write_coil":
                    addr, val, res = data
                    if res.get("success"):
                        self._log(f"Write coil OK @ {addr} = {val}")
                    else:
                        self._log("Write coil failed: " + str(res.get("error")))
                else:
                    self._log(f"Unknown queue item: {item}")
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)


def main():
    app = ACMCGui()
    app.mainloop()


if __name__ == '__main__':
    main()
