# Provider inputs and reproducible preparation

Download inputs from PhysioNet. This repository contains no provider tables,
prepared person/stay records, person-level indicator matrices or linkage arrays.
Do not add those inputs to Git or release assets. Keep local raw/prepared data,
model fits, caches and detailed run records outside Git. The small numerical
summaries and plots under `results/`, `figures/` and `tables/` are our derived
scientific findings, not copies of provider input databases.

## Sources, versions and conditions

Use these **open-access demo versions**, not the credentialed full databases:

- [MIMIC-IV Clinical Database Demo 2.2](https://physionet.org/content/mimic-iv-demo/2.2/),
  Johnson et al. (2023), DOI [10.13026/dp1f-ex47](https://doi.org/10.13026/dp1f-ex47).
  We use `hosp/patients`, `hosp/admissions`, `icu/icustays` and
  `icu/procedureevents`. The provider selected 100 people with anchor-year groups
  2011–2013 or 2014–2016. Dates are shifted; do not treat them as calendar dates.
- [eICU Collaborative Research Database Demo 2.0.1](https://physionet.org/content/eicu-crd-demo/2.0.1/),
  Johnson et al. (2021), DOI [10.13026/4mxk-na84](https://doi.org/10.13026/4mxk-na84).
  We use `patient`, `lab` and `treatment` from the 2014–2015 source collection.
  This demo contains 2,520 unit stays; repeated stays are not independent people.

Both providers allow open access under ODbL 1.0. No account or credentials are
needed for these seven demo files. Follow the current provider conditions and
required citations, including the parent databases and PhysioNet, recorded in
[ATTRIBUTION.md](ATTRIBUTION.md). Database terms in
[ODbL-1.0](../LICENSES/ODbL-1.0.txt) remain separate from the software MIT licence.
The decision to acquire inputs from their provider is this project's distribution
policy, not a claim that the providers prohibit redistribution.

## Download and prepare

Python 3.12, uv and network access for initial setup/download are required.
Allow roughly 1 GB free disk for dependencies and local outputs and 2 GB RAM
for these demo workloads. The seven compressed inputs total 6,390,092 bytes;
no full database, GPU or pretrained weights are required.

From the repository root:

```sh
make setup
make fetch-data
make verify-data
make prepare-inputs
make smoke
```

`fetch-data` uses only versioned original-provider URLs in
[input-manifest.json](input-manifest.json). Files are installed after size and
SHA-256 checks; existing mismatched files are preserved and rejected. These
checks identify the intended input version, not a bitwise-output requirement.
If a URL becomes unavailable, use the provider page to obtain the **same version**
and exact tables. Do not silently substitute a newer dataset. No Git-hosted input
archive is provided. A URL/checksum is not a recovery backup.

Default local inputs are ignored `data/raw/` and `data/processed/link-change/`.
For storage outside the checkout, set `LINKAGE_RAW_ROOT` and
`LINKAGE_PROCESSED_ROOT` for every command. For example, with existing provider
files in the manifest's two versioned subdirectories:

```sh
LINKAGE_RAW_ROOT=/path/to/raw LINKAGE_PROCESSED_ROOT=/path/to/fresh-prepared make verify-data prepare-inputs smoke
```

Preparation validates keys and selects each MIMIC person's first recorded
admission, with ICU/procedure indicators at 24/72 hours. Seeded splits use 40
training and 60 test people. eICU selection uses person keys and eligible visible
profiles, never the query outcomes: ordered repeated-stay pairs use 30 training
people; separate-admission and 128-person corrupted rosters are selected by the
fixed rules in [prepare_stays.py](../experiments/joint_queries/prepare_stays.py),
[contexts.py](../experiments/joint_queries/contexts.py) and
[cases.py](../experiments/joint_queries/cases.py). Sex and age groups,
recorded expiry, missing discharge weight and a recorded creatinine row with
`labresultoffset` from 0 through 360 minutes after source-unit admission define
the eICU query. This is draw time, not revised-entry time; a nonmissing lab value
is not required. Source clocks and absent-interface limitations are retained.
Preparation writes local workload/profile/record JSONs; it never commits them.

## Analysis and findings

`make smoke` rebuilds all 28 proposals and solves 18 comparisons across MIMIC,
hospital-blocked eICU and an adverse additional-noise case. It checks exact
discrete radii, reference verdicts and feasible witnesses. It is not the whole
support/sampling campaign. `make test displays` works without provider data:
tests use generated finite examples; plots/tables use aggregate findings.

For the complete declared comparison after preparation, run `make reproduce`.
Then `make verify analyses` checks the newly generated certificates/witnesses and
recomputes sampling/support analyses. For repeats, use fresh ignored names such as
`RUN_DIR=results/reproduced-02`, `CHECK_DIR=results/verification-02`,
`FOLLOWUP_DIR=results/followup-checks-02` and `FIG_DIR=results/displays-02`.
`SUPPORT_DIR` defaults beneath `RUN_DIR`; existing records are preserved.
The ignore rules cover these prefixes, not every directory under `results/`.
Add an ignore rule before using other names for prepared cases or detailed runs;
keep the selected scientific summaries, figures and tables tracked.

Substantive comparison checks the published scientific summaries: discrete radii,
verdicts and counts must agree exactly; fitted floating quantities use relative
1e-6 and absolute 1e-8 tolerances. Timings, fit internals, witness choices and
figure/ZIP bytes can vary. Investigate changed or unresolved answers; do not
replace recorded findings silently. The retained demos reuse people and splits,
and neither population inference nor deployment validity follows from this route.
