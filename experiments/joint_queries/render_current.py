"""Generate portable figures and CSV summaries from retained numerical evidence."""
import argparse
import csv
import json
from pathlib import Path
from statistics import median
from paths import ROOT


def write_csv(path, rows):
    with path.open('x', newline='') as stream:
        csv.writer(stream, lineterminator='\n').writerows(rows)


def render(output, check=False):
    """Render fixed evidence; optionally require exact retained display bytes."""
    if output.exists():
        raise FileExistsError('Choose a fresh display directory')
    figures, tables = output/'figures', output/'tables'
    figures.mkdir(parents=True)
    tables.mkdir()
    import display_example, display_runtime, display_sampling
    display_example.FIGURES = figures
    display_example.render(display_example.checked_data())
    display_runtime.FIGURES = figures
    display_runtime.main()
    display_sampling.FIGURES = figures
    display_sampling.main()
    rows = json.loads((ROOT/'results/joint-query-validation/summary.json').read_text())['rows']
    selected = [(0,'MIMIC/complete'),(1,'MIMIC/complete'),(4,'MIMIC/complete'),
                (8,'eICU/complete'),(10,'eICU/hospital'),(16,'eICU/complete'),
                (18,'eICU/hospital'),(14,'eICU/hospital'),(27,'eICU/complete')]
    output_rows = [['roster_support','linker','n','separate_bound','joint_radius',
                    'wrong_pairs','known_training_pairs']]
    for index, label in selected:
        row = next(r for r in rows if r['case_index'] == index and r['delta'] == '1/20')
        result = row['methods']['profile']
        radius = 'inf' if result['rigorous_invariant'] else result['lower']
        separate = 'inf' if row['separate_invariant'] else row['separate_lower']
        output_rows.append([label,'FS' if row['linker']=='fs' else 'Logistic',row['n'],
                            separate,radius,row['identity_errors'],row['startup']['training_known_matches']])
    write_csv(tables/'case-results.csv', output_rows)
    rows = json.loads((ROOT/'results/support-validation/summary.json').read_text())['rows']
    distinct = json.loads((ROOT/'results/query-followups/weighting.json').read_text())['summary']
    output_rows = [['merge','gains_tasks','joint_workloads','variables_ratio',
                    'time_ratio','distinct_query_time_ratio']]
    for width in [1,4,16,'all']:
        selected = [r for r in rows if r['width'] == width]
        gains = sum(r['methods']['profile']['lower'] is not None and
                    r['methods']['profile']['lower'] > r['separate_lower'] for r in selected)
        joint = sum(r['methods']['profile']['route'] == 'joint' for r in selected)
        variables = median(r['potential_assignment']/r['potential_profile'] for r in selected)
        time = median(r['methods']['assignment']['median_seconds']/r['methods']['profile']['median_seconds']
                      for r in selected)
        deduplicated = next(r['distinct_query_median_ratio'] for r in distinct if r['width']==width)
        output_rows.append([width,f'{gains}/{len(selected)}',joint,
                            f'{variables:.1f}',f'{time:.1f}',f'{deduplicated:.1f}'])
    write_csv(tables/'workload-outcomes.csv', output_rows)
    if check:
        for category, names in [('figures',[f'{n}.{ext}' for n in
                ['joint-example','checked-computation','audit-acceptance'] for ext in ['pdf','png']]),
                ('tables',['case-results.csv','workload-outcomes.csv'])]:
            for name in names:
                if (output/category/name).read_bytes() != (ROOT/category/'joint-query'/name).read_bytes():
                    raise ValueError('Changed display bytes: '+name)
    print('Generated three figure pairs and two CSV tables; retained-byte comparison: '+str(check))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'results/displays')
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    render(args.output.resolve(),args.check)
