"""
Moduł wizualizacji (matplotlib) do osadzenia w tkinter: wyświetla listę znalezionych jednostek oraz prosty wykres aktywności.
Funkcja: make_figure_from_scan(results) -> matplotlib.Figure
"""
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure


def make_figure_from_scan(results):
    # results: list of (unit, ok, details)
    fig = Figure(figsize=(6,3))
    ax = fig.add_subplot(111)
    units = [r[0] for r in results]
    oks = [1 if r[1] else 0 for r in results]
    ax.bar(units, oks, color=['green' if v==1 else 'red' for v in oks])
    ax.set_xlabel('Unit ID')
    ax.set_ylabel('Dostępność (1=OK)')
    ax.set_ylim(-0.1,1.1)
    ax.set_title('Wyniki skanowania jednostek')
    ax.grid(axis='y')
    return fig
