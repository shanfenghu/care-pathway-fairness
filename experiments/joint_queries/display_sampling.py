"""Render the overall assurance limit and selected radius/frame comparisons.

Acceptance is conditional on the retained true error count and random fixed-size
sampling without replacement. The 95% acceptance target differs from the audit's
5% false-assurance bound. No patient-level arrays are needed for these displays.
"""
from fractions import Fraction
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from linkage_bounds.robustness_audit import cdf, cutoff
from paths import ROOT

BLUE, ORANGE, GRAY = '#0072B2', '#D55E00', '#666666'
FIGURES = None


def checked_evidence():
    """Check all finite curves and derive minimum budgets from exact fractions."""
    data = json.loads((ROOT/'results/query-followups/sampling.json').read_text())
    finite = [r for r in data['rows'] if not r['invariant']]
    counts = {}
    for design in ('global', 'frame'):
        unattainable = 0
        for row in finite:
            curve = row['curve']
            assert [p['budget'] for p in curve] == list(range(row['n'] + 1))
            minimum = next((p['budget'] for p in curve
                            if Fraction(p[design]) >= Fraction(19, 20)), None)
            assert minimum == row['minimum_budget'][design+'_95']
            if minimum is None:
                # The dominant failure is zero acceptance, even after every
                # available pair in the corresponding frame has been checked.
                assert Fraction(curve[-1][design]) == 0
                unattainable += 1
        assert unattainable == data['summary']['95_unattainable_'+design]
        counts[design] = unattainable
    selected = next(r for r in finite if r['case_index'] == 10 and r['delta'] == '1/20')
    controls = json.loads((ROOT/'results/query-followups/same-frame-control.json').read_text())['rows']
    control = next(r for r in controls if r['case_index'] == 10 and r['delta'] == '1/20')
    separate = next(p['budget'] for p in control['curve']
                    if Fraction(p['frame_separate']) >= Fraction(19, 20))
    assert separate == control['minimum_budget']['frame_separate_95']
    budgets = [selected['minimum_budget']['global_95'],
               selected['minimum_budget']['frame_95'], separate]
    return finite, counts, budgets


def main():
    """Keep unattainable workloads visible beside conditional improvements."""
    finite, counts, budgets = checked_evidence()
    rows = json.loads((ROOT/'results/joint-query-validation/summary.json').read_text())['rows']
    row = next(r for r in rows if r['case_index'] == 0 and r['delta'] == '1/20')
    fig, (overall, curve, questions) = plt.subplots(
        1, 3, figsize=(7.16, 2.30), gridspec_kw={'width_ratios': [1.05, 1.35, 1.2]})
    for y, design in enumerate(('global', 'frame')):
        failed = counts[design]
        overall.barh(y, failed, color=GRAY, height=.5)
        overall.barh(y, len(finite)-failed, left=failed, color=BLUE, height=.5)
        overall.text(failed/2, y, str(failed), ha='center', va='center', color='white')
        overall.text(failed+(len(finite)-failed)/2, y, str(len(finite)-failed),
                     ha='center', va='center', color='white')
    overall.set(yticks=[0, 1], yticklabels=['All pairs', 'Profile\nframe'],
                xlim=(0, len(finite)), xticks=[0, 20, 40], xlabel='Finite workloads (40)')
    overall.invert_yaxis()
    overall.set_title('(a) 95% acceptance target', fontsize=8.5)
    overall.text(.02, -.45, 'Gray: unattainable\nBlue: attainable',
                 transform=overall.transAxes, fontsize=8, va='top')
    n, errors = row['n'], row['identity_errors']
    mvals = np.arange(n+1)
    for radius, color, style, label in [
            (row['methods']['profile']['lower'], BLUE, '-', 'Joint radius (ours)'),
            (row['separate_lower'], ORANGE, '--', 'Separate bound')]:
        values = [float(cdf(n, errors, int(m), cutoff(n, radius, int(m)))) for m in mvals]
        curve.plot(100*mvals/n, values, color=color, linestyle=style, label=label, linewidth=1.3)
    curve.set(xlim=(0, 100), ylim=(-.02, 1.03), xticks=[0, 50, 100],
              xlabel='Pairs checked (%)', ylabel='Acceptance probability')
    curve.set_title('(b) MIMIC 60\nsix wrong pairs', fontsize=8.5)
    curve.grid(alpha=.2)
    curve.legend(loc='upper left', bbox_to_anchor=(-.02, -.4), fontsize=7.5, frameon=False)
    questions.barh(range(3), budgets, height=.55, color=[BLUE, BLUE, ORANGE])
    questions.set(yticks=range(3), yticklabels=['All pairs\njoint', 'Frame\njoint', 'Frame\nseparate'],
                  xlim=(0, 166), xticks=[0, 75, 150], xlabel='Questions for 95%')
    questions.invert_yaxis()
    for y, budget in enumerate(budgets):
        questions.text(budget+3, y, str(budget), va='center', fontsize=8)
    questions.set_title('(c) eICU 225\nfour wrong pairs', fontsize=8.5)
    fig.subplots_adjust(left=.105, right=.975, bottom=.38, top=.83, wspace=.78)
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES/'audit-acceptance.pdf', metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(FIGURES/'audit-acceptance.png', dpi=190)
    plt.close(fig)
