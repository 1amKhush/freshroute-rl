# Initial trained Q-learning demonstration

These are **real outputs from the implemented simulator**, provided so the project can run before you train a model. They are original development/validation evidence at commit `dd61a07`, not the later frozen DQN result or evidence of performance on an actual database.

## Contents and provenance

| File | Purpose |
| --- | --- |
| `q-agent.json` | trained Q-values, visit counts, encoder/configuration, seeds, source hash |
| `q-agent.training.json` | all 1,200 training episodes: return, SLA rate, epsilon, seed, scenario |
| `evaluation.json` | frozen validation: four scenarios, four policies, eight seeds each; aggregate and per-episode metrics |
| `decisions.jsonl` | 160 actual agent decisions from an outage-scenario replay |
| `decisions.manifest.json` | model and trace SHA-256 hashes, run identity, configuration, summary |

Training used Python 3.12.3, agent seed 7, environment seeds 7 through 1,206 inclusive, 160 decisions per episode, and **192,000 interaction/update steps**. It cycles the four implemented scenarios. The resulting Q-table contains **685 aggregated states**. Core runtime dependencies: Python standard library only.

The validation split uses seeds 100,000 through 100,007, giving 1,280 requests per scenario/policy. The trace uses seed 110,000 in `regional-outage`. The reserved final test range has not been evaluated. No evaluation step updates the agent.

## Initial measured results

| Scenario | Q-learning mean reward | Q-learning SLA met | Q-learning response availability |
| --- | ---: | ---: | ---: |
| Balanced | -0.907 | 82.7% | 98.0% |
| Write burst | -2.166 | 53.8% | 79.7% |
| Regional outage | -1.492 | 71.6% | 84.7% |
| Traffic shift | -0.974 | 79.0% | 98.4% |

For the balanced workload, nearest, leader-only, and random achieved 24.5%, 5.3%, and 49.8% joint SLA satisfaction respectively. In this synthetic model, routing all traffic to one replica can saturate its service queue; leader-only is particularly affected. These figures describe this calibration and this single trained model. They do not establish general superiority of RL or represent geographic database measurements. Full controls and per-episode evidence are in `evaluation.json`.

The workload was calibrated during development using validation results; the initial 8 ms arrival interval overloaded the nominal case and was changed to 12 ms before generating these artifacts. This is a development choice, not a test-set result. The final multi-seed and held-out-regime protocol is still required.

## Reproduce without overwriting the supplied evidence

From the repository root. These commands reproduce behavior with current code; exact original-file byte comparison requires source revision `dd61a07` and Python 3.12.3:

```bash
python3 -m freshroute train --episodes 1200 --steps 160 --seed 7 --scenario mixed --output artifacts/runs/reproduced/q-agent.json
python3 -m freshroute evaluate --model artifacts/runs/reproduced/q-agent.json --episodes 8 --seed 100000 --output artifacts/runs/reproduced/evaluation.json
python3 -m freshroute trace --model artifacts/runs/reproduced/q-agent.json --scenario regional-outage --seed 110000 --output artifacts/runs/reproduced/decisions.jsonl
```

With the same source and Python interpreter, all five generated files should match byte for byte:

```bash
python3 - <<'PY'
import hashlib
from pathlib import Path

for name in (
    'q-agent.json', 'q-agent.training.json', 'evaluation.json',
    'decisions.jsonl', 'decisions.manifest.json',
):
    original = (Path('artifacts/demo') / name).read_bytes()
    repeated = (Path('artifacts/runs/reproduced') / name).read_bytes()
    assert original == repeated, name
    print(name, hashlib.sha256(original).hexdigest())
PY
```

Changing source code or interpreter metadata changes checkpoint provenance and hashes. Compare behavior and metadata deliberately across revisions rather than expecting old byte hashes to remain fixed.

## Verification performed

- All 13 simulator/learning checks passed, including a repeat in a fresh virtual environment without third-party runtime packages.
- A second complete 192,000-step training run reproduced the checkpoint, learning curve, evaluation report, trace, and manifest **byte for byte**.
- The supplied model's source fingerprint matches the Python sources at the original demonstration commit `dd61a07`.
- The trace model/trace hashes verify, and deterministic checkpoint reload produces the same decisions.
- Optional editable package installation and the `freshroute` console entry point worked with local build tooling and network access disabled.
- CodeRabbit CLI was available but signed out, so its external review was not run. Direct code inspection and the executable checks above were completed.

The `Latest` request class is a zero timestamp-lag target at dispatch, not a proof of linearizable reads. The model uses coarse aggregated telemetry; unknown states and per-action visits are visible in every RL trace record. Q-values are estimated future returns, not probabilities or measured counterfactual outcomes.
