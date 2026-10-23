# Structured commit record

The original 16-unit plan and the routing-motion extension have been implemented as real commits on `main`, with `origin` configured to `https://github.com/1amKhush/freshroute-rl.git`. Independent web work was committed once its prerequisites were ready; Git history records the actual order. No dates or contributor identities were fabricated.

| Unit | Commit | Work |
| --- | --- | --- |
| C01 | `432d9d0` | docs: define FreshRoute RL scope and execution plan |
| C02 | `0a08204` | feat: add seeded replica simulator and Q-learning pipeline |
| C03 | `dd61a07` | experiment: record reproducible Q-learning demo artifacts |
| C04 | `0386f88` | feat: version workload scenarios and observation schema |
| C05 | `6486867` | feat: expose replica routing as a Gymnasium environment |
| C06 | `87e5756` | feat: train and reload a DQN routing agent |
| C07 | `54bb60b` | feat: add paired multi-seed evaluation and SLA breakdowns |
| C08 | `5e6f0d2` | experiment: evaluate DQN and routing ablations |
| C09 | `c700836` | feat: scaffold trace-driven web decision explorer |
| C10 | `f076d25` | feat: visualize topology action values and reward outcomes |
| C11 | `9abcddd` | feat: add replay timeline and evaluation comparisons |
| C12 | `d6e32d1` | feat: serve isolated live simulator sessions |
| C13 | `4a7bdda` | feat: inject replica faults during live inference |
| C14 | `0a708a3` | feat: explain alternatives with snapshot counterfactuals |
| C15 | `23ad6f6` | experiment: freeze final models and held-out test results |
| C16 | `a376277` | docs: publish reproduction guide report and demo script |
| C17 | `4319ddc` | feat: animate recorded read routing with Motion mini |
| C18 | this documentation commit | docs: explain routing motion and refresh demonstration evidence |

## Validation and scope

Simulator/learning invariants, Gymnasium checker, real DQN save/reload, paired evaluation, frozen artifact integrity, API/CLI equivalence, isolated sessions, fault semantics, and exact-state counterfactuals are checked. Browser checks cover replay, actual live DQN/fault/branch flow, keyboard use, mobile layout, malformed files, and automated accessibility. See [verification](validation.md).

C08/C15 use the documented initial 50000-step-per-model budget: 14 models and 700000 interactions, five full-agent seeds and three per ablation. The original longer training and reward-weight sweeps remain extensions. Final-test results were generated after recording validation selection and model hashes.

C16 provides setup, methods/results, screenshots, a demo script, and automated clean-checkout verification. Approved team names/roles and the narrated presentation remain to be supplied by the actual team.

C17 adds finite, trace-driven request/response motion, phase narration, replay/live pause controls, accessible motion preferences, a pinned lightweight engine with its MIT notice, and four new behavioral browser checks. C18 documents the visual semantics and measured bundle cost, updates the demonstration instructions, and captures the real revised interface. Eight production browser checks, representative React development checks, and a clean frontend install/build validate the extension.

## Future commit discipline

Implement one coherent change, run its relevant checks, inspect the staged diff, and commit with the real contributor identity. Preserve model/configuration/seed provenance for experiment claims. Keep new experiments in new output directories. Push normal commits and verify the remote head; never fabricate incremental effort or silently retune against the published test split.

A local PostgreSQL experiment is an optional separate extension after this simulator project.
