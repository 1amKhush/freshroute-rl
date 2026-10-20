# Initial CPU DQN experiment

This is a fixed-budget study: 14 independently trained models, 50,000 interactions per model, 700,000 interactions total. Five full-observation training seeds and three seeds for each ablation are preserved. The proposed longer 250,000-step-per-model study has not been run.

Training uses the source fingerprint in each model metadata file. All models in this experiment share that fingerprint. Validation selects checkpoints on seeds 100000 and 100001; this report uses 30 additional validation episode seeds starting at 100100 in each scenario. Final-test seeds have not been used in this experiment.

| Condition | Macro mean reward | Macro SLA met |
| --- | ---: | ---: |
| full | -1.220 | 71.6% |
| no-freshness | -1.259 | 70.8% |
| no-queue | -1.681 | 63.0% |
| gamma-zero | -1.442 | 68.6% |

The macro averages weight the four scenarios equally. See `validation.json.gz` (standard gzip-compressed JSON) for per-scenario summaries, descriptive bootstrap intervals across independent training seeds, and all raw per-episode metrics. Small training-seed counts limit precision. Baselines are paired on common exogenous seeds; they are evaluation controls only.

Do not infer general necessity of every feature from these results: an ablation may match or outperform full observations in this simulator. No claim of convergence or real-database performance is made.

Reproduce in a new output directory from the repository root:

```bash
PYTHONPATH=. .venv/bin/python scripts/run-experiments.py --output artifacts/runs/repeated-experiment
```

Model archive timestamps and wall-time metadata need not match byte for byte after retraining. Frozen checkpoint inference and workload seeds are reproducible.
