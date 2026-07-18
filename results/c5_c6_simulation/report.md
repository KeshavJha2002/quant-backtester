# c5 / c6 Portfolio Simulation

## Setup
- Strategies simulated: `c5 W/W`, `c6 D`, `c6 W`
- Strategy omitted: `c5 D/W`
- Universe: combined `N50 + N150 + N250`, with universe-level breakdowns preserved
- Entry capital per trade: `INR 10,000.00`
- Cone threshold: `sigma < 2.0`
- Scenario A: infinite capital, baseline capital set to required max deployed capital for reporting
- Scenario B: capital capped at `INR 4.00 lakh (0.40 mn)`
- Scenario B ranking: deeper cone discount adjusted by a holding-horizon proxy to favor return-per-day and turnover
- Scenario B weekly cap: max `5` new `W` trades per week across `c5 W/W` and `c6 W` combined

## Raw Trade Summary By Strategy And Universe
| strategy   | segment   |   trades |   avg_return_pct |   win_rate_pct |   avg_duration_days |   avg_sigma | total_pnl_inr            |
|:-----------|:----------|---------:|-----------------:|---------------:|--------------------:|------------:|:-------------------------|
| c5_ww      | N150      |     4925 |             9.37 |          44.06 |               91.42 |       -0.66 | INR 46.17 lakh (4.62 mn) |
| c5_ww      | N250      |     6507 |            11.72 |          42.71 |               92.97 |       -0.74 | INR 76.24 lakh (7.62 mn) |
| c5_ww      | N50       |     2304 |             8.44 |          46.35 |               92.95 |       -0.61 | INR 19.44 lakh (1.94 mn) |
| c6_d       | N150      |     5123 |            13.39 |          40.66 |              117.91 |       -0.57 | INR 68.60 lakh (6.86 mn) |
| c6_d       | N250      |     6937 |            16.54 |          38.78 |              116.43 |       -0.59 | INR 1.15 cr (11.48 mn)   |
| c6_d       | N50       |     2588 |             9.97 |          44.13 |              110.92 |       -0.58 | INR 25.80 lakh (2.58 mn) |
| c6_w       | N150      |      938 |           101.43 |          51.92 |              596.84 |       -0.48 | INR 95.14 lakh (9.51 mn) |
| c6_w       | N250      |     1295 |            94.05 |          51.66 |              555.36 |       -0.5  | INR 1.22 cr (12.18 mn)   |
| c6_w       | N50       |      449 |            95.82 |          57.24 |              606.9  |       -0.47 | INR 43.02 lakh (4.30 mn) |

## Scenario A
- Ending equity: `INR 3.53 cr (35.30 mn)`
- Max deployed capital: `INR 48.80 lakh (4.88 mn)`
- Executed trades: `20357`

|   year | start_equity             | end_equity               | pnl                       |   return_pct | max_deployed             |
|-------:|:-------------------------|:-------------------------|:--------------------------|-------------:|:-------------------------|
|   1996 | INR 48.80 lakh (4.88 mn) | INR 48.60 lakh (4.86 mn) | -INR 19,920.99            |        -0.41 | INR 5.10 lakh (0.51 mn)  |
|   1997 | INR 48.83 lakh (4.88 mn) | INR 49.68 lakh (4.97 mn) | INR 84,468.29             |         1.73 | INR 8.60 lakh (0.86 mn)  |
|   1998 | INR 49.70 lakh (4.97 mn) | INR 50.70 lakh (5.07 mn) | INR 99,616.95             |         2    | INR 8.50 lakh (0.85 mn)  |
|   1999 | INR 50.71 lakh (5.07 mn) | INR 57.52 lakh (5.75 mn) | INR 6.82 lakh (0.68 mn)   |        13.44 | INR 9.70 lakh (0.97 mn)  |
|   2000 | INR 58.35 lakh (5.84 mn) | INR 56.21 lakh (5.62 mn) | -INR 2.15 lakh (0.21 mn)  |        -3.68 | INR 8.80 lakh (0.88 mn)  |
|   2001 | INR 56.21 lakh (5.62 mn) | INR 54.87 lakh (5.49 mn) | -INR 1.34 lakh (0.13 mn)  |        -2.38 | INR 9.40 lakh (0.94 mn)  |
|   2002 | INR 54.83 lakh (5.48 mn) | INR 58.79 lakh (5.88 mn) | INR 3.96 lakh (0.40 mn)   |         7.22 | INR 19.10 lakh (1.91 mn) |
|   2003 | INR 58.96 lakh (5.90 mn) | INR 93.83 lakh (9.38 mn) | INR 34.88 lakh (3.49 mn)  |        59.16 | INR 27.90 lakh (2.79 mn) |
|   2004 | INR 95.03 lakh (9.50 mn) | INR 1.02 cr (10.22 mn)   | INR 7.21 lakh (0.72 mn)   |         7.59 | INR 29.30 lakh (2.93 mn) |
|   2005 | INR 1.03 cr (10.31 mn)   | INR 1.22 cr (12.22 mn)   | INR 19.14 lakh (1.91 mn)  |        18.57 | INR 29.10 lakh (2.91 mn) |
|   2006 | INR 1.23 cr (12.26 mn)   | INR 1.34 cr (13.38 mn)   | INR 11.17 lakh (1.12 mn)  |         9.1  | INR 27.30 lakh (2.73 mn) |
|   2007 | INR 1.34 cr (13.38 mn)   | INR 1.60 cr (15.95 mn)   | INR 25.76 lakh (2.58 mn)  |        19.25 | INR 33.60 lakh (3.36 mn) |
|   2008 | INR 1.61 cr (16.05 mn)   | INR 1.36 cr (13.64 mn)   | -INR 24.18 lakh (2.42 mn) |       -15.06 | INR 33.80 lakh (3.38 mn) |
|   2009 | INR 1.37 cr (13.72 mn)   | INR 1.78 cr (17.75 mn)   | INR 40.32 lakh (4.03 mn)  |        29.38 | INR 36.60 lakh (3.66 mn) |
|   2010 | INR 1.78 cr (17.84 mn)   | INR 1.89 cr (18.86 mn)   | INR 10.28 lakh (1.03 mn)  |         5.76 | INR 34.30 lakh (3.43 mn) |
|   2011 | INR 1.89 cr (18.88 mn)   | INR 1.80 cr (18.05 mn)   | -INR 8.38 lakh (0.84 mn)  |        -4.44 | INR 31.20 lakh (3.12 mn) |
|   2012 | INR 1.80 cr (18.04 mn)   | INR 1.92 cr (19.17 mn)   | INR 11.26 lakh (1.13 mn)  |         6.24 | INR 36.40 lakh (3.64 mn) |
|   2013 | INR 1.92 cr (19.20 mn)   | INR 1.96 cr (19.64 mn)   | INR 4.37 lakh (0.44 mn)   |         2.28 | INR 38.00 lakh (3.80 mn) |
|   2014 | INR 1.97 cr (19.67 mn)   | INR 2.30 cr (23.04 mn)   | INR 33.76 lakh (3.38 mn)  |        17.17 | INR 40.40 lakh (4.04 mn) |
|   2015 | INR 2.31 cr (23.07 mn)   | INR 2.37 cr (23.68 mn)   | INR 6.08 lakh (0.61 mn)   |         2.64 | INR 33.10 lakh (3.31 mn) |
|   2016 | INR 2.37 cr (23.72 mn)   | INR 2.40 cr (24.02 mn)   | INR 3.05 lakh (0.30 mn)   |         1.28 | INR 38.00 lakh (3.80 mn) |
|   2017 | INR 2.40 cr (24.05 mn)   | INR 2.66 cr (26.59 mn)   | INR 25.44 lakh (2.54 mn)  |        10.58 | INR 37.10 lakh (3.71 mn) |
|   2018 | INR 2.66 cr (26.59 mn)   | INR 2.57 cr (25.72 mn)   | -INR 8.77 lakh (0.88 mn)  |        -3.3  | INR 39.00 lakh (3.90 mn) |
|   2019 | INR 2.57 cr (25.73 mn)   | INR 2.56 cr (25.56 mn)   | -INR 1.70 lakh (0.17 mn)  |        -0.66 | INR 38.80 lakh (3.88 mn) |
|   2020 | INR 2.56 cr (25.58 mn)   | INR 2.79 cr (27.86 mn)   | INR 22.80 lakh (2.28 mn)  |         8.91 | INR 43.70 lakh (4.37 mn) |
|   2021 | INR 2.79 cr (27.93 mn)   | INR 3.15 cr (31.55 mn)   | INR 36.21 lakh (3.62 mn)  |        12.97 | INR 44.60 lakh (4.46 mn) |
|   2022 | INR 3.16 cr (31.62 mn)   | INR 3.16 cr (31.62 mn)   | -INR 974.46               |        -0    | INR 43.80 lakh (4.38 mn) |
|   2023 | INR 3.17 cr (31.66 mn)   | INR 3.47 cr (34.65 mn)   | INR 29.98 lakh (3.00 mn)  |         9.47 | INR 48.70 lakh (4.87 mn) |
|   2024 | INR 3.47 cr (34.66 mn)   | INR 3.61 cr (36.12 mn)   | INR 14.58 lakh (1.46 mn)  |         4.21 | INR 46.50 lakh (4.65 mn) |
|   2025 | INR 3.62 cr (36.16 mn)   | INR 3.58 cr (35.80 mn)   | -INR 3.59 lakh (0.36 mn)  |        -0.99 | INR 48.80 lakh (4.88 mn) |
|   2026 | INR 3.58 cr (35.81 mn)   | INR 3.53 cr (35.30 mn)   | -INR 5.16 lakh (0.52 mn)  |        -1.44 | INR 32.00 lakh (3.20 mn) |

## Scenario B
- Starting capital: `INR 4.00 lakh (0.40 mn)`
- Ending equity: `INR 2.82 cr (28.18 mn)`
- Executed trades: `19524`
- Skipped trades: `11542`

|   year | start_equity             | end_equity               | pnl                       |   return_pct | max_deployed             |
|-------:|:-------------------------|:-------------------------|:--------------------------|-------------:|:-------------------------|
|   1996 | INR 4.00 lakh (0.40 mn)  | INR 3.83 lakh (0.38 mn)  | -INR 17,408.31            |        -4.35 | INR 3.50 lakh (0.35 mn)  |
|   1997 | INR 3.96 lakh (0.40 mn)  | INR 4.47 lakh (0.45 mn)  | INR 50,334.96             |        12.7  | INR 4.40 lakh (0.44 mn)  |
|   1998 | INR 4.50 lakh (0.45 mn)  | INR 4.80 lakh (0.48 mn)  | INR 30,725.64             |         6.83 | INR 4.40 lakh (0.44 mn)  |
|   1999 | INR 4.80 lakh (0.48 mn)  | INR 8.20 lakh (0.82 mn)  | INR 3.40 lakh (0.34 mn)   |        70.74 | INR 5.50 lakh (0.55 mn)  |
|   2000 | INR 8.72 lakh (0.87 mn)  | INR 7.86 lakh (0.79 mn)  | -INR 86,508.23            |        -9.92 | INR 7.30 lakh (0.73 mn)  |
|   2001 | INR 7.87 lakh (0.79 mn)  | INR 6.63 lakh (0.66 mn)  | -INR 1.23 lakh (0.12 mn)  |       -15.66 | INR 6.90 lakh (0.69 mn)  |
|   2002 | INR 6.60 lakh (0.66 mn)  | INR 9.52 lakh (0.95 mn)  | INR 2.91 lakh (0.29 mn)   |        44.13 | INR 7.80 lakh (0.78 mn)  |
|   2003 | INR 9.59 lakh (0.96 mn)  | INR 24.14 lakh (2.41 mn) | INR 14.55 lakh (1.46 mn)  |       151.81 | INR 9.60 lakh (0.96 mn)  |
|   2004 | INR 24.66 lakh (2.47 mn) | INR 32.94 lakh (3.29 mn) | INR 8.27 lakh (0.83 mn)   |        33.55 | INR 18.50 lakh (1.85 mn) |
|   2005 | INR 33.51 lakh (3.35 mn) | INR 50.74 lakh (5.07 mn) | INR 17.23 lakh (1.72 mn)  |        51.42 | INR 23.50 lakh (2.35 mn) |
|   2006 | INR 51.13 lakh (5.11 mn) | INR 62.31 lakh (6.23 mn) | INR 11.18 lakh (1.12 mn)  |        21.86 | INR 26.50 lakh (2.65 mn) |
|   2007 | INR 62.28 lakh (6.23 mn) | INR 87.80 lakh (8.78 mn) | INR 25.53 lakh (2.55 mn)  |        40.99 | INR 33.30 lakh (3.33 mn) |
|   2008 | INR 88.80 lakh (8.88 mn) | INR 65.19 lakh (6.52 mn) | -INR 23.61 lakh (2.36 mn) |       -26.59 | INR 33.50 lakh (3.35 mn) |
|   2009 | INR 66.05 lakh (6.61 mn) | INR 1.06 cr (10.64 mn)   | INR 40.32 lakh (4.03 mn)  |        61.04 | INR 36.60 lakh (3.66 mn) |
|   2010 | INR 1.07 cr (10.72 mn)   | INR 1.17 cr (11.75 mn)   | INR 10.28 lakh (1.03 mn)  |         9.59 | INR 34.30 lakh (3.43 mn) |
|   2011 | INR 1.18 cr (11.77 mn)   | INR 1.09 cr (10.93 mn)   | -INR 8.38 lakh (0.84 mn)  |        -7.12 | INR 31.20 lakh (3.12 mn) |
|   2012 | INR 1.09 cr (10.92 mn)   | INR 1.21 cr (12.05 mn)   | INR 11.26 lakh (1.13 mn)  |        10.31 | INR 36.40 lakh (3.64 mn) |
|   2013 | INR 1.21 cr (12.08 mn)   | INR 1.25 cr (12.52 mn)   | INR 4.37 lakh (0.44 mn)   |         3.62 | INR 38.00 lakh (3.80 mn) |
|   2014 | INR 1.26 cr (12.55 mn)   | INR 1.59 cr (15.93 mn)   | INR 33.76 lakh (3.38 mn)  |        26.9  | INR 40.40 lakh (4.04 mn) |
|   2015 | INR 1.60 cr (15.96 mn)   | INR 1.66 cr (16.56 mn)   | INR 6.08 lakh (0.61 mn)   |         3.81 | INR 33.10 lakh (3.31 mn) |
|   2016 | INR 1.66 cr (16.60 mn)   | INR 1.69 cr (16.91 mn)   | INR 3.05 lakh (0.30 mn)   |         1.84 | INR 38.00 lakh (3.80 mn) |
|   2017 | INR 1.69 cr (16.93 mn)   | INR 1.95 cr (19.47 mn)   | INR 25.44 lakh (2.54 mn)  |        15.03 | INR 37.10 lakh (3.71 mn) |
|   2018 | INR 1.95 cr (19.48 mn)   | INR 1.86 cr (18.60 mn)   | -INR 8.77 lakh (0.88 mn)  |        -4.5  | INR 39.00 lakh (3.90 mn) |
|   2019 | INR 1.86 cr (18.61 mn)   | INR 1.84 cr (18.44 mn)   | -INR 1.70 lakh (0.17 mn)  |        -0.91 | INR 38.80 lakh (3.88 mn) |
|   2020 | INR 1.85 cr (18.46 mn)   | INR 2.07 cr (20.74 mn)   | INR 22.80 lakh (2.28 mn)  |        12.35 | INR 43.70 lakh (4.37 mn) |
|   2021 | INR 2.08 cr (20.81 mn)   | INR 2.44 cr (24.43 mn)   | INR 36.21 lakh (3.62 mn)  |        17.4  | INR 44.60 lakh (4.46 mn) |
|   2022 | INR 2.45 cr (24.50 mn)   | INR 2.45 cr (24.50 mn)   | -INR 974.46               |        -0    | INR 43.80 lakh (4.38 mn) |
|   2023 | INR 2.45 cr (24.54 mn)   | INR 2.75 cr (27.54 mn)   | INR 29.98 lakh (3.00 mn)  |        12.22 | INR 48.70 lakh (4.87 mn) |
|   2024 | INR 2.75 cr (27.55 mn)   | INR 2.90 cr (29.00 mn)   | INR 14.58 lakh (1.46 mn)  |         5.29 | INR 46.50 lakh (4.65 mn) |
|   2025 | INR 2.90 cr (29.05 mn)   | INR 2.87 cr (28.69 mn)   | -INR 3.59 lakh (0.36 mn)  |        -1.24 | INR 48.80 lakh (4.88 mn) |
|   2026 | INR 2.87 cr (28.70 mn)   | INR 2.82 cr (28.18 mn)   | -INR 5.16 lakh (0.52 mn)  |        -1.8  | INR 32.00 lakh (3.20 mn) |

## Charts
- [equity_curves.png](results/c5_c6_simulation/equity_curves.png)
- [annual_returns.png](results/c5_c6_simulation/annual_returns.png)
- [strategy_pnl.png](results/c5_c6_simulation/strategy_pnl.png)
