# Structured commit record

The first 20 milestones on `main` are a disclosed reconstruction of preserved project snapshots. Their dates and author assignments are illustrative; each commit body retains the original source revision, author, and author date. Later fixes use ordinary commits with the actual committer identity and time.

The table follows the original implementation-unit plan. Use the **snapshot on main** IDs for checkout and source-fingerprint verification in a fresh clone. Original revision IDs are provenance labels and are not guaranteed to exist as Git objects in that clone. Git log records the snapshot order.

| Unit | Snapshot on main | Original revision | Work |
| --- | --- | --- | --- |
| C01 | `d5fea99` | `432d9d0` | docs: define FreshRoute RL scope and execution plan |
| C02 | `e4a3cfa` | `0a08204` | feat: add seeded replica simulator and Q-learning pipeline |
| C03 | `14c0ede` | `dd61a07` | experiment: record reproducible Q-learning demo artifacts |
| C04 | `3670783` | `0386f88` | feat: version workload scenarios and observation schema |
| C05 | `34d16ac` | `6486867` | feat: expose replica routing as a Gymnasium environment |
| C06 | `b0eee4f` | `87e5756` | feat: train and reload a DQN routing agent |
| C07 | `4a755e6` | `54bb60b` | feat: add paired multi-seed evaluation and SLA breakdowns |
| C08 | `11375d3` | `5e6f0d2` | experiment: evaluate DQN and routing ablations |
| C09 | `e9db7cf` | `c700836` | feat: scaffold trace-driven web decision explorer |
| C10 | `efeac3b` | `f076d25` | feat: visualize topology action values and reward outcomes |
| C11 | `5071ed0` | `9abcddd` | feat: add replay timeline and evaluation comparisons |
| C12 | `49ab14c` | `d6e32d1` | feat: serve isolated live simulator sessions |
| C13 | `beccee0` | `4a7bdda` | feat: inject replica faults during live inference |
| C14 | `a10aacc` | `0a708a3` | feat: explain alternatives with snapshot counterfactuals |
| C15 | `e781067` | `23ad6f6` | experiment: freeze final models and held-out test results |
| C16 | `55170a8` | `a376277` | docs: publish reproduction guide report and demo script |
| C17 | `ace896f` | `4319ddc` | feat: animate recorded read routing with Motion mini |
| C18 | `591c9b7` | `99f26c6` | docs: explain routing motion and refresh demonstration evidence |
| C19 | `bfb877e` | `e21c747` | refactor: consolidate decision records and replay state changes |
| C20 | `90c054c` | `ccb43fe` | docs: redesign project README for presentation and navigation |
| C21 | `ee2dfdf` | — | fix: reject unexpected reward fields and clean up abandoned sessions |

## Validation and scope

Simulator/learning invariants, Gymnasium checker, real DQN save/reload, paired evaluation, frozen artifact integrity, API/CLI equivalence, isolated sessions, fault semantics, and exact-state counterfactuals are checked. Browser checks cover replay, actual live DQN/fault/branch flow, keyboard use, mobile layout, malformed files, and automated accessibility. See [verification](validation.md).

C08/C15 use the documented initial 50000-step-per-model budget: 14 models and 700000 interactions, five full-agent seeds and three per ablation. The original longer training and reward-weight sweeps remain extensions. Final-test results were generated after recording validation selection and model hashes.

C16 provides setup, methods/results, screenshots, a demo script, and automated clean-checkout verification. Team names and roll numbers are listed in the README and two-page report. Speaking roles, instructor approval/submission, and the narrated presentation remain team responsibilities.

C17 adds finite, trace-driven request/response motion, phase narration, replay/live pause controls, accessible motion preferences, a pinned lightweight engine with its MIT notice, and four new behavioral browser checks. C18 documents the visual semantics and measured bundle cost, updates the demonstration instructions, and captures the real revised interface. Eight production browser checks, representative React development checks, and a clean frontend install/build validate the extension.

C19 shares the API/evaluator decision schema, centralizes replay pause/seek operations, simplifies trace guards and action-value bounds, and removes an overwritten percentile calculation. Verification includes 32 Python checks, eight browser checks, exact comparisons against 32 pre-refactor rollout/metric baselines, unchanged artifact hashes, and an identical default replay screenshot. The learning algorithms, simulator, animation lifecycle, and saved models retain their behavior.

C21 fixes the two browser issues reproduced in the final audit. Trace validation rejects unknown reward components, and session cleanup handles responses that arrive after navigation. All 32 Python checks, nine production browser checks, and both regression cases in React Strict Mode pass. Report packaging and provenance documentation follow as a normal documentation commit.

## Future commit discipline

Implement one coherent change, run its relevant checks, inspect the staged diff, and commit with the real contributor identity. Preserve model/configuration/seed provenance for experiment claims. Keep new experiments in new output directories. Push normal commits and verify the remote head; never fabricate incremental effort or silently retune against the published test split.

A local PostgreSQL experiment is an optional separate extension after this simulator project.
