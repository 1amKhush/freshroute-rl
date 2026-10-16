"""Versioned, validated workload schedules; future phases are not policy inputs."""

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path


@dataclass(frozen=True)
class Phase:
    start: float
    end: float = 1.01
    write_probability: float = 0.25
    background_ms: float = 6
    lag_multiplier: float = 1
    offline_replica: int | None = None
    client_region: int | None = None

    def __post_init__(self):
        if not 0 <= self.start < self.end <= 1.01:
            raise ValueError("phase boundaries must satisfy 0 <= start < end <= 1.01")
        if not 0 <= self.write_probability <= 1:
            raise ValueError("write probability must be in [0,1]")
        for value in (self.background_ms, self.lag_multiplier):
            if not math.isfinite(value) or value < 0:
                raise ValueError("phase load and lag multiplier must be finite and nonnegative")
        for region in (self.offline_replica, self.client_region):
            if region is not None and (type(region) is not int or region not in range(3)):
                raise ValueError("region must be an integer in [0,2]")


@dataclass(frozen=True)
class Scenario:
    name: str
    schema_version: int = 1
    write_probability: float = 0.25
    background_ms: float = 6
    follower_delay_ms: tuple = (80, 0, 160)
    phases: tuple[Phase, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.schema_version != 1 or not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("scenario requires schema version 1 and a name")
        Phase(0, write_probability=self.write_probability, background_ms=self.background_ms)
        if len(self.follower_delay_ms) != 3 or self.follower_delay_ms[1] != 0 or any(
            not math.isfinite(value) or value < 0 for value in self.follower_delay_ms
        ):
            raise ValueError("three finite nonnegative replica delays required; leader delay must be zero")
        for previous, following in zip(self.phases, self.phases[1:]):
            if previous.end > following.start:
                raise ValueError("phases must be ordered and non-overlapping")

    def at(self, progress: float) -> Phase:
        return next((phase for phase in self.phases if phase.start <= progress < phase.end),
                    Phase(0, write_probability=self.write_probability, background_ms=self.background_ms))

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, payload):
        data = dict(payload)
        data["phases"] = tuple(Phase(**phase) for phase in data.get("phases", []))
        data["follower_delay_ms"] = tuple(data.get("follower_delay_ms", (80, 0, 160)))
        try:
            return cls(**data)
        except TypeError as error:
            raise ValueError(f"invalid scenario fields: {error}") from error


BUILTINS = {
    "balanced": Scenario("balanced"),
    "write-burst": Scenario("write-burst", phases=(Phase(.25, .75, .85, 12, 3),)),
    "regional-outage": Scenario("regional-outage", phases=(Phase(.30, .65, offline_replica=0),)),
    "traffic-shift": Scenario("traffic-shift", phases=(Phase(.5, client_region=2),)),
}


def load_scenario(value: str | Path | Scenario) -> Scenario:
    if isinstance(value, Scenario):
        return value
    if str(value) in BUILTINS:
        return BUILTINS[str(value)]
    try:
        return Scenario.from_dict(json.loads(Path(value).read_text()))
    except (TypeError, KeyError) as error:
        raise ValueError(f"invalid scenario configuration: {error}") from error
