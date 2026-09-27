from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .charging import build_charge_plan
from .config import SimulationConfig
from .queueing import Arrival, Session, dispatch_fifo, sample_counts, sample_power_kw
from .storage import required_storage_capacity_kwh
from .vehicles import sample_charging_vehicle, sample_vehicle


@dataclass(frozen=True)
class SimulationResult:
    config: SimulationConfig
    seed: int
    motorway_evs: int
    sessions: list[Session]
    times_min: np.ndarray
    power_kw: np.ndarray
    charging_count: np.ndarray
    queue_count: np.ndarray
    unavailable_count: np.ndarray
    required_storage_kwh: float

    @property
    def stop_fraction(self) -> float:
        return len(self.sessions) / self.motorway_evs if self.motorway_evs else 0.0

    def summary(self) -> dict[str, float | int | str]:
        waits = np.array([session.wait_min for session in self.sessions])
        service = np.array([session.plan.duration_min for session in self.sessions])
        interval_hours = self.config.sample_interval_min / 60.0
        return {
            "seed": self.seed,
            "profile": self.config.profile.value,
            "penetration": self.config.penetration,
            "chargers": self.config.chargers,
            "duration_hours": len(self.times_min) * self.config.sample_interval_min / 60.0,
            "motorway_evs": self.motorway_evs,
            "charging_evs": len(self.sessions),
            "stop_fraction": self.stop_fraction,
            "mean_charge_min": float(service.mean()) if len(service) else 0.0,
            "mean_wait_min": float(waits.mean()) if len(waits) else 0.0,
            "wait_probability": float((waits > 1e-9).mean()) if len(waits) else 0.0,
            "mean_queue": float(self.queue_count.mean()),
            "max_queue": int(self.queue_count.max(initial=0)),
            "mean_charging_evs": float(self.charging_count.mean()),
            "mean_power_kw": float(self.power_kw.mean()),
            "p95_power_kw": float(np.percentile(self.power_kw, 95)),
            "peak_power_kw": float(self.power_kw.max(initial=0.0)),
            "energy_mwh": float(self.power_kw.sum() * interval_hours / 1000.0),
            "required_storage_mwh": self.required_storage_kwh / 1000.0,
        }


@dataclass(frozen=True)
class MonteCarloResult:
    config: SimulationConfig
    days: list[SimulationResult]

    def summary(self) -> dict[str, float | int | str]:
        summaries = [day.summary() for day in self.days]
        keys = (
            "stop_fraction", "mean_charge_min", "mean_wait_min",
            "wait_probability", "mean_queue", "mean_charging_evs",
            "mean_power_kw", "p95_power_kw", "peak_power_kw",
            "energy_mwh", "required_storage_mwh",
        )
        output: dict[str, float | int | str] = {
            "profile": self.config.profile.value,
            "penetration": self.config.penetration,
            "chargers": self.config.chargers,
            "days": len(self.days),
        }
        for key in keys:
            values = np.asarray([float(item[key]) for item in summaries])
            output[f"mean_{key}"] = float(values.mean())
            output[f"p95_{key}"] = float(np.percentile(values, 95))
        return output


def _hour_arrivals(rate_per_min: float, hour: int, rng: Generator) -> np.ndarray:
    count = int(rng.poisson(rate_per_min * 60.0))
    return hour * 60.0 + rng.uniform(0.0, 60.0, size=count)


def _period_arrivals(rate_per_min: float, duration_min: float, rng: Generator) -> np.ndarray:
    count = int(rng.poisson(rate_per_min * duration_min))
    return np.sort(rng.uniform(0.0, duration_min, size=count))


def simulate_day(config: SimulationConfig | None = None, seed: int = 1) -> SimulationResult:
    config = config or SimulationConfig()
    rng = np.random.default_rng(seed)
    arrivals: list[Arrival] = []
    motorway_evs = 0
    if config.use_published_station_rates:
        for hour, base_rate in enumerate(config.traffic_rates_30):
            motorway_evs += len(
                _hour_arrivals(base_rate * config.traffic_scale, hour, rng)
            )
        for hour, station_rate in enumerate(config.station_rates_30):
            times = _hour_arrivals(station_rate * config.traffic_scale, hour, rng)
            for time_min in times:
                vehicle = sample_charging_vehicle(rng, config)
                arrivals.append(
                    Arrival(float(time_min), vehicle, build_charge_plan(vehicle, config))
                )
    else:
        for hour, base_rate in enumerate(config.traffic_rates_30):
            times = _hour_arrivals(base_rate * config.traffic_scale, hour, rng)
            motorway_evs += len(times)
            for time_min in times:
                vehicle = sample_vehicle(rng, config)
                if vehicle.needs_charge:
                    arrivals.append(
                        Arrival(float(time_min), vehicle, build_charge_plan(vehicle, config))
                    )
    sessions = dispatch_fifo(arrivals, config)
    times_min = np.arange(0.0, 1440.0, config.sample_interval_min)
    power_kw = sample_power_kw(sessions, times_min, config)
    charging, queue, unavailable = sample_counts(sessions, times_min)
    storage_kwh = required_storage_capacity_kwh(
        power_kw, config.grid_limit_kw, config.sample_interval_min
    )
    return SimulationResult(
        config=config,
        seed=seed,
        motorway_evs=motorway_evs,
        sessions=sessions,
        times_min=times_min,
        power_kw=power_kw,
        charging_count=charging,
        queue_count=queue,
        unavailable_count=unavailable,
        required_storage_kwh=storage_kwh,
    )


def run_monte_carlo(
    config: SimulationConfig | None = None,
    days: int = 100,
    seed: int = 1,
) -> MonteCarloResult:
    if days < 1:
        raise ValueError("days must be at least one")
    config = config or SimulationConfig()
    sequence = np.random.SeedSequence(seed)
    child_seeds = sequence.generate_state(days)
    return MonteCarloResult(
        config=config,
        days=[simulate_day(config, int(day_seed)) for day_seed in child_seeds],
    )


def simulate_peak(
    config: SimulationConfig | None = None,
    hours: float = 2400.0,
    seed: int = 1,
) -> SimulationResult:
    """Simulate the thesis's homogeneous peak hour, repeated for ``hours``.

    The thesis used 2,400 hours (100 days) to estimate steady-state queue and
    power distributions. The 30% base rates are 4.3 motorway EV/min and
    0.75 charging EV/min.
    """
    if hours <= 0:
        raise ValueError("hours must be positive")
    config = config or SimulationConfig()
    duration_min = hours * 60.0
    rng = np.random.default_rng(seed)
    arrivals: list[Arrival] = []
    motorway_rate = 4.3 * config.traffic_scale
    motorway_times = _period_arrivals(motorway_rate, duration_min, rng)
    motorway_evs = len(motorway_times)
    if config.use_published_station_rates:
        station_times = _period_arrivals(
            0.75 * config.traffic_scale, duration_min, rng
        )
        for time_min in station_times:
            vehicle = sample_charging_vehicle(rng, config)
            arrivals.append(
                Arrival(float(time_min), vehicle, build_charge_plan(vehicle, config))
            )
    else:
        for time_min in motorway_times:
            vehicle = sample_vehicle(rng, config)
            if vehicle.needs_charge:
                arrivals.append(
                    Arrival(float(time_min), vehicle, build_charge_plan(vehicle, config))
                )
    sessions = dispatch_fifo(arrivals, config)
    times_min = np.arange(0.0, duration_min, config.sample_interval_min)
    power_kw = sample_power_kw(sessions, times_min, config)
    charging, queue, unavailable = sample_counts(sessions, times_min)
    return SimulationResult(
        config=config,
        seed=seed,
        motorway_evs=motorway_evs,
        sessions=sessions,
        times_min=times_min,
        power_kw=power_kw,
        charging_count=charging,
        queue_count=queue,
        unavailable_count=unavailable,
        required_storage_kwh=required_storage_capacity_kwh(
            power_kw, config.grid_limit_kw, config.sample_interval_min
        ),
    )
