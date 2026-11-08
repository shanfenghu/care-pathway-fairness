"""Exact sampling comparisons and weighting sensitivity from retained records.

These are conditional analyses on reused people, not new measurements. All
integer question budgets and both sampling policies are retained, including
budgets where frame restriction reduces acceptance.
"""
import argparse,hashlib,json
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from math import ceil
from pathlib import Path
from statistics import median
import numpy as np
from linkage_bounds.profile_robustness import Problem
from linkage_bounds.query_sampling import relevant_rows
from linkage_bounds.robustness_audit import cdf
from paths import ROOT


@lru_cache(None)
def acceptance(n,k,lower,m):
    lo,hi=-1,m+1
    while hi-lo>1:
        mid=(lo+hi)//2
        if cdf(n,lower,m,mid)<=Fraction(1,20):lo=mid
        else:hi=mid
    assert cdf(n,lower,m,lo)<=Fraction(1,20)
    return cdf(n,k,m,lo)


def sampling(primary):
    cases=json.loads((primary/'cases.json').read_text())['cases']
    rows=json.loads((primary/'summary.json').read_text())['rows'];out=[];control=[];checks=0
    for row in rows:
        c=cases[row['case_index']];p=Problem(*(np.asarray(c[k]) for k in ['groups','flags','proposal','left_blocks','right_blocks']))
        q=relevant_rows(p).tolist();n=p.n;truth=np.asarray(c['truth']);proposal=p.proposal
        kq=int(np.count_nonzero(proposal[q]!=truth[q]));k=int(np.count_nonzero(proposal!=truth));result=row['methods']['profile']
        lower=result['lower'];invariant=result['rigorous_invariant']
        rec={k2:row[k2] for k2 in ['case_index','id','dataset','family','support','linker','delta','point_correct']}
        rec.update(n=n,frame_size=len(q),global_errors=k,frame_errors=kq,radius=lower,invariant=invariant,frame=q)
        if invariant:
            rec.update(curve=[],minimum_budget={'global_half':0,'frame_half':0,'global_95':0,'frame_95':0});out.append(rec);continue
        assert result['bracket_closed'] and 0<lower<=len(q)<=n
        if not row['point_correct']:assert kq>=lower
        curve=[{'budget':b,'global':str(acceptance(n,k,lower,b)),
                'frame':str(acceptance(len(q),kq,lower,min(b,len(q))))} for b in range(n+1)]
        for old in row['audit']['rows']:assert curve[old['sample']]['global']==old['full_rule_acceptance']
        rec['curve']=curve;rec['minimum_budget']={}
        for label,target in [('half',Fraction(1,2)),('95',Fraction(19,20))]:
            for policy in ['global','frame']:
                rec['minimum_budget'][policy+'_'+label]=next((x['budget'] for x in curve if Fraction(x[policy])>=target),None)
        rec['prescribed']=[{'budget':ceil(f*n),'global':curve[ceil(f*n)]['global'],'frame':curve[ceil(f*n)]['frame']}
                           for f in [Fraction(1,10),Fraction(1,4),Fraction(1,2),Fraction(3,4),Fraction(1)]]
        out.append(rec)
        separate=row['separate_lower'];assert 0<separate<=lower;cc=[]
        for v in curve:
            b=v['budget'];g=acceptance(n,k,separate,b);f=acceptance(len(q),kq,separate,min(b,len(q)))
            assert Fraction(v['global'])>=g and Fraction(v['frame'])>=f;checks+=2
            cc.append({'budget':b,'global_separate':str(g),'frame_separate':str(f)})
        cr={k2:rec[k2] for k2 in ['case_index','delta','n','frame_size','global_errors','frame_errors','radius']}
        cr.update(separate_lower=separate,minimum_budget={},curve=cc)
        for label,target in [('half',Fraction(1,2)),('95',Fraction(19,20))]:
            for policy in ['global_separate','frame_separate']:
                cr['minimum_budget'][policy+'_'+label]=next((v['budget'] for v in cc if Fraction(v[policy])>=target),None)
        control.append(cr)
    finite=[x for x in out if not x['invariant']];reduced=[x for x in finite if x['frame_size']<x['n']]
    half=lambda x:next(y for y in x['prescribed'] if y['budget']==ceil(Fraction(1,2)*x['n']))
    summary={'workloads':len(out),'finite':len(finite),'finite_smaller_frame':len(reduced),'invariant':len(out)-len(finite),
        'half_budget_improved':sum(Fraction(half(x)['frame'])>Fraction(half(x)['global']) for x in finite),
        'half_budget_harmed':sum(Fraction(half(x)['frame'])<Fraction(half(x)['global']) for x in finite),
        'all_integer_budget_improvement_points':sum(Fraction(y['frame'])>Fraction(y['global']) for x in finite for y in x['curve']),
        'all_integer_budget_harm_points':sum(Fraction(y['frame'])<Fraction(y['global']) for x in finite for y in x['curve']),
        'global_half_budget_median':float(median(Fraction(half(x)['global']) for x in finite)),
        'frame_half_budget_median':float(median(Fraction(half(x)['frame']) for x in finite)),
        '95_unattainable_global':sum(x['minimum_budget']['global_95'] is None for x in finite),
        '95_unattainable_frame':sum(x['minimum_budget']['frame_95'] is None for x in finite)}
    return {'summary':summary,'rows':out}, {'same_frame_joint_not_weaker_checks':checks,'rows':control}


def weighting(support):
    cases=json.loads((support/'cases.json').read_text())['cases'];rows=json.loads((support/'summary.json').read_text())['rows'];groups=defaultdict(list)
    for row in rows:
        c=cases[row['study_case']]
        key=json.dumps([c['groups'],c['flags'],c['proposal'],(np.asarray(c['left_blocks'])[:,None]==np.asarray(c['right_blocks'])[None,:]).astype(int).tolist(),row['delta']],separators=(',',':'))
        groups[key].append(row)
    unique=[]
    for key,rs in groups.items():
        assert len({r['width'] for r in rs})==1
        endpoints={(r['methods'][m]['lower'],r['methods'][m]['upper'],r['methods'][m]['rigorous_invariant']) for r in rs for m in ['profile','assignment','mes']};assert len(endpoints)==1
        times={m:[] for m in ['profile','assignment','mes']}
        for r in rs:
            for rep in range(3):
                run=json.loads((support/'runs'/f"case-{r['study_case']:02d}-rep-{rep}.json").read_text())
                assert run['cases_sha256']==hashlib.sha256((support/'cases.json').read_bytes()).hexdigest()
                for m in times:times[m].append(next(x['total_seconds'] for x in run['results'] if x['delta']==r['delta'] and x['method']==m))
        med={m:median(t) for m,t in times.items()}
        unique.append(dict(key_sha256=hashlib.sha256(key.encode()).hexdigest(),width=rs[0]['width'],design_cells=len(rs),timing_samples_per_method=len(times['profile']),paired_ratio=med['assignment']/med['profile']))
    summary=[]
    for width in [1,4,16,'all']:
        full=[r['methods']['assignment']['median_seconds']/r['methods']['profile']['median_seconds'] for r in rows if r['width']==width]
        dedup=[r['paired_ratio'] for r in unique if r['width']==width]
        summary.append(dict(width=width,design_workloads=len(full),distinct_queries=len(dedup),full_design_median_ratio=median(full),distinct_query_median_ratio=median(dedup),distinct_query_ratio_range=[min(dedup),max(dedup)]))
    return dict(dependent_design_workloads=len(rows),distinct_queries=len(unique),all_coincident_endpoints_agree=True,summary=summary,distinct_task_cells=unique)


def analyse(primary,support,output,reference=None):
    if output.exists():raise FileExistsError('Choose a fresh analysis directory')
    output.mkdir(parents=True)
    a,b=sampling(primary);c=weighting(support)
    for name,value in [('sampling.json',a),('same-frame-control.json',b),('weighting.json',c)]:
        if reference:
            expected=json.loads((reference/name).read_text())
            assert all(expected[k]==v for k,v in value.items()),'Changed retained analysis: '+name
        with (output/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps({'workloads':a['summary']['workloads'],'finite':a['summary']['finite'],'support_design_workloads':c['dependent_design_workloads'],'distinct_queries':c['distinct_queries'],'reference_comparison':'matched' if reference else 'not requested'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--primary',type=Path,default=ROOT/'results/joint-query-validation')
    p.add_argument('--support',type=Path,default=ROOT/'results/support-validation')
    p.add_argument('--output',type=Path,default=ROOT/'results/followup-checks')
    p.add_argument('--reference',type=Path)
    a=p.parse_args();analyse(a.primary.resolve(),a.support.resolve(),a.output.resolve(),a.reference.resolve() if a.reference else None)
