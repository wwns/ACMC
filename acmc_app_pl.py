"""
Polska wersja GUI aplikacji ACMC - sterowanie bramką Modbus TCP.
Uruchomienie: python acmc_app_pl.py
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import os
import sys

import scanner
import tester
import visual
import db
import logger
from acmc_registers import fan_percent_to_fs, FS_NAMES
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def resource_path(relative_path):
    """Zwraca prawidłową ścieżkę do zasobu - działa zarówno uruchomiony
    ze źródła Python, jak i spakowany przez PyInstaller (--onefile)."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


MODE_NAMES = ['AUTO', 'CHŁODZENIE', 'NAWIEW', 'GRZANIE', 'OSUSZANIE']


class AppPL(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ACMC - Narzędzie Modbus (PL)')
        self.geometry('1150x780')

        # === ikona aplikacji (acmc.png / acmc.ico) ===
        try:
            ico_path = resource_path('acmc.ico')
            png_path = resource_path('acmc.png')
            if os.path.exists(ico_path):
                self.iconbitmap(default=ico_path)
            if os.path.exists(png_path):
                self._icon_img = tk.PhotoImage(file=png_path)
                self.iconphoto(True, self._icon_img)
        except Exception as e:
            logger.error(f"Nie udało się załadować ikony: {e}")

        db.init_db()
        self._q = queue.Queue()
        self._units = {}  # index -> ostatnio odczytane dane jednostki
        self._build_ui()
        self._poll()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # --- Połączenie ---
        conn = ttk.Labelframe(frm, text='Połączenie z bramką ACMC')
        conn.grid(row=0, column=0, sticky='ew')
        ttk.Label(conn, text='Host:').grid(row=0, column=0, padx=(4, 0))
        self.host = tk.StringVar(value='192.168.1.10')
        ttk.Entry(conn, textvariable=self.host, width=16).grid(row=0, column=1)
        ttk.Label(conn, text='Port:').grid(row=0, column=2, padx=(8, 0))
        self.port = tk.IntVar(value=502)
        ttk.Entry(conn, textvariable=self.port, width=6).grid(row=0, column=3)
        ttk.Label(conn, text='Maks. jednostek:').grid(row=0, column=4, padx=(8, 0))
        self.max_units = tk.IntVar(value=250)
        ttk.Entry(conn, textvariable=self.max_units, width=6).grid(row=0, column=5)
        ttk.Button(conn, text='Skanuj jednostki', command=self._scan).grid(row=0, column=6, padx=8)
        ttk.Button(conn, text='Status bramki', command=self._check_gateway_status).grid(row=0, column=7, padx=4)

        self.gw_status_var = tk.StringVar(value='Status bramki: nieznany (wykonaj skanowanie lub sprawdź status)')
        ttk.Label(conn, textvariable=self.gw_status_var, foreground='#555').grid(
            row=1, column=0, columnspan=8, sticky='w', padx=4, pady=(4, 0))

        # --- wyniki + szczegóły + wizualizacja ---
        res_frame = ttk.Panedwindow(frm, orient=tk.HORIZONTAL)
        res_frame.grid(row=1, column=0, sticky='nsew', pady=8)
        frm.rowconfigure(1, weight=1)
        frm.columnconfigure(0, weight=1)

        left = ttk.Frame(res_frame)
        right = ttk.Frame(res_frame)
        res_frame.add(left, weight=1)
        res_frame.add(right, weight=1)

        ttk.Label(left, text='Znalezione jednostki:').pack(anchor='w')
        cols = ('slot', 'adres', 'typ', 'fs', 'md', 'st', 'at', 'on', 'er')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', height=12)
        headers = {
            'slot': 'Slot', 'adres': 'Adres (grupa.nr)', 'typ': 'Typ', 'fs': 'FS',
            'md': 'MD', 'st': 'ST (°C)', 'at': 'AT (°C)', 'on': 'ON', 'er': 'ER',
        }
        widths = {'slot': 45, 'adres': 100, 'typ': 55, 'fs': 110, 'md': 110, 'st': 60, 'at': 60, 'on': 45, 'er': 160}
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor='center')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', lambda e: self._on_selection_changed())

        btns = ttk.Frame(left)
        btns.pack(fill='x')
        ttk.Button(btns, text='Przetestuj wybraną jednostkę', command=self._test_selected).pack(side='left', padx=4, pady=4)
        ttk.Button(btns, text='Przetestuj wszystkie znalezione', command=self._test_all_found).pack(side='left', padx=4, pady=4)

        details_frame = ttk.Labelframe(left, text='Szczegóły jednostki')
        details_frame.pack(fill='x', pady=6)
        self.detail_vars = {k: tk.StringVar(value='') for k in
                             ('slot', 'adres', 'typ', 'fs', 'md', 'st', 'at', 'flags', 'er')}
        rows = [
            ('Slot:', 'slot'), ('Adres (grupa.nr):', 'adres'), ('Typ jednostki:', 'typ'),
            ('Nawiew (FS):', 'fs'), ('Tryb (MD):', 'md'), ('Temp. zadana (ST):', 'st'),
            ('Temp. zmierzona (AT):', 'at'), ('Flagi (FA/PF/PL/AS/ON):', 'flags'),
            ('Błąd jednostki (ER):', 'er'),
        ]
        for i, (label, key) in enumerate(rows):
            ttk.Label(details_frame, text=label).grid(row=i, column=0, sticky='w', padx=4)
            ttk.Label(details_frame, textvariable=self.detail_vars[key]).grid(row=i, column=1, sticky='w', padx=4)

        # --- prawa strona: wizualizacja + log + sterowanie ---
        ttk.Label(right, text='Wizualizacja:').pack(anchor='w')
        self.fig_canvas = None
        self.canvas_container = ttk.Frame(right)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text='Log:').pack(anchor='w')
        self.log = ScrolledText(right, height=8)
        self.log.pack(fill=tk.BOTH, expand=False)

        ctrl = ttk.Labelframe(right, text='Sterowanie wybraną jednostką i testy komunikacji')
        ctrl.pack(fill='x', pady=6)

        ttk.Label(ctrl, text='Nawiew (0-100%):').grid(row=0, column=0, sticky='w')
        self.fan_speed = tk.IntVar(value=50)
        tk.Spinbox(ctrl, from_=0, to=100, textvariable=self.fan_speed, width=6,
                   command=self._update_fan_preview).grid(row=0, column=1, sticky='w', padx=4)
        self.fan_preview = ttk.Label(ctrl, text='FS: 0 (AUTO)')
        self.fan_preview.grid(row=0, column=2, sticky='w', padx=4)

        ttk.Label(ctrl, text='Temp. zadana (18-30°C):').grid(row=0, column=3, sticky='w', padx=(12, 0))
        self.temp_setpoint = tk.DoubleVar(value=22.0)
        ttk.Entry(ctrl, textvariable=self.temp_setpoint, width=6).grid(row=0, column=4, sticky='w', padx=4)

        ttk.Label(ctrl, text='Tryb pracy (MD):').grid(row=1, column=0, sticky='w', pady=6)
        self.mode_cb = ttk.Combobox(ctrl, values=MODE_NAMES, state='readonly', width=12)
        self.mode_cb.current(0)
        self.mode_cb.grid(row=1, column=1, sticky='w')

        self.on_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl, text='Włączona (ON)', variable=self.on_var).grid(row=1, column=2, sticky='w', padx=4)
        self.pf_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text='Plasma (PF)', variable=self.pf_var).grid(row=1, column=3, sticky='w', padx=4)
        self.pl_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text='Blokada panelu (PL)', variable=self.pl_var).grid(row=1, column=4, sticky='w', padx=4)
        self.as_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text='Auto Swing (AS)', variable=self.as_var).grid(row=1, column=5, sticky='w', padx=4)

        ttk.Button(ctrl, text='Wyślij sterowanie (szybkie)', command=self._send_control).grid(
            row=2, column=0, columnspan=2, pady=6, sticky='w')
        ttk.Button(ctrl, text='Zapisz pełne parametry', command=self._save_params).grid(
            row=2, column=2, columnspan=2, pady=6, sticky='w')
        ttk.Button(ctrl, text='Test: bramka ↔ komp', command=self._test_gateway_pc).grid(
            row=3, column=0, columnspan=2, pady=4, sticky='w')
        ttk.Button(ctrl, text='Test: bramka ↔ płyta LG', command=self._test_gateway_plate).grid(
            row=3, column=2, columnspan=2, pady=4, sticky='w')

    # ------------------------------------------------------------ pomocnicze --
    def _log(self, msg: str):
        logger.info(msg)
        self.log.insert(tk.END, msg + '\n')
        self.log.see(tk.END)

    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], 'values')
        return int(vals[0])

    def _current_mode_code(self):
        name = self.mode_cb.get() or 'AUTO'
        return MODE_NAMES.index(name) if name in MODE_NAMES else 0

    # ------------------------------------------------------------------ skan --
    def _scan(self):
        host = self.host.get().strip()
        port = int(self.port.get())
        max_units = max(1, int(self.max_units.get()))
        self._log(f'Rozpoczynam skanowanie {host}:{port} (do {max_units} slotów jednostek)...')

        def do_scan():
            res = scanner.scan_units(host=host, port=port, max_units=max_units, timeout=3.0)
            self._q.put(('scan_done', res))

        threading.Thread(target=do_scan, daemon=True).start()

    def _check_gateway_status(self):
        host = self.host.get().strip()
        port = int(self.port.get())
        self._log(f'Sprawdzam status bramki {host}:{port}...')

        def do_check():
            res = tester.test_gateway_pc(host, port)
            self._q.put(('gateway_pc_done', res))

        threading.Thread(target=do_check, daemon=True).start()

    def _on_scan_done(self, result):
        if not result.get('success'):
            self._log(f"BŁĄD skanowania: {result.get('error')}")
            messagebox.showerror('Błąd skanowania', str(result.get('error')))
            return

        units = result.get('units', [])
        self._units = {u['index']: u for u in units}

        for i in self.tree.get_children():
            self.tree.delete(i)
        for u in units:
            typ = 'AC' if u['ac'] else ('VENT' if u['vent'] else '?')
            self.tree.insert('', 'end', values=(
                u['index'], f"{u['gn']}.{u['un']}", typ, f"{u['fs']} ({u['fs_text']})",
                f"{u['md']} ({u['md_text']})", u['st'], u['at'], 'TAK' if u['on'] else 'nie', u['er_text'],
            ))

        gw = result.get('gateway_status')
        if gw:
            self.gw_status_var.set(
                f"Status bramki: RDY={gw['rdy']}  BSY={gw['bsy']}  SCN={gw['scn']}  błąd={gw['error_text']}"
            )

        fig = visual.make_figure_from_scan(units)
        if self.fig_canvas:
            self.fig_canvas.get_tk_widget().destroy()
        self.fig_canvas = FigureCanvasTkAgg(fig, master=self.canvas_container)
        self.fig_canvas.draw()
        self.fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._log(f'Skanowanie zakończone. Znaleziono {len(units)} jednostek.')

    # ------------------------------------------------------------------ testy --
    def _test_selected(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        host, port = self.host.get().strip(), int(self.port.get())
        self._log(f'Rozpoczynam test jednostki {idx}...')

        def do_test():
            res = tester.test_unit(host, port, idx)
            self._q.put(('test_done_single', (idx, res)))

        threading.Thread(target=do_test, daemon=True).start()

    def _test_all_found(self):
        if not self._units:
            messagebox.showwarning('Uwaga', 'Brak znalezionych jednostek do testu (wykonaj skanowanie)')
            return
        host, port = self.host.get().strip(), int(self.port.get())
        indices = list(self._units.keys())
        self._log(f'Rozpoczynam testy dla {len(indices)} jednostek...')

        def do_tests():
            all_res = {i: tester.test_unit(host, port, i) for i in indices}
            self._q.put(('test_done_all', all_res))

        threading.Thread(target=do_tests, daemon=True).start()

    def _on_test_single(self, idx, res):
        self._log(f'Wyniki testu jednostki {idx}:')
        for k, v in res.items():
            self._log(f" - {k}: {'OK' if v.get('success') else 'BŁĄD'} ({v.get('details')})")
        messagebox.showinfo('Test zakończony', f'Testy dla jednostki {idx} zakończone')

    def _on_test_all(self, all_res):
        ok_count = sum(1 for r in all_res.values() if all(v.get('success') for v in r.values()))
        self._log(f'Testy wszystkich zakończone. Całkowicie OK: {ok_count} / {len(all_res)}')
        messagebox.showinfo('Testy zakończone', f'Całkowicie OK: {ok_count} / {len(all_res)}')

    def _on_selection_changed(self):
        idx = self._selected_index()
        if idx is None:
            return
        host, port = self.host.get().strip(), int(self.port.get())
        self._log(f'Pobieram rejestry jednostki {idx}...')

        def do_read():
            res = tester.read_unit_registers(host, port, idx)
            self._q.put(('unit_regs', (idx, res)))

        threading.Thread(target=do_read, daemon=True).start()

    def _update_fan_preview(self):
        perc = max(0, min(100, int(self.fan_speed.get())))
        code = fan_percent_to_fs(perc)
        self.fan_preview.config(text=f'FS: {code} ({FS_NAMES.get(code, code)})')

    # ------------------------------------------------------------- sterowanie --
    def _save_params(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        host, port = self.host.get().strip(), int(self.port.get())
        fs_code = fan_percent_to_fs(int(self.fan_speed.get()))
        md_code = self._current_mode_code()
        try:
            st_val = int(round(float(self.temp_setpoint.get())))
        except Exception:
            messagebox.showerror('Błąd', 'Temp. zadana musi być liczbą')
            return
        if not (18 <= st_val <= 30):
            messagebox.showerror('Błąd', 'Temp. zadana poza zakresem (18-30)')
            return

        pf, pl = bool(self.pf_var.get()), bool(self.pl_var.get())
        aswing, on = bool(self.as_var.get()), bool(self.on_var.get())
        self._log(f'Zapisuję parametry jednostki {idx}: FS={fs_code} MD={md_code} ST={st_val} '
                  f'PF={pf} PL={pl} AS={aswing} ON={on}')

        def do_write():
            res = tester.write_unit_params(host, port, idx, fs=fs_code, md=md_code, st=st_val,
                                            pf=pf, pl=pl, auto_swing=aswing, on=on)
            self._q.put(('write_params_done', (idx, res)))

        threading.Thread(target=do_write, daemon=True).start()

    def _send_control(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        host, port = self.host.get().strip(), int(self.port.get())
        fan = int(self.fan_speed.get())
        temp = float(self.temp_setpoint.get())
        md_code = self._current_mode_code()
        on = bool(self.on_var.get())
        self._log(f'Wysyłam sterowanie do jednostki {idx}: nawiew={fan}%, temp={temp}°C, tryb={md_code}, ON={on}')

        def do_send():
            res = tester.send_control(host, port, idx, fan_speed_percent=fan, temp_setpoint=temp,
                                       mode=md_code, on=on)
            self._q.put(('control_done', (idx, res)))

        threading.Thread(target=do_send, daemon=True).start()

    def _test_gateway_pc(self):
        host, port = self.host.get().strip(), int(self.port.get())
        self._log(f'Rozpoczynam test komunikacji bramka ↔ komp do {host}:{port}...')

        def do_test():
            res = tester.test_gateway_pc(host, port)
            self._q.put(('gateway_pc_done', res))

        threading.Thread(target=do_test, daemon=True).start()

    def _test_gateway_plate(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        host, port = self.host.get().strip(), int(self.port.get())
        self._log(f'Rozpoczynam test komunikacji bramka ↔ płyta LG dla jednostki {idx}...')

        def do_test():
            res = tester.test_gateway_plate(host, port, idx)
            self._q.put(('gateway_plate_done', (idx, res)))

        threading.Thread(target=do_test, daemon=True).start()

    # -------------------------------------------------------------------- poll --
    def _poll(self):
        try:
            while True:
                kind, data = self._q.get_nowait()
                if kind == 'scan_done':
                    self._on_scan_done(data)
                elif kind == 'test_done_single':
                    idx, res = data
                    self._on_test_single(idx, res)
                elif kind == 'test_done_all':
                    self._on_test_all(data)
                elif kind == 'control_done':
                    idx, res = data
                    self._log(f'Wynik sterowania dla jednostki {idx}: {res}')
                    messagebox.showinfo('Sterowanie', f'Jednostka {idx}: {res.get("details", "")}')
                elif kind == 'gateway_pc_done':
                    self._log(f'Test bramka ↔ komp: {data}')
                    if data.get('success') and data.get('status'):
                        gw = data['status']
                        self.gw_status_var.set(
                            f"Status bramki: RDY={gw['rdy']}  BSY={gw['bsy']}  SCN={gw['scn']}  "
                            f"błąd={gw['error_text']}"
                        )
                    messagebox.showinfo('Test bramka ↔ komp', data.get('details', str(data)))
                elif kind == 'gateway_plate_done':
                    idx, res = data
                    self._log(f'Test bramka ↔ płyta LG dla jednostki {idx}: {res}')
                    messagebox.showinfo('Test bramka ↔ płyta LG', res.get('details', str(res)))
                elif kind == 'unit_regs':
                    idx, res = data
                    if res.get('success'):
                        info = res['data']
                        self._units[idx] = info
                        self.detail_vars['slot'].set(str(idx))
                        self.detail_vars['adres'].set(f"{info['gn']}.{info['un']}")
                        self.detail_vars['typ'].set('AC' if info['ac'] else ('VENT' if info['vent'] else '?'))
                        self.detail_vars['fs'].set(f"{info['fs']} ({info['fs_text']})")
                        self.detail_vars['md'].set(f"{info['md']} ({info['md_text']})")
                        self.detail_vars['st'].set(str(info['st']))
                        self.detail_vars['at'].set(str(info['at']))
                        self.detail_vars['flags'].set(
                            f"FA={info['fa']} PF={info['pf']} PL={info['pl']} AS={info['auto_swing']} ON={info['on']}"
                        )
                        self.detail_vars['er'].set(info['er_text'])

                        self.temp_setpoint.set(info['st'])
                        self.mode_cb.set(MODE_NAMES[info['md']] if info['md'] < len(MODE_NAMES) else 'AUTO')
                        self.on_var.set(info['on'])
                        self.pf_var.set(info['pf'])
                        self.pl_var.set(info['pl'])
                        self.as_var.set(info['auto_swing'])
                        self.fan_preview.config(text=f"FS: {info['fs']} ({info['fs_text']})")
                    else:
                        self._log(f"Błąd odczytu rejestrów jednostki {idx}: {res.get('error')}")
                        messagebox.showerror('Błąd odczytu', str(res.get('error')))
                elif kind == 'write_params_done':
                    idx, res = data
                    self._log(f'Zapis parametrów dla jednostki {idx}: {res}')
                    messagebox.showinfo('Zapis parametrów', res.get('details', str(res)))
        except queue.Empty:
            pass
        self.after(200, self._poll)


def main():
    app = AppPL()
    app.mainloop()


if __name__ == '__main__':
    main()
