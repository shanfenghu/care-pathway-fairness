"""Meaningful finite-world, numerical-certificate and audit-risk checks."""
import copy
from fractions import Fraction
from itertools import permutations
from math import inf
import unittest
import numpy as np
from linkage_bounds.profile_robustness import (Problem,build_model,solve_radius,checked_lp_bound,
                                verify_lp_certificate,verify_permutation)
from linkage_bounds.robustness_audit import cdf,cutoff


class RobustnessTests(unittest.TestCase):
    def test_reject_fractional_indicators_before_conversion(self):
        valid=np.array([[1.,0.,0.]])
        blocks=np.zeros(3,dtype=int)
        for side in ('groups','flags'):
            for value in (.5,-.5,1.5,np.nan):
                with self.subTest(side=side,value=value):
                    invalid=valid.copy();invalid[0,1]=value
                    groups=invalid if side=='groups' else valid
                    flags=invalid if side=='flags' else valid
                    with self.assertRaises(ValueError):
                        Problem(groups,flags,np.arange(3),blocks,blocks)

    def test_reject_fractional_partner_indices_before_conversion(self):
        g=np.array([[1,0,0]]);blocks=np.zeros(3,dtype=int)
        problem=Problem(g,g,np.arange(3),blocks,blocks)
        for proposal in ([.5,1.5,2.5],[-.1,1,2],[0,1,np.nan]):
            with self.subTest(proposal=proposal):
                with self.assertRaises(ValueError):
                    Problem(g,g,proposal,blocks,blocks)
        for witness in ([1.5,.5,2.5],[1,0,2.5],[1,0,np.nan]):
            with self.subTest(witness=witness):
                with self.assertRaises(ValueError):
                    verify_permutation(problem,witness,problem.caps(Fraction(1,2)),False)

    def test_exact_numeric_arrays_remain_valid(self):
        g=np.array([[1.,0.,0.]]);blocks=np.zeros(3,dtype=int)
        problem=Problem(g,g,np.arange(3,dtype=float),blocks,blocks)
        self.assertEqual(problem.groups.tolist(),[[1,0,0]])
        self.assertEqual(problem.flags.tolist(),[[1,0,0]])
        self.assertEqual(problem.proposal.tolist(),[0,1,2])
        self.assertEqual(verify_permutation(problem,[1.,0.,2.],
                         problem.caps(Fraction(1,2)),False)[0],2)

    def test_block_complete_against_exhaustive_worlds(self):
        rng=np.random.default_rng(2026110361)
        worlds=0
        for n in range(3,8):
            for repeat in range(3):
                blocks=np.arange(n)%2 if repeat else np.zeros(n,dtype=int)
                g=rng.integers(0,2,(2,n));g[:,0]=0;g[:,1]=1
                z=rng.integers(0,2,(2,n)); p=np.arange(n)
                problem=Problem(g,z,p,blocks,blocks); delta=Fraction(1,4); caps=problem.caps(delta)
                original=bool(np.all(abs(problem.values(p))<=caps)); expected=inf
                for perm in permutations(range(n)):
                    pp=np.asarray(perm)
                    if not np.array_equal(blocks,blocks[pp]):continue
                    worlds+=1
                    if bool(np.all(abs(problem.values(pp))<=caps))!=original:
                        expected=min(expected,int(np.count_nonzero(pp!=p)))
                for method in ('profile','assignment','mes'):
                    answer=solve_radius(problem,delta,method)
                    if expected==inf:
                        self.assertIsNone(answer['upper'])
                    else:
                        self.assertEqual(answer['upper'],expected)
                        self.assertLessEqual(answer['lower'],expected)
                        self.assertEqual(verify_permutation(problem,answer['witness'],caps,original)[0],expected)
        self.assertGreater(worlds,5000)
        print('Checked block-complete worlds:',worlds)

    def test_sparse_support_counterexample(self):
        p=np.arange(3);g=np.array([[1,0,0]]);z=g.copy();blocks=np.zeros(3,dtype=int)
        problem=Problem(g,z,p,blocks,blocks)
        answer=solve_radius(problem,Fraction(1,2),'profile')
        self.assertEqual(answer['upper'],2)
        cycle=np.array([1,2,0]); allowed=np.eye(3,dtype=bool);allowed[np.arange(3),cycle]=True
        restricted=[]
        for perm in permutations(range(3)):
            pp=np.asarray(perm)
            if allowed[np.arange(3),pp].all() and np.all(abs(problem.values(pp))<=problem.caps(Fraction(1,2))):
                restricted.append(int(np.count_nonzero(pp!=p)))
        self.assertEqual(min(restricted),3)

    def test_singleton_profiles_reduce_to_assignment(self):
        n=6;ids=np.eye(n,dtype=int);p=np.arange(n);b=np.zeros(n,dtype=int)
        problem=Problem(ids,ids,p,b,b)
        profile=build_model(problem,'profile'); direct=build_model(problem,'assignment')
        self.assertEqual(len(profile.cost),n*n)
        self.assertEqual(len(direct.cost),n*n)
        self.assertEqual(sorted(profile.cost.tolist()),sorted(direct.cost.tolist()))

    def test_fractional_lp_does_not_imply_integer_attainability(self):
        g=np.array([[1,0]]);p=np.arange(2);b=np.zeros(2,dtype=int)
        problem=Problem(g,g,p,b,b);model=build_model(problem,'profile')
        B=np.r_[model.query,-model.query];d=np.zeros(2,dtype=int)
        lower,certificate=checked_lp_bound(model,B,d)
        self.assertEqual(lower,1)  # fractional halfway exchange costs one, no such permutation exists
        self.assertEqual(verify_lp_certificate(model,B,d,certificate),1)
        answer=solve_radius(problem,0)
        self.assertTrue(answer['rigorous_invariant'])  # exact binary-count margins reject the target

    def test_integer_dual_certificate_rejects_corruption(self):
        g=np.array([[1,0,0]]);p=np.arange(3);b=np.zeros(3,dtype=int)
        model=build_model(Problem(g,g,p,b,b),'profile')
        B=model.query;d=np.array([0])
        _,cert=checked_lp_bound(model,B,d)
        bad=copy.deepcopy(cert);bad['numerator']+=1
        with self.assertRaises(ValueError):verify_lp_certificate(model,B,d,bad)
        bad=copy.deepcopy(cert);bad['inequality'][0]=-1
        with self.assertRaises(ValueError):verify_lp_certificate(model,B,d,bad)

    def test_infeasibility_separator_checked_independently(self):
        g=np.array([[1,0,0]]);p=np.arange(3);b=np.zeros(3,dtype=int)
        model=build_model(Problem(g,g,p,b,b),'profile')
        B=np.zeros((1,len(model.cost)),dtype=int);d=np.array([-1])
        bound,cert=checked_lp_bound(model,B,d)
        self.assertEqual(bound,inf)
        self.assertEqual(verify_lp_certificate(model,B,d,cert),inf)

    def test_hypergeometric_risk_for_every_possible_error_count(self):
        for n in range(3,14):
            for radius in range(2,n+1):
                for sample in range(n+1):
                    threshold=cutoff(n,radius,sample)
                    for actual in range(radius,n+1):
                        self.assertLessEqual(cdf(n,actual,sample,threshold),Fraction(1,20))

    def test_reject_invalid_support_and_wrong_witness(self):
        g=np.array([[1,0]]);p=np.arange(2)
        with self.assertRaises(ValueError):Problem(g,g,p,np.array([0,1]),np.array([1,0]))
        problem=Problem(g,g,p,np.zeros(2),np.zeros(2))
        with self.assertRaises(ValueError):verify_permutation(problem,p,problem.caps(0),False)


if __name__=='__main__':unittest.main()
