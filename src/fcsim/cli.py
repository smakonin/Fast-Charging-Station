from __future__ import annotations

import argparse
import json

from .config import ChargingProfile, SimulationConfig
from .io import write_day, write_monte_carlo
from .simulation import run_monte_carlo, simulate_day, simulate_peak


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fcsim", description="Saugier fast-charging station simulator"
    )
    parser.add_argument("--profile", choices=["cp", "cccv"], default="cccv")
    parser.add_argument("--penetration", type=float, default=0.30)
    parser.add_argument("--chargers", type=int, default=10)
    parser.add_argument("--dead-time", type=float, default=2.0)
    parser.add_argument("--charger-power", type=float, default=200.0)
    parser.add_argument("--grid-limit", type=float, default=800.0)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument(
        "--peak-hours",
        type=float,
        default=0.0,
        help="run a constant peak-rate experiment (thesis used 2400)",
    )
    parser.add_argument("--output", default="output/latest")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = SimulationConfig(
        profile=ChargingProfile(args.profile),
        penetration=args.penetration,
        chargers=args.chargers,
        dead_time_min=args.dead_time,
        charger_power_kw=args.charger_power,
        grid_limit_kw=args.grid_limit,
        sample_interval_min=args.interval,
    )
    if args.peak_hours > 0:
        result = simulate_peak(config, args.peak_hours, args.seed)
        write_day(result, args.output)
    elif args.days == 1:
        result = simulate_day(config, args.seed)
        write_day(result, args.output)
    else:
        result = run_monte_carlo(config, args.days, args.seed)
        write_monte_carlo(result, args.output)
    print(json.dumps(result.summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
