# Joint query robustness

Compute the fewest changed identity partners that reverse a fixed report of
several recorded group-rate comparisons. Profile transport, direct assignment
and a matching-restricted maximal error score adaptation solve the same task
under balanced complete-block support. See [methods and assumptions](docs/joint-queries.md).

## Included scientific outputs

The selected outputs are included as files, alongside their generation scripts.
`figures/joint-query/` contains PDF and PNG versions of `joint-example`,
`checked-computation` and `audit-acceptance`. `tables/joint-query/` contains the
readable `case-results.csv` and `workload-outcomes.csv` tables.

`results/joint-query-validation/summary.json` retains all 56 query summaries,
and `results/support-validation/summary.json` all 96 support-query summaries.
`results/query-followups/` retains the 56-workload sampling curves and question
budgets, same-frame controls and distinct-query weighting results, including
adverse findings. Only the person-level sampling-frame indices are omitted.
`results/query-summaries/illustration.json` retains the aggregate worked example;
`results/query-development/` retains earlier endpoint and geometry summaries.
These are scientific findings, distinct from provider input records. `make
displays` regenerates the selected figures and tables; `make reproduce` followed
by `make analyses` recomputes the analyses after original-provider acquisition.

## Setup and quick checks

Install Python 3.12 and [uv](https://docs.astral.sh/uv/), then run:

```sh
make setup
make test
make displays
```

Dependencies are pinned in `uv.lock`. With a populated dependency cache, setup
also supports `uv sync --frozen --offline --python python3.12`. Run with assertions
enabled, not `python -O`. Tests cover finite-world equivalence, invalid inputs,
integer witnesses and scientific-summary regression checks. Display generation
uses aggregate results and produces three PDF/PNG figure pairs and two CSV tables;
it needs no provider inputs and does not require bitwise-identical image files.

## Acquire inputs and reproduce

Follow [data/README.md](data/README.md) for original-provider links, versions,
licences, selections, resources and detailed preparation:

```sh
make fetch-data
make prepare-inputs
make smoke
```

Raw and prepared provider records are downloaded/generated locally and stay
outside Git, together with detailed runs, fits and caches. `make smoke` prepares
28 proposals and checks 18 method/tolerance results on three representative
cases, including a wrong additional-noise verdict. It is a practical partial run.
For the full comparison after preparation:

```sh
make reproduce
make verify
make analyses
```

`make reproduce` builds 24 primary and four additional-noise proposals using the
fixed seeds and training selections, both tolerances, three formulations and
three repetitions, then runs the support and sampling controls.
The complete campaign produces 1,368 checked results: 504 in the main comparison
and 864 in the support control, counting methods, tolerances and repetitions.
Scientific summary comparison requires exact discrete answers and permits relative 1e-6,
absolute 1e-8 differences in floating quantities; timings are excluded.
`make verify` checks the newly generated witnesses/certificates without solving
again. The original small summaries retain measured timing results; new timings
are not substituted into those summaries or plots.

`LINKAGE_RAW_ROOT` and `LINKAGE_PROCESSED_ROOT` select local input directories.
`RUN_DIR` defaults to `results/reproduced`; `SUPPORT_DIR` to its `support/`.
For repeated commands, keep the ignored output prefixes: for example,
`RUN_DIR=results/reproduced-02`, `CHECK_DIR=results/verification-02`,
`FOLLOWUP_DIR=results/followup-checks-02` and `FIG_DIR=results/displays-02`.
`SUPPORT_DIR` defaults beneath `RUN_DIR`. Other custom names are not automatically
ignored; add an ignore rule before generating data-derived cases or detailed runs.
Existing outputs are preserved. The source records under `data/generation-sources/`
are our software provenance, not provider data. The declared source amendments
retain strict checks on mathematical method/protocol identities.

## Locate a question-budget result

After `make analyses`, the new sampling results are in
`results/followup-checks/sampling.json`; the separate-bound comparison is in
`results/followup-checks/same-frame-control.json`. To inspect the blocked
225-person, five-point example, run:

```sh
.venv/bin/python - results/followup-checks <<'PY'
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
sampling = json.loads((root / "sampling.json").read_text())
row = next(r for r in sampling["rows"]
           if r["n"] == 225 and r["support"] == "hospital"
           and r["linker"] == "fs" and r["delta"] == "1/20")
control = json.loads((root / "same-frame-control.json").read_text())
separate = next(r for r in control["rows"]
                if r["case_index"] == row["case_index"]
                and r["delta"] == row["delta"])
print(row["minimum_budget"]["global_95"],
      row["minimum_budget"]["frame_95"],
      separate["minimum_budget"]["frame_separate_95"])
print(sampling["summary"]["95_unattainable_global"],
      sampling["summary"]["95_unattainable_frame"])
PY
```

The expected lines are `136 72 82` and `31 31`. They distinguish the local
question savings from the frequent failure to reach the 95% acceptance target.
Use `results/query-followups` instead to inspect the included findings without
recomputing them. If you set `FOLLOWUP_DIR`, pass that directory instead.

## Scope and interpretation

The two public critical-care demos have distinct recording structures but reused
people and overlapping splits; additional noise is not a new population. Strict
joint gains occur in seven of 48 primary and one of eight additional-noise
workloads. Two additional-noise verdicts are wrong. Hospital blocking leaves
little processing-time benefit. Neither sampling design reaches 95% acceptance
in 31 of 40 finite workloads. Human review costs are unmeasured.

A strict joint gain means that the exact joint radius is larger than the
separate scalar lower bound for the same proposal, support and tolerance.
The reported gains are finite; invariant cases are reported separately,
and unresolved brackets are not claimed as exact radii.

The algorithms require known sufficient profiles, intact source bundles and
balanced complete blocks. Sparse candidates, missing true candidates, unmatched
people and noisy review require further methods. These computations concern
recorded reports, not clinical effects or natural linkage-error rates.

Original software terms are in [LICENCE.md](LICENCE.md). Database attribution
and terms remain in [data/ATTRIBUTION.md](data/ATTRIBUTION.md). Generated PDFs
embed DejaVu subsets; required notices are retained in
[LICENSES/DejaVu-fonts.txt](LICENSES/DejaVu-fonts.txt).
