from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import ChargingProfile, SimulationConfig
from .vehicles import Vehicle


@dataclass(frozen=True)
class ChargePlan:
    profile: ChargingProfile
    duration_min: float
    constant_duration_min: float
    taper_duration_min: float
    taper_start_fraction: float
    input_energy_kwh: float

    def power_kw(self, elapsed_min: np.ndarray | float, config: SimulationConfig):
        elapsed = np.asarray(elapsed_min, dtype=float)
        if self.profile == ChargingProfile.CP:
            power = np.where(
                (elapsed >= 0) & (elapsed < self.duration_min),
                config.charger_power_kw,
                0.0,
            )
        else:
            in_constant = (elapsed >= 0) & (elapsed < self.constant_duration_min)
            taper_elapsed = elapsed - self.constant_duration_min
            full_taper_min = _full_taper_duration_min(config, self._battery_kwh)
            taper_fraction = self.taper_start_fraction + taper_elapsed / full_taper_min
            taper_power = config.charger_power_kw - (
                config.charger_power_kw - config.taper_end_power_kw
            ) * taper_fraction
            in_taper = (
                (taper_elapsed >= 0)
                & (taper_elapsed < self.taper_duration_min)
            )
            power = np.where(
                in_constant,
                config.charger_power_kw,
                np.where(in_taper, taper_power, 0.0),
            )
        return float(power) if power.ndim == 0 else power

    def cumulative_input_kwh(
        self, elapsed_min: np.ndarray | float, config: SimulationConfig
    ):
        """Exact station-side energy delivered up to an elapsed time."""
        elapsed = np.clip(np.asarray(elapsed_min, dtype=float), 0.0, self.duration_min)
        constant_elapsed = np.minimum(elapsed, self.constant_duration_min)
        energy = config.charger_power_kw * constant_elapsed / 60.0
        if self.profile == ChargingProfile.CCCV and self.taper_duration_min > 0:
            taper_elapsed = np.clip(
                elapsed - self.constant_duration_min, 0.0, self.taper_duration_min
            )
            full_taper_min = _full_taper_duration_min(config, self._battery_kwh)
            span = config.charger_power_kw - config.taper_end_power_kw
            taper_energy = (
                config.charger_power_kw * taper_elapsed
                - span
                * (
                    self.taper_start_fraction * taper_elapsed
                    + taper_elapsed**2 / (2.0 * full_taper_min)
                )
            ) / 60.0
            energy = energy + taper_energy
        return float(energy) if energy.ndim == 0 else energy

    def energy_between_kwh(
        self,
        start_min: np.ndarray | float,
        end_min: np.ndarray | float,
        config: SimulationConfig,
    ):
        return self.cumulative_input_kwh(end_min, config) - self.cumulative_input_kwh(
            start_min, config
        )

    # Kept out of repr/equality; populated by build_charge_plan on frozen object.
    _battery_kwh: float = 0.0


def _full_taper_duration_min(config: SimulationConfig, battery_kwh: float) -> float:
    taper_energy = (config.target_soc - config.taper_start_soc) * battery_kwh
    average_input_power = (
        config.charger_power_kw + config.taper_end_power_kw
    ) / 2.0
    return taper_energy * 60.0 / (
        config.charger_efficiency * average_input_power
    )


def _taper_fraction_at_soc(
    soc: float, battery_kwh: float, config: SimulationConfig
) -> float:
    """Invert energy delivered by a linearly-in-time taper."""
    if soc <= config.taper_start_soc:
        return 0.0
    if soc >= config.target_soc:
        return 1.0
    p0 = config.charger_power_kw
    slope_span = p0 - config.taper_end_power_kw
    total_area = (p0 + config.taper_end_power_kw) / 2.0
    energy_fraction = (soc - config.taper_start_soc) / (
        config.target_soc - config.taper_start_soc
    )
    # p0*u - 0.5*slope_span*u^2 = energy_fraction*total_area
    disc = p0**2 - 2.0 * slope_span * energy_fraction * total_area
    return (p0 - disc**0.5) / slope_span


def build_charge_plan(vehicle: Vehicle, config: SimulationConfig) -> ChargePlan:
    input_energy = vehicle.charge_energy_kwh / config.charger_efficiency
    if config.profile == ChargingProfile.CP:
        return ChargePlan(
            profile=config.profile,
            duration_min=input_energy * 60.0 / config.charger_power_kw,
            constant_duration_min=input_energy * 60.0 / config.charger_power_kw,
            taper_duration_min=0.0,
            taper_start_fraction=0.0,
            input_energy_kwh=input_energy,
            _battery_kwh=vehicle.battery_kwh,
        )

    start_soc = max(vehicle.arrival_soc, 0.0)
    constant_energy = max(
        0.0,
        min(config.taper_start_soc, config.target_soc) - start_soc,
    ) * vehicle.battery_kwh
    constant_min = constant_energy * 60.0 / (
        config.charger_efficiency * config.charger_power_kw
    )
    taper_start_soc = max(start_soc, config.taper_start_soc)
    taper_start_fraction = _taper_fraction_at_soc(
        taper_start_soc, vehicle.battery_kwh, config
    )
    full_taper_min = _full_taper_duration_min(config, vehicle.battery_kwh)
    taper_min = max(0.0, (1.0 - taper_start_fraction) * full_taper_min)
    return ChargePlan(
        profile=config.profile,
        duration_min=constant_min + taper_min,
        constant_duration_min=constant_min,
        taper_duration_min=taper_min,
        taper_start_fraction=taper_start_fraction,
        input_energy_kwh=input_energy,
        _battery_kwh=vehicle.battery_kwh,
    )
