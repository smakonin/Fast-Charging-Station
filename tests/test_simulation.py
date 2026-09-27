import unittest
from dataclasses import replace

import numpy as np

from fcsim.config import ChargingProfile, SimulationConfig
from fcsim.simulation import simulate_day


class SimulationTests(unittest.TestCase):
    def test_seed_is_reproducible(self):
        config = SimulationConfig(sample_interval_min=5)
        first = simulate_day(config, seed=42)
        second = simulate_day(config, seed=42)
        self.assertEqual(first.summary(), second.summary())
        np.testing.assert_array_equal(first.power_kw, second.power_kw)

    def test_more_chargers_do_not_increase_wait(self):
        base = SimulationConfig(
            penetration=0.40,
            profile=ChargingProfile.CCCV,
            sample_interval_min=5,
        )
        ten = simulate_day(base, seed=9)
        twelve = simulate_day(replace(base, chargers=12), seed=9)
        self.assertLessEqual(
            twelve.summary()["mean_wait_min"], ten.summary()["mean_wait_min"]
        )

    def test_counts_never_exceed_chargers(self):
        config = SimulationConfig(sample_interval_min=2)
        result = simulate_day(config, seed=3)
        self.assertLessEqual(result.charging_count.max(), config.chargers)
        self.assertLessEqual(
            (result.charging_count + result.unavailable_count).max(), config.chargers
        )


if __name__ == "__main__":
    unittest.main()
