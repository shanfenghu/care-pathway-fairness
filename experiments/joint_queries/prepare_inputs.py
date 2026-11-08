"""Reconstruct the recorded workloads and profiles from the exact public demos."""
import json
from paths import RAW, PROCESSED
from prepare_mimic import mimic, read_gzip, timestamp
from prepare_stays import prepare
from run_rate import save
from acquire_inputs import verify


def main():
    verify(RAW)
    target = RAW/'mimic-iv-demo-2.2-files'
    workload = mimic(target)
    patients = read_gzip(target, 'hosp/patients.csv.gz')
    admissions = read_gzip(target, 'hosp/admissions.csv.gz')
    profiles = []
    for person in patients:
        choices = [a for a in admissions if a['subject_id'] == person['subject_id']]
        if not choices:
            continue
        admission = min(choices, key=lambda a: timestamp(a['admittime']))
        attributes = [person['gender'], *[admission.get(k, '') for k in
                      ('race', 'marital_status', 'language', 'insurance')]]
        profiles.append(dict(age=int(person['anchor_age']), group=person['gender'],
                             attributes=[str(x).strip().upper() if str(x).strip()
                                         else '<MISSING>' for x in attributes]))
    assert len(profiles) == len(workload['cohort']) == 100
    for profile, row in zip(profiles, workload['cohort'], strict=True):
        assert (profile['age'], profile['group']) == (row['age'], row['group'])
    save(PROCESSED/'prepared-workloads.json', {'datasets': [workload]})
    save(PROCESSED/'linkage-profiles.json', {'datasets': [dict(
        name=workload['name'], profiles=profiles,
        fields=['sex', 'race', 'marital', 'language', 'insurance'])]})
    save(PROCESSED/'prepared-records.json', prepare(RAW/'eicu-crd-demo-2.0.1-files'))
    print('Prepared 100 MIMIC people and the fixed eICU stay rosters.')


if __name__ == '__main__':
    main()
