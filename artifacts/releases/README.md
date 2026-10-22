# Frozen DQN release

The model was selected by the largest equal-weight macro reward across the four validation scenarios, before reserved test episodes were evaluated. Full-observation seed 71 was selected. `frozen.json` records the selection rule, all 14 model hashes, validation input hash, and fixed test seeds. The validation hash covers the decompressed JSON bytes.

Test seeds: 200000 through 200029 inclusive in each scenario. The full matrix retains five independent full-agent training seeds and three per ablation. These are new random seeds in the same configured regimes, not an out-of-distribution study.

| Scenario | Selected DQN reward | SLA met | Response availability |
| --- | ---: | ---: | ---: |
| balanced | -0.763 | 82.7% | 98.8% |
| write-burst | -2.136 | 52.3% | 78.7% |
| regional-outage | -1.280 | 73.7% | 88.3% |
| traffic-shift | -0.860 | 78.4% | 98.3% |

Files: `dqn/` contains the reloadable selected agent and its training evidence; `evaluation.json` holds all selected-model metrics and control policies; `test-matrix.json.gz` holds compressed complete per-model/per-episode test evidence and training-seed uncertainty; `decisions.jsonl` and its manifest contain an independent validation replay for the GUI.

Model archives come from the fixed 50,000-step-per-run CPU budget. Results are simulator measurements, not production database benchmarks or evidence of convergence. The Q-learning demonstration is retained separately and was not included as a paired comparator in this DQN test matrix.

Reproduce the complete selection and test protocol into an empty directory:

```bash
PYTHONPATH=. .venv/bin/python scripts/freeze-release.py --output artifacts/runs/repeated-release
```

Re-evaluation reproduces frozen-policy behavior; it must not be used to retune the model against these test seeds.
