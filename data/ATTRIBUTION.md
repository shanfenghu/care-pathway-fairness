# Input versions, attribution and database terms

Only these **open-access demo versions** are used. They do not require credentials
or access to the full credentialed databases. The manifest pins seven compressed
provider tables, totalling 6,390,092 bytes. From the repository root,
`make fetch-data` downloads them from the versioned PhysioNet file service and
verifies exact bytes. `make verify-data` checks an existing input directory
without network access.

MIMIC-IV Clinical Database Demo, version 2.2:
Alistair Johnson, Lucas Bulgarelli, Tom Pollard, Steven Horng, Leo Anthony Celi
and Roger Mark (2023), PhysioNet, DOI
[10.13026/dp1f-ex47](https://doi.org/10.13026/dp1f-ex47).
Source: https://physionet.org/content/mimic-iv-demo/2.2/.
Required tables: patients, admissions, ICU stays and ICU procedure events.
The parent dataset description is Johnson et al., MIMIC-IV, a freely accessible
electronic health record dataset, Scientific Data 10, 1 (2023), DOI
[10.1038/s41597-022-01899-x](https://doi.org/10.1038/s41597-022-01899-x).

eICU Collaborative Research Database Demo, version 2.0.1:
Alistair Johnson, Tom Pollard, Omar Badawi and Jesse Raffa (2021), PhysioNet,
DOI [10.13026/4mxk-na84](https://doi.org/10.13026/4mxk-na84).
Source: https://physionet.org/content/eicu-crd-demo/2.0.1/.
Required tables: patient, lab and treatment. The parent database description is
Pollard et al., The eICU Collaborative Research Database, a freely available
multi-center database for critical care research, Scientific Data 5, 180178
(2018), DOI [10.1038/sdata.2018.178](https://doi.org/10.1038/sdata.2018.178).

Both resources request PhysioNet attribution: Pollard et al., PhysioNet as a
global platform for biomedical research, Nature Health 1, 792–795 (2026), DOI
[10.1038/s44360-026-00096-z](https://doi.org/10.1038/s44360-026-00096-z).

The provider database licence is the Open Data Commons Open Database License
1.0, retained verbatim in `LICENSES/ODbL-1.0.txt`; authoritative terms:
https://opendatacommons.org/licenses/odbl/1-0/.
Provider tables and prepared person/stay records are acquired or generated
locally from the original providers, and are not distributed in the software
repository or its release assets. Transformation code selects keyed rosters,
forms recorded indicators and constructs controlled-corruption comparisons.
Small aggregate numerical summaries and plots report the resulting scientific
findings. Preserve the applicable database attribution and terms for local
preparation and any independently permitted downstream use.

Original software is offered under the MIT License with the scope in
`LICENCE.md`. These software terms do not replace the database or font terms.
