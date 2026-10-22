# Methods and results

FreshRoute RL learns which replica should serve a read under latency, freshness, and availability tradeoffs. The submitted policies are Q-learning and DQN trained from environment rewards. Static routing controls provide comparisons; they do not replace either learned policy.

## Environment and sequential effects

The simulator has one write leader in Frankfurt and followers in Mumbai and Virginia. Requests arrive every 12 ms. Service work remains in replica queues; queue pressure affects both later read latency and follower replay. Workloads cover balanced traffic, write bursts, regional outages, and client-region shifts. Network and service constants are synthetic. Reads take dispatch-time snapshots, and response time is analytical.

Freshness is committed-versus-applied timestamp lag, not time since the last write. Zero lag does not imply a general distributed consistency guarantee. Current telemetry is exact inside the simulator; policy observations aggregate state and omit write histories. This is not claimed to be a fully observed MDP.

## Learners and fixed experiment budget

- Q-learning: coarse state encoder, alpha 0.12, gamma 0.95, epsilon-greedy exploration, 192000 initial demonstration interactions.
- DQN: Stable-Baselines3 vanilla DQN, 26 bounded telemetry features, three actions, two 128-unit hidden layers, replay capacity 100000, batch 64, learning rate 1e-4, target update every 1000 steps, gamma 0.95, CPU with one thread.
- Five full-agent training seeds: 7, 23, 47, 71, 97. Three seeds per ablation: 7, 23, 47. Each model used 50000 interactions, totaling 700000.
- Ablations: remove freshness/replay channels; remove queue/replay-delay channels; independently train gamma zero. All preserve the original environment/reward definition.

The 10000-step CPU trial took about 3.45 seconds on this execution host. The 50000-step setting was used for the initial study; the longer 250000-step setting in the original plan was not run. Neither budget establishes convergence. Each checkpoint metadata file preserves actual wall time, package versions, source fingerprint, and model hash. Training sources are at commit `54bb60b`; later API/fault additions preserve the frozen no-fault replay.

## Selection and evaluation

Training environment seeds stay below 100000. Checkpoint selection uses fixed validation seeds 100000 and 100001. The paired validation matrix uses 30 seeds starting at 100100 in each scenario. The full-observation model with the best equal-weight mean validation reward across four scenarios was selected: seed 71.

`frozen.json` records the selection rule, decompressed validation-report hash, and all 14 weights hashes before final evaluation. The final test uses seeds 200000 through 200029, 160 requests per episode, in each of the same four workload regimes. These are held-out random seeds, not held-out system configurations.

All policies use the same exogenous random draw schedules, while their own queues and replication consequences evolve separately. Controls are repeated for pairing and are not counted as independent new trials. Bootstrap intervals resample independent training-seed means, not dependent requests. They are descriptive given five or three training seeds.

## All full-agent training seeds: macro test results

The following averages weight scenarios equally. Intervals are percentile bootstrap intervals across independently trained agents.

| Condition | Training seeds | Mean reward | 95% reward interval | SLA met |
| --- | ---: | ---: | --- | ---: |
| full | 5 | -1.281 | [-1.302, -1.265] | 71.0% |
| no-freshness | 3 | -1.311 | [-1.315, -1.306] | 70.4% |
| no-queue | 3 | -1.788 | [-1.849, -1.735] | 61.3% |
| gamma-zero | 3 | -1.484 | [-1.548, -1.412] | 68.7% |

Removing queue telemetry reduced return in this configuration. Removing freshness telemetry had a smaller effect; do not assume every feature is necessary in every simulator. Gamma-zero differences can reflect optimization effects as well as reduced planning. These experiments are evidence about this particular model and workload calibration.

## Validation-selected demonstration model: test results

| Scenario | Policy | Mean reward | SLA met | Response availability | Freshness violations among responses |
| --- | --- | ---: | ---: | ---: | ---: |
| balanced | dqn | -0.763 | 82.7% | 98.8% | 16.4% |
| balanced | nearest | -3.124 | 31.2% | 60.0% | 48.0% |
| balanced | leader | -4.809 | 4.4% | 4.4% | 0.0% |
| balanced | random | -2.595 | 44.0% | 72.2% | 39.1% |
| write-burst | dqn | -2.136 | 52.3% | 78.7% | 33.5% |
| write-burst | nearest | -3.653 | 22.1% | 48.7% | 54.7% |
| write-burst | leader | -4.809 | 4.4% | 4.4% | 0.0% |
| write-burst | random | -3.284 | 29.6% | 60.9% | 51.3% |
| regional-outage | dqn | -1.280 | 73.7% | 88.3% | 16.5% |
| regional-outage | nearest | -3.298 | 28.9% | 53.1% | 45.6% |
| regional-outage | leader | -4.809 | 4.4% | 4.4% | 0.0% |
| regional-outage | random | -2.862 | 40.0% | 63.5% | 37.0% |
| traffic-shift | dqn | -0.860 | 78.4% | 98.3% | 20.2% |
| traffic-shift | nearest | -3.474 | 24.8% | 52.1% | 52.5% |
| traffic-shift | leader | -4.809 | 4.4% | 4.4% | 0.0% |
| traffic-shift | random | -2.695 | 41.9% | 70.4% | 40.5% |

Response availability means a reply within the request deadline, not replica uptime. In this synthetic configuration, concentrating all requests on the leader overloads its service queue, explaining its low reply rate. Changing service capacity or arrival rate can change this ranking. Failures consume a timeout budget and never count as fresh responses.

The original Q-learning demonstration is a separate validation artifact. It was not included as a paired comparator in this DQN final-test matrix, so these tables do not establish a DQN-versus-Q-learning advantage.

## Decision explanations and GUI

The web interface renders pre-action observations, all three learned action values, the chosen route, measured outcome, and each reward component. It verifies the bundled replay hash. Q-values are labeled as estimated discounted returns rather than probabilities.

Live sessions load a frozen policy; they do not train online. Faults change actual reachability, background work, or replay delays. Past recorded decisions remain immutable. Counterfactuals clone the complete simulator and RNG state from the selected pre-action snapshot, execute each alternative first action, then follow the same frozen policy for up to eight steps. Tests establish repeatability, exact reproduction of the chosen action outcome, and no mutation of the source session.

![Live fault and counterfactual view](images/live-laboratory.png)

## Reproduction and evidence

- [Full setup and commands](../README.md).
- [Original Q-learning artifacts](../artifacts/demo/README.md).
- [All DQN training runs and validation](../artifacts/experiments/initial/README.md).
- [Frozen model and complete test evidence](../artifacts/releases/README.md).
- [Verification record](validation.md).

Reports ending in `.json.gz` are standard gzip-compressed JSON and retain all per-episode, regional, and request-class metrics. Checkpoint metadata records actual tested dependency versions.

## Limits and remaining coursework steps

There is no real database benchmark, delayed/noisy telemetry study, mid-flight failure model, hard consistency enforcement, leader election, or out-of-distribution qualification. Reward-weight sweeps, longer training, session minimum-version constraints, hedged strategies, and PostgreSQL validation remain extensions.

Team identities/roles, instructor approval/submission, and the final narrated presentation are still human coursework steps. The repository supplies runnable code, trained agents, experiment evidence, screenshots, and a demo script; it does not claim those submissions happened.

## References

[Q-learning](https://www.gatsby.ucl.ac.uk/~dayan/papers/cjch.pdf), [Gymnasium environments](https://gymnasium.farama.org/introduction/create_custom_env/), [DQN implementation](https://stable-baselines3.readthedocs.io/en/master/modules/dqn.html), [termination versus truncation](https://farama.org/Gymnasium-Terminated-Truncated-Step-API), and [asynchronous standby replication](https://www.postgresql.org/docs/current/warm-standby.html).
