# FreshRoute RL

**Learning where fresh reads should go.**

FreshRoute RL is a runnable reinforcement learning laboratory for staleness-aware read routing across geographically distributed database replicas. It implements the GeoRead-RL idea with a seeded simulator, real Q-learning and DQN agents, reproducible experiments, and a web interface that exposes actual routing decisions.

[GitHub repository](https://github.com/1amKhush/freshroute-rl) · [Results and methods](docs/report.md) · [Commit record](docs/commit-plan.md) · [Original implementation plan](docs/implementation-plan.md) · [Demo guide](docs/demo-guide.md)

![FreshRoute RL decision explorer](docs/images/decision-explorer.png)

## What works

- Three simulated replicas with persistent queues, asynchronous version replay, region-dependent RTTs, deadlines, and request-specific freshness budgets.
- Genuine tabular Q-learning and CPU DQN training, saved models, frozen inference, and checksummed replay traces.
- Replay controls, topology, pre-action telemetry, learned action values, reward terms, learning curves, and policy comparisons.
- Isolated live sessions with outages, lag, workload pressure, restoration, trace export, and exact-state counterfactual branches.
- A preserved 14-model DQN study: five full-observation training seeds and three per ablation; 700,000 training interactions, paired validation, and a frozen final test.

The solution policies learn from environment interaction. Nearest, leader-only, and random are evaluation controls only. They do not generate training labels or act as hidden routing fallbacks. There is no supervised learning or heuristic search solution.

## Run the web laboratory

The full application is tested on Linux with **Python 3.12**, **Node.js 24**, and CPU PyTorch. Core Q-learning also works with Python 3.11+ without third-party runtime dependencies. No GPU, database server, cloud account, or external dataset is required.

From this directory, with [uv](https://docs.astral.sh/uv/getting-started/installation/) installed:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python --torch-backend cpu --require-hashes -r requirements-rl.lock -r requirements-server.lock
npm --prefix web ci
node scripts/sync-demo.mjs
npm --prefix web run build
.venv/bin/python -m freshroute serve
```

Open **http://127.0.0.1:8000**. The Python server serves both the built interface and inference API. Fonts and replay assets are bundled locally. Installation downloads the CPU PyTorch wheel; later execution needs no external service.

For pip instead of uv, create and activate a Python 3.12 virtual environment and install the same locks with:

```bash
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu --require-hashes -r requirements-rl.lock -r requirements-server.lock
```

In the interface:

1. **Decision explorer:** play, step, seek, filter events, open a local JSONL trace, and compare pre-action versus next-state telemetry. The bundled trace is verified against its manifest hash.
2. **Training & evaluation:** inspect raw learning curves and the bundled frozen model's test results. This report has its own model/split identity; it does not evaluate a newly opened custom trace.
3. **Live laboratory:** choose a trained model, workload, and validation seed; start a session, inject faults, step the agent, compare all replica choices from the selected exact snapshot, or export the trace.

## Run the RL core without the web stack

The original Q-learning demonstration uses only the Python standard library:

```bash
python3 -m freshroute evaluate --model artifacts/demo/q-agent.json --episodes 8 --seed 100000
python3 -m freshroute trace --model artifacts/demo/q-agent.json --scenario regional-outage --seed 110000
python3 -m freshroute train --episodes 1200 --steps 160 --seed 7 --output artifacts/runs/my-q-agent.json
```

After installing the RL dependencies, train and evaluate DQN:

```bash
.venv/bin/python -m freshroute train-dqn --timesteps 50000 --seed 7 --output artifacts/runs/my-dqn
.venv/bin/python -m freshroute evaluate --model artifacts/runs/my-dqn --episodes 30 --seed 100100
.venv/bin/python -m freshroute trace --model artifacts/runs/my-dqn --scenario regional-outage --seed 110000
```

Use a new DQN output directory for every experiment. JSON and ZIP checkpoints include configuration, schema, seeds, package versions, source fingerprints, and weights hashes. The Python library's ZIP checkpoint uses object serialization; load trusted local models.

## Reproduce the study

```bash
PYTHONPATH=. .venv/bin/python scripts/run-experiments.py --output artifacts/runs/repeated-experiment
PYTHONPATH=. .venv/bin/python scripts/freeze-release.py --experiment artifacts/runs/repeated-experiment --output artifacts/runs/repeated-release
```

The checked-in configuration uses **50,000 interactions per model**, not the longer 250,000-step trial setting discussed in the original plan. Full observations use five independent training seeds. No-freshness, no-queue, and gamma-zero ablations use three each. Validation selects checkpoints and the demonstration model. The selection and complete model hashes are written before final-test evaluation.

Training seeds stay below 100,000. Validation uses 100,000–199,999; final test uses 200,000–299,999. The supplied final test uses 30 episodes per scenario starting at 200,000. Reports preserve all model runs, per-episode metrics, request-class/region breakdowns, and descriptive bootstrap intervals across training seeds. Large reports are standard gzip-compressed JSON.

The supplied selected DQN meets both deadline and freshness requirements on **82.7%** of balanced-scenario test requests. Across all five full-agent training seeds and all four test scenarios, macro SLA satisfaction is **71.0%**. These are synthetic simulator results under this workload calibration, not production database measurements or an out-of-distribution claim. See the [complete report](docs/report.md).

## Formulation

Actions directly choose Mumbai, Frankfurt (leader), or Virginia. Requests originate in all three regions:

| Request class | Timestamp-lag budget | Response deadline |
| --- | ---: | ---: |
| Latest | 0 ms | 240 ms |
| Bounded | 100 ms | 180 ms |
| Relaxed | 500 ms | 140 ms |

Routing adds service work to the chosen queue. Queue pressure affects later response times and follower replay, giving actions future consequences. The reward penalizes normalized response time, excess freshness lag, and failed requests. Every cost term is recorded.

Freshness is the latest committed write timestamp minus the replica's applied write timestamp at dispatch. A caught-up replica is fresh even if no write happened recently. The zero-lag class does not establish linearizability. Responses are analytical admission-time snapshots, with no mid-flight failure, automatic retry, leader election, quorum protocol, or production consistency guarantee.

DQN uses 26 bounded telemetry features and three discrete actions. Q-learning uses an inspectable coarse encoder. Both have partial observability/state aggregation; neither is claimed to see a complete Markov state. Q-values estimate future returns, not probabilities. Counterfactuals measure cloned simulator branches and are distinguished from those estimates.

## Checks and development

```bash
.venv/bin/python -m unittest discover -s tests -v
npm --prefix web run build
```

For browser checks, keep the server running in another terminal:

```bash
LAB_URL=http://127.0.0.1:8000 npm --prefix web run test:e2e
```

Tests use installed Chrome at `/usr/bin/google-chrome`; set `CHROME_PATH` for another installation, or install Playwright Chromium. Automated checks cover replay accuracy, keyboard navigation, invalid uploads, mobile layout, actual live DQN/fault/counterfactual flow, and WCAG A/AA rules in replay/live views. They do not replace a manual screen-reader review.

For frontend development, keep the Python server running and use `npm --prefix web run dev`. Vite proxies `/api` to port 8000. After changing demo/release artifacts, rerun `node scripts/sync-demo.mjs` and rebuild.

## Repository

```text
freshroute/                 simulator, scenarios, learners, experiments, API, CLI
web/                        React + TypeScript + Vite explorer and browser checks
tests/                      simulator, learning, API, fault, branch, release checks
configs/                    versioned scenarios and fixed experiment budget
scripts/                    experiment, freeze, and web-asset preparation commands
artifacts/demo/             original trained Q-learning model and validation evidence
artifacts/experiments/      all 14 DQN runs and compressed validation report
artifacts/releases/         frozen selected DQN, full test evidence, GUI replay
artifacts/runs/             ignored personal outputs
requirements-*.lock         pinned and hashed Python dependency sets
```

The [16-unit commit plan](docs/commit-plan.md) now has actual implementation commits. Before course submission, the team still needs to fill in its approved member details, review contributor roles, record the presentation/video, and complete the instructor's submission form. No course submission has been performed.

## References

[Q-learning paper](https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf), [Gymnasium custom environments](https://gymnasium.farama.org/introduction/create_custom_env/), [Stable-Baselines3 DQN](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html), and [PostgreSQL asynchronous replication](https://www.postgresql.org/docs/current/warm-standby.html). Reward weights, synthetic topology, workload calibration, and GUI design are project choices.
