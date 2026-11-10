"""Check the common integer-count reformulation against fresh exact worlds."""
from fractions import Fraction
from itertools import permutations
from math import inf
import unittest
import numpy as np
from linkage_bounds.profile_robustness import Problem,build_model,verify_permutation
from linkage_bounds.count_robustness import count_constraints,solve_count_radius


class CountTests(unittest.TestCase):
    def test_exact_tolerance_preserves_inclusive_boundary(self):
        # Independent recorded contrast: (7*1 - 2*2)/(2*5) = 3/10.
        problem=Problem(np.array([[1,1,0,0,0,0,0]]),
                        np.array([[1,0,1,0,0,0,0]]),np.arange(7),
                        np.zeros(7,dtype=int),np.zeros(7,dtype=int))
        numerator=int(problem.values(problem.proposal)[0])
        self.assertEqual(Fraction(numerator,2*5),Fraction(3,10))
        for tolerance in ("3/10",Fraction(3,10)):
            self.assertEqual(problem.caps(tolerance).tolist(),[3])
            answer=solve_count_radius(problem,tolerance,'profile')
            self.assertTrue(answer['baseline_inside'])
            self.assertEqual((answer['lower'],answer['upper']),(2,2))
        # Documented compatibility: Fraction(float) keeps the binary value.
        self.assertLess(Fraction(0.3),Fraction(3,10))
        self.assertEqual(problem.caps(0.3).tolist(),[2])

    def test_fresh_worlds_and_all_routes(self):
        rng=np.random.default_rng(2026110363);worlds=0;routes=set()
        inside=Problem(np.array([[1,1,0,0]]),np.array([[1,0,1,0]]),np.arange(4),np.zeros(4,dtype=int),np.zeros(4,dtype=int))
        for method in ('profile','assignment','mes'):
            answer=solve_count_radius(inside,Fraction(1,4),method);routes.add(answer['route'])
            self.assertEqual(answer['lower'],2);self.assertEqual(answer['upper'],2)
            verify_permutation(inside,answer['witness'],inside.caps(Fraction(1,4)),True)
        for n in range(3,8):
            for repeat in range(4):
                g=rng.integers(0,2,(2,n));g[:,0]=0;g[:,1]=1
                z=rng.integers(0,2,(2,n));p=np.arange(n)
                blocks=np.arange(n)%2 if repeat%2 else np.zeros(n,dtype=int)
                problem=Problem(g,z,p,blocks,blocks);delta=Fraction(1,4);caps=problem.caps(delta)
                baseline=bool(np.all(abs(problem.values(p))<=caps));minimum=inf
                # The direct-edge count rows must agree exactly with the original rate condition.
                direct=build_model(problem,'assignment');count,lo,hi=count_constraints(problem,direct,caps)
                edge_index={edge:i for i,edge in enumerate(direct.edges)}
                for perm in permutations(range(n)):
                    pp=np.asarray(perm)
                    if not np.array_equal(blocks,blocks[pp]):continue
                    worlds+=1;x=np.zeros(len(direct.cost),dtype=int)
                    for i,j in enumerate(pp):x[edge_index[(i,int(j))]]=1
                    within=bool(np.all(abs(problem.values(pp))<=caps))
                    self.assertEqual(within,bool(np.all(count@x>=lo) and np.all(count@x<=hi)))
                    if within!=baseline:minimum=min(minimum,int(np.count_nonzero(pp!=p)))
                for method in ('profile','assignment','mes'):
                    answer=solve_count_radius(problem,delta,method);routes.add(answer['route'])
                    if minimum==inf:self.assertTrue(answer['rigorous_invariant'])
                    else:
                        self.assertEqual(answer['lower'],minimum);self.assertEqual(answer['upper'],minimum)
                        verify_permutation(problem,answer['witness'],caps,baseline)
        self.assertEqual(routes,{'scalar_invariant','scalar_violation','scalar_entry','joint'})
        print('Integer-count equivalence worlds:',worlds,'all three routes checked')


if __name__=='__main__':unittest.main()
