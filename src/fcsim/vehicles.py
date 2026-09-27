from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np
from numpy.random import Generator

from .config import SimulationConfig


class VehicleClass(IntEnum):
    SMALL = 0
    MEDIUM = 1
    LARGE = 2


@dataclass(frozen=True)
class Vehicle:
    battery_kwh: float
    vehicle_class: VehicleClass
    initial_soc: float
    arrival_soc: float
    trip_energy_kwh: float
    charge_energy_kwh: float
    needs_charge: bool


def classify_battery(capacity_kwh: float) -> VehicleClass:
    if capacity_kwh < 50.0:
        return VehicleClass.SMALL
    if capacity_kwh > 75.0:
        return VehicleClass.LARGE
    return VehicleClass.MEDIUM


def motorway_energy_kwh(
    capacity_kwh: float,
    vehicle_class: VehicleClass,
    auxiliary_power_w: float,
    config: SimulationConfig,
) -> float:
    """Equation in thesis section 2.3.4 for a quasi-steady 115 km/h trip."""
    mass_kg = 20.0 * capacity_kwh + 300.0
    frontal_area_m2 = (2.1, 2.2, 2.3)[int(vehicle_class)]
    speed_ms = config.speed_kmh / 3.6
    force_n = (
        0.005 * mass_kg * 9.81
        + 0.5 * 1.2 * speed_ms**2 * 0.25 * frontal_area_m2
        + 0.2607 * mass_kg * 0.079
    )
    drive_power_w = force_n * speed_ms / 0.95
    trip_hours = config.trip_distance_km / config.speed_kmh
    return (drive_power_w + auxiliary_power_w) / 1000.0 * trip_hours


def sample_vehicle(rng: Generator, config: SimulationConfig) -> Vehicle:
    # Shifted lognormal battery model: theta=20 kWh, mu=3.7, sigma=0.35.
    capacity = 20.0 + float(rng.lognormal(mean=3.7, sigma=0.35))
    vehicle_class = classify_battery(capacity)
    soc_mu = (2.9, 3.2, 3.4)[int(vehicle_class)]
    initial_soc = 1.0 - float(rng.lognormal(mean=soc_mu, sigma=0.25)) / 100.0
    # The source distribution has an unbounded tail. Clipping only handles its
    # vanishingly rare nonphysical draws and makes arbitrary seeds robust.
    initial_soc = float(np.clip(initial_soc, 0.0, 1.0))
    auxiliary_w = max(0.0, float(rng.normal(1200.0, 300.0)))
    trip_energy = motorway_energy_kwh(
        capacity, vehicle_class, auxiliary_w, config
    )
    remaining_kwh = initial_soc * capacity - trip_energy
    arrival_soc = remaining_kwh / capacity
    needs_charge = (
        remaining_kwh - trip_energy < config.reserve_soc * capacity
    )
    charge_energy = max(0.0, config.target_soc * capacity - remaining_kwh)
    return Vehicle(
        battery_kwh=capacity,
        vehicle_class=vehicle_class,
        initial_soc=initial_soc,
        arrival_soc=arrival_soc,
        trip_energy_kwh=trip_energy,
        charge_energy_kwh=charge_energy,
        needs_charge=bool(needs_charge and charge_energy > 0),
    )


def sample_charging_vehicle(rng: Generator, config: SimulationConfig) -> Vehicle:
    """Draw from the population conditional on stopping at the FCS."""
    while True:
        vehicle = sample_vehicle(rng, config)
        if vehicle.needs_charge:
            return vehicle
