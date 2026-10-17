# Task24 release-candidate preparation report — October17,2026

Status: independent final spec/quality PASS after both P2 documentation findings
were corrected and re-reviewed. Root current Task24 candidate gates PASS as below.
Task24a cfa50b6/c1d93cd resolves all4code findings; remaining targeted whole-audit
coverage completed. Candidate0.6.0rc1 integration/repeated merged gates and verified
push are complete and recorded in the final handoff section. Main/tag/package
publication remain separate owner actions. Earlier worker checkpoints are history.

## Requirement-to-evidence mapping

| Requirement | Concrete evidence / disposition |
| --- | --- |
| Exact release identity | VERSION, pyproject.toml project.version, src/living_world/__init__.py __version__ set0.6.0rc1. Only test_inspection_api expected release literal changes; all health/consistency assertions retained. |
| Generated metadata | setuptools.build_meta.prepare_metadata_for_build_wheel into isolated /tmp metadata directory; copied only permitted PKG-INFO,SOURCES.txt,requires.txt into tracked egg-info. Approved dependencies/package data unchanged; server extra/manifest aligned. |
| Release/operator guidance | README, docs/releases/v0_6_0rc1.md and canonical_founders/API/inspector/boundary guides link candidate and current evidence. Three run commands and inspect startup/optional server documented. |
| Task artifact coverage | Milestone index links21 task plans/prompts/reports, including completed Task24 and reviewed24a. All21 completed tasks have existing reports; ordered merge history covers16 through23 without unexplained implementation merge. |
| Historical accepted evidence | Task23 delivery87af71a, merge58b6ba7; reviewed report records task and merged1376passed/10existing skips,76Chrome,examples001–039, source/installed exact hashes, real inspect/browser GET-only/full state and database preservation. Historical counts were not rerun or claimed current by worker. |
| Whole-milestone review | All4findings corrected by reviewed Task24a deliverycfa50b6/mergec1d93cd; task+merged1416passed/10existing skips,76Chrome/examples001–039; full canonical matrices unchanged. Remaining targeted audit coverage completed without additional findings. See committed audit and24a report linked below. |
| Current status and remaining work | Candidate docs reviewed; root task gates PASS. Integration/merged final status is recorded below. Historical reports/release sections/usage checkpoints preserved. |
| Scope/architecture | Runtime delta only three version literals; one existing test literal; no behavior/architecture/schema/dependency changes. Only exact Task24 allowed files edited. |
| Future work/limits | Deterministic tapes are not live-LLM strategy validation; fixed recipe/two founders, legacy replay without labels, generic authoring, reusable stage templates/demotion, automatic stage perception remain deferred. Inspector is privileged fixed GET-only snapshot; dense labels use accessible list fallback. |
| Final candidate acceptance | Independent final review PASS; root candidate make/examples/whitespace, source+installed3.13+installed3.11 exact CLI matrices, wheel/assets/import/API/health/entrypoint/actualinspect and all-outcome Chrome PASS. Repeated merged gates/live remote verification passed; see final handoff. |
| Owner handoff | PASS final task/merged gates and delivery integration; live refs verified in final handoff below. Primary retains only the user configuration edit. Owner-only main integration/tag/publication remain outside authorization. |

## Historical first-checkpoint focused worker validation

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_inspection_api.py -k release_version_surfaces_are_consistent`: PASS1,11deselected; exact version and health assertions preserved.
- `PYTHONPATH=src .venv/bin/python` public-export import check: PASS55root and10founders exports; runtime0.6.0rc1.
- `git diff --check`: PASS before report-only checkpoint.
- Isolated setuptools metadata generation: PASS; only3allowed tracked outputs copied.
- Local document-link check: NOT RUN before root usage stop. Exact20 plan/prompt/report existence checked while generating index; link targets/anchors still require root validation.
- No full suite/examples/wheel/CLI/browser/minimum-Python gate run by worker.

## Artifact and merge audit

Read canonical Task23 reviewed report and exact contract; inspected actual merge
history from58b6ba7. Milestone implementation merges in dependency order:
16 808bdde;16a ca5b75c;15a a6d77a9;15b 2e43ada;17 c909d8a;
17a 9c006fc;18 0fe099d;18a 033ed60;15d 43405ee;19 a3f4bc5;
19a bba7549;20 bb9fa53;20a 0b6760f;20b 5489b73;21 1ab288b;
22 7806f29;15 91e33bf;15c 0a81a11;23 58b6ba7.
All corresponding exact plan/prompt/report paths exist and are linked in the
index. Earlier task reports are canonical historical review evidence; this
worker did not reconstruct earlier implementation or rerun historical commands.

Stale current claims repaired: README0.5 summary; missing report links; handoff
README atTask19; continuation at unfinishedTask23; backlog/journal Task23 review
pending; completion-plan Phase4 boxes. Earlier journal checkpoint entries remain
historical with an explicit current summary. No broad old version replacement.

## Historical worker-delivery completion fields

Worker preparation began at contract6f033c2 based on reviewed milestone58b6ba7.
Metadata/docs are intentionally uncommitted. Root must fill actual corrected
milestone provenance, independent final review disposition, current task gates,
delivery/merge refs, repeated merged gates and live remote/main verification
before concluding completion. Task24a corrected code/audit review is already complete.
No planned or unavailable check is marked passed.
Owner hard stop is before10% five-hour allowance; root retains buffer and final
checkpoint responsibility. Existing .codex/config.toml user edit is outside scope.

## Historical usage stop checkpoint — October17,2026

Root instructed immediate stop at21% remaining allowance, above owner10% floor.
All edits remain uncommitted and reviewable; no worker process remains running.
No further implementation or validation is authorized before explicit resume.

Root whole-milestone audit has TWO P1 findings: (1) reproduced custom goal/objective
ID and non-stage criterion threshold leak through NPC goal interpretation;
(2) reservation counter overwrite confirmed by code, runtime reproduction pending.
Audit coverage is explicitly incomplete; supplemental root report is
`.superpowers/sdd/v0_6_completion_plan/whole-milestone-review.md` in primary checkout.
This report path is supplemental ignored evidence, not a tracked deliverable.
Root must establish bounded correction contracts, fix/review/validate both findings,
complete audit coverage and all release gates before resuming readiness claims.
Do not integrate this closeout with unresolved audit findings. Related current
docs describe the first blocker; root must synchronize the second upon resume.

## Corrected-base restoration and current evidence

Root merged correctedmilestonec1d93cd into Task24 as e60262d. Exact ownedstash
29d9f3cf7811a9c8fd53f16f3dda4add5e84e0e1 applied withoutdrop; independent25-file
backup preserved. Worker editorially reconciled the five documentation conflicts,
retaining correction architecture/history and candidate metadata. Root alone stages
resolution. Historical usage-stop findings above describe their then-current state;
all four findings are now ADDRESSED, scoped spec/qualityPASS. The
[committed audit](../../orchestrator_handoff/v0_6_release_audit_2026_10_17.md) and
[Task24a plan](24a_v06_audit_corrections.md),
[prompt](24a_v06_audit_corrections-prombt.md),
[report](24a_v06_audit_corrections-report.md) are canonical current evidence.

Corrections retain arbitrary valid goal/objective IDs in engine state but reject
their keys and recursively discovered numeric policy/evidence in NPC-facing text;
allocate work reservations from authoritative highwater while preserving history;
load destroyed placements as retained history while place/replace remain live-only;
and reject repeated ancestors promptly with structural validation unchanged.
No schema, public signature, canonical tape/rule or scheduler changes. All three
accepted schema12 hashes remain the Task23 values. Task24a root task AND merged
make passed1416tests/10existing skips,76Chrome/examples001–039; separate examples,
whitespace and complete canonical source matrices passed. These are root corrected-
base results, not worker-run or final0.6.0rc1 installed/minimum-Python gates.

## Root architecture rulings retained for owner review

- Use durable project-local worktrees after native checkout proved read-only;
  report their actual path. Scoped SSH workaround bypasses broken system Include
  while retaining host-key verification; it is not a global SSH configuration edit.
- Failed engine ticks refuse further advance/save until checkpoint reload; direct
  manager rollback/retry remains supported. Replay rollback restores manager-owned
  state/events without a new EventManager removal/rewind API. Exceptional event
  allocator gaps remain accepted; no gapless or byte-identical failed-retry claim.
- Replay preparation guards direct engine advance/save as well as ScenarioRunner,
  including exhausted tapes. Complete schema12 boundaries require cursor/event
  bijection; missing or guessed legacy label bindings are unsupported.
- Earlier Task21/22 test-boundary amendments updated only schema/phase assertions.
  Work-phase retry tests invoke WorkExecutionSystem directly because whole-engine
  failed ticks intentionally require reload; scheduler/replay poison tests remain.
- Fixed canonical growth/population definitions use existing settlement_work
  authorization because categories cannot be empty. No current work offer references
  that population objective; future offers must explicitly authorize their domain.
- Sustained-history accumulation is pending only with unique need_created provenance
  and a complete contiguous available prefix. Missing/gapped/stale/unavailable
  history remains unavailable; initial housing/storage capacity is explicitly zero.
- Existing dispatch_external_trade is permitted only as exact structured replay
  action vocabulary. Prose/labels/arguments/context and other keys retain boundary
  checks and actor-bound gateway authorization.
- Canonical composition marker tick equals constructiontick+1 and cannot be future;
  only current live owns edges qualify. Manual same-constructiontick composition
  is unsupported; public pending intervals are unchanged.
- Maintenance-retained destroyed spatial records are readable history on load;
  place/replace stay live-only and all geometry/containment integrity checks remain.
  Public assignment failure restores manager/world snapshots without rewinding
  EventManager's private allocator. Successful live/resume full equality is required;
  exceptional retry checks use unique IDs and semantic events with accepted gaps.

## Historical worker synchronization checks before root validation

- Exact version/health focused test: PASS1,11deselected on corrected candidate.
- Source public exports: PASS55root/10founders; runtime0.6.0rc1.
- Primary supplemental `document-links.py` against this worktree: PASS74Markdown files,230local file links. Heading anchors not checked by that checker.
- Regenerated current metadata with approved setuptools `setup(script_args=["egg_info"])`; three allowed tracked outputs align approved pyproject/assets. Initial isolated dist-info preparation emitted temporary absolute paths into SOURCES.txt; corrected with normal in-place egg_info before delivery.
- Final direct conflict-marker/whitespace checks: PASS24candidate/contract files; generated manifest PASS8assets/no temporary paths. Git still intentionally records five unmerged paths until root stages editorial resolutions. No successful logs copied; no full gates duplicated.

All final root release/installed/Python3.11/browser and repeated merged gates
remain pending. Candidate is not release-complete.

## Historical independent final review correction round1 — October17

Root accepted both P2 documentation findings. Corrected only README, candidate
release notes, backlog, completion plan and this report; no runtime/metadata/VCS
mutation or full gate. Quickstart now runs `make install` from the candidate
checkout and activates `.venv` before all three run commands and inspect. Direct
Makefile inspection confirms install creates `.venv`, installs editable `.[dev]`
and therefore supplies uvicorn; pyproject scripts register living-world to CLI main.
No unversioned index requirement is used to select an unpublished candidate.
Actual reinstall was deliberately not repeated; root installed smoke follows review.

Backlog now identifies20completed tasks through reviewed24a/c1d93cd, all4fixed,
audit coverage complete and1416/10corrected-base gates. Old two-finding paragraphs
are retained under explicitly superseded historical heading; stale Spatial review
status corrected. Completion-plan header has current corrected status and its old
starting-state section is explicitly historical. Final Task24 release gates remain
pending. Focused link/whitespace results follow; independent re-review required.

Round1 focused checks: primary `document-links.py` against Task24: PASS74Markdown
files/230local links (heading anchors not checked). Direct Python whitespace,
final-newline and conflict-marker checks: PASS5corrected files. No test/fullgate
rerun for this documentation-only round; no running worker processes.


## Root current candidate gates — October17,2026

Independent full metadata/doc review required2P2 corrections (candidate quickstart
and stale status). Scoped re-review bothADDR, spec/qualityPASS, NO SUBSTANTIVE
FINDINGS. Exact single test-version literal/assertions and allowedfiles verified.

- `make`: PASS1416tests/10existing deliberate skips,76actualChrome cases,
  examples001–039. Ruff/Black PASS,207Pythonfiles unchanged by formatting.
- Separate `make examples`: PASS001–039. Unstaged AND staged whitespace: PASS.
- Root document checker: PASS74files/230localfilelinks; headinganchors notchecked.
- Public source CLI matrix: success10/settlement_success,stall5/tick_limit,
  failure13/founding_failure; twofresh/resume1,3,4 exactschema12JSONpayloads and
  terminalno-step resumes. Same complete hashes as reviewed Task23/24a.
- Isolated wheel living_world_simulator-0.6.0rc1-py3-none-any.whl build/install:
  PASS3.13.5withserverextra AND Python3.11.2defaultwithoutserverextra. Allthree
  independently reviewed generated metadata files unchanged by finalbuild.
- Installed public CLI matrix on BOTH Pythons: PASSsameoutcomes/bounds/exactfull
  payloads acrossfresh/resume boundaries. Source/3.13/3.11 hashes equal below.
- BOTH installed environments: site-packages imports,55root/10founders exports,
 8byte-identicalassets, versionmetadata/runtime/health0.6.0rc1, three savedworld
  domain/inspector APIs,404/405; fullworld+SQLitebytes unchanged. Root's temporary
  asset-check helper initially used Traversable multi-argument joinpath unsupported
  by Python3.11namespacepaths; corrected to chained single-component traversal and
  reran minimum smoke successfully. No production change was needed.
- Actual installed console successrun+loopbackinspect server: PASShealthversion,
  assets/needs/placements GETs, filename spaces/?/#, savedbytes unchanged, server
  cleanlyexited. Actual minimuminstall lacksuvicorn: inspect exits2 with fixed
  actionable server-extra diagnostic and savedbytes unchanged.
- Actual sourceuvicorn/Chrome for success/stall/failure: sevenviews each,
  wide/narrowSpatialscreenshots, GETonly/no pageerrors, completeworld+DBunchanged.
  Dense-label overlap retains the alreadyreviewed complete-listfallback.

Fullpayload SHA256 (schema12; identical source/installed3.13/installed3.11):
- success ec4a908de25253fa56872c5b5db9cd3c7a65d640c5be5c9b0b398b3a9f78fad0
- stall 6fcb0e0003c59faa1eb661329ea55fbbb4ed21e297ff6cef180733e302e6ec3d
- failure fd80996bb1e122cd38e9f16fcb96ad1ecccf0dd5dcb530529a59aa3806024f2f

Fullsuite runs Python3.13.5; Python3.11.2 evidence is installedCLI/import/API/
asset/health compatibility, not a second fullsuite claim. No finaltooling gate
unavailable; no new productwarnings. Final integration/mergedgates/refs follow.


## Final root integration and owner handoff — October 17, 2026

Task 24 delivery `a5c275f`, integrated as `badd5f9`, completes the reviewed `0.6.0rc1`
candidate on `milestone/v0.6`. Root task and merged gates each passed 1,416 tests / 10
existing deliberate skips, 76 Chrome cases and examples 001–039. Separate examples and
whitespace checks passed. Source and installed Python 3.13.5 / 3.11.2 canonical runs
preserve identical complete schema-12 payloads across fresh runs and resume ticks 1, 3
and 4. Wheel, exports, eight assets, health, read-only APIs, actual console/loopback
inspection and all-outcome browser checks passed.

Delivery `a5c275ff51d0d21c4e53341c112a4c9d371bc945` was pushed, merged into
`milestone/v0.6` as `badd5f9`, and validated before integration commit/push.
Merged `make VENV=.worktrees/task24/.venv`: PASS1,416tests/10existing skips,
76Chrome cases and examples001–039; separate `make examples` and staged/unstaged
`git diff --check`: PASS. Merged CLI matrix and both installed artifact smokes:
PASS, identical hashes to source/installed3.13/installed3.11 recorded above.
An initial merged helper invocation named a console script absent from the
dependency-only environment; reran with its Python executable successfully.
The default SSH invocation hit the known system include permissions error;
scoped SSH succeeded without modifying configuration. Neither was a product defect.

Root final documentation checkpoint updates current statuses, completed Phase5
checkboxes and requirement evidence only; no runtime or metadata delta.
Local link checks PASS74files/230localfilelinks (heading anchors not checked);
whitespace checks PASS. Live delivery and milestone integration refs verified
after push at a5c275f/badd5f9; main remains
`12f2f173796500f73f003c520c0ac848b9e1e9c8`. Task24 release checkout is clean;
primary has only user-owned `.codex/config.toml` unstaged. Durable worktrees,
review evidence and already-incorporated owned stash/backup are retained.
No remaining authorized implementation work. Candidate is ready for separately
authorized owner integration; no main merge, tag, publication or v0.7 work.
