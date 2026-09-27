from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class QueueApproximation:
    utilization: float
    wait_probability: float
    mmc_wait_min: float
    mgc_wait_min: float
    mgc_queue_length: float


def erlang_c(
    arrival_rate_per_min: float,
    mean_service_min: float,
    servers: int,
    squared_cv: float = 1.0,
) -> QueueApproximation:
    """M/M/c exact values and the thesis's M/G/c variability correction."""
    offered_load = arrival_rate_per_min * mean_service_min
    utilization = offered_load / servers
    if utilization >= 1:
        return QueueApproximation(utilization, 1.0, math.inf, math.inf, math.inf)
    terms = sum(offered_load**n / math.factorial(n) for n in range(servers))
    tail = offered_load**servers / math.factorial(servers) / (1.0 - utilization)
    p0 = 1.0 / (terms + tail)
    wait_probability = tail * p0
    mmc_wait = wait_probability * mean_service_min / (
        servers * (1.0 - utilization)
    )
    mgc_wait = (1.0 + squared_cv) / 2.0 * mmc_wait
    return QueueApproximation(
        utilization=utilization,
        wait_probability=wait_probability,
        mmc_wait_min=mmc_wait,
        mgc_wait_min=mgc_wait,
        mgc_queue_length=arrival_rate_per_min * mgc_wait,
    )
