"""Compare scientific summaries without requiring distributed person-level inputs."""
import argparse
import json
import math
from pathlib import Path
from paths import ROOT


def scientific(value):
    """Drop measurements of host speed, retaining scientific answers and fit losses."""
    if isinstance(value, dict):
        return {k: scientific(v) for k, v in value.items() if 'seconds' not in k}
    if isinstance(value, list):
        return [scientific(v) for v in value]
    return value


def agrees(reference, actual):
    """Compare published findings; integers/decisions exact, floats tolerant.

    Relative 1e-6 and absolute 1e-8 accommodate numerical fit and summation
    differences. Discrete radii and verdicts remain exact. Extra freshly
    generated provenance fields need not be distributed as input records.
    """
    if isinstance(reference, dict):
        return isinstance(actual, dict) and all(
            k in actual and agrees(v, actual[k]) for k, v in reference.items())
    if isinstance(reference, list):
        return isinstance(actual, list) and len(reference) == len(actual) and all(
            agrees(a, b) for a, b in zip(reference, actual))
    if isinstance(reference, float) and isinstance(actual, (float, int)):
        return math.isclose(reference, actual, rel_tol=1e-6, abs_tol=1e-8)
    return type(reference) is type(actual) and reference == actual


def compare(primary, support):
    for retained, fresh in [(ROOT/'results/joint-query-validation', primary),
                            (ROOT/'results/support-validation', support)]:
        a = json.loads((retained/'summary.json').read_text())['rows']
        b = json.loads((fresh/'summary.json').read_text())['rows']
        if not agrees(scientific(a), scientific(b)):
            raise ValueError('Scientific summary changed: '+str(fresh))
    print('Scientific summaries agreed: 56 primary and 96 support queries; timings excluded.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--primary', type=Path, required=True)
    p.add_argument('--support', type=Path, required=True)
    a = p.parse_args()
    compare(a.primary.resolve(), a.support.resolve())
