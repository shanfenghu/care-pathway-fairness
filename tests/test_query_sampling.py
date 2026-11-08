"""Finite-world checks of structural pair-sampling rosters."""
from fractions import Fraction
from itertools import permutations,product
import unittest
import numpy as np
from linkage_bounds.profile_robustness import Problem
from linkage_bounds.query_sampling import relevant_rows


class QuerySamplingTests(unittest.TestCase):
    def test_excludes_either_fixed_profile_side(self):
        blocks=np.array([0,0,1,1,2,2]);p=np.arange(6)
        problem=Problem([[0,1,0,0,1,1]],[[0,1,0,1,1,1]],p,blocks,blocks)
        self.assertEqual(relevant_rows(problem).tolist(),[0,1])

    def test_empty_frame_has_fixed_query_even_with_unresolved_identities(self):
        blocks=np.array([0,0,1,1]);p=np.arange(4)
        problem=Problem([[0,0,1,1]],[[0,1,0,1]],p,blocks,blocks)
        self.assertEqual(relevant_rows(problem).tolist(),[])
        for alt in [np.array([1,0,3,2]),np.array([0,1,3,2])]:
            np.testing.assert_array_equal(problem.values(p),problem.values(alt))

    def test_full_frame_recovers_original_roster(self):
        p=np.arange(4);blocks=np.zeros(4,dtype=int)
        problem=Problem([[0,1,0,1]],[[0,0,1,1]],p,blocks,blocks)
        self.assertEqual(relevant_rows(problem).tolist(),list(range(4)))

    def test_right_roster_can_have_a_different_order(self):
        problem=Problem([[0,1,0,0]],[[0,1,0,1]],[2,3,0,1],[0,0,1,1],[1,1,0,0])
        self.assertEqual(relevant_rows(problem).tolist(),[0,1])

    def test_reset_and_radius_match_all_small_binary_worlds(self):
        blocks=np.array([0,0,1,1]);worlds=[np.array(x) for x in permutations(range(4))
            if np.array_equal(blocks,blocks[list(x)])]
        checked=0
        for g in product([0,1],repeat=4):
            if sum(g) in (0,4):continue
            for h in product([0,1],repeat=4):
                for p in worlds:
                    problem=Problem([g],[h],p,blocks,blocks);q=relevant_rows(problem)
                    for delta in [Fraction(0),Fraction(1,4),Fraction(1,2)]:
                        caps=problem.caps(delta);base=bool(np.all(abs(problem.values(p))<=caps));global_costs=[];frame_costs=[]
                        for alt in worlds:
                            reset=p.copy();reset[q]=alt[q]
                            self.assertEqual(sorted(reset.tolist()),list(range(4)))
                            np.testing.assert_array_equal(problem.values(reset),problem.values(alt))
                            if bool(np.all(abs(problem.values(alt))<=caps))!=base:
                                global_costs.append(int(np.count_nonzero(p!=alt)))
                                frame_costs.append(int(np.count_nonzero(p[q]!=alt[q])))
                            checked+=1
                        self.assertEqual(min(global_costs,default=None),min(frame_costs,default=None))
        self.assertEqual(checked,10752)


if __name__=='__main__':unittest.main()
