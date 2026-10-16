# Observation schema v1

The raw observation in decision traces contains request context and current simulator telemetry. Scenario schedules, future random draws, alternative-action outcomes, and reward outcomes are never policy inputs.

The planned Gymnasium vector uses 26 float32 values in [0,1], ordered as follows:

| Indices | Meaning | Scaling |
| --- | --- | --- |
| 0–2 | client region | one-hot Mumbai / Frankfurt / Virginia |
| 3–5 | request class | one-hot latest / bounded / relaxed |
| 6 | tolerance | ms / 500 |
| 7 | deadline | ms / 240 |
| 8–13, 14–19, 20–25 | each replica in fixed ID order | six features below |

Replica feature order: online (0/1), RTT/250, queue/(queue+100), timestamp lag/(lag+200), version lag/(lag+10), replication delay/(delay+200). Bounded rational transforms avoid fitting a normalizer on validation/test data. Time, scenario name, future phase schedule, and absolute version numbers are excluded. Aggregation and hidden write histories mean this remains a partially observed control problem; a vector interface alone does not make it fully observable.

`no-freshness` zeros the three replica freshness/replay channels. `no-queue` zeros queue and replay-delay channels; timestamp/version lag can still carry indirect consequences of workload. Both preserve shape and require independently trained agents. Schema and ablation identities belong in checkpoint metadata.

Scenario files use schema version 1 and are validated by `Scenario.from_dict`. Their explicit phase windows are fractions of the episode horizon. They support changes in write probability, background service work, replay-delay multiplier, forced replica outage, and client region. Built-in scenarios preserve the original foundation's dynamics. Synthetic constants are configuration choices, not measured network data.
