import argparse
from fractions import Fraction
import hashlib
import json
from math import inf
from pathlib import Path
import platform
from statistics import median
import subprocess
from time import perf_counter
import numpy as np
import scipy
from linkage_bounds.profile_robustness import (Problem,build_model,solve_radius,verify_permutation,
                                verify_lp_certificate,independent_conditions)
from linkage_bounds.robustness_audit import audit_curve

from paths import ROOT,PROCESSED,DEFAULT
PROTOCOL=ROOT/'configs/joint-query.json'
SOURCES=sorted((ROOT/'src/linkage_bounds').glob('*robustness*.py'))+sorted((ROOT/'experiments/joint_queries').glob('*.py'))
INPUTS=[PROCESSED/x for x in ('prepared-workloads.json','linkage-profiles.json','prepared-records.json')]


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def save(path,value):
    if path.exists():raise FileExistsError('Preserve existing evidence: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def problem(case):
    return Problem(np.array(case['groups']),np.array(case['flags']),np.array(case['proposal']),
                   np.array(case['left_blocks']),np.array(case['right_blocks']))


def prepare(output):
    from cases import prepare_cases
    started=perf_counter(); cases,exclusions=prepare_cases()
    save(output/'cases.json',dict(status='frozen before robustness outcomes',cases=cases,support_exclusions=exclusions,
         preparation_wall_seconds=perf_counter()-started,protocol_sha256=digest(PROTOCOL),
         inputs=[], input_versions='data/input-manifest.json',
         sources=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in SOURCES],
         environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform())))
    print(json.dumps(dict(cases=len(cases),exclusions=exclusions,preparation_seconds=perf_counter()-started)),flush=True)


def read_cases(output,validate=True):
    bundle=json.loads((output/'cases.json').read_text())
    if validate:
        assert digest(PROTOCOL)==bundle['protocol_sha256']
        for record in bundle['inputs']+bundle['sources']:
            assert digest(ROOT/record['path'])==record['sha256'],record['path']
    return bundle


def run(output):
    bundle=read_cases(output); rng=np.random.default_rng(2026110360)
    for index,case in enumerate(bundle['cases']):
        p=problem(case)
        for rep in range(3):
            destination=output/'runs'/f'case-{index:02d}-rep-{rep}.json'
            if destination.exists():
                # Restarting resumes complete case records; their inputs are immutable.
                continue
            rows=[]; start=perf_counter()
            for delta in (Fraction(1,20),Fraction(1,10)):
                order=rng.permutation(['profile','assignment','mes']).tolist()
                for method in order:
                    result=solve_radius(p,delta,method,mip_seconds=5.,lp_seconds=2.)
                    rows.append(result)
            save(destination,dict(case_index=index,repetition=rep,cases_sha256=digest(output/'cases.json'),
                                  elapsed_seconds=perf_counter()-start,results=rows))
        label=case['meta']
        print(f"completed {index+1}/{len(bundle['cases'])}: {label['id']} {label['support']} {label['linker']}",flush=True)


def check(output):
    bundle=read_cases(output); checked=certificates=witnesses=closed=0; numerical_disagreements=[]
    for index,case in enumerate(bundle['cases']):
        p=problem(case)
        for rep in range(3):
            saved=json.loads((output/'runs'/f'case-{index:02d}-rep-{rep}.json').read_text())
            assert saved['cases_sha256']==digest(output/'cases.json')
            assert len(saved['results'])==6
            for delta in ('1/20','1/10'):
                rows=[r for r in saved['results'] if r['delta']==delta]; assert {r['method'] for r in rows}=={'profile','assignment','mes'}
                numeric=[(r['numerical_optimum'],r['rigorous_invariant']) for r in rows]
                if len(set(numeric))>1:numerical_disagreements.append(dict(case_index=index,repetition=rep,delta=delta,values=numeric))
                for r in rows:
                    model=build_model(p,r['method']);caps=p.caps(delta); base_inside=bool(np.all(abs(p.values(p.proposal))<=caps))
                    assert base_inside==r['baseline_inside']; scalar=independent_conditions(p,caps)
                    expected=[]
                    if base_inside:
                        for q,s in enumerate(scalar):
                            if s['negative']<inf:expected.append((f'{q}:negative',s['negative']))
                            if s['positive']<inf:expected.append((f'{q}:positive',s['positive']))
                    elif all(s['enter']<inf for s in scalar):expected=[('all_within',max(s['enter'] for s in scalar))]
                    assert [x[0] for x in expected]==[x['branch'] for x in r['branches']]
                    lowers=[]
                    for branch,(_,analytic) in zip(r['branches'],expected):
                        label=branch['branch']
                        if label=='all_within':B=np.r_[model.query,-model.query];d=np.r_[caps,caps]
                        else:
                            q,side=label.split(':');q=int(q)
                            B=model.query[q:q+1]*(1 if side=='negative' else -1);d=np.array([-int(caps[q])-1])
                        cert=branch['certificate']; lower=0
                        if cert is not None:lower=verify_lp_certificate(model,B,d,cert);certificates+=1
                        lower=max(lower,analytic,2);lowers.append(lower)
                        assert (lower==inf)==branch['infeasible_proved']
                        if lower<inf:assert lower==branch['lower']
                    lower=min(lowers,default=inf)
                    assert (lower==inf)==r['rigorous_invariant']
                    if lower<inf:assert lower==r['lower']
                    if r['upper'] is not None:
                        distance,_=verify_permutation(p,r['witness'],caps,base_inside)
                        assert distance==r['upper'];assert lower<=distance;witnesses+=1
                    if r['bracket_closed']:closed+=1
                    checked+=1
    receipt=dict(records=checked,integer_dual_certificates=certificates,original_space_witnesses=witnesses,
                 closed_brackets=closed,numerical_disagreements=numerical_disagreements,inputs_and_sources_match=True)
    save(output/'verification.json',receipt);print(json.dumps(receipt),flush=True)


def summarise(output):
    bundle=read_cases(output);rows=[]
    for index,case in enumerate(bundle['cases']):
        p=problem(case);runs=[json.loads((output/'runs'/f'case-{index:02d}-rep-{r}.json').read_text()) for r in range(3)]
        for delta in ('1/20','1/10'):
            methods={}
            for method in ('profile','assignment','mes'):
                repeated=[next(x for x in run['results'] if x['delta']==delta and x['method']==method) for run in runs]
                result=repeated[0];times=[r['timing']['total_seconds'] for r in repeated]
                methods[method]={k:result[k] for k in ('lower','upper','numerical_optimum','bracket_closed','rigorous_invariant','geometry')}
                methods[method].update(total_seconds_median=median(times),total_seconds_range=[min(times),max(times)],
                                      timing_components_first=result['timing'])
            profile=next(x for x in runs[0]['results'] if x['delta']==delta and x['method']=='profile')
            truth_inside=bool(np.all(abs(p.values(np.asarray(case['truth'])))<=p.caps(delta)))
            correct=truth_inside==profile['baseline_inside']
            if not profile['rigorous_invariant'] and case['identity_errors']<profile['lower']:assert correct
            rows.append(dict(case_index=index,**case['meta'],delta=delta,identity_errors=case['identity_errors'],
                             source_profile_errors=case['source_profile_errors'],point_verdict_correct=correct,
                             baseline_inside=profile['baseline_inside'],truth_inside=truth_inside,
                             methods=methods,separate_lower=profile['separate_lower'],separate_invariant=profile['separate_invariant'],
                             audit=audit_curve(p.n,case['identity_errors'],profile['lower'],profile['rigorous_invariant']),
                             separate_audit=audit_curve(p.n,case['identity_errors'],profile['separate_lower'],profile['separate_invariant']),
                             startup=case['startup']))
    save(output/'summary.json',dict(scope='conditional development evaluation; reused populations and new fixed noise',
                                   rows=rows,support_exclusions=bundle['support_exclusions'],
                                   preparation_wall_seconds=bundle['preparation_wall_seconds']))
    for dataset in ('MIMIC-IV Demo2.2','eICU Demo2.0.1'):
        selected=[r for r in rows if r['dataset']==dataset]
        gains=[r for r in selected if (r['methods']['profile']['rigorous_invariant'] and not r['separate_invariant']) or
               (not r['methods']['profile']['rigorous_invariant'] and r['separate_lower'] is not None and r['methods']['profile']['lower']>r['separate_lower'])]
        print(json.dumps(dict(dataset=dataset,workload_instances=len(selected),certified_joint_gains=len(gains),
                              point_correct=sum(r['point_verdict_correct'] for r in selected),
                              closed=sum(r['methods']['profile']['bracket_closed'] for r in selected),
                              profile_median=median(r['methods']['profile']['total_seconds_median'] for r in selected),
                              assignment_median=median(r['methods']['assignment']['total_seconds_median'] for r in selected))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','check','summarise'])
    parser.add_argument('--output',type=Path,default=DEFAULT);args=parser.parse_args()
    globals()[args.action](args.output)
