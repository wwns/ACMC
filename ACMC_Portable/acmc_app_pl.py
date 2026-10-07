"""
Polska wersja GUI aplikacji ACMC z funkcjami skanowania, testowania i wizualizacji.
Uruchomienie: python acmc_app_pl.py
"""
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import os
import scanner
import tester
import visual
import db
import logger
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def plural_units(n):
    return f"{n} jednostek" if n!=1 else "1 jednostka"


class AppPL(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ACMC - Narzędzie Modbus (PL)')
        self.geometry('1000x700')
        
        # === OSTATECZNA PRÓBA: Windows API do ikony ===
        try:
            import ctypes
            import os
            icon_path = os.path.join(os.path.dirname(__file__), 'LG.png')
            if os.path.exists(icon_path):
                # Try to set window icon using Windows API
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    from PIL import Image, ImageTk
                    try:
                        img = Image.open(icon_path).convert('RGBA').resize((256, 256))
                        # Save as temp PPM for Tkinter
                        ppm_path = '.acmc_icon.ppm'
                        img.save(ppm_path)
                        photo = tk.PhotoImage(file=ppm_path)
                        self.iconphoto(False, photo)
                        self._photo = photo  # Keep reference
                    except Exception:
                        pass  # Fallback: no icon
        except Exception:
            pass  # If Windows API fails, just continue without icon
        
        db.init_db()
        self._q = queue.Queue()
        self._build_ui()
        self._poll()

    def _build_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # connection
        conn = ttk.Labelframe(frm, text='Połączenie')
        conn.grid(row=0, column=0, sticky='ew')
        ttk.Label(conn, text='Host:').grid(row=0, column=0)
        self.host = tk.StringVar(value='127.0.0.1')
        ttk.Entry(conn, textvariable=self.host, width=20).grid(row=0, column=1)
        ttk.Label(conn, text='Port:').grid(row=0, column=2)
        self.port = tk.IntVar(value=502)
        ttk.Entry(conn, textvariable=self.port, width=8).grid(row=0, column=3)
        ttk.Label(conn, text='Zakres unit ID (od):').grid(row=0, column=4)
        self.unit_from = tk.IntVar(value=1)
        ttk.Entry(conn, textvariable=self.unit_from, width=6).grid(row=0, column=5)
        ttk.Label(conn, text='do:').grid(row=0, column=6)
        self.unit_to = tk.IntVar(value=10)
        ttk.Entry(conn, textvariable=self.unit_to, width=6).grid(row=0, column=7)
        self.mock = tk.BooleanVar(value=False)
        ttk.Checkbutton(conn, text='Tryb mock (dla testów bez urządzenia)', variable=self.mock).grid(row=0, column=8, padx=8)
        ttk.Button(conn, text='Skanuj jednostki', command=self._scan).grid(row=0, column=9, padx=6)

        # results frame
        res_frame = ttk.Panedwindow(frm, orient=tk.HORIZONTAL)
        res_frame.grid(row=1, column=0, sticky='nsew', pady=8)
        frm.rowconfigure(1, weight=1)
        frm.columnconfigure(0, weight=1)

        left = ttk.Frame(res_frame)
        right = ttk.Frame(res_frame)
        res_frame.add(left, weight=1)
        res_frame.add(right, weight=1)

        # table of results
        ttk.Label(left, text='Wyniki skanowania:').pack(anchor='w')
        self.tree = ttk.Treeview(left, columns=('unit','ok','details'), show='headings')
        self.tree.heading('unit', text='Unit ID')
        self.tree.heading('ok', text='Dostępność')
        self.tree.heading('details', text='Szczegóły')
        self.tree.pack(fill=tk.BOTH, expand=True)

        btns = ttk.Frame(left)
        btns.pack(fill='x')
        ttk.Button(btns, text='Przetestuj wybraną jednostkę', command=self._test_selected).pack(side='left', padx=4, pady=4)
        ttk.Button(btns, text='Przetestuj wszystkie znalezione', command=self._test_all_found).pack(side='left', padx=4, pady=4)
        # bind selection change to show details
        self.tree.bind('<<TreeviewSelect>>', lambda e: self._on_selection_changed())

        # details panel for selected unit
        details_frame = ttk.Labelframe(left, text='Szczegóły jednostki')
        details_frame.pack(fill='x', pady=6)
        self.detail_vars = {
            'unit': tk.StringVar(value=''),
            'fs': tk.StringVar(value=''),
            'md': tk.StringVar(value=''),
            'st': tk.StringVar(value=''),
            'flags': tk.StringVar(value=''),
            'raw': tk.StringVar(value='')
        }
        ttk.Label(details_frame, text='Unit:').grid(row=0, column=0, sticky='w')
        ttk.Label(details_frame, textvariable=self.detail_vars['unit']).grid(row=0, column=1, sticky='w')
        ttk.Label(details_frame, text='FS:').grid(row=1, column=0, sticky='w')
        ttk.Label(details_frame, textvariable=self.detail_vars['fs']).grid(row=1, column=1, sticky='w')
        ttk.Label(details_frame, text='MD:').grid(row=2, column=0, sticky='w')
        ttk.Label(details_frame, textvariable=self.detail_vars['md']).grid(row=2, column=1, sticky='w')
        ttk.Label(details_frame, text='ST (setpoint):').grid(row=3, column=0, sticky='w')
        ttk.Label(details_frame, textvariable=self.detail_vars['st']).grid(row=3, column=1, sticky='w')
        ttk.Label(details_frame, text='Flags:').grid(row=4, column=0, sticky='w')
        ttk.Label(details_frame, textvariable=self.detail_vars['flags']).grid(row=4, column=1, sticky='w')
        ttk.Label(details_frame, text='Raw registers:').grid(row=5, column=0, sticky='w')
        ttk.Label(details_frame, textvariable=self.detail_vars['raw']).grid(row=5, column=1, sticky='w')

        # right: visualization + log + sterowanie
        ttk.Label(right, text='Wizualizacja:').pack(anchor='w')
        self.fig_canvas = None
        self.canvas_container = ttk.Frame(right)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text='Log:').pack(anchor='w')
        self.log = ScrolledText(right, height=8)
        self.log.pack(fill=tk.BOTH, expand=False)

        # sterowanie (nawiew/temperatura) i dodatkowe testy komunikacji
        ctrl = ttk.Labelframe(right, text='Sterowanie i testy')
        ctrl.pack(fill='x', pady=6)
        ttk.Label(ctrl, text='Nawiew (0-100):').grid(row=0, column=0, sticky='w')
        self.fan_speed = tk.IntVar(value=50)
        fan_sb = tk.Spinbox(ctrl, from_=0, to=100, textvariable=self.fan_speed, width=6, command=lambda: self._update_fan_preview())
        fan_sb.grid(row=0, column=1, sticky='w', padx=4)
        ttk.Label(ctrl, text='Temp. zadana (°C):').grid(row=0, column=2, sticky='w', padx=(8,0))
        self.temp_setpoint = tk.DoubleVar(value=22.0)
        ttk.Entry(ctrl, textvariable=self.temp_setpoint, width=8).grid(row=0, column=3, sticky='w', padx=4)
        ttk.Button(ctrl, text='Wyślij sterowanie do wybranej jednostki', command=self._send_control).grid(row=0, column=4, padx=8)

        # additional controls: Mode and ON/Off and Save Params
        ttk.Label(ctrl, text='Tryb (MD):').grid(row=1, column=0, sticky='w', pady=6)
        self.mode_var = tk.IntVar(value=0)
        self.mode_cb = ttk.Combobox(ctrl, values=['AUTO','COOLING','FAN','HEAT','DRY'], state='readonly', width=10)
        self.mode_cb.current(0)
        self.mode_cb.grid(row=1, column=1, sticky='w')
        self.on_var = tk.IntVar(value=1)
        ttk.Checkbutton(ctrl, text='ON', variable=self.on_var).grid(row=1, column=2, sticky='w', padx=4)
        ttk.Button(ctrl, text='Zapisz parametry (FS/MD/ST/Flags)', command=self._save_params).grid(row=1, column=3, sticky='w', padx=6)

        # testy komunikacji: bramka <-> komp oraz bramka <-> płyta LG
        ttk.Button(ctrl, text='Test: bramka ↔ komp', command=self._test_gateway_pc).grid(row=2, column=0, pady=6)
        ttk.Button(ctrl, text='Test: bramka ↔ płyta LG', command=self._test_gateway_plate).grid(row=2, column=1, pady=6, padx=6)
        # fan preview
        self.fan_preview = ttk.Label(ctrl, text='FS code: 0 (AUTO)')
        self.fan_preview.grid(row=2, column=2, padx=8)

    def _log(self, msg: str):
        logger.info(msg)
        self.log.insert(tk.END, msg + '\n')
        self.log.see(tk.END)

    def _scan(self):
        host = self.host.get()
        port = int(self.port.get())
        a = int(self.unit_from.get())
        b = int(self.unit_to.get())
        if a > b:
            messagebox.showerror('Błąd', 'Zakres unit ID jest nieprawidłowy')
            return
        unit_range = range(a, b+1)
        use_mock = bool(self.mock.get())
        self._log(f'Rozpoczynam skanowanie {host}:{port} dla jednostek {a}-{b} (mock={use_mock})')

        def do_scan():
            res = scanner.scan_units(host=host, port=port, unit_range=unit_range, timeout=1.0, use_mock=use_mock)
            self._q.put(('scan_done', res))

        threading.Thread(target=do_scan, daemon=True).start()

    def _on_scan_done(self, results):
        # wypełnij drzewko
        for i in self.tree.get_children():
            self.tree.delete(i)
        for unit, ok, details in results:
            self.tree.insert('', 'end', values=(unit, 'OK' if ok else 'BRAK', details))
        # rysuj wykres
        fig = visual.make_figure_from_scan(results)
        if self.fig_canvas:
            self.fig_canvas.get_tk_widget().destroy()
        self.fig_canvas = FigureCanvasTkAgg(fig, master=self.canvas_container)
        self.fig_canvas.draw()
        self.fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._log(f'Skanowanie zakończone. Znaleziono: {sum(1 for r in results if r[1])} urządzeń')

    def _test_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        vals = self.tree.item(sel[0], 'values')
        unit = int(vals[0])
        host = self.host.get()
        port = int(self.port.get())
        use_mock = bool(self.mock.get())
        self._log(f'Rozpoczynam test jednostki {unit}...')

        def do_test():
            res = tester.test_unit(host, port, unit, use_mock=use_mock)
            self._q.put(('test_done_single', (unit, res)))

        threading.Thread(target=do_test, daemon=True).start()

    def _test_all_found(self):
        items = self.tree.get_children()
        units = [int(self.tree.item(it, 'values')[0]) for it in items if self.tree.item(it, 'values')[1] == 'OK']
        if not units:
            messagebox.showwarning('Uwaga', 'Brak znalezionych urządzeń do testu')
            return
        host = self.host.get()
        port = int(self.port.get())
        use_mock = bool(self.mock.get())
        self._log(f'Rozpoczynam testy dla {len(units)} urządzeń...')

        def do_tests():
            all_res = {}
            for u in units:
                r = tester.test_unit(host, port, u, use_mock=use_mock)
                all_res[u] = r
            self._q.put(('test_done_all', all_res))

        threading.Thread(target=do_tests, daemon=True).start()

    def _on_test_single(self, unit, res):
        self._log(f'Wyniki testu jednostki {unit}:')
        for k, v in res.items():
            self._log(f' - {k}: {"OK" if v.get("success") else "BŁĄD"} ({v.get("details")})')
        messagebox.showinfo('Test zakończony', f'Testy dla jednostki {unit} zakończone')

    def _on_test_all(self, all_res):
        ok_count = 0
        for u, r in all_res.items():
            all_ok = all(v.get('success') for v in r.values())
            if all_ok:
                ok_count += 1
        self._log(f'Testy wszystkich zakończone. Całkowicie OK: {ok_count} z {len(all_res)}')
        messagebox.showinfo('Testy zakończone', f'Testy zakończone. Całkowicie OK: {ok_count} / {len(all_res)}')

    def _on_selection_changed(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        unit = int(vals[0])
        host = self.host.get()
        port = int(self.port.get())
        use_mock = bool(self.mock.get())
        self._log(f'Pobieram rejestry jednostki {unit}...')

        def do_read():
            res = tester.read_unit_registers(host, port, unit, use_mock=use_mock)
            self._q.put(('unit_regs', (unit, res)))

        threading.Thread(target=do_read, daemon=True).start()

    def _update_fan_preview(self):
        perc = int(max(0, min(100, int(self.fan_speed.get()))))
        if perc == 0:
            code = 0
            txt = 'AUTO'
        elif perc <= 10:
            code = 1
            txt = 'VERY LOW'
        elif perc <= 30:
            code = 2
            txt = 'LOW'
        elif perc <= 60:
            code = 3
            txt = 'MIDDLE'
        elif perc <= 85:
            code = 4
            txt = 'HIGH'
        else:
            code = 5
            txt = 'VERY HIGH'
        self.fan_preview.config(text=f'FS code: {code} ({txt})')

    def _save_params(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        vals = self.tree.item(sel[0], 'values')
        unit = int(vals[0])
        host = self.host.get()
        port = int(self.port.get())
        use_mock = bool(self.mock.get())
        # map fan percentage to code
        perc = int(max(0, min(100, int(self.fan_speed.get()))))
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
        # mode
        md_map = {'AUTO':0,'COOLING':1,'FAN':2,'HEAT':3,'DRY':4}
        md_sel = self.mode_cb.get() if self.mode_cb.get() else 'AUTO'
        md_code = md_map.get(md_sel, 0)
        # on flag set bit 0 in flags register
        flags = 1 if bool(self.on_var.get()) else 0
        # validate ST
        try:
            st_val = int(round(float(self.temp_setpoint.get())))
        except Exception:
            messagebox.showerror('Błąd', 'Temp. zadana musi być liczbą')
            return
        if st_val < 18 or st_val > 30:
            messagebox.showerror('Błąd', 'Temp. zadana poza zakresem (18..30)')
            return
        self._log(f'Zapisuję parametry dla {unit}: FS={fs_code}, MD={md_code}, ST={st_val}, FLAGS={flags}')

        def do_write():
            res = tester.write_unit_params(host, port, unit, fs_code=fs_code, md_code=md_code, st_val=st_val, flags=flags, use_mock=use_mock)
            self._q.put(('write_params_done', (unit, res)))

        threading.Thread(target=do_write, daemon=True).start()

    def _send_control(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        vals = self.tree.item(sel[0], 'values')
        unit = int(vals[0])
        host = self.host.get()
        port = int(self.port.get())
        use_mock = bool(self.mock.get())
        fan = int(self.fan_speed.get())
        temp = float(self.temp_setpoint.get())
        self._log(f'Wysyłam sterowanie do jednostki {unit}: nawiew={fan}, temp={temp}')

        def do_send():
            res = tester.send_control(host, port, unit, fan_speed=fan, temp_setpoint=temp, use_mock=use_mock)
            self._q.put(('control_done', (unit, res)))

        threading.Thread(target=do_send, daemon=True).start()

    def _test_gateway_pc(self):
        host = self.host.get()
        port = int(self.port.get())
        self._log(f'Rozpoczynam test komunikacji bramka↔komp do {host}:{port}...')

        def do_test():
            res = tester.test_gateway_pc(host, port)
            self._q.put(('gateway_pc_done', res))

        threading.Thread(target=do_test, daemon=True).start()

    def _test_gateway_plate(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Uwaga', 'Wybierz jednostkę z listy')
            return
        vals = self.tree.item(sel[0], 'values')
        unit = int(vals[0])
        host = self.host.get()
        port = int(self.port.get())
        use_mock = bool(self.mock.get())
        self._log(f'Rozpoczynam test komunikacji bramka↔płyta LG dla jednostki {unit}...')

        def do_test():
            res = tester.test_gateway_plate(host, port, unit, use_mock=use_mock)
            self._q.put(('gateway_plate_done', (unit, res)))

        threading.Thread(target=do_test, daemon=True).start()

    def _poll(self):
        try:
            while True:
                item = self._q.get_nowait()
                kind = item[0]
                data = item[1]
                if kind == 'scan_done':
                    self._on_scan_done(data)
                elif kind == 'test_done_single':
                    unit, res = data
                    self._on_test_single(unit, res)
                elif kind == 'test_done_all':
                    self._on_test_all(data)
                elif kind == 'control_done':
                    unit, res = data
                    self._log(f'Resultat sterowania dla {unit}: {res}')
                    messagebox.showinfo('Sterowanie', f'Sterowanie dla jednostki {unit} zakończone: {res.get("details", "")}')
                elif kind == 'gateway_pc_done':
                    res = data
                    self._log(f'Test bramka↔komp: {res}')
                    messagebox.showinfo('Test bramka↔komp', str(res))
                elif kind == 'gateway_plate_done':
                    unit, res = data
                    self._log(f'Test bramka↔płyta LG dla {unit}: {res}')
                    messagebox.showinfo('Test bramka↔płyta LG', f'Jednostka {unit}: {res}')
                elif kind == 'unit_regs':
                    unit, res = data
                    if res.get('success'):
                        regs = res.get('data')
                        # parse known fields
                        fs = regs[1] if len(regs) > 1 else None
                        md = regs[2] if len(regs) > 2 else None
                        st = regs[3] if len(regs) > 3 else None
                        flags = regs[4] if len(regs) > 4 else None
                        raw = regs
                        self.detail_vars['unit'].set(str(unit))
                        self.detail_vars['fs'].set(str(fs))
                        self.detail_vars['md'].set(str(md))
                        self.detail_vars['st'].set(str(st))
                        self.detail_vars['flags'].set(str(flags))
                        self.detail_vars['raw'].set(str(raw))
                        # update controls to reflect values
                        try:
                            # set fan preview based on fs
                            fs_code = int(fs) if fs is not None else 0
                            mapping = {0:'AUTO',1:'VERY LOW',2:'LOW',3:'MIDDLE',4:'HIGH',5:'VERY HIGH'}
                            txt = mapping.get(fs_code, str(fs_code))
                            self.fan_preview.config(text=f'FS code: {fs_code} ({txt})')
                        except Exception:
                            pass
                        try:
                            st_val = int(st) if st is not None else None
                            if st_val is not None:
                                self.temp_setpoint.set(st_val)
                        except Exception:
                            pass
                        try:
                            md_val = int(md) if md is not None else 0
                            md_names = ['AUTO','COOLING','FAN','HEAT','DRY']
                            if 0 <= md_val < len(md_names):
                                self.mode_cb.set(md_names[md_val])
                        except Exception:
                            pass
                        try:
                            flags_val = int(flags) if flags is not None else 0
                            self.on_var.set(1 if (flags_val & 0x1) else 0)
                        except Exception:
                            pass
                    else:
                        self._log(f'Błąd odczytu rejestrów jednostki {unit}: {res.get("error")}')
                        messagebox.showerror('Błąd odczytu', str(res.get('error')))
                elif kind == 'write_params_done':
                    unit, res = data
                    self._log(f'Zapis parametrów dla {unit}: {res}')
                    messagebox.showinfo('Zapis parametrów', str(res))
        except Exception:
            pass
        self.after(200, self._poll)


def main():
    app = AppPL()
    app.mainloop()


if __name__ == '__main__':
    main()
