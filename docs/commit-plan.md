# Structured commit plan

Git is initialized locally on `main`. **No commits or remote have been created.** The rows below are a plan for real work; prepared files are not an invented history. Commit each unit when it is implemented and verified. Do not backdate commits, fabricate authors, or split unchanged code into artificial “daily progress.”

## Initial work prepared in this directory

| ID | Suggested commit message | Scope | Validation | Status |
| --- | --- | --- | --- | --- |
| C01 | `docs: define FreshRoute RL scope and execution plan` | README, proposal, implementation plan, UI spec, this plan, `.gitignore` | team reviews scope and remaining submission fields; check links and claimed status | prepared; team review pending |
| C02 | `feat: add seeded replica simulator and Q-learning pipeline` | `pyproject.toml`, `freshroute/`, `tests/` | unit tests; train/evaluate/trace smoke run; saved-model replay equals in-memory replay | implemented and locally checked |
| C03 | `experiment: record reproducible Q-learning demo artifacts` | `artifacts/demo/` checkpoint, curve, validation, trace, manifest, evidence README | regenerate from documented seeds and compare hashes; keep limitations visible | generated and locally checked |

Review and commit the prepared units from the project root:

```bash
git add .gitignore README.md docs/
git diff --cached --stat
git commit -m "docs: define FreshRoute RL scope and execution plan"

git add pyproject.toml freshroute/ tests/
python3 -m unittest discover -s tests -v
git diff --cached --stat
git commit -m "feat: add seeded replica simulator and Q-learning pipeline"

git add artifacts/demo/
git diff --cached --stat
git commit -m "experiment: record reproducible Q-learning demo artifacts"
```

These are commands for the team to execute; they have not been run for you. C01 establishes the roadmap; C02 makes its documented application commands runnable. If you prefer every historical commit to have fully runnable README commands, combine C01/C02 as the initial commit and keep C03 separate. Real cohesion matters more than commit count.

## Planned implementation commits

| ID | Suggested commit message | Files/behavior to change | Acceptance / checks | Depends on |
| --- | --- | --- | --- | --- |
| C04 | `feat: version workload scenarios and observation schema` | scenario configs, explicit workload/fault schedules, normalized telemetry specification | deterministic config loading, invalid values rejected, no future information in observations | C02 |
| C05 | `feat: expose replica routing as a Gymnasium environment` | adapter, declared spaces, seed/reset integration, termination semantics | Gymnasium environment checker plus simulator invariants and observation bounds | C04 |
| C06 | `feat: train and reload a DQN routing agent` | DQN adapter, training CLI, tested dependency lock, checkpoint metadata | short CPU training, save/load equivalence, frozen inference, correct truncation handling | C05 |
| C07 | `feat: add paired multi-seed evaluation and SLA breakdowns` | experiment matrix, per-class/region metrics, confidence intervals, strict split management | same exogenous schedule across policies; no parameter updates; independent training-run aggregation | C06 |
| C08 | `experiment: evaluate DQN and routing ablations` | configs, five training seeds where feasible, full/no-freshness/no-queue/gamma-zero runs, results | reproducible commands and raw evidence; compute budget and losses reported | C07 |
| C09 | `feat: scaffold trace-driven web decision explorer` | `web/` React/Vite/TypeScript, manifest/trace loading, semantic layout, pinned lockfile | frontend typecheck/build; actual fixture values render; invalid files get useful errors | C03 and trace contract |
| C10 | `feat: visualize topology action values and reward outcomes` | replica diagram, request inspector, state coverage, pre/next-state toggle | values match trace; Q-values not called probabilities; null failures stay null | C09 |
| C11 | `feat: add replay timeline and evaluation comparisons` | accessible play/pause/step/seek/speed, charts, policy comparison | browser replay reaches last record correctly; reset/keyboard/reduced motion/narrow screen work | C10, C07 for full comparisons |
| C12 | `feat: serve isolated live simulator sessions` | local FastAPI, model registry, create/step/delete session routes | same seeded CLI/API outputs; independent sessions; bounded resources | C06, C11 |
| C13 | `feat: inject replica faults during live inference` | versioned fault events, outage/lag/load controls, live trace export | fault changes actual transitions; replay immutable; fault metadata recorded | C12 |
| C14 | `feat: explain alternatives with snapshot counterfactuals` | simulator/RNG clone, branch API, UI outcomes, snapshot hashes | original session unchanged; branch replay deterministic; estimates distinguished from measured alternatives | C13 |
| C15 | `experiment: freeze final models and held-out test results` | selected checkpoints/normalizers, test matrix, hashes, metric tables | frozen validation-selected config; reserved test seeds used only now; no handpicked runs | C08 and final model selection |
| C16 | `docs: publish reproduction guide report and demo script` | final README, methods/results/limits, contributor roles, clean setup evidence, demo script/video link | another teammate runs from clean checkout; complete submission checklist | C11–C15 |

Optional extension after C16: `feat: validate routing with a local PostgreSQL replica workload`. Keep this separate from simulator conclusions and document actual database/network setup. It must not delay the RL submission.

## Routine for each unit

1. Implement one coherent behavior and update relevant docs.
2. Run checks that establish its acceptance criteria. Save experiment configurations and outputs when claiming results.
3. Review `git diff`, stage only that unit, and inspect `git diff --cached`.
4. Commit with the real contributor identity. Use co-authorship only for actual contributors.
5. Once a remote exists, push and verify the remote branch. A local commit is not publication evidence.

Suggested work branches after the initial commits: `feat/gymnasium-env`, `feat/dqn-agent`, `feat/evaluation`, `feat/web-replay`, `feat/live-lab`. The team can use pull requests after adding the remote. Choose owners from actual approved members; keep implementation and review visible rather than assigning fictitious roles.
