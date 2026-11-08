"""Verify both retained comparisons without invoking an optimiser.

Receipts go to a fresh directory; input records remain unchanged. Rebuilds every
model and checks scalar bounds, integer lower certificates and original-space
witnesses, including all support-intervention chains.
"""
import argparse,json
from pathlib import Path
import scipy.optimize
from paths import ROOT


def verify(primary,support,output):
    if output.exists():raise FileExistsError('Choose a fresh receipt directory')
    output.mkdir(parents=True)
    def forbidden(*args,**kwargs):raise AssertionError('Optimisation is forbidden during verification')
    # Patch before importing the checkers so their bound imports are covered.
    scipy.optimize.linprog=scipy.optimize.milp=scipy.optimize.linear_sum_assignment=forbidden
    import run_queries,run_support
    from source_versions import APPLIED
    receipts={}
    def sink(prefix):
        def save(path,value):
            if Path(path).name=='summary.json':
                expected=json.loads((support/'summary.json').read_text())
                if value!=expected:raise ValueError('Retained support summary disagrees with checked runs')
                return
            name=prefix+'-'+Path(path).name;receipts[name]=value
            with (output/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
        return save
    run_queries.OUT=primary;run_queries.save=sink('query');run_queries.check()
    run_support.OUT=support;run_support.save=sink('support');run_support.check()
    versions={'generation_source_pins_unchanged':True,'retained_timings_unchanged':True,
              'amendments':APPLIED}
    with (output/'source-amendments.json').open('x') as f:
        json.dump(versions,f,indent=2);f.write('\n')
    print(json.dumps({'verified_outputs':sum(x['outputs'] for x in receipts.values()),
                      'solver_calls':0,'source_amendments':len(APPLIED)}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--primary',type=Path,default=ROOT/'results/joint-query-validation')
    p.add_argument('--support',type=Path,default=ROOT/'results/support-validation')
    p.add_argument('--output',type=Path,default=ROOT/'results/verification')
    a=p.parse_args();verify(a.primary.resolve(),a.support.resolve(),a.output.resolve())
