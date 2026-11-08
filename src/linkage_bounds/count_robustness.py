"""Integer-count formulation and common scalar-first route for all comparators."""
from fractions import Fraction
from math import ceil,floor,inf,log
from time import perf_counter
import numpy as np
from scipy.optimize import Bounds,LinearConstraint,milp
from .profile_robustness import build_model,independent_conditions,checked_lp_bound,verify_permutation
from .robustness_integer_proof import prove_integer_lower,verify_integer_tree


def count_constraints(problem,model,caps):
    low=[];high=[]
    for g in problem.groups:
        a=int(g.sum())
        for f in problem.flags:
            cap=int(caps[len(low)]);t=int(f.sum())
            low.append(ceil(Fraction(a*t-cap,problem.n)))
            high.append(floor(Fraction(a*t+cap,problem.n)))
    return (model.query>0).astype(np.int64),np.array(low,dtype=np.int64),np.array(high,dtype=np.int64)


def scalar_violation_witness(problem,q,direction,distance):
    p=problem.proposal.copy(); g=problem.groups[q//len(problem.flags)].astype(bool);f=problem.flags[q%len(problem.flags)]
    remaining=distance//2
    for block in sorted(set(problem.left_blocks.tolist())):
        rows=np.flatnonzero(problem.left_blocks==block);y=f[p]
        first=[int(i) for i in rows if g[i] and y[i]==(0 if direction=='positive' else 1)]
        second=[int(i) for i in rows if not g[i] and y[i]==(1 if direction=='positive' else 0)]
        take=min(remaining,len(first),len(second))
        for i,j in zip(first[:take],second[:take]):p[i],p[j]=p[j],p[i]
        remaining-=take
    if remaining:raise ArithmeticError('Scalar attaining swaps unavailable')
    return p


def scalar_entry_witness(problem,caps,scalar):
    """Try attaining the scalar lower bound for an outside-band joint query.

Use the fixed row-order swap construction for each worst violated condition.
A returned permutation is checked against every original condition; failure to
find one says nothing about joint feasibility or the exact radius.
"""
    separate=max(s['enter'] for s in scalar)
    if separate==inf:return None
    base=problem.values(problem.proposal)
    for q,s in enumerate(scalar):
        if s['enter']!=separate:continue
        direction='positive' if base[q]<-caps[q] else 'negative'
        p=scalar_violation_witness(problem,q,direction,int(separate))
        if np.all(np.abs(problem.values(p))<=caps):
            distance,_=verify_permutation(problem,p,caps,False)
            if distance!=separate:raise ArithmeticError('Scalar lower bound and witness disagree')
            return p
    return None


def checked_count_candidate(problem,model,B,d,candidate,caps,inside):
    """Treat a solver vector only as a proposal; reject fractional/invalid counts."""
    if not np.isfinite(candidate).all() or np.max(abs(candidate-np.rint(candidate)))>1e-6:
        return None
    x=np.rint(candidate).astype(np.int64)
    if (not np.array_equal(model.equality@x,model.totals) or np.any(B@x>d)
            or np.any(x<0) or np.any(x>model.upper)):
        return None
    p=model.permutation(x);distance,values=verify_permutation(problem,p,caps,inside)
    return distance,p,values


def solve_count_radius(problem,delta,kind='profile'):
    started=perf_counter();caps=problem.caps(delta);base=problem.values(problem.proposal)
    inside=bool(np.all(abs(base)<=caps));scalar=independent_conditions(problem,caps)
    separate=min((min(s['negative'],s['positive']) for s in scalar),default=inf) if inside else max(s['enter'] for s in scalar)
    entry=scalar_entry_witness(problem,caps,scalar) if not inside and separate<inf else None
    result=dict(method=kind,delta=str(Fraction(delta)),baseline_inside=inside,base_values=base.tolist(),caps=caps.tolist(),
                separate_lower=None if separate==inf else int(separate),separate_invariant=separate==inf,
                lower=None,upper=None,rigorous_invariant=False,bracket_closed=False,
                branches=[],proof_parts=[],geometry=dict(variables=0),constraint_form='integer_count')
    if separate==inf:
        result.update(route='scalar_invariant',rigorous_invariant=True,bracket_closed=True)
    elif inside:
        candidates=[(int(s[side]),q,side) for q,s in enumerate(scalar) for side in ('negative','positive') if s[side]<inf]
        distance,q,side=min(candidates);p=scalar_violation_witness(problem,q,side,distance)
        checked,values=verify_permutation(problem,p,caps,inside);assert checked==distance
        result.update(route='scalar_violation',lower=distance,upper=distance,bracket_closed=True,witness=p.tolist(),witness_values=values)
    elif entry is not None:
        distance,values=verify_permutation(problem,entry,caps,inside)
        result.update(route='scalar_entry',lower=distance,upper=distance,bracket_closed=True,
                      witness=entry.tolist(),witness_values=values)
    else:
        tick=perf_counter();model=build_model(problem,kind);representation=perf_counter()-tick
        counts,low,high=count_constraints(problem,model,caps);B=np.r_[counts,-counts];d=np.r_[high,-low]
        primals=[]
        tick=perf_counter();lower,cert=checked_lp_bound(model,B,d,primal_candidates=primals);lp_seconds=perf_counter()-tick
        lower=max(separate,lower,2)
        result.update(route='joint',geometry=model.geometry,lower=None if lower==inf else int(lower),
                      rigorous_invariant=lower==inf,branches=[dict(branch='all_within',certificate=cert)],
                      representation_seconds=representation,lp_bound_seconds=lp_seconds,count_low=low.tolist(),count_high=high.tolist())
        if lower==inf:result['bracket_closed']=True
        else:
            result.update(lp_primal_accepted=False,lp_closed_without_mip=False,witness_check_seconds=0.)
            for candidate in primals:
                tick=perf_counter()
                checked=checked_count_candidate(problem,model,B,d,candidate,caps,inside)
                result['witness_check_seconds']+=perf_counter()-tick
                if checked is not None:
                    distance,p,values=checked
                    if lower>distance:raise ArithmeticError('Lower bound exceeds attaining distance')
                    result.update(upper=distance,witness=p.tolist(),witness_values=values,lp_primal_accepted=True)
            if result['upper']==lower:
                result['lp_closed_without_mip']=True
            else:
                tick=perf_counter();scale=log(9.) if kind=='mes' else 1.
                answer=milp(model.cost*scale,integrality=np.ones(len(model.cost)),bounds=Bounds(0,model.upper),
                            constraints=[LinearConstraint(model.equality,model.totals,model.totals),LinearConstraint(B,-np.inf,d)],
                            options=dict(time_limit=5.,mip_rel_gap=0.))
                result.update(mip_seconds=perf_counter()-tick,solver_status=int(answer.status))
                if answer.x is not None:
                    tick=perf_counter();checked=checked_count_candidate(problem,model,B,d,answer.x,caps,inside)
                    if checked is None:raise ArithmeticError('Invalid integer count-model incumbent')
                    distance,p,values=checked
                    if lower>distance:raise ArithmeticError('Lower bound exceeds attaining distance')
                    if result['upper'] is None or distance<result['upper']:
                        result.update(upper=distance,witness=p.tolist(),witness_values=values)
                    result['witness_check_seconds']+=perf_counter()-tick
            if result['upper'] is not None:
                if lower<result['upper']:
                    tick=perf_counter();proof=prove_integer_lower(model,B,d,result['upper'],seconds=2.,max_nodes=128)
                    if proof['complete']:
                        proof['verification']=verify_integer_tree(model,B,d,result['upper'],proof['tree']);result['lower']=result['upper']
                    result['proof_parts']=[proof];result['integer_proof_seconds']=perf_counter()-tick
                result['bracket_closed']=result['lower']==result['upper']
        if kind=='mes' and result['upper'] is not None:
            result['mes_log_likelihood']=(problem.n-result['upper'])*log(.9)+result['upper']*log(.1)
    result['total_seconds']=perf_counter()-started
    return result
