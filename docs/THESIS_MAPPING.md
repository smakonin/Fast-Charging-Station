# Thesis-to-code mapping

Source: Paul F. R. Saugier, *Design of a Fast-Charging Station for Electric Vehicles*, University of Cambridge, 2017.

| Thesis material | Implementation |
|---|---|
| 2.1 Poisson process and M/G/c queue | `analytics.py`, `queueing.py` |
| 2.2 hourly motorway and station flow; Appendix A1.1 | `config.py`, `simulation.py` |
| 2.3.2 shifted-lognormal capacity and EV classes | `vehicles.py` |
| 2.3.3 inverse-lognormal initial SOC | `vehicles.py` |
| 2.3.4 vehicle force, mass, auxiliary load, trip energy | `motorway_energy_kwh` in `vehicles.py` |
| 2.3.5 20% reserve decision and 80% target | `sample_vehicle` in `vehicles.py` |
| 2.3.6 CP and CC/CV profiles | `charging.py` |
| 2.4 ten-server FIFO and two-minute dead time | `dispatch_fifo` in `queueing.py` |
| 2.5 peak and daily simulations | `simulate_peak`, `simulate_day`, `run_monte_carlo` |
| 2.6 ideal storage behind an 800 kW grid tie | `storage.py` |
| Appendix 2 M/M/c / Erlang C | `erlang_c` in `analytics.py` |

## Reproduction checks

The following checks used deterministic seeds and the published station-arrival rates. Monte Carlo values vary slightly by seed and run length.

| Quantity | Thesis | Simulator check |
|---|---:|---:|
| Fraction of motorway BEVs stopping | 17.4% | 17.2-17.4% |
| Mean CP charge | 7.0 min | 7.03 min |
| Mean CC/CV charge | 9.1 min | 9.17 min |
| 30% daily energy | 12 MWh | about 12 MWh |
| 40% daily energy | 16 MWh | 16.2 MWh |
| 40% CC/CV mean usable storage | 3 MWh | 3.34 MWh |
| 40% CC/CV 95th-percentile usable storage | 4 MWh | 4.09 MWh |

## Explicit interpretations

- The blue curve in Figure 2.8 is treated as a charging-power taper linear in time from 200 kW at 60% SOC to 50 kW at 80% SOC. Energy is integrated analytically.
- Charger power is station-side input; battery-side power is reduced by the stated 90% efficiency.
- A charger becomes available only after charging plus dead time. Power is zero during dead time.
- Hourly arrivals are conditionally uniform within each hour, which is equivalent to a homogeneous Poisson process over that hour.
- The ideal storage model starts full, accepts surplus grid energy until full, spills excess, and has no loss or power limit, matching section 2.6.
- The published station rates are the default reproduction path. The bottom-up stopping decision remains available with `use_published_station_rates=False`.

## Deliberately out of scope

The thesis does not specify a finite queue, customer abandonment, battery aging, storage efficiency, storage power limits, converter losses beyond charger efficiency, renewable generation, tariffs, or economic optimization. Those are therefore extension points rather than silently invented behavior.
