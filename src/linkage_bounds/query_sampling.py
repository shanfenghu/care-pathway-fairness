"""Sampling rosters justified by fixed profile tables on complete blocks."""
import numpy as np
from .profile_robustness import Problem


def relevant_rows(problem: Problem) -> np.ndarray:
    """Return entry rows in blocks whose joint profile table can vary.

    The input must describe balanced complete candidate products with known
    cohort/source profiles. A block with one profile on either side has a fixed
    table. Resetting any linkage to the proposal on those blocks preserves every
    table-based query. A wrong report therefore needs at least its reversal
    radius in wrong proposed pairs among the returned rows.

    Choose this roster before pair answers and sample uniformly without
    replacement within it. Pair answers are still truthful binary identity
    checks. This is a sufficient roster, not an optimal question policy; an empty
    result means that all block tables are fixed under the stated support.
    """
    selected = []
    for block in sorted(set(problem.left_blocks.tolist())):
        left = np.flatnonzero(problem.left_blocks == block)
        right = np.flatnonzero(problem.right_blocks == block)
        if len(left) != len(right):
            raise ValueError('Unbalanced complete block')
        cohort_count = len(np.unique(problem.groups[:, left].T, axis=0))
        source_count = len(np.unique(problem.flags[:, right].T, axis=0))
        if cohort_count > 1 and source_count > 1:
            selected.extend(left.tolist())
    return np.asarray(sorted(selected), dtype=int)
