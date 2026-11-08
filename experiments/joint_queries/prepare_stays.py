"""Prepare person-disjoint, real unit-stay records without outcome selection."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

from paths import RAW
RAW = RAW/'eicu-crd-demo-2.0.1-files'


def read_table(root, name):
    with gzip.open(root/(name+'.csv.gz'), 'rt', newline='') as stream:
        yield from csv.DictReader(stream)


def age_value(text):
    value = text.strip().replace(' ', '')
    if value == '>89':
        return 90, True
    if value.isdigit() and 0 <= int(value) <= 89:
        return int(value), False
    return None


def eligible(row):
    return row['gender'].strip() in ('Female', 'Male') and age_value(row['age']) is not None


def profile(row):
    age, topcoded = age_value(row['age'])
    return dict(age=age, age_topcoded=topcoded,
                group='F' if row['gender'].strip() == 'Female' else 'M',
                attributes=[row[k].strip() or '<MISSING>' for k in
                            ('gender', 'ethnicity', 'hospitaladmitsource', 'unittype')])


def hash_order(rows, salt):
    return sorted(rows, key=lambda r: (hashlib.sha256((salt+r['person_key']).encode()).hexdigest(), r['person_key']))


def choose_records(patient):
    """Choose rosters using keys and profile eligibility, never query outcomes."""
    people = defaultdict(list)
    for row in patient:
        if not row['uniquepid'].strip():
            raise ValueError('Missing reference person key')
        people[row['uniquepid']].append(row)
    natural, main = [], []
    counts = Counter(raw_unit_stays=len(patient), raw_persons=len(people))
    for person, rows in people.items():
        admissions = defaultdict(list)
        for row in rows:
            admissions[row['patienthealthsystemstayid']].append(row)
        repeats = {key: values for key, values in admissions.items() if len(values) >= 2}
        if repeats:
            counts['repeat_persons'] += 1
            selected = repeats[min(repeats, key=int)]
            selected = sorted(selected, key=lambda r: (int(r['unitvisitnumber']), int(r['patientunitstayid'])))[:2]
            if all(eligible(row) for row in selected):
                counts['repeat_visit_ties'] += int(selected[0]['unitvisitnumber'] == selected[1]['unitvisitnumber'])
                natural.append(dict(person_key=person, left=selected[0], right=selected[1]))
                continue
            counts['ineligible_repeat_pairs'] += 1
        row = min(rows, key=lambda r: int(r['patientunitstayid']))
        if eligible(row):
            main.append(dict(person_key=person, record=row))
        else:
            counts['ineligible_main_persons'] += 1
    natural = hash_order(natural, 'unit-stay-natural-v1|')
    main = hash_order(main, 'unit-stay-validation-v1|')
    counts['natural_pairs'] = len(natural)
    counts['eligible_main_persons'] = len(main)
    assert not ({r['person_key'] for r in natural} & {r['person_key'] for r in main})
    return main, natural, dict(counts)


def offset(text):
    value = float(text)
    if not math.isfinite(value) or value != int(value):
        raise ValueError('Expected exact integer-minute offset')
    return int(value)


def prepare(raw=RAW):
    patient = list(read_table(raw, 'patient'))
    main, natural, counts = choose_records(patient)
    if len(main) < 1352 or len(natural) <= 30:
        raise ValueError('Insufficient person-disjoint records for frozen protocol')
    selected = {r['record']['patientunitstayid'] for r in main}
    selected.update(r[side]['patientunitstayid'] for r in natural for side in ('left', 'right'))
    stages, endpoints = defaultdict(list), defaultdict(list)
    event_counts = Counter()
    for row in read_table(raw, 'lab'):
        key = row['patientunitstayid']
        if key in selected and row['labname'].strip().casefold() == 'creatinine':
            stages[key].append(offset(row['labresultoffset']))
            event_counts['selected_creatinine_rows'] += 1
    for row in read_table(raw, 'treatment'):
        key = row['patientunitstayid']
        if key in selected and row['treatmentstring'].strip():
            endpoints[key].append(offset(row['treatmentoffset']))
            event_counts['selected_treatment_rows'] += 1

    def record(row):
        key = row['patientunitstayid']
        stage, event = sorted(stages[key]), sorted(endpoints[key])
        return dict(reference_unit_stay=key, reference_admission=row['patienthealthsystemstayid'],
                    profile=profile(row), stage_minutes=stage, event_minutes=event,
                    outcomes=dict(recorded_expired=row['unitdischargestatus'].strip() == 'Expired',
                                  missing_discharge_weight=not row['dischargeweight'].strip(),
                                  creatinine_6h=any(0 <= x <= 360 for x in stage)),
                    recorded_discharge_status=row['unitdischargestatus'].strip())
    ordinary = [dict(person_key=r['person_key'], **record(r['record'])) for r in main]
    paired = [dict(person_key=r['person_key'], left=record(r['left']), right=record(r['right'])) for r in natural]
    assert sum(len(r['stage_minutes']) for r in ordinary)+sum(len(r[s]['stage_minutes']) for r in paired for s in ('left','right')) == event_counts['selected_creatinine_rows']
    assert sum(len(r['event_minutes']) for r in ordinary)+sum(len(r[s]['event_minutes']) for r in paired for s in ('left','right')) == event_counts['selected_treatment_rows']
    return dict(dataset='eICU Collaborative Research Database Demo 2.0.1', clock='exact integer minutes relative to selected unit admission',
                profile_fields=['age', 'gender', 'ethnicity', 'hospital_admission_source', 'unit_type'],
                roster_counts=counts, event_counts=dict(event_counts), main=ordinary, natural=paired,
                selection='Keys and visible-profile eligibility only; query outcomes and event availability do not select records')


