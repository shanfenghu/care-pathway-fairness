"""Classical fixed-sample hypergeometric tests applied to checked radii.

No independent-link-error model or calibrated score probability is assumed.
All fractions below are exact; randomisation is over the audit sample only.
"""
from fractions import Fraction
from math import ceil,comb


def cdf(n,errors,sample,observed):
    if not 0<=errors<=n or not 0<=sample<=n:raise ValueError('Invalid finite population')
    lo=max(0,sample-(n-errors)); hi=min(observed,errors,sample)
    return Fraction(sum(comb(errors,k)*comb(n-errors,sample-k) for k in range(lo,hi+1)),comb(n,sample))


def cutoff(n,radius,sample,alpha=Fraction(1,20)):
    """Largest observed-error count rejecting K>=radius at the given level."""
    if not 0<radius<=n:raise ValueError('Finite positive checked radius required')
    return max((e for e in range(sample+1) if cdf(n,radius,sample,e)<=alpha),default=-1)


def audit_curve(n,actual_errors,lower,invariant=False):
    if invariant:
        return dict(no_checks_required=True,reason='declared support fixes the workload verdict',rows=[])
    alpha=Fraction(1,20); rows=[]
    for fraction in (Fraction(1,10),Fraction(1,4),Fraction(1,2),Fraction(3,4),Fraction(1)):
        m=ceil(fraction*n)
        threshold=cutoff(n,lower,m,alpha) if lower else -1
        acceptance=cdf(n,actual_errors,m,threshold)
        worst=cdf(n,lower,m,threshold) if lower else Fraction(0)
        zero_allowed=lower>0 and cdf(n,lower,m,0)<=alpha
        zero=cdf(n,actual_errors,m,0) if zero_allowed else Fraction(0)
        assert worst<=alpha
        rows.append(dict(sample=m,cutoff=threshold,checks=m,
                         full_rule_acceptance=str(acceptance),full_rule_acceptance_decimal=float(acceptance),
                         worst_wrong_world_bound=str(worst),zero_only_acceptance=str(zero),
                         zero_only_acceptance_decimal=float(zero)))
    m0=next((m for m in range(n+1) if lower>0 and cdf(n,lower,m,0)<=alpha),None)
    return dict(alpha=str(alpha),checked_lower_radius=lower,zero_error_minimum_sample=m0,rows=rows)
