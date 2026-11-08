"""Fixed within- and separate-admission selection, with person disjointness."""
import numpy as np
from paths import RAW as RAW_ROOT, PROCESSED
from prepare_stays import read_table,eligible,profile,offset
from linkers import fit_score,nonconformity
import json
RAW=RAW_ROOT/"eicu-crd-demo-2.0.1-files"

def prepared():
    return json.loads((PROCESSED/"prepared-records.json").read_text())

def binary_contexts():
    data = prepared()
    natural = data['natural']
    train, test = natural[:30], natural[30:]
    weights = fit_score([r['left']['profile'] for r in train], [[r['right']['profile'] for r in train]], True)
    order = np.random.default_rng(93699).permutation(len(test))
    right = [test[j]['right'] for j in order]
    left = [r['left'] for r in test]
    scores = nonconformity([r['profile'] for r in left], [r['profile'] for r in right], weights, True)
    yield dict(id='natural', study='natural', family='natural_profiles', n=len(test), training_pair_labels=30,
               training_persons=[r['person_key'] for r in train], test_persons=[r['person_key'] for r in test]), left, right, scores, np.argsort(order)


def context_cases():
    data=prepared()
    original=next(binary_contexts())
    meta,left,right,scores,truth=original
    yield dict(id='index-within-admission',study='context',family='within_admission_context',n=len(left),training_pair_labels=30,
               phase='post_observation_diagnostic',training_persons=meta['training_persons'],test_persons=meta['test_persons']),left,right,scores,truth
    raw={}
    for row in read_table(RAW,'patient'):raw.setdefault(row['uniquepid'],[]).append(row)
    pairs=[];excluded=0
    for item in data['main'][1352:]:
        candidates=[r for r in raw[item['person_key']] if r['patienthealthsystemstayid']!=item['reference_admission']]
        if not candidates:continue
        target=min(candidates,key=lambda r:int(r['patientunitstayid']))
        if not eligible(target):excluded+=1;continue
        pairs.append((item,target))
    keys={r['patientunitstayid'] for _,r in pairs};labs={k:[] for k in keys}
    for row in read_table(RAW,'lab'):
        if row['patientunitstayid'] in keys and row['labname'].strip().casefold()=='creatinine':
            labs[row['patientunitstayid']].append(offset(row['labresultoffset']))
    left=[item for item,row in pairs]
    unpermuted=[dict(profile=profile(row),reference_unit_stay=row['patientunitstayid'],
                    outcomes=dict(recorded_expired=row['unitdischargestatus'].strip()=='Expired',
                                  missing_discharge_weight=not row['dischargeweight'].strip(),
                                  creatinine_6h=any(0<=t<=360 for t in labs[row['patientunitstayid']]))) for item,row in pairs]
    order=np.random.default_rng(93799).permutation(len(pairs));right=[unpermuted[j] for j in order]
    train=data['natural'][:30]
    weights=fit_score([r['left']['profile'] for r in train],[[r['right']['profile'] for r in train]],True)
    scores=nonconformity([r['profile'] for r in left],[r['profile'] for r in right],weights,True)
    yield dict(id='index-separate-admission',study='context',family='separate_admission_context',n=len(left),training_pair_labels=30,phase='fresh_unused_people',
               candidate_people=len(pairs)+excluded,excluded_profile_pairs=excluded,
               training_persons=[r['person_key'] for r in train],test_persons=[r['person_key'] for r in left]),left,right,scores,np.argsort(order)
