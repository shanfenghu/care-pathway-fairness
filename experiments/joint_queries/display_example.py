"""Render recorded scalar/shared repair endpoints and intact-bundle circulation."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch,FancyBboxPatch
from paths import ROOT
BLUE,ORANGE,GRAY='#0072B2','#B44700','#535A60'
FIGURES=None
def checked_data():
    """Read aggregate findings, without distributing person-level case arrays.

    These consistency checks validate plotting quantities; independent witness
    checks require a newly prepared workload from the original provider tables.
    """
    data = json.loads((ROOT/'results/query-summaries/illustration.json').read_text())
    initial, target = (np.asarray(data[k], dtype=int) for k in ('initial', 'target'))
    assert initial.shape == target.shape == (4, 4)
    assert np.all(initial >= 0) and np.all(target >= 0)
    assert np.array_equal(initial.sum(0), target.sum(0))
    assert np.array_equal(initial.sum(1), target.sum(1))
    assert int(initial.sum()) == 60
    assert int(np.maximum(target-initial, 0).sum()) == data['changed_partners'] == 10
    values = np.asarray(data['numerator_values'])
    assert np.allclose(100*values/np.asarray(data['denominators'])[:, None], data['percentages'])
    return data
def render(data):
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9.2, 'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig = plt.figure(figsize=(7.16, 1.65))
    fig.text(0.005, 0.99, '(a) Fixing one contrast can worsen others', va='top', fontsize=10.2, weight='bold')
    ax = fig.add_axes([0.17, 0.25, 0.3, 0.5])
    values = np.array(data['percentages'])
    ax.axvspan(-5, 5, facecolor='#E4F2F8', zorder=0)
    ax.axvline(0, color='#B8C2C8', linewidth=0.5, zorder=0)
    for q in range(6):
        ax.add_patch(FancyArrowPatch((values[q, 0], q), (values[q, 1], q), arrowstyle='-|>', mutation_scale=6, color=GRAY, linewidth=0.65, shrinkA=3, shrinkB=3, zorder=1))
    ax.scatter(values[:, 0], range(6), s=13, facecolors='white', edgecolors=GRAY, linewidths=0.8, zorder=3)
    ax.scatter(values[:, 2], range(6), s=15, marker='o', color=BLUE, zorder=4)
    ax.scatter(values[:, 1], range(6), s=18, marker='x', color=ORANGE, linewidths=1.0, zorder=5)
    ax.set(xlim=(-30, 20), ylim=(5.5, -0.5), xticks=[-25, -5, 5, 15], yticks=range(6), yticklabels=['Sex: ICU 24h', 'Sex: proc. 24h', 'Sex: proc. 72h', 'Age: ICU 24h', 'Age: proc. 24h', 'Age: proc. 72h'])
    ax.tick_params(axis='both', labelsize=9.2, length=2, pad=2)
    ax.set_xlabel('Difference (percentage points)', fontsize=9.2, labelpad=2)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    fig.text(0.17, 0.83, '○ proposed   × 8 changes   ● 10 changes', fontsize=9.2)
    right = fig.add_axes([0.535, 0.045, 0.46, 0.94])
    right.set(xlim=(0, 1), ylim=(0, 1))
    right.axis('off')
    right.text(0, 0.99, '(b) One linkage, ten reassigned bundles', va='top', fontsize=10.2, weight='bold')
    positions = {(0, 0): (0.16, 0.65), (0, 1): (0.84, 0.65), (1, 1): (0.5, 0.23)}
    nodes = {}
    for (g, label) in [((0, 0), 'Male\n<65'), ((0, 1), 'Male\n65+'), ((1, 1), 'Female\n65+')]:
        (x, y) = positions[g]
        patch = FancyBboxPatch((x - 0.11, y - 0.1), 0.22, 0.2, boxstyle='round,pad=.007', facecolor='#F4F6F7', edgecolor=GRAY, linewidth=0.7, zorder=4)
        right.add_patch(patch)
        nodes[g] = patch
        right.text(x, y, label, ha='center', va='center', fontsize=9.2, linespacing=1.05, zorder=5)
    flows = [((0, 0), (0, 1), '2 all', BLUE, 0.0, (0.5, 0.77)), ((0, 0), (1, 1), '1 all', BLUE, 0.2, (0.23, 0.39)), ((0, 1), (1, 1), '3 72h', ORANGE, 0.2, (0.65, 0.49)), ((1, 1), (0, 0), '3 none', GRAY, 0.2, (0.38, 0.49)), ((1, 1), (0, 1), '1 none', GRAY, 0.2, (0.79, 0.39))]
    for (source, target, label, colour, curve, label_pos) in flows:
        right.add_patch(FancyArrowPatch(positions[source], positions[target], connectionstyle=f'arc3,rad={curve}', patchA=nodes[source], patchB=nodes[target], arrowstyle='-|>', mutation_scale=9, color=colour, linewidth=1.15, shrinkA=3, shrinkB=3, zorder=1))
        right.text(*label_pos, label, ha='center', va='center', fontsize=9.2, color=colour, bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 0.5}, zorder=3)
    right.text(0.5, 0.025, '50 proposed pairs stay; 10 partners change', ha='center', va='bottom', fontsize=9.2, weight='bold')
    for extension in ('pdf', 'png'):
        options = {'metadata': {'CreationDate': None, 'ModDate': None}} if extension == 'pdf' else {'dpi': 210}
        fig.savefig(FIGURES / f'joint-example.{extension}', **options)
    plt.close(fig)
