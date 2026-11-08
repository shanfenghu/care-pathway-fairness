"""Consequential regressions for scientific-summary comparisons."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'experiments/joint_queries'))
from compare_current import agrees, scientific


class ScientificSummaries(unittest.TestCase):
    def test_host_timings_and_unpublished_provenance_do_not_change_finding(self):
        old = {'lower': 10, 'loss': .2, 'total_seconds': .01}
        new = {'lower': 10, 'loss': .200000001, 'total_seconds': 3., 'test_persons': ['local']}
        self.assertTrue(agrees(scientific(old), scientific(new)))

    def test_discrete_decisions_and_missing_findings_remain_errors(self):
        for new in [{'lower': 9}, {'lower': 10.000000001}, {}]:
            with self.subTest(new=new):
                self.assertFalse(agrees({'lower': 10}, new))
        self.assertFalse(agrees({'inside': True}, {'inside': False}))

    def test_material_fit_drift_is_not_tolerated(self):
        self.assertFalse(agrees({'loss': .2}, {'loss': .21}))
