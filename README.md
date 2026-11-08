# Joint query robustness

Compute the fewest changed identity partners that reverse a fixed report of
several recorded group-rate comparisons. Profile transport, direct assignment
and a matching-restricted maximal error score adaptation solve the same task
under balanced complete-block support. See [methods and assumptions](docs/joint-queries.md).

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
three repetitions, then runs the support and sampling controls. Scientific
summary comparison requires exact discrete answers and permits relative 1e-6,
absolute 1e-8 differences in floating quantities; timings are excluded.
`make verify` checks the newly generated witnesses/certificates without solving
again. The original small summaries retain measured timing results; new timings
are not substituted into those summaries or plots.

`LINKAGE_RAW_ROOT` and `LINKAGE_PROCESSED_ROOT` select local input directories.
`RUN_DIR` defaults to `results/reproduced`; `SUPPORT_DIR` to its `support/`.
`CHECK_DIR`, `FOLLOWUP_DIR` and `FIG_DIR` select fresh output directories under
`results/`. Existing outputs are preserved. Private historical source versions
are unnecessary: the included source records under `data/generation-sources/`
are our software provenance, not provider data. The declared source amendments
retain strict checks on mathematical method/protocol identities.

## Scope and interpretation

The two public critical-care demos have distinct recording structures but reused
people and overlapping splits; additional noise is not a new population. Strict
joint gains occur in seven of 48 primary and one of eight additional-noise
workloads. Two additional-noise verdicts are wrong. Hospital blocking leaves
little processing-time benefit. Neither sampling design reaches 95% acceptance
in 31 of 40 finite workloads. Human review costs are unmeasured.

The algorithms require known sufficient profiles, intact source bundles and
balanced complete blocks. Sparse candidates, missing true candidates, unmatched
people and noisy review require further methods. These computations concern
recorded reports, not clinical effects or natural linkage-error rates.

Original software terms are in [LICENCE.md](LICENCE.md). Database attribution
and terms remain in [data/ATTRIBUTION.md](data/ATTRIBUTION.md). Generated PDFs
embed DejaVu subsets; required notices are retained in
[LICENSES/DejaVu-fonts.txt](LICENSES/DejaVu-fonts.txt).
