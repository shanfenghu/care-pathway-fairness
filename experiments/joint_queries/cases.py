"""Frozen rosters, held-out noise and same-feature statistical point linkers."""
from pathlib import Path
import csv
import gzip
import json
from time import perf_counter
import numpy as np
from scipy.optimize import linear_sum_assignment, minimize
from scipy.special import expit
from linkers import agreements,corrupt,fit_score,nonconformity
from contexts import context_cases
from contexts import prepared
from paths import PROCESSED,RAW


def comparison_features(left,right):
    matrices=agreements(left,right,True)
    return np.stack([np.ones_like(matrices[0],dtype=float)]+
                    [(a==v).astype(float) for k,a in enumerate(matrices) for v in range(4 if k==0 else 3)],axis=-1)


def fit_logistic(features,regularisation):
    n=features.shape[0]; X=features.reshape(n*n,-1)
    y=np.eye(n).ravel(); weight=np.where(y,.5/n,.5/(n*(n-1)))
    penalty=np.ones(X.shape[1]);penalty[0]=0
    def objective(beta):
        score=np.einsum('ij,j->i',X,beta,optimize=False)
        loss=np.sum(weight*(np.logaddexp(0,score)-y*score))+.5*regularisation*np.sum(penalty*beta**2)/n
        gradient=np.einsum('ij,i->j',X,weight*(expit(score)-y),optimize=False)+regularisation*penalty*beta/n
        return float(loss),gradient
    result=minimize(objective,np.zeros(X.shape[1]),jac=True,method='L-BFGS-B',options=dict(maxiter=500,gtol=1e-8))
    if not result.success or not np.isfinite(result.x).all():raise RuntimeError('Logistic fitting did not converge: '+str(result.message))
    return result.x


def train_models(left,right,seed):
    start=perf_counter(); features=comparison_features(left,right); n=len(left)
    order=np.random.default_rng(seed).permutation(n); cut=int(.75*n); fit=order[:cut]; val=order[cut:]
    loss=[]
    for reg in (.1,1.,10.):
        beta=fit_logistic(features[np.ix_(fit,fit)],reg)
        scores=np.einsum('ijk,k->ij',features[np.ix_(val,val)],beta,optimize=False); y=np.eye(len(val)); w=np.where(y,.5/len(val),.5/(len(val)*(len(val)-1)))
        loss.append(float(np.sum(w*(np.logaddexp(0,scores)-y*scores))))
    selected=(.1,1.,10.)[int(np.argmin(loss))]
    beta=fit_logistic(features,selected); logistic_seconds=perf_counter()-start
    start=perf_counter(); fs=fit_score(left,[right],True); fs_seconds=perf_counter()-start
    return dict(fs=fs,beta=beta,summary=dict(training_known_matches=n,logistic_lambda=selected,
                validation_balanced_log_losses=loss,person_holdout=len(val),
                logistic_fit_and_tuning_seconds=logistic_seconds,fs_fit_seconds=fs_seconds))


def roster_data():
    """The eight predeclared population/noise settings; no outcome-based selection."""
    start=perf_counter()
    original=json.loads((PROCESSED/'prepared-workloads.json').read_text())['datasets']
    profiles=json.loads((PROCESSED/'linkage-profiles.json').read_text())['datasets']
    ds=next(d for d in original if 'MIMIC' in d['name']); pr=next(d for d in profiles if 'MIMIC' in d['name'])['profiles']
    data=prepared()
    with gzip.open(RAW/'eicu-crd-demo-2.0.1-files/patient.csv.gz','rt') as stream:
        raw=list(csv.DictReader(stream))
    hospitals={r['patientunitstayid']:r['hospitalid'] for r in raw}
    load_seconds=perf_counter()-start
    index=0
    for roster_idx,split in enumerate((101201,101202)):
        ids=np.random.default_rng(split).permutation(len(pr));train,test=ids[:40],ids[40:]
        training=[pr[i] for i in train];left=[pr[i] for i in test]
        vocab=[sorted({r['attributes'][k] for r in training}) for k in range(len(training[0]['attributes']))]
        training_feed=corrupt(training,np.random.default_rng(2026110310+roster_idx),vocab)
        models=train_models(training,training_feed,2026110350+roster_idx)
        flags=np.array([[any(0<=v<=24 for v in ds['cohort'][i]['stage']),
                         any(0<=v<=24 for v in ds['cohort'][i]['event']),
                         any(0<=v<=72 for v in ds['cohort'][i]['event'])] for i in test],dtype=int).T
        groups=np.array([[r['group']=='F',r['age']>=65] for r in left],dtype=int).T
        for family in ('base','shifted'):
            rng=np.random.default_rng(2026110400+index);feed=corrupt(left,rng,vocab,shifted=family=='shifted');order=rng.permutation(len(left))
            yield (dict(id=f'mimic-{split}-{family}',dataset='MIMIC-IV Demo2.2',family=family,n=len(left),
                       reused_population=True,test_indices=test.tolist(),training_indices=train.tolist(),
                       noise_seed=2026110400+index,shared_load_seconds=load_seconds,
                       source_indicators=['stage within 24h','event within 24h','event within 72h']),
                       left,[feed[j] for j in order],groups,flags[:,order],np.argsort(order),
                       np.zeros(len(left),dtype=int),np.zeros(len(left),dtype=int),models)
            index+=1
    # Actual cross-stay records retain their recorded differences; only source order changes.
    natural_train=data['natural'][:30]
    training=[r['left']['profile'] for r in natural_train]; training_feed=[r['right']['profile'] for r in natural_train]
    natural_models=train_models(training,training_feed,2026110352)
    for meta,left_rows,right_rows,_,truth in context_cases():
        left=[r.get('profile',r.get('left',{}).get('profile')) for r in left_rows]
        right=[r['profile'] for r in right_rows]
        groups=np.array([[r['group']=='F',r['age']>=65] for r in left],dtype=int).T
        flags=np.array([[r['outcomes'][k] for k in ('recorded_expired','missing_discharge_weight','creatinine_6h')] for r in right_rows],dtype=int).T
        lb=np.array([hospitals[r['reference_unit_stay']] for r in left_rows])
        rb=np.array([hospitals[r['reference_unit_stay']] for r in right_rows])
        # The within-admission left rows are the prepared nested left records.
        if meta['id']=='index-within-admission':
            test_people=meta['test_persons']
        else:test_people=meta['test_persons']
        yield (dict(id='eicu-'+meta['id'],dataset='eICU Demo2.0.1',family=meta['family'],n=len(left),
                   reused_population=True,test_persons=test_people,training_persons=meta['training_persons'],
                   noise_seed=None,shared_load_seconds=load_seconds,
                   source_indicators=['recorded expired','missing discharge weight','creatinine within 6h']),
                   left,right,groups,flags,truth,lb,rb,natural_models)
        index+=1
    # Exactly the earlier 128-person selection, with new attribute corruption.
    separate_people=set(list(context_cases())[1][0]['test_persons'])
    used={r['person_key'] for r in data['natural']}|{r['person_key'] for r in data['main'][:1352]}|separate_people
    test=[r for r in data['main'][1352:] if r['person_key'] not in used][:128]
    assert len(test)==128
    train=data['main'][612:712];training=[r['profile'] for r in train];left=[r['profile'] for r in test]
    vocab=[sorted({r['attributes'][k] for r in training}) for k in range(4)]
    training_feed=corrupt(training,np.random.default_rng(2026110313),vocab)
    models=train_models(training,training_feed,2026110353)
    groups=np.array([[r['group']=='F',r['age']>=65] for r in left],dtype=int).T
    flags=np.array([[r['outcomes'][k] for k in ('recorded_expired','missing_discharge_weight','creatinine_6h')] for r in test],dtype=int).T
    lb=np.array([hospitals[r['reference_unit_stay']] for r in test])
    for family in ('base','shifted'):
        rng=np.random.default_rng(2026110400+index);feed=corrupt(left,rng,vocab,shifted=family=='shifted');order=rng.permutation(len(left))
        yield (dict(id='eicu-128-'+family,dataset='eICU Demo2.0.1',family=family,n=len(left),
                   reused_population=True,test_persons=[r['person_key'] for r in test],training_persons=[r['person_key'] for r in train],
                   noise_seed=2026110400+index,shared_load_seconds=load_seconds,
                   source_indicators=['recorded expired','missing discharge weight','creatinine within 6h']),
                   left,[feed[j] for j in order],groups,flags[:,order],np.argsort(order),lb,lb[order],models)
        index+=1


def prepare_cases():
    cases=[]; exclusions=[]
    for meta,left,right,groups,flags,truth,lb,rb,models in roster_data():
        for support in ('complete','hospital'):
            if support=='hospital' and meta['dataset'].startswith('MIMIC'):continue
            if support=='hospital' and not np.array_equal(lb,rb[truth]):
                exclusions.append(dict(case=meta['id'],support=support,reason='reference identity crosses hospitals',
                                       crossing_pairs=int(np.count_nonzero(lb!=rb[truth]))))
                continue
            left_blocks=lb if support=='hospital' else np.zeros(len(left),dtype=int)
            right_blocks=rb if support=='hospital' else np.zeros(len(right),dtype=int)
            allowed=left_blocks[:,None]==right_blocks[None,:]
            for linker in ('fs','logistic'):
                tick=perf_counter()
                scores=nonconformity(left,right,models['fs'],True) if linker=='fs' else -np.einsum('ijk,k->ij',comparison_features(left,right),models['beta'],optimize=False)
                if not np.isfinite(scores).all():raise ArithmeticError('Non-finite point-linkage scores')
                proposal=linear_sum_assignment(np.where(allowed,scores,np.inf))[1]
                prediction_seconds=perf_counter()-tick
                cases.append(dict(meta={**meta,'support':support,'linker':linker},groups=groups.tolist(),flags=flags.tolist(),
                                  truth=truth.tolist(),proposal=proposal.tolist(),left_blocks=left_blocks.tolist(),right_blocks=right_blocks.tolist(),
                                  startup={**models['summary'],'prediction_seconds':prediction_seconds},
                                  identity_errors=int(np.count_nonzero(proposal!=truth)),
                                  source_profile_errors=int(np.any(flags[:,proposal]!=flags[:,truth],axis=0).sum())))
    return cases,exclusions
