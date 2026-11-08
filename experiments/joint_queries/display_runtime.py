"""Compare retained processing ranges and potential model sizes."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from paths import ROOT
SOURCE=ROOT/'results/joint-query-validation/summary.json'
INITIAL=ROOT/'results/query-development/summary.json'
BLUE,ORANGE,PURPLE='#0072B2','#D55E00','#8C5A9D'
FIGURES=None
def main():
    """Render the same six selected cases, exposing the count coincidence."""
    rows = json.loads(SOURCE.read_text())['rows']
    initial = json.loads(INITIAL.read_text())['rows']
    select = lambda i: next((r for r in rows if r['case_index'] == i and r['delta'] == '1/20'))
    indices = [0, 8, 10, 16, 18, 14]
    labels = ['MIMIC 60\ncomplete', 'eICU 225\ncomplete', 'eICU 225\nhospital blocks', 'eICU 128\ncomplete', 'eICU 128\nhospital blocks', 'eICU 18\nhospital blocks']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.labelsize': 9, 'xtick.labelsize': 8, 'ytick.labelsize': 8.5, 'legend.fontsize': 8, 'pdf.fonttype': 42, 'ps.fonttype': 42, 'axes.spines.top': False, 'axes.spines.right': False})
    (fig, (ax, other)) = plt.subplots(1, 2, figsize=(7.16, 2.85), sharey=True)
    plotted = {i: {'timings_ms': {}} for i in indices}
    for (method, color, marker, offset, label) in [('profile', BLUE, 'o', -0.19, 'Profile (ours)'), ('assignment', ORANGE, 's', 0, 'Assignment'), ('mes', PURPLE, '^', 0.19, 'MES adaptation')]:
        (values, lower, upper) = ([], [], [])
        for i in indices:
            result = select(i)['methods'][method]
            value = result['total_seconds_median'] * 1000
            (lo, hi) = np.array(result['total_seconds_range']) * 1000
            values.append(value)
            lower.append(value - lo)
            upper.append(hi - value)
            plotted[i]['timings_ms'][method] = {'median': value, 'range': [float(lo), float(hi)]}
        ax.errorbar(values, np.arange(len(indices)) + offset, xerr=[lower, upper], fmt=marker, color=color, markersize=4, capsize=2, linestyle='none', label=label)
    ax.set_xscale('log')
    ax.set_xlim(0.1, 3000)
    ax.set_yticks(np.arange(6), labels)
    ax.invert_yaxis()
    ax.set_xlabel('Checked processing time (ms)\nlogarithmic scale')
    ax.grid(axis='x', alpha=0.2)
    ax.legend(loc='lower left', bbox_to_anchor=(-0.4, 1.015), ncol=2, frameon=False)
    coincidences = []
    for (y, i) in enumerate(indices):
        row = next((r for r in initial if r['case_index'] == i and r['delta'] == '1/20'))
        a = row['methods']['assignment']['geometry']['variables']
        p = row['methods']['profile']['geometry']['variables']
        plotted[i]['potential_counts'] = {'profile': p, 'assignment': a}
        other.plot([p, a], [y, y], color='#B7B7B7', linewidth=1)
        circle_size = 36 if p == a else 23
        other.scatter([p], [y], marker='o', facecolor='white', edgecolor=BLUE, s=circle_size, zorder=3)
        square_size = 6 if p == a else 12
        other.scatter([a], [y], marker='s', facecolor=ORANGE, edgecolor=ORANGE, s=square_size, zorder=4)
        if p == a:
            coincidences.append({'case_index': i, 'profile': p, 'assignment': a})
    assert coincidences == [{'case_index': 14, 'profile': 18, 'assignment': 18}]
    other.plot([], [], marker='o', markerfacecolor='white', color=BLUE, linestyle='none', label='Profile arcs (ours)')
    other.plot([], [], marker='s', color=ORANGE, linestyle='none', label='Record edges')
    other.set_xscale('log')
    other.set_xlim(10, 90000)
    other.set_xlabel('Potential model variables\nlogarithmic scale')
    other.grid(axis='x', alpha=0.2)
    other.legend(loc='lower left', bbox_to_anchor=(-0.03, 1.015), ncol=1, frameon=False)
    fig.subplots_adjust(left=0.165, right=0.975, bottom=0.235, top=0.8, wspace=0.23)
    FIGURES.mkdir(exist_ok=True)
    (pdf, png) = (FIGURES / 'checked-computation.pdf', FIGURES / 'checked-computation.png')
    fig.savefig(pdf, metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(png, dpi=190)
    plt.close(fig)
