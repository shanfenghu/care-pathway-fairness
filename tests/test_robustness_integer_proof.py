"""Fresh finite-world and adversarial checks for the integer-proof refinement."""
import copy
from fractions import Fraction
from itertools import permutations
import unittest
import numpy as np
from linkage_bounds.profile_robustness import Problem,build_model
from linkage_bounds.robustness_integer_proof import prove_integer_lower,verify_integer_tree


class IntegerProofTests(unittest.TestCase):
    def test_fractional_obstruction_and_missing_branch_rejection(self):
        g=np.array([[1,0]]);p=np.arange(2);b=np.zeros(2,dtype=int)
        model=build_model(Problem(g,g,p,b,b),'profile')
        B=np.r_[model.query,-model.query];d=np.zeros(2,dtype=int)
        proof=prove_integer_lower(model,B,d,3)
        self.assertTrue(proof['complete']);self.assertEqual(proof['tree']['kind'],'split')
        checked=verify_integer_tree(model,B,d,3,proof['tree'])
        self.assertGreater(checked['leaves'],1)
        bad=copy.deepcopy(proof['tree']);bad['right']=None
        with self.assertRaises(ValueError):verify_integer_tree(model,B,d,3,bad)
        bad=copy.deepcopy(proof['tree']);bad['split']=-1
        with self.assertRaises(ValueError):verify_integer_tree(model,B,d,3,bad)

    def test_fresh_finite_world_minima(self):
        rng=np.random.default_rng(2026110362);checked=0;worlds=0
        for n in range(4,8):
            for repeat in range(4):
                g=rng.integers(0,2,(2,n));g[:,0]=0;g[:,1]=1
                z=rng.integers(0,2,(2,n));p=np.arange(n)
                b=np.arange(n)%2 if repeat%2 else np.zeros(n,dtype=int)
                problem=Problem(g,z,p,b,b);caps=problem.caps(Fraction(1,5))
                baseline=bool(np.all(abs(problem.values(p))<=caps));opposite=[]
                for perm in permutations(range(n)):
                    pp=np.asarray(perm)
                    if not np.array_equal(b,b[pp]):continue
                    worlds+=1
                    if bool(np.all(abs(problem.values(pp))<=caps))!=baseline:
                        opposite.append(int(np.count_nonzero(pp!=p)))
                if not opposite:continue
                upper=min(opposite)
                model=build_model(problem,'profile')
                # Most finite cases start outside the joint band. Branch witnesses
                # are also tested when the baseline starts inside.
                conditions=[]
                if not baseline:conditions=[(np.r_[model.query,-model.query],np.r_[caps,caps])]
                else:
                    for q in range(len(caps)):
                        conditions.extend([(model.query[q:q+1],np.array([-caps[q]-1])),
                                           (-model.query[q:q+1],np.array([-caps[q]-1]))])
                for B,d in conditions:
                    proof=prove_integer_lower(model,B,d,upper)
                    self.assertTrue(proof['complete'])
                    verify_integer_tree(model,B,d,upper,proof['tree']);checked+=1
        self.assertGreater(checked,0)
        print('Fresh integer-proof checks:',checked,'over',worlds,'block-complete worlds')


if __name__=='__main__':unittest.main()
