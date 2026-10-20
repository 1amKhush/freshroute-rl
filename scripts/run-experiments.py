"""Run the checked-in CPU budget and preserve all trained seeds and raw metrics."""

import argparse
import gzip
import json
from pathlib import Path

from freshroute.dqn import DQNAgent, train_dqn
from freshroute.experiments import evaluate_matrix, source_fingerprint, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=Path('configs/experiment.json'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/experiments/initial'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    if config['schema_version'] != 1:
        raise ValueError('unsupported experiment schema')
    start_hash = source_fingerprint()
    models = []
    for condition in config['conditions']:
        seeds = config['training_seeds'] if condition == 'full' else config['ablation_seeds']
        for seed in seeds:
            path = args.output / f'{condition}-seed-{seed}'
            if path.exists() and (path / 'metadata.json').exists():
                existing = DQNAgent.load(path)
                if existing.metadata['source_sha256'] != start_hash:
                    raise ValueError(f'source changed; use a fresh experiment directory: {path}')
            else:
                print(f'Training {condition}, seed {seed}', flush=True)
                train_dqn(output=path, timesteps=config['timesteps_per_run'], seed=seed,
                          ablation='full' if condition == 'gamma-zero' else condition,
                          gamma=0 if condition == 'gamma-zero' else .95)
            models.append(path)
    if source_fingerprint() != start_hash:
        raise ValueError('Python source changed during training; repeat under a fixed revision')
    write_json(args.output / 'experiment.json', config)
    print('Evaluating independent training seeds on paired validation workloads', flush=True)
    report = evaluate_matrix(models, episodes=config['validation_episodes'], seed=config['validation_seed'])
    (args.output / 'validation.json.gz').write_bytes(gzip.compress(
        (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode(), mtime=0))
    print(f'Preserved {len(models)} models and validation evidence in {args.output}', flush=True)


if __name__ == '__main__':
    main()
