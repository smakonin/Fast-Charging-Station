import math
import unittest
from dataclasses import replace

import numpy as np

from fcsim.analytics import erlang_c
from fcsim.charging import build_charge_plan
from fcsim.config import ChargingProfile, SimulationConfig
from fcsim.storage import required_storage_capacity_kwh
from fcsim.vehicles import Vehicle, VehicleClass, motorway_energy_kwh


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.config = SimulationConfig()

    def vehicle(self, arrival_soc=0.40, battery_kwh=60.0):
        return Vehicle(
            battery_kwh=battery_kwh,
            vehicle_class=VehicleClass.MEDIUM,
            initial_soc=0.70,
            arrival_soc=arrival_soc,
            trip_energy_kwh=18.0,
            charge_energy_kwh=(0.80 - arrival_soc) * battery_kwh,
            needs_charge=True,
        )

    def test_cp_charge_conserves_energy(self):
        config = replace(self.config, profile=ChargingProfile.CP)
        plan = build_charge_plan(self.vehicle(), config)
        delivered = config.charger_power_kw * plan.duration_min / 60
        self.assertAlmostEqual(delivered, plan.input_energy_kwh, places=10)

    def test_cccv_full_taper_matches_thesis_profile(self):
        plan = build_charge_plan(self.vehicle(arrival_soc=0.60, battery_kwh=50), self.config)
        average_power = (200 + 50) / 2
        input_energy = average_power * plan.duration_min / 60
        self.assertAlmostEqual(input_energy * 0.9, 10.0, places=10)
        self.assertAlmostEqual(plan.power_kw(0, self.config), 200.0)
        self.assertTrue(50.0 <= plan.power_kw(plan.duration_min - 1e-8, self.config) < 50.001)
        self.assertAlmostEqual(
            plan.cumulative_input_kwh(plan.duration_min, self.config),
            plan.input_energy_kwh,
            places=10,
        )

    def test_motorway_energy_is_in_thesis_range(self):
        energy = motorway_energy_kwh(60, VehicleClass.MEDIUM, 1200, self.config)
        self.assertTrue(12.0 < energy < 20.0)

    def test_erlang_c_thesis_peak_approximation(self):
        result = erlang_c(0.75, 7.0, 10, squared_cv=0.13)
        self.assertAlmostEqual(result.utilization, 0.525, places=3)
        self.assertTrue(0.02 < result.mgc_wait_min < 0.06)

    def test_storage_capacity_is_maximum_drawdown(self):
        demand = np.array([0.0, 1000.0, 1000.0, 0.0])
        capacity = required_storage_capacity_kwh(demand, 500.0, 60.0)
        self.assertEqual(capacity, 1000.0)


if __name__ == "__main__":
    unittest.main()
