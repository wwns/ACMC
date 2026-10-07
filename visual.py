"""
Moduł wizualizacji (matplotlib) do osadzenia w Tkinter.
Funkcja: make_figure_from_scan(units) -> matplotlib.Figure

'units' to lista słowników zwrócona przez scanner.scan_units()['units']
(każdy zawiera m.in.: index, gn, un, st, at, on, er).
"""
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure


def make_figure_from_scan(units):
    fig = Figure(figsize=(6, 3.2))
    ax = fig.add_subplot(111)

    if not units:
        ax.set_title('Brak znalezionych jednostek')
        ax.axis('off')
        return fig

    labels = [f"{u['index']}\n({u['gn']}.{u['un']})" for u in units]
    st_vals = [u['st'] for u in units]
    at_vals = [u['at'] for u in units]
    colors_on = ['#2ca02c' if u['on'] else '#999999' for u in units]

    x = list(range(len(units)))
    width = 0.35
    ax.bar([i - width / 2 for i in x], st_vals, width, label='Zadana (ST)', color='#1f77b4')
    ax.bar([i + width / 2 for i in x], at_vals, width, label='Zmierzona (AT)', color='#ff7f0e')

    # kropka pod słupkiem = stan ON/OFF jednostki
    for i, c in zip(x, colors_on):
        ax.scatter(i, -1.5, color=c, s=30, clip_on=False)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel('Temperatura (°C)')
    ax.set_title(f'Znalezione jednostki: {len(units)} (zielona kropka = ON)')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    return fig
