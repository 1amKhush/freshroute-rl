# FreshRoute RL: Learning Staleness-Aware Read Routing

**Domain:** reinforcement learning for distributed database systems.

**Problem.** A geographically distributed database maintains replicas with different network delays, processing loads, replication lag, and availability. Always reading from the nearest replica can return outdated data; always reading from the leader can increase latency and concentrate load. Different requests also tolerate different levels of staleness.

**Proposed solution.** Train an RL agent to choose the destination of each incoming read. The agent observes the client region, freshness budget, response deadline, and replica telemetry. It learns from a reward that penalizes latency, stale responses, and failed requests. Its routing decisions influence future queueing pressure and replication progress, making this a sequential control problem.

**RL formulation.** The environment is a seeded simulator of one leader and two asynchronous followers. Actions initially select a replica. Tabular Q-learning establishes an inspectable learning baseline; a DQN agent using continuous telemetry is the implemented main experiment. The solution policy is trained through environment interaction, not through supervised labels, heuristic search, or a hand-written routing rule.

**Visualization.** The web interface animates read routes and replica state, replay individual decisions, show learned action values and reward components, and compare policies under the same exogenous workload seeds. Users can inject outages or lag spikes and observe adaptation. Model explanations will report estimates and observed outcomes rather than inventing a rationale.

**Evaluation.** Measure response latency, response availability, freshness violations, SLA satisfaction, and return across balanced traffic, write bursts, outages, and changing client locations. Compare frozen RL agents with clearly labeled static reference policies using separate training, validation, and final test seeds. Report multiple independent training runs and uncertainty; do not assume RL will win every metric or scenario.

**Distinctive contribution.** The intended contribution is the combination of request-specific freshness budgets, workload-dependent replication and queue effects, and reproducible decision replay with simulator counterfactuals. This is a proposed project distinction, not a claim that the research problem is previously unsolved.

**Submission artifacts.** Complete source code and setup instructions, trained agent with configuration and seed provenance, evaluation scripts/results, interactive demonstration, and a real incremental Git history. The repository is https://github.com/1amKhush/freshroute-rl. Team details and the instructor's submission deadline will be filled in by the team.
