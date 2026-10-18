# CPU DQN training

The `rl` extra adds Gymnasium and Stable-Baselines3 DQN. The dependency lock is tested on Linux x86_64 with Python 3.12 and CPU PyTorch. Use the CPU backend flag when installing the lock; other operating systems may need a separate PyTorch wheel resolution.

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python --torch-backend cpu --require-hashes -r requirements-rl.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m freshroute train-dqn --timesteps 250000 --seed 7 --output artifacts/runs/dqn-seed-7
.venv/bin/python -m freshroute evaluate --model artifacts/runs/dqn-seed-7 --episodes 30 --seed 100100
.venv/bin/python -m freshroute trace --model artifacts/runs/dqn-seed-7 --output artifacts/runs/dqn-decisions.jsonl
```

Use a fresh output directory for every training run. Checkpoints store `model.zip`, checksummed metadata, training curves, and validation measurements. Only trusted local model files should be loaded: the RL library's checkpoint format contains Python object serialization.

Training uses mixed scenarios, a two-layer 128-unit MLP, replay, target updates, epsilon exploration, and one CPU thread. Evaluation at fixed validation seeds chooses the saved checkpoint; it never uses the reserved final-test seeds. Training episode seeds remain below 100,000. Episode time limits remain truncations, so the library can bootstrap correctly. The fixed bounded observation transform does not fit statistics on validation/test data.

For a compute trial, use `--timesteps 10000`. That confirms training and checkpoint reload; it does not establish policy quality. Observation ablations use `--ablation no-freshness` or `--ablation no-queue`; a myopic learner uses `--gamma 0`. All require new training runs.
