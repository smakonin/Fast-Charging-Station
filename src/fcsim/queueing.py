from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np

from .charging import ChargePlan
from .config import SimulationConfig
from .vehicles import Vehicle


@dataclass(frozen=True)
class Arrival:
    time_min: float
    vehicle: Vehicle
    plan: ChargePlan


@dataclass(frozen=True)
class Session:
    arrival_min: float
    start_min: float
    end_min: float
    available_min: float
    charger: int
    vehicle: Vehicle
    plan: ChargePlan

    @property
    def wait_min(self) -> float:
        return self.start_min - self.arrival_min


def dispatch_fifo(arrivals: list[Arrival], config: SimulationConfig) -> list[Session]:
    """Exact FCFS dispatch for identical parallel chargers."""
    available = [(0.0, charger) for charger in range(config.chargers)]
    heapq.heapify(available)
    sessions: list[Session] = []
    for arrival in sorted(arrivals, key=lambda item: item.time_min):
        free_min, charger = heapq.heappop(available)
        start_min = max(arrival.time_min, free_min)
        end_min = start_min + arrival.plan.duration_min
        available_min = end_min + config.dead_time_min
        sessions.append(
            Session(
                arrival_min=arrival.time_min,
                start_min=start_min,
                end_min=end_min,
                available_min=available_min,
                charger=charger,
                vehicle=arrival.vehicle,
                plan=arrival.plan,
            )
        )
        heapq.heappush(available, (available_min, charger))
    return sessions


def sample_power_kw(
    sessions: list[Session], times_min: np.ndarray, config: SimulationConfig
) -> np.ndarray:
    """Average station power in bins beginning at ``times_min``.

    Charge-plan energy is integrated analytically, so changing the reporting
    interval does not change total energy or storage calculations.
    """
    power = np.zeros_like(times_min, dtype=float)
    if len(times_min) == 0:
        return power
    interval = config.sample_interval_min
    origin = float(times_min[0])
    for session in sessions:
        first = max(0, int(np.floor((session.start_min - origin) / interval)))
        stop = min(len(times_min), int(np.ceil((session.end_min - origin) / interval)))
        if first < stop:
            bins = times_min[first:stop]
            relative_start = np.maximum(bins, session.start_min) - session.start_min
            relative_end = np.minimum(bins + interval, session.end_min) - session.start_min
            energy = session.plan.energy_between_kwh(
                relative_start, relative_end, config
            )
            power[first:stop] += energy * 60.0 / interval
    return power


def sample_counts(
    sessions: list[Session], times_min: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    def event_count(intervals: list[tuple[float, float]]) -> np.ndarray:
        changes = np.zeros(len(times_min) + 1, dtype=int)
        for start, end in intervals:
            first = int(np.searchsorted(times_min, start, side="left"))
            stop = int(np.searchsorted(times_min, end, side="left"))
            if first < len(times_min) and first < stop:
                changes[first] += 1
                changes[min(stop, len(times_min))] -= 1
        return np.cumsum(changes[:-1])

    charging = event_count([(item.start_min, item.end_min) for item in sessions])
    queue = event_count([(item.arrival_min, item.start_min) for item in sessions])
    unavailable = event_count([(item.end_min, item.available_min) for item in sessions])
    return charging, queue, unavailable
