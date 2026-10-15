# FreshRoute RL

**Learning where fresh reads should go.**

FreshRoute RL is a reinforcement learning mini-project based on **GeoRead-RL: Staleness-Aware Read Routing for Distributed Databases**. An agent routes each incoming read to a geographically distributed replica, learning the tradeoff between response time, availability, and data freshness.

**Current milestone:** a runnable Python simulator, genuine tabular Q-learning training, a saved demonstration agent, frozen validation against reference policies, and JSON decision traces. The web interface, Gymnasium wrapper, and DQN experiment are planned; they are not implemented yet. This is a simulated single-shard database, not a production database router.

## Start here

- [Implementation plan](docs/implementation-plan.md): formulation, milestones, evaluation protocol, acceptance criteria, and submission requirements.
- [Web interface plan](docs/web-interface.md): screens, decision explanations, interactions, and integration contracts.
- [Structured commit plan](docs/commit-plan.md): reviewable work units and validation for each commit.
- [Idea submission](docs/idea-submission.md): a concise proposal you can adapt for submission.
- [Demonstration artifact](artifacts/demo/README.md): provenance, reproduction commands, and measured limitations.

## Setup

Requires **Python 3.11 or newer**. The initial simulator and learner use only the Python standard library. No GPU, database, cloud account, or external dataset is needed.

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m freshroute --help
python3 -m unittest discover -s tests -v
```

The `python3 -m freshroute` commands work directly from the repository without installation. Optionally install a console command with `python3 -m pip install -e .`, then run `freshroute --help`. Only this optional packaging step needs setuptools/build tooling; the core has no runtime dependencies. Future DQN and web dependencies will be added and locked in their implementation milestones.

## Train, evaluate, and inspect decisions

Use the supplied agent immediately:

```bash
python3 -m freshroute evaluate --model artifacts/demo/q-agent.json --episodes 8 --seed 100000 --output artifacts/runs/evaluation.json
python3 -m freshroute trace --model artifacts/demo/q-agent.json --scenario regional-outage --seed 110000 --output artifacts/runs/decisions.jsonl
```

Train your own agent from interaction with the simulator:

```bash
python3 -m freshroute train --episodes 1200 --steps 160 --seed 7 --scenario mixed --output artifacts/runs/q-agent.json
python3 -m freshroute evaluate --model artifacts/runs/q-agent.json --episodes 8 --seed 100000 --output artifacts/runs/evaluation.json
python3 -m freshroute trace --model artifacts/runs/q-agent.json --scenario regional-outage --seed 110000 --output artifacts/runs/decisions.jsonl
```

Training saves a JSON Q-table and a `.training.json` learning curve. Evaluation saves aggregate and per-episode metrics. Trace export saves one decision per line plus a manifest identifying its model, configuration, seed, and SHA-256 hashes. Generated personal runs are ignored by Git; the small demonstration artifacts are tracked.

Each decision contains the observation available before routing, all three learned action values, the selected replica, action visit counts, actual latency/freshness/failure outcomes, reward terms, and the resulting next observation. These records are the foundation of the planned web decision explorer.

## What the agent learns

There are three direct-read actions: Mumbai, Frankfurt (leader), and Virginia. Requests originate in different regions and have one of three SLA classes:

| Class | Freshness tolerance | Response deadline |
| --- | ---: | ---: |
| Latest | 0 ms of commit timestamp lag | 240 ms |
| Bounded | 100 ms | 180 ms |
| Relaxed | 500 ms | 140 ms |

The agent receives request context and per-replica telemetry. A compact encoder groups states by client region, request class, replica availability, queue pressure, and whether each replica meets the freshness tolerance. Q-learning updates action values from observed rewards and future estimated returns. It uses no labeled routing decisions, supervised fitting, or heuristic search. `nearest`, `leader`, and `random` exist only as evaluation controls; they do not route on behalf of the learned agent or generate its training labels.

Routing adds persistent replica work, increasing later queueing delays and slowing follower replay. This gives actions consequences beyond a single request. The scenarios include balanced traffic, write bursts, a regional outage, and a client traffic shift.

The initial cost is:

```text
reward = -(latency_cost + freshness_cost + failure_cost)
latency_cost = response_ms / request_deadline_ms
freshness_cost = 2 * min(max(staleness_ms - tolerance_ms, 0) / max(tolerance_ms, 50), 2)
failure_cost = 4 if unavailable or timed out, otherwise 0
```

Freshness cost is evaluated only for successful responses. Failures consume a timeout budget and receive the failure cost; a missing response cannot count as a fresh read. Every reward term is included in the trace. These are initial weights to validate, not an assertion of an optimal tradeoff.

## Model boundaries

- Freshness means **latest committed write timestamp minus applied write timestamp** at dispatch, with zero lag when caught up. It does not mean time since the last write. The `Latest` SLA is not a claim of linearizability.
- Reads use an admission-time snapshot; response completion is analytical (`RTT + queued work + service`). There is no mid-flight failure simulation yet.
- The simulator knows exact current telemetry. Coarse tabular observations aggregate states and are not a full Markov state. Delayed telemetry and richer continuous observations are later experiments.
- An unreachable replica fails; there is no silent fallback, retry, failover election, read quorum, or production consistency guarantee.
- Episodes truncate a continuing process. Training bootstraps at truncation and only removes the future-value term for true termination.
- Unknown Q-table states use zero initialization and the documented lowest-index tie rule during deterministic evaluation. The trace explicitly flags unseen states. There is no hidden nearest-replica fallback.
- The supplied model demonstrates training and replay. It has not passed the final multi-seed evaluation protocol, and improved performance is not assumed.

## Layout

```text
freshroute/                 simulator, Q-learning, experiments, CLI
tests/                     simulator invariants and learning/replay checks
docs/                      execution plan, UI design, commit plan, proposal
artifacts/demo/             reproducible initial trained agent and evidence
artifacts/runs/             ignored local training/evaluation outputs
pyproject.toml             package metadata; no core runtime dependencies
```

## Development and GitHub

Local Git is initialized on `main`. No remote or fabricated development history is supplied. Follow the [commit plan](docs/commit-plan.md) as work is completed, and commit real implementation, tests, and results together. Team member names and responsibilities remain to be assigned by the team.

After making your first real local commits and creating an empty GitHub repository:

```bash
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

## Technical references

- [Watkins and Dayan: Q-learning](https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf): the temporal-difference learner used in the initial milestone.
- [Gymnasium environment design](https://gymnasium.farama.org/introduction/create_custom_env/): the planned standard environment interface.
- [Stable-Baselines3 DQN](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html): the planned discrete-action DQN implementation. Its standard DQN is not Double DQN or Dueling DQN.
- [PostgreSQL standby replication](https://www.postgresql.org/docs/current/warm-standby.html): practical motivation for lag between primary commits and follower reads. The simulator simplifies those mechanics.
