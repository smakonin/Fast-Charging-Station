import unittest

from fcsim import SimulationConfig, run_monte_carlo, simulate_peak


class ThesisRegressionTests(unittest.TestCase):
    def test_30_percent_daily_case_tracks_reported_results(self):
        result = run_monte_carlo(
            SimulationConfig(sample_interval_min=5), days=20, seed=2017
        ).summary()
        self.assertTrue(0.15 < result["mean_stop_fraction"] < 0.20)
        self.assertTrue(8.8 < result["mean_mean_charge_min"] < 9.5)
        self.assertTrue(10.5 < result["mean_energy_mwh"] < 13.5)
        self.assertTrue(0.7 < result["p95_required_storage_mwh"] < 1.7)

    def test_40_percent_case_exposes_storage_growth(self):
        result = run_monte_carlo(
            SimulationConfig(penetration=0.40, sample_interval_min=5),
            days=20,
            seed=2017,
        ).summary()
        self.assertTrue(14.0 < result["mean_energy_mwh"] < 18.0)
        self.assertTrue(3.0 < result["p95_required_storage_mwh"] < 5.2)

    def test_peak_cccv_case_has_high_utilization(self):
        result = simulate_peak(
            SimulationConfig(sample_interval_min=2), hours=100, seed=2017
        )
        # Thesis Table 3.1 reports 6.8 EVs charging and 1.3 queued on average.
        self.assertTrue(6.3 < result.charging_count.mean() < 7.4)
        self.assertTrue(0.7 < result.queue_count.mean() < 2.5)


if __name__ == "__main__":
    unittest.main()
