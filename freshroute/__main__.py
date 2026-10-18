"""Run with python3 -m freshroute; no third-party runtime packages required."""

import argparse
import hashlib
import json
from pathlib import Path

from .agent import QAgent
from .environment import SCENARIOS
from .experiments import evaluate, rollout, summarize, train, write_json
from .policies import load_agent


def model_hash(path):
    path = Path(path)
    return hashlib.sha256((path / 'model.zip' if path.is_dir() else path).read_bytes()).hexdigest()


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main():
    parser = argparse.ArgumentParser(description="FreshRoute RL: learn where reads should go.")
    commands = parser.add_subparsers(dest="command", required=True)
    training = commands.add_parser("train", help="learn a Q-table from simulator interaction")
    training.add_argument("--episodes", type=positive, default=1200)
    training.add_argument("--steps", type=positive, default=160)
    training.add_argument("--seed", type=int, default=7)
    training.add_argument("--scenario", choices=(*SCENARIOS, "mixed"), default="mixed")
    training.add_argument("--output", type=Path, default=Path("artifacts/runs/q-agent.json"))
    deep = commands.add_parser('train-dqn', help='train a CPU DQN using the rl extra')
    deep.add_argument('--timesteps', type=positive, default=250_000)
    deep.add_argument('--seed', type=int, default=7)
    deep.add_argument('--ablation', choices=('full', 'no-freshness', 'no-queue'), default='full')
    deep.add_argument('--gamma', type=float, default=.95)
    deep.add_argument('--output', type=Path, required=True)
    validation = commands.add_parser("evaluate", help="compare a frozen agent against reference policies")
    validation.add_argument("--model", type=Path, default=Path("artifacts/demo/q-agent.json"))
    validation.add_argument("--episodes", type=positive, default=8)
    validation.add_argument("--seed", type=int, default=100_000)
    validation.add_argument("--output", type=Path, default=Path("artifacts/runs/evaluation.json"))
    replay = commands.add_parser("trace", help="export real decisions for the planned web explorer")
    replay.add_argument("--model", type=Path, default=Path("artifacts/demo/q-agent.json"))
    replay.add_argument("--seed", type=int, default=110_000)
    replay.add_argument("--scenario", choices=SCENARIOS, default="regional-outage")
    replay.add_argument("--output", type=Path, default=Path("artifacts/runs/decisions.jsonl"))
    args = parser.parse_args()
    try:
        if args.command == "train":
            agent, curve = train(episodes=args.episodes, steps=args.steps, seed=args.seed, scenario=args.scenario)
            agent.save(args.output)
            write_json(args.output.with_suffix(".training.json"), {"metadata": agent.metadata, "episodes": curve})
            print(f"Saved {args.output}: {len(agent.table)} states, {args.episodes * args.steps} RL transitions")
        elif args.command == 'train-dqn':
            from .dqn import train_dqn
            agent = train_dqn(output=args.output, timesteps=args.timesteps, seed=args.seed,
                              ablation=args.ablation, gamma=args.gamma)
            print(f'Saved trained DQN in {args.output}: {agent.metadata["training_steps"]} interactions')
        elif args.command == "evaluate":
            agent = load_agent(args.model)
            report = evaluate(agent, episodes=args.episodes, seed=args.seed)
            report["model_sha256"] = model_hash(args.model)
            write_json(args.output, report)
            print("scenario          policy       reward    SLA      available")
            for row in report["results"]:
                print(f'{row["scenario"]:17} {row["policy"]:12} {row["mean_reward"]:7.3f}'
                      f'  {row["sla_rate"]:7.1%}  {row["availability_rate"]:7.1%}')
            print(f"Saved {args.output}; validation only, not final test results")
        else:
            if not 100_000 <= args.seed < 200_000:
                raise ValueError("demo trace seeds must stay in [100000, 200000)")
            agent = load_agent(args.model)
            rows = rollout(agent, seed=args.seed, scenario=args.scenario)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text("".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in rows))
            write_json(args.output.with_suffix(".manifest.json"), {
                "schema_version": 1, "model_sha256": model_hash(args.model),
                "trace_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                "model_metadata": agent.metadata, "seed": args.seed, "scenario": args.scenario,
                "summary": summarize(rows),
            })
            print(f"Saved {len(rows)} actual RL decisions to {args.output}")
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"freshroute: {error}\n")


if __name__ == "__main__":
    main()
