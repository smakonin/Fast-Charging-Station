from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class ChargingProfile(str, Enum):
    CP = "cp"
    CCCV = "cccv"


# Table A1.1, density of BEVs at the station level on the motorway (EV/min),
# for the thesis base case of 30% EV penetration and a 50% BEV share.
THESIS_MOTORWAY_RATES_30 = (
    0.30, 0.20, 0.10, 0.10, 0.30, 0.80,
    2.10, 3.50, 3.60, 2.80, 2.70, 2.80,
    2.90, 2.90, 3.10, 3.50, 4.20, 4.30,
    3.40, 2.30, 1.60, 1.20, 0.90, 0.50,
)

# Table A1.1 station arrival densities (EV/min). These are the published,
# rounded result of thinning motorway traffic by the modelled stopping decision.
THESIS_STATION_RATES_30 = (
    0.05, 0.03, 0.02, 0.02, 0.04, 0.13,
    0.36, 0.61, 0.62, 0.49, 0.47, 0.49,
    0.50, 0.51, 0.54, 0.61, 0.72, 0.75,
    0.59, 0.40, 0.28, 0.20, 0.15, 0.09,
)


@dataclass(frozen=True)
class SimulationConfig:
    """Parameters for one 24-hour station simulation.

    Defaults reproduce the thesis's 30% penetration, ten-charger design.
    Power values are station-side kW and times are minutes.
    """

    penetration: float = 0.30
    bev_share: float = 0.50
    chargers: int = 10
    profile: ChargingProfile = ChargingProfile.CCCV
    dead_time_min: float = 2.0
    charger_power_kw: float = 200.0
    charger_efficiency: float = 0.90
    target_soc: float = 0.80
    reserve_soc: float = 0.20
    taper_start_soc: float = 0.60
    taper_end_power_kw: float = 50.0
    trip_distance_km: float = 100.0
    speed_kmh: float = 115.0
    grid_limit_kw: float = 800.0
    sample_interval_min: float = 1.0
    traffic_rates_30: tuple[float, ...] = THESIS_MOTORWAY_RATES_30
    station_rates_30: tuple[float, ...] = THESIS_STATION_RATES_30
    use_published_station_rates: bool = True

    def __post_init__(self) -> None:
        if self.penetration <= 0 or self.bev_share <= 0:
            raise ValueError("penetration and BEV share must be positive")
        if self.chargers < 1:
            raise ValueError("chargers must be at least one")
        if not 0 < self.charger_efficiency <= 1:
            raise ValueError("charger efficiency must be in (0, 1]")
        if not 0 <= self.reserve_soc < self.taper_start_soc < self.target_soc <= 1:
            raise ValueError("SOC thresholds must satisfy reserve < taper start < target")
        if len(self.traffic_rates_30) != 24:
            raise ValueError("traffic_rates_30 must contain 24 hourly rates")
        if len(self.station_rates_30) != 24:
            raise ValueError("station_rates_30 must contain 24 hourly rates")
        if self.sample_interval_min <= 0:
            raise ValueError("sample interval must be positive")

    @property
    def traffic_scale(self) -> float:
        return (self.penetration / 0.30) * (self.bev_share / 0.50)

    def as_dict(self) -> dict[str, object]:
        values = asdict(self)
        values["profile"] = self.profile.value
        return values
