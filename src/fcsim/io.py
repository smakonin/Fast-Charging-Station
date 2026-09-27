from __future__ import annotations

import csv
import json
from pathlib import Path

from .simulation import MonteCarloResult, SimulationResult


def write_day(result: SimulationResult, output_dir: str | Path) -> None:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(
        json.dumps(result.summary(), indent=2) + "\n", encoding="utf-8"
    )
    with (directory / "timeseries.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["time_min", "power_kw", "charging_evs", "queued_evs", "dead_time_chargers"]
        )
        writer.writerows(
            zip(
                result.times_min,
                result.power_kw,
                result.charging_count,
                result.queue_count,
                result.unavailable_count,
            )
        )
    with (directory / "sessions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "arrival_min", "start_min", "end_min", "available_min", "wait_min",
                "charger", "battery_kwh", "arrival_soc", "charge_energy_kwh",
                "charge_duration_min",
            ]
        )
        for session in result.sessions:
            writer.writerow(
                [
                    session.arrival_min, session.start_min, session.end_min,
                    session.available_min, session.wait_min, session.charger,
                    session.vehicle.battery_kwh, session.vehicle.arrival_soc,
                    session.vehicle.charge_energy_kwh, session.plan.duration_min,
                ]
            )


def write_monte_carlo(result: MonteCarloResult, output_dir: str | Path) -> None:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(
        json.dumps(result.summary(), indent=2) + "\n", encoding="utf-8"
    )
    summaries = [day.summary() for day in result.days]
    with (directory / "days.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
