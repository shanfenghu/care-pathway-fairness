"""Exercise both provider preparations and three representative query comparisons."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import numpy as np
from linkage_bounds.count_robustness import solve_count_radius
from linkage_bounds.profile_robustness import verify_permutation
from paths import ROOT
import run_queries


def smoke(output):
    """Check strict gain, blocking and an adverse case after fitting fixed proposals.

    This practical run does not repeat the full support/sampling campaign.
    Generated workloads and witnesses remain local outside Git.
    """
    run_queries.OUT = output
    run_queries.prepare()
    cases = json.loads((output/'cases.json').read_text())['cases']
    retained = json.loads((ROOT/'results/joint-query-validation/summary.json').read_text())['rows']
    rows = []
    for index in (0, 10, 27):
        case = cases[index]
        p = run_queries.problem(case)
        for delta in ('1/20', '1/10'):
            expected = next(r for r in retained if r['case_index'] == index and r['delta'] == delta)
            for method in ('profile', 'assignment', 'mes'):
                r = solve_count_radius(p, delta, method)
                e = expected['methods'][method]
                for k in ('lower', 'upper', 'rigorous_invariant', 'bracket_closed'):
                    if r[k] != e[k]:
                        raise ValueError(f'Changed discrete result: {index}/{delta}/{method}/{k}')
                caps = p.caps(Fraction(delta))
                if r['upper'] is not None:
                    verify_permutation(p, r['witness'], caps, r['baseline_inside'])
                truth_inside = bool(np.all(abs(p.values(np.asarray(case['truth']))) <= caps))
                if truth_inside != expected['truth_inside']:
                    raise ValueError('Changed recorded reference verdict')
                rows.append(dict(case_index=index, delta=delta, method=method,
                                 lower=r['lower'], upper=r['upper'],
                                 rigorous_invariant=r['rigorous_invariant']))
    with (output/'smoke-summary.json').open('x') as f:
        json.dump({'comparisons': rows, 'prepared_cases': len(cases)}, f, indent=2)
        f.write('\n')
    print('Prepared 28 provider-based cases; 18 three-method comparisons agreed, including adverse case 27.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    smoke(p.parse_args().output.resolve())
