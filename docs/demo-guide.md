# Demonstration guide

Run the setup/build/server commands in the [README](../README.md), then open `http://127.0.0.1:8000`. All demonstration decisions come from real saved or live frozen-policy inference. No training needs to run during the presentation.

| Time | Show | Explain |
| --- | --- | --- |
| 0:00–0:45 | Three-region topology and SLA classes | Nearest reads can be stale; leader reads can be slow or overloaded. Requests have different budgets. |
| 0:45–1:30 | Pause and step a replay decision | Separate the observation available before acting from the outcome measured afterward. Identify the largest Q-value and selected action. |
| 1:30–2:15 | Queue pressure, data lag, reward costs, next-state toggle | Routing changes future workload; timestamp lag differs from time since the last write. Sum the cost terms. |
| 2:15–3:00 | Training and evaluation view | Show the actual learning curve, test split, named controls, and limitations. Reported scores come from a fixed synthetic workload. |
| 3:00–4:00 | Live laboratory, DQN, seed 110000, balanced workload | Start a session, inject a Mumbai outage for 20 reads, and step. Observe actual availability/choice changes. Restore the replica or inject follower lag. |
| 4:00–4:40 | Compare all choices from the selected snapshot | Each branch starts from identical simulator/RNG state. Immediate outcomes are measured; later steps follow the same frozen policy. Branches do not mutate the live run. |
| 4:40–5:00 | Export trace/manifest and open repository | Show reproducible setup, trained models, validation/test evidence, and actual incremental commits. |

Outage or lag injection need not change the chosen replica on every request. The agent may already prefer another replica. Explain the actual displayed result instead of promising a scripted reaction.

For a compact backup, use the bundled immutable replay. It works without a live inference session. Keyboard navigation, reduced-motion support, and a narrow-screen layout are available. Screenshots of the real interface are in [images](images/decision-explorer.png).

Before recording, assign real speaking roles and add the approved team identities. The repository includes this script and screenshots; a narrated video has not been recorded or uploaded.
