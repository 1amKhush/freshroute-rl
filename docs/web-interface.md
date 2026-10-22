# Web decision laboratory

**Status: core interface implemented.** The local React/FastAPI application supports replay, learned action values, reward outcomes, learning curves, comparisons, live sessions, faults, exports, and exact-state branches. The text below is the original design specification; optional extensions remain subject to the current [report](report.md). See the [demo guide](demo-guide.md) for the implemented flow. No cloud host or paid service is needed.

## Product goal and visual direction

Let an evaluator understand one decision in under a minute and then investigate the learning process. Use the name **FreshRoute RL** and the subtitle **Learning where fresh reads should go**.

Use a light technical-lab visual style: warm white canvas, ink text, cobalt for the selected route, teal for fresh data, amber for freshness violations, and red for unavailable replicas or timeouts. Use line patterns, icons, and text labels alongside color. A schematic three-region diagram is enough; avoid a map service dependency or suggesting that synthetic RTTs are live geographic measurements.

Desktop layout:

```text
FreshRoute RL                 [Replay / Live]   model + run identity
scenario selector             [Play] [Pause] [Step] [Reset]   speed

+--------------------------------------+-------------------------------+
| Replica topology                     | Selected request              |
|                                      | Origin / freshness / deadline |
| Mumbai ---- Frankfurt ---- Virginia  | Observed replica measurements |
| queue, lag, online, role              | Three estimated Q-values      |
| highlighted client -> chosen replica | Chosen action + visit counts  |
|                                      | Outcome + reward components   |
+--------------------------------------+-------------------------------+
| Replay timeline: writes, failures, freshness violations, selection   |
+--------------------------------------------------------------------+
| Latency / SLA / freshness / route share  | policy comparison          |
+--------------------------------------------------------------------+
```

On small screens, stack the topology, request inspector, timeline, and charts. Keep playback controls visible and make tables horizontally scrollable with accessible labels.

## Screen 1: decision explorer (first UI milestone)

Load the supplied `decisions.jsonl`, its manifest, and the matching training/evaluation artifacts. Loaders must validate schema version, replica IDs, finite numbers, and record ordering. File selection is an explicit local action; offer a checked-in demo run as the default.

1. **Topology:** three replica cards show region, leader/follower role, reachability, RTT, queued service work, applied version, timestamp lag, and version lag. Draw the current request's route. Display units on every quantity.
2. **Request inspector:** show request class, client region, freshness tolerance, deadline, and all pre-action observations. Keep measured outcomes visually separate from observations that existed before the action.
3. **Action inspector:** show the actual selected replica and all learned Q-values from the trace. Mark the maximum. State “estimated discounted return; larger is preferred.” Negative values are expected for negative costs. Do not transform values into confidence percentages.
4. **Training coverage:** show whether this encoded state was seen and its per-action visit counts. Unseen states display “unseen state; zero-initialized values; deterministic tie rule.” A high visit count is not a calibrated confidence estimate.
5. **Outcome:** response time, transport result, returned data freshness if present, SLA result, reward, and its latency/freshness/failure terms. Failed reads show no returned version/lag, rather than zero staleness.
6. **Transition:** let the evaluator toggle between pre-action and next-state telemetry. Label which request each snapshot belongs to.

Supported controls: play/pause, next and previous decision, jump to a step, adjustable playback speed, and filters for failure/freshness events. Replay is immutable: selecting a different replica or dragging a fault control cannot alter recorded outcomes. Any branch creates a new live/counterfactual run with its own identity.

Begin with a library-free SVG topology and ordinary semantic tables. Use a chart library only when it improves the required time series; do not add a map or a node editor just for appearance.

## Screen 2: training and evaluation

- Learning curves: episode return, epsilon, and SLA rate from the actual training log. Smooth only as an optional overlay with the raw series visible.
- Comparison table: Q-learning, DQN when available, nearest, leader, and random. Include model identity, scenario, seed count, return, latency, availability, freshness violations, and SLA satisfaction.
- Distributions and breakdowns: latency by request class/region, lag distribution, replica route share, and queue pressure.
- Clearly label validation versus final test. Do not mix them or pool independent training runs without explaining aggregation.
- Show empty states for unavailable experiments. A DQN tab remains unavailable until a real checkpoint and report exist.
- Display original configuration and downloadable results. No “RL improvement” badge unless computed against a named baseline with the metric, scenario, and uncertainty visible.

## Screen 3: live fault laboratory (later milestone)

Create a local simulator session bound to a loaded model, scenario, reward configuration, and seed. Controls send actual commands to that session:

- Route automatically with the frozen policy; single-step or run at a bounded speed.
- Make a selected replica unreachable or restore it.
- Increase follower replay delay or background work for a specified duration.
- Change the client-region mixture or request-class mix.
- Reset into a new seeded session and compare with an unmodified run.

Sliders that change workload or topology affect transitions. Sliders that change reward weights cannot change an already trained policy's preferences by magic: label the run as an evaluation under different costs, or select/retrain a model trained with those weights. Online training is out of scope initially.

Keep the seed, model, configuration, current simulation step, and active faults visible. Export the session trace and manifest. Isolate sessions so two browser tabs do not share mutable environment state. The server is local and bound to loopback in the initial demo.

## Explanation without invented reasoning

For every selected decision, distinguish:

| Evidence | What the GUI may say |
| --- | --- |
| Observation | “Mumbai's observed timestamp lag exceeded this request's 100 ms budget.” |
| Learned values | “Frankfurt had the largest estimated action value for this encoded observation.” |
| Executed outcome | “The read returned in 150 ms and met the recorded freshness budget.” |
| Reward | “Latency contributed -0.83; freshness and failure contributed 0.” |
| Counterfactual | “A simulator branch from the same snapshot produced this alternative outcome.” |

The example numbers above are wording examples, not reported project measurements. Do not infer a causal rationale from Q-value ordering alone. No LLM-generated explanation is required.

For counterfactuals, the API must clone simulator state **and RNG state**, apply each alternative action, and use a named frozen rollout policy for any subsequent steps. Identify one-step cost separately from estimated long-term return. Unchosen Q-values are predictions, not measured alternative outcomes. Baseline evaluation from a fresh episode is also not a same-state counterfactual.

## Integration contract

The implemented JSONL record has:

```text
schema_version, policy, seed, scenario, step
observation: request context and replicas[] at decision time
state_key, q_values[3], state_seen_in_training, action_training_visits[3]
action, reward
outcome: response_ms, transport_ok, unavailable, timeout,
         staleness_ms, version_lag, freshness_violation, sla_met, reward_terms
next_observation, terminated, truncated
```

The manifest holds checkpoint and trace hashes, model metadata/configuration, seed, scenario, and summary. For reference policies, Q-values and Q-table coverage are null. Preserve nulls as “not applicable.”

Planned local API routes (not implemented):

| Route | Purpose |
| --- | --- |
| `GET /api/models` | list validated local checkpoints and metadata |
| `GET /api/runs` | list replay manifests and evaluation reports |
| `GET /api/runs/{id}/decisions?offset=&limit=` | page through immutable trace records |
| `POST /api/sessions` | create a seeded environment/model session |
| `POST /api/sessions/{id}/step` | execute one actual frozen-policy decision |
| `POST /api/sessions/{id}/faults` | apply a versioned fault event |
| `POST /api/sessions/{id}/counterfactuals` | branch a selected exact state |
| `DELETE /api/sessions/{id}` | release a live session |

Begin with HTTP request/response stepping; add server-sent events only if needed for efficient continuous playback. Version faults and manifests before publishing APIs. Validate payloads, cap live session lifetime/trace size, and avoid accepting arbitrary server file paths from the browser.

## Stack and build order

Use React + TypeScript + Vite for the UI, SVG for topology, and FastAPI for the later Python API. Styling can use ordinary CSS; a styling framework is optional. Keep the interface independent of the RL training library.

1. Commit an actual captured trace and typed schema fixtures.
2. Render a single request accurately before animation.
3. Add topology, action-value and reward views.
4. Add replay timeline/playback and evaluation comparison.
5. Verify keyboard use, reduced motion, labels, contrast, and narrow screens.
6. Add local live sessions and confirm CLI/API seeded equivalence.
7. Add fault controls and exact-state counterfactuals.

## Acceptance and demo script

First UI acceptance: an evaluator can pause a real decision, inspect all observed values, verify the selected action against saved Q-values, sum reward components, and inspect the resulting state. Playback must stop at the last record; reset returns to step zero; controls work with a keyboard; motion respects reduced-motion preferences.

Final demo, about five minutes:

1. Introduce the latency/freshness tension using the topology and SLA examples.
2. Replay a read and explain the observation, learned values, and actual outcome.
3. Compare the trained policy with the named static controls on the same validation workload seeds.
4. Inject an outage and lag spike; show changed choices and consequences without claiming guaranteed adaptation.
5. Show a snapshot counterfactual if implemented, then the learning curve, final evaluation evidence, and limitations.

Record a video only after the full flow works. Keep a saved-replay mode usable without running training or a live server.
