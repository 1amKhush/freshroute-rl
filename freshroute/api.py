"""Local inference sessions, immutable replay, and a static web application."""

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Literal
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .agent import encode
from .environment import Config, SCENARIOS, ReplicaEnv
from .policies import load_agent


ROOT = Path(__file__).resolve().parents[1]


class NewSession(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model_id: str = 'q-learning'
    seed: int = Field(default=110_000, ge=100_000, lt=200_000)
    scenario: Literal['balanced', 'write-burst', 'regional-outage', 'traffic-shift'] = 'balanced'


class FaultRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['outage', 'lag', 'load', 'restore']
    replica: int = Field(ge=0, le=2)
    duration_steps: int = Field(default=20, ge=1, le=160)
    value: float = Field(default=100, ge=0, le=1000, allow_inf_nan=False)


class BranchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    horizon: int = Field(default=8, ge=1, le=30)


def record_step(env, agent, seed):
    observation = env.observe()
    action = agent.act(observation)
    values = agent.values(observation)
    following, reward, terminated, truncated, info = env.step(action)
    key = encode(observation)
    tabular = agent.algorithm == 'q-learning'
    return {
        'schema_version': 1, 'policy': agent.algorithm, 'seed': seed, 'scenario': env.scenario,
        'step': observation['step'], 'observation': observation, 'state_key': key,
        'q_values': values, 'state_seen_in_training': key in agent.table if tabular else None,
        'action_training_visits': list(agent.visits.get(key, [0, 0, 0])) if tabular else None,
        'action': action, 'reward': reward, 'outcome': info, 'next_observation': following,
        'terminated': terminated, 'truncated': truncated,
    }


@dataclass
class Session:
    id: str
    model_id: str
    agent: object
    env: ReplicaEnv
    seed: int
    model_sha256: str
    records: list = field(default_factory=list)
    updated: float = field(default_factory=time.monotonic)
    lock: object = field(default_factory=threading.RLock)
    last_snapshot: object = None

    def describe(self):
        return {'id': self.id, 'model_id': self.model_id, 'seed': self.seed,
                'scenario': self.env.scenario, 'observation': self.env.observe()}

    def step(self):
        with self.lock:
            if self.env.step_index >= self.env.config.episode_steps:
                raise HTTPException(409, 'Episode complete. Create a new session to reset.')
            self.last_snapshot = deepcopy(self.env)
            row = record_step(self.env, self.agent, self.seed)
            self.records.append(row)
            self.updated = time.monotonic()
            return row

    def trace_text(self):
        return ''.join(json.dumps(row, sort_keys=True, allow_nan=False) + '\n' for row in self.records)


class Laboratory:
    def __init__(self, models=None):
        self.models = models if models is not None else {'q-learning': ROOT / 'artifacts/demo/q-agent.json'}
        if models is None and (ROOT / 'artifacts/releases/dqn/metadata.json').exists():
            self.models['dqn'] = ROOT / 'artifacts/releases/dqn'
        self.sessions, self.agents = {}, {}
        self.lock = threading.RLock()

    def create(self, request):
        with self.lock:
            now = time.monotonic()
            self.sessions = {key: value for key, value in self.sessions.items() if now - value.updated < 1800}
            if len(self.sessions) >= 16:
                raise HTTPException(429, 'Session limit reached. Close an earlier session or wait for expiry.')
            if request.model_id not in self.models:
                raise HTTPException(404, 'Unknown model ID')
            path = Path(self.models[request.model_id])
            if request.model_id not in self.agents:
                self.agents[request.model_id] = load_agent(path)
            agent = self.agents[request.model_id]
            env = ReplicaEnv(Config(**agent.metadata['config']), request.scenario)
            env.reset(seed=request.seed)
            weights = path / 'model.zip' if path.is_dir() else path
            session = Session(uuid.uuid4().hex, request.model_id, agent, env, request.seed,
                              hashlib.sha256(weights.read_bytes()).hexdigest())
            self.sessions[session.id] = session
            return session.describe()

    def get(self, session_id):
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or time.monotonic() - session.updated >= 1800:
                self.sessions.pop(session_id, None)
                raise HTTPException(404, 'Session not found or expired')
            return session


def create_app(*, models=None, web_directory=None):
    app = FastAPI(title='FreshRoute RL laboratory', version='0.2.0')
    lab = Laboratory(models)
    app.state.laboratory = lab

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'models': list(lab.models), 'schema_version': 1}

    @app.get('/api/models')
    def list_models():
        return [{'id': key, 'label': 'DQN · frozen validation selection' if key == 'dqn' else 'Q-learning · 192k interactions',
                 'algorithm': 'dqn' if Path(path).is_dir() else 'q-learning'} for key, path in lab.models.items()]

    @app.get('/api/runs')
    def list_runs():
        return [{'id': 'demo', 'label': 'Original Q-learning validation replay'},
                *([{'id': 'release', 'label': 'Frozen DQN replay'}] if (ROOT / 'artifacts/releases/decisions.jsonl').exists() else [])]

    @app.get('/api/runs/{run_id}/decisions')
    def replay(run_id: Literal['demo', 'release'], offset: int = Query(0, ge=0), limit: int = Query(160, ge=1, le=1000)):
        path = ROOT / ('artifacts/demo' if run_id == 'demo' else 'artifacts/releases') / 'decisions.jsonl'
        if not path.exists():
            raise HTTPException(404, 'Replay is not available')
        return [json.loads(line) for line in path.read_text().splitlines()[offset:offset + limit]]

    @app.post('/api/sessions', status_code=201)
    def create_session(request: NewSession):
        return lab.create(request)

    @app.post('/api/sessions/{session_id}/step')
    def step(session_id: str):
        return lab.get(session_id).step()

    @app.delete('/api/sessions/{session_id}', status_code=204)
    def delete_session(session_id: str):
        with lab.lock:
            if lab.sessions.pop(session_id, None) is None:
                raise HTTPException(404, 'Session not found')

    @app.post('/api/sessions/{session_id}/faults')
    def fault(session_id: str, request: FaultRequest):
        session = lab.get(session_id)
        with session.lock:
            try:
                event = session.env.inject_fault(**request.model_dump())
            except ValueError as error:
                raise HTTPException(400, str(error)) from error
            session.updated = time.monotonic()
            return {'event': event, 'observation': session.env.observe()}

    @app.get('/api/sessions/{session_id}/trace', response_class=PlainTextResponse)
    def trace(session_id: str):
        session = lab.get(session_id)
        with session.lock:
            return PlainTextResponse(session.trace_text(), headers={'Content-Disposition': 'attachment; filename="decisions.jsonl"'})

    @app.post('/api/sessions/{session_id}/counterfactuals')
    def counterfactuals(session_id: str, request: BranchRequest):
        from .counterfactual import branch_actions
        session = lab.get(session_id)
        with session.lock:
            snapshot = session.last_snapshot if session.last_snapshot is not None else session.env
            return branch_actions(snapshot, session.agent, horizon=request.horizon)

    @app.get('/api/sessions/{session_id}/manifest')
    def manifest(session_id: str):
        session = lab.get(session_id)
        with session.lock:
            return {'schema_version': 1, 'seed': session.seed, 'scenario': session.env.scenario,
                    'model_sha256': session.model_sha256, 'model_metadata': session.agent.metadata,
                    'trace_sha256': hashlib.sha256(session.trace_text().encode()).hexdigest(),
                    'faults': getattr(session.env, 'fault_events', [])}

    web_directory = Path(web_directory) if web_directory else ROOT / 'web/dist'
    if web_directory.exists():
        app.mount('/', StaticFiles(directory=web_directory, html=True), name='web')
    return app
