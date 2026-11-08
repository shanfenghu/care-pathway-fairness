"""Recorded MIMIC hospital-admission workload preparation."""
import datetime as dt
import csv,gzip

def timestamp(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

def read_gzip(root, relative):
    with gzip.open(root / relative, "rt") as stream:
        return list(csv.DictReader(stream))

def mimic(root):
    patients = read_gzip(root, "hosp/patients.csv.gz")
    admissions = read_gzip(root, "hosp/admissions.csv.gz")
    stays = read_gzip(root, "icu/icustays.csv.gz")
    procedures = read_gzip(root, "icu/procedureevents.csv.gz")
    subjects = {p["subject_id"] for p in patients}
    admission_map = {a["hadm_id"]: a for a in admissions}
    stay_map = {s["stay_id"]: s for s in stays}
    checks = {"duplicate_subjects": len(patients) - len(subjects),
              "duplicate_admissions": len(admissions) - len(admission_map),
              "duplicate_stays": len(stays) - len(stay_map),
              "admission_unknown_subject": sum(a["subject_id"] not in subjects for a in admissions),
              "stay_parent_disagreement": sum(s["hadm_id"] not in admission_map or
                  admission_map[s["hadm_id"]]["subject_id"] != s["subject_id"] for s in stays),
              "procedure_parent_disagreement": sum(p["stay_id"] not in stay_map or
                  any(stay_map[p["stay_id"]][k] != p[k] for k in ("subject_id", "hadm_id"))
                  for p in procedures)}
    if any(checks.values()):
        raise ValueError("Demo key validation failed: " + str(checks))
    cohort = []
    for patient in patients:
        choices = [a for a in admissions if a["subject_id"] == patient["subject_id"]]
        if not choices:
            continue
        index = min(choices, key=lambda a: timestamp(a["admittime"]))
        t0 = timestamp(index["admittime"])
        stage = sorted((timestamp(s["intime"]) - t0).total_seconds() / 3600
                       for s in stays if s["hadm_id"] == index["hadm_id"])
        event = sorted((timestamp(p["starttime"]) - t0).total_seconds() / 3600
                       for p in procedures if p["hadm_id"] == index["hadm_id"])
        cohort.append({"group": patient["gender"], "age": int(patient["anchor_age"]),
                       "stage": [x for x in stage if 0 <= x <= 168],
                       "event": [x for x in event if 0 <= x <= 168]})
    return {"name": "MIMIC-IV demo hospital records", "source_kind": "deidentified clinical demo",
            "index": "first recorded hospital admission per person",
            "stage": "recorded ICU admission within index hospital admission",
            "event": "any recorded ICU procedure within index hospital admission",
            "time_unit": "hours", "horizons": [6, 24, 48, 72, 168], "cohort": cohort,
            "structural_checks": checks,
            "source_rows": {"patients": len(patients), "admissions": len(admissions),
                            "icustays": len(stays), "procedureevents": len(procedures)},
            "limitations": ["selected 100-person US demo", "shifted dates",
                "sequence across source bundles after deliberately hiding stay IDs",
                "not an estimate of clinical access, treatment benefit or population disparity"]}
