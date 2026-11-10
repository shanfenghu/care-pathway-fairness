# Methods and assumptions

An entry roster and a source roster each have n bundles. A proposed bijection
assigns a whole source bundle to each entry. Alternative bijections may change
partners but keep all recorded values and group denominators fixed. Candidate
support is a complete product globally, or a disjoint union of balanced complete
blocks. True-link coverage is an additional assumption for interpreting
robustness relative to an unknown true linkage. Arbitrary sparse candidate
graphs, unmatched entries, many-to-one links and uncertain source bundling are
outside this implementation.

`Problem(groups, flags, proposal, left_blocks, right_blocks)` takes binary
indicator matrices shaped `(number_of_indicators, n)`, a permutation of
`0,...,n-1`, and two length-n block-label arrays. Every group and its complement
must be nonempty. Only within-block pairs are admissible. The code validates
the proposal, binary domains and nonempty groups. Users are responsible for
the scientific validity of the supplied profiles and hard support.
`proposal[i]` is the source-column index assigned to entry column `i`;
returned witness permutations use the same convention.

Every group row is compared with every source-indicator row; the report requires
all these conditions to hold. Passing fewer rows selects a rectangular subset
of comparisons. An arbitrary mask of group–indicator pairs is not supported.

For a group of size a and source indicator with t positives, let X count the
linked positives in that group. The recorded rate difference is
`(n*X-a*t)/(a*(n-a))`. A report is inside a specified band when all absolute
contrasts are at most delta. The reversal radius is the minimum number of
changed proposed partners giving the opposite Boolean report, or infinity if
none exists. These are finite recorded comparisons, not causal or population
fairness estimates. Tolerances 1/20 and 1/10 are sensitivity settings.

## Exact tolerance inputs

Use an exact rational string such as `"3/10"` or `Fraction(3, 10)` for `delta`.
The API converts inputs with `Fraction(delta)`: a Python float is accepted as
its exact binary rational value, not as the decimal rational suggested by its
printed form. In particular, `Fraction(0.3) < Fraction(3, 10)`. With n=7,
group size a=2, total positives t=2 and linked positives X=1, the contrast is
exactly 3/10. The intended tolerance `"3/10"` includes this boundary; float
`0.3` gives a numerator cap of two instead of three and excludes it. Do not
use a float when requesting an exact decimal/rational tolerance. The retained
evaluation uses exact rational tolerances `1/20` and `1/10`.

## Small runnable example

After setup, run this from the repository root:

```sh
PYTHONPATH=src .venv/bin/python - <<'PY'
import numpy as np
from linkage_bounds.profile_robustness import Problem, verify_permutation
from linkage_bounds.count_robustness import solve_count_radius

groups = np.array([[1, 1, 0, 0]])
flags = np.array([[1, 1, 0, 0]])
blocks = np.zeros(4, dtype=int)
problem = Problem(groups, flags, np.arange(4), blocks, blocks)
answer = solve_count_radius(problem, "1/4", "profile")
print(answer["lower"], answer["upper"])  # 2 2
if answer["upper"] is not None:
    changed, _ = verify_permutation(
        problem, answer["witness"], problem.caps("1/4"),
        answer["baseline_inside"])
    assert changed == answer["upper"]
PY
```

Initially the group rate is one and its complement's rate is zero. Swapping two
assigned partners makes both rates one half, reversing the outside-band report.
The equal finite bounds give an exact radius of two; `witness` gives an attaining
permutation. An `upper` value of `None` means no finite witness was found. Check
`rigorous_invariant` to distinguish proved invariance from an unresolved search.
The explicit permutation check rechecks the upper witness, not the lower bound.
The solver performs its integer-bound checks internally; `make verify` rechecks
saved campaign records using the same core verification routines.

## Exact profiles and numerical checks

Entries sharing cohort indicators and sources sharing queried indicators can
be grouped. For proposed cell counts N and feasible target counts T with the
same within-block margins, the minimum changed partners are
`sum(max(T-N,0))`. Retain `min(N,T)` original pairs per cell and match the
remaining rows and sources inside complete blocks. The construction attains
that cost in the original identity space. It describes an at-most-distance
image, not every exact-distance sphere. Sparse support can invalidate the fill
step; unique profiles recover assignment and remove compression.

`build_model(problem, kind)` builds free/overflow profile arcs or direct
identity variables. Integer count windows enforce the exact non-strict band
boundary before optimisation. A scalar entry/violation calculation settles
invariant and inside-band cases first. Outside the band, an impossible scalar entry proves invariance; inside it, invariance means no scalar violation is attainable. For an outside-band query, the current
implementation also tries each worst scalar condition's fixed swap witness.
It closes the radius at the scalar lower bound only if original-space checking
confirms that the same witness satisfies every condition. Failure is
inconclusive. Every formulation receives this same inexpensive route before
building a model. Remaining joint entry queries use a common SciPy HiGHS
interface. All methods use the same query, support, proposal,
count windows and resource limits. Query constraints do not imply LP integrality.

`solve_count_radius(problem, delta, kind='profile')` returns a radius bracket, route,
attaining permutation when found, numerical certificates and component costs.
Methods are `profile`, `assignment` and `mes`. Numerical solver status is
insufficient for an exact claim: an original-space permutation is checked as
an upper bound and integer arithmetic checks a bounded-box Lagrangian lower
bound with residual corrections. The multiplier grid is 1,000,000; the common
MIP limit is five seconds, with two-second/128-node proof fallback. An unfinished
tree or unsupported infeasibility claim remains unresolved. The checking commands run without an optimiser and reuse the core
model-building and verification routines.

The MES objective is inherited from Schreiber and Amsterdamer, Query-Guided
Analysis and Mitigation of Data Verification Errors, ICDE 2026, 1994–2007,
DOI 10.1109/ICDE65706.2026.00151. It is adapted to this Boolean aggregate and
matching-world support. That work's formal language is SPJU, and its authors
explicitly outline aggregate extensions; this is a structured adaptation. Under
independent symmetric proposed-positive LABEL errors with epsilon=0.1, negative
log likelihood is a constant plus distance times log(9). Truth matchings remain
dependent. This is neither a new uncertainty metric, posterior correctness,
published-software reproduction nor an independent third representation.
Query-guided resolution follows Drien et al., PACMMOD 1(2), 2023, 1–27,
DOI 10.1145/3589325; safe numerical bounds follow Neumaier and Shcherbina,
Mathematical Programming 99(2), 2004, 283–296, DOI 10.1007/s10107-003-0433-3.

## Recorded workloads and evaluation

MIMIC-IV Demo 2.2 has 100 people and 275 admissions. Two overlapping 40-train/
60-test splits use seeds 101201 and 101202. A source bundle records ICU entry
within 24 hours and any row in `icu/procedureevents` starting from zero through 24/72 hours
after the earliest hospital admission (selected by admission time). eICU Demo 2.0.1 has 2,520 stays for 1,841 people distinguished by provider identifiers. Fixed keyed
selection gives 30 training/225 evaluation within-admission pairs, an 18-person
separate-admission control and a 100-train/128-test additional roster with the
documented exclusions. Its indicators are unit-discharge death, missing discharge
weight and presence of a recorded creatinine row with `labresultoffset` from
zero through 360 minutes after source-unit admission. This is the recorded draw
time, not the revised-entry time; it does not require a nonmissing lab value. Missing documentation
does not imply absent care. Keys and visible-profile eligibility select rosters;
query outcomes do not. MIMIC entries use demographic/linkage fields and
source bundles use the same person's earliest admission by admission time;
source linkage features are corrupted copies, with ICU flags left fixed.
Within-admission eICU pairs select the repeated-stay admission with the lowest
identifier, then its first two unit stays by visit number (stay identifier
breaks ties), retaining the pair only if both records have recorded Female/Male sex and
a parseable age (0–89 or the provider's `>89` category). Groups
and entry linkage fields come from the first stay; source fields, outcomes
and the unit-entry clock come from the second. In the separate-admission
control, the entry is the lowest-identifier stay and the source is the
lowest-identifier stay in another admission. Selection checks that
chosen source's eligibility; it does not skip an ineligible minimum to take
a later stay. Identifiers do not establish chronological follow-up. The
128-person roster uses one selected unit stay on both sides before source
feature corruption. Provider person keys establish the reference pairings.
The two control evaluation rosters exclude the 255 paired-stay people and the
first 1,352 other eligible people in a fixed hash order, used for earlier
development and evaluation. The 18-person control reuses the 30 within-admission
training pairs. The 128-person control trains on 100 people from the earlier
pool, outside all three eICU evaluation rosters. Exact selection is implemented
in the preparation routines. The provider documents stay-relative clocks and warns
that identifiers do not encode stay order in its [patient table reference](https://eicu.mit.edu/eicutables/patient/).

Recorded female sex and recorded age at least 65 form overlapping groups.
For MIMIC, `age` is the provider's `anchor_age` at `anchor_year`, not
admission-adjusted age; for eICU it is the retained unit-entry age field. Both point
linkers use the same age-agreement bins (one, three, eight years), category
agreement and missingness, without query flags or evaluation keys. Fellegi–Sunter
uses add-one-smoothed comparison weights; logistic regression selects its L2
penalty from 0.1, 1, 10 on a person-level training holdout and refits. Known
training correspondences also imply cross-person negatives. The 30/40/100 known
matches are information inputs whose acquisition cost is unmeasured.

Base feature corruption has age standard deviation two years, 5% category
missingness and fixed small replacements. Shift adds group-dependent age bias,
larger noise and category corruption. The exact seeds, splits and category
probabilities are in the fixed configuration and preparation functions. These
are controlled stresses, not estimated natural clinical error rates. Hospital
labels stay intact; reference coverage is checked for each blocked roster.

Each MIMIC split and the 128-person eICU roster trains its linkers on
base-corrupted source features, then reuses the fitted linkers for base and
shifted evaluation draws. The within- and separate-admission rosters instead
retain recorded profile differences between stays. Their linkers share the
same 30 within-admission training pairs.

The initial rate formulation left seven dependent workload brackets open
(63 of 432 repeated outputs). Earlier endpoint summaries and the worked example are retained for continuity;
the initial incomplete proof attempts are not part of the retained current comparison. Common integer-count windows and scalar routing then gave the
final representation comparison; two further fixed noise draws use the same
people. The final suite has 56 dependent instances and 504 repeated outputs.
All 48 primary verdicts are correct and begin outside the bands. Two of the
eight additional-noise verdicts are wrong at ten-point tolerance, giving 54 of
56 correct proposed verdicts. Their radius is two, settled by the scalar
violation route. The current additional-noise seeds are 2026110712 and
2026110713. These tests support conditional query-processing effects, not
increased point-prediction accuracy or independent population frequencies.

## Assurance and cost

Uniform fixed-size sampling of proposed pairs gives a hypergeometric error
count under truthful reference answers. A checked lower radius supplies the
null boundary for a conventional finite-population test at alpha=0.05. The
code computes exact rational conditional acceptance probabilities, with no
independent-linkage-error assumption or repeated-monitoring guarantee. The
same proposal's total-error bound may support several report conditions;
different populations need separate evidence. Harmless identity errors can
make this global-error route conservative. A correct report can therefore have
zero acceptance at every prescribed budget.

Recorded computation charges model construction, solving, exact-bound checking
and original-space lifting. In the current implementation, group totals are
cached once during construction for every representation. An integral LP
candidate is checked against all exact constraints and lifted to the original
records; if it attains the checked lower bound, a separate integer solve is
unnecessary. Otherwise the common integer/proof fallback applies. These standard
steps do not assert general LP integrality. Common preparation/tuning/scoring is separate.
Common prepared-input loading, fitting/tuning and proposal construction took
0.8134 seconds in the retained primary suite. Adding it once to the sum of
per-workload processing medians gives approximately 0.90, 5.79 and 6.19 seconds
for profiles, direct assignment and MES. The earlier development summaries have
different processing costs and are not the current timing comparison.
These measurements stop at n=225 and use
three repetitions. They exclude operational roster/bundle construction, human
review time/accuracy and clinical effects. Fresh timings are machine-dependent;
the reproduction comparison excludes them and preserves discrete endpoints.

The distributed numerical summaries and plots report useful and adverse regimes.
Person-level prepared cases and detailed solver records are reconstructed locally
from the versioned original-provider tables using the data README. Display
regeneration uses the small aggregate findings without a download; independent
certificate/witness checking uses a newly generated local run. External scientific
review remains separate from these computational checks.

## Pair questions on blocks that can affect the query

`linkage_bounds.query_sampling.relevant_rows(problem)` returns entry rows in
complete blocks with more than one cohort profile and more than one source
profile. If either side has one profile, margins fix that block's joint table.
Resetting an alternative linkage to the proposal in every excluded block
preserves all table-based query values. Consequently, a wrong report still needs
at least its checked reversal lower bound in wrong proposed pairs among the
returned rows.

Choose this roster before seeing pair answers. Uniform sampling without
replacement within it can use the same exact hypergeometric test, with the
roster's size and error count replacing their whole-roster counterparts. The
oracle remains truthful binary correctness of a proposed pair. Empty returned
rows mean that all profile tables are fixed under the supplied support; this is
not a declaration that all identities are correct. This sufficient roster is not
an optimal question policy, and discrete cutoffs need not improve acceptance at
every budget. Known profiles, complete support and acquisition costs remain
separate assumptions.

Run the finite reset/radius tests:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_query_sampling.py' -v
```

## Fixed-proposal support control and repeated-query weighting

The support comparison fixes each of eight blocked eICU proposals, its reference
pairs and all queried profiles. Two fixed random label orders merge blocks in
chunks of four and sixteen labels; original and fully merged endpoints are
shared. Both tolerances give 96 dependent design workloads. Every encoding sees
the same support within a comparison. All 32 nested chains have nonincreasing
radii. Changing support changes the uncertainty family, not just the encoding.

The exact gain/task fractions are 2/16, 6/32, 4/32 and 2/16 across merge levels.
Model-building workloads number 2, 10, 16 and 10. All scalar bypasses remain in
the timing summaries. Coincident proposals leave 30 distinct proposal/support
problems before tolerance and 60 distinct queries after tolerance. The weighting
analysis pools repetitions for identical profile/proposal/support/tolerance
queries, then weights distinct queries equally. This is sensitivity to duplicated
design cells, not independent population replication.

After original-provider acquisition and `make reproduce`, `make verify` and
`make analyses` check generated records and recompute analyses. `make displays`
regenerates plots and tables from distributed aggregate summaries. Three repeats
measure host variation; two merge orders measure construction sensitivity. Neither
supplies a confidence interval over clinical populations. In the blocked
225-person example, 119 relevant entries contain all four wrong pairs. The joint
95%-acceptance question budget falls from 136 on the full roster to 72 on this
frame; on the same frame the separate bound needs 82. Across all finite cases,
31 of 40 still cannot reach 95% acceptance under either design. These are exact
conditional probabilities under truthful binary answers, not measured human
review accuracy, acquisition time or a universal policy improvement.
