"""Freeze validation selection before evaluating the reserved final-test split."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics

from freshroute.dqn import DQNAgent
from freshroute.experiments import evaluate_matrix, rollout, source_fingerprint, summarize, write_json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', type=Path, default=Path('artifacts/experiments/initial'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/releases'))
    args = parser.parse_args()
    validation_path = args.experiment / 'validation.json.gz'
    validation_bytes = gzip.decompress(validation_path.read_bytes())
    validation = json.loads(validation_bytes)
    if validation['split'] != 'validation':
        raise ValueError('selection requires a validation report')
    candidates = [run for run in validation['runs']
                  if run['model_metadata'].get('ablation') == 'full' and run['model_metadata'].get('gamma') == .95]
    if len(candidates) < 3:
        raise ValueError('at least three independent full-observation models required')

    def score(run):
        return statistics.fmean(row['mean_reward'] for row in run['results'] if row['policy'] == 'dqn')

    selected = max(candidates, key=score)
    models = [Path(run['model_path']) for run in validation['runs']]
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('release directory must be empty; preserve the existing frozen evaluation')
    args.output.mkdir(parents=True, exist_ok=True)
    frozen = {
        'schema_version': 1, 'selection_rule': 'largest macro mean reward across four validation scenarios',
        'validation_sha256': hashlib.sha256(validation_bytes).hexdigest(), 'selected_model': selected['model_path'],
        'selected_validation_score': score(selected), 'test_seed_start': 200_000,
        'test_episodes_per_scenario': 30, 'evaluation_source_sha256': source_fingerprint(),
        'models': [{'path': str(path), 'weights_sha256': digest(path / 'model.zip')} for path in models],
        'test_scope': 'new seeds in the same four configured workload regimes; not an out-of-distribution claim',
    }
    # Persist the decision and complete model matrix before accessing any test episode.
    write_json(args.output / 'frozen.json', frozen)
    shutil.copytree(Path(selected['model_path']), args.output / 'dqn')
    report = evaluate_matrix(models, episodes=30, seed=200_000, split='test')
    (args.output / 'test-matrix.json.gz').write_bytes(gzip.compress(
        (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode(), mtime=0))
    selected_test = next(run for run in report['runs'] if run['model_path'] == selected['model_path'])
    write_json(args.output / 'evaluation.json', selected_test)
    agent = DQNAgent.load(args.output / 'dqn')
    rows = rollout(agent, seed=110_000, scenario='regional-outage')
    trace = args.output / 'decisions.jsonl'
    trace.write_text(''.join(json.dumps(row, sort_keys=True, allow_nan=False) + '\n' for row in rows))
    write_json(args.output / 'decisions.manifest.json', {
        'schema_version': 1, 'model_sha256': digest(args.output / 'dqn/model.zip'),
        'trace_sha256': digest(trace), 'model_metadata': agent.metadata,
        'seed': 110_000, 'scenario': 'regional-outage', 'summary': summarize(rows),
    })
    print(f'Frozen seed {agent.metadata["agent_seed"]}; final-test evidence and replay saved to {args.output}')


if __name__ == '__main__':
    main()
