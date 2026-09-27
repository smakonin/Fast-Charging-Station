from __future__ import annotations

import numpy as np


def required_storage_capacity_kwh(
    demand_kw: np.ndarray, grid_limit_kw: float, interval_min: float
) -> float:
    """Minimum ideal storage capacity with a full initial store and spill control."""
    deficit = 0.0
    maximum = 0.0
    for demand in demand_kw:
        deficit = max(
            0.0,
            deficit + (float(demand) - grid_limit_kw) * interval_min / 60.0,
        )
        maximum = max(maximum, deficit)
    return maximum


def storage_trace_kwh(
    demand_kw: np.ndarray,
    grid_limit_kw: float,
    interval_min: float,
    capacity_kwh: float,
) -> np.ndarray:
    energy = capacity_kwh
    trace = np.empty(len(demand_kw) + 1, dtype=float)
    trace[0] = energy
    for index, demand in enumerate(demand_kw, start=1):
        energy += (grid_limit_kw - float(demand)) * interval_min / 60.0
        energy = min(capacity_kwh, max(0.0, energy))
        trace[index] = energy
    return trace
