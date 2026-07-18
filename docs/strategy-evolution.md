# List of all strategies and their combinations

## Standalone Strategies

1) tema_macd [D and W]
2) trend_supertrend [D and W]
3) projection_cone [D and W]

## Combinations Strategies

1) tema_macd [D in W]
2) trend_supertrend [D in W]
3) tema_macd [D in W] + projection_cone [D]
4) trend_supertrend [D in W] + projection_cone [D] - [dropped]
5) tema_macd [W] + projection_cone [W]
6) trend_supertrend [W] + projection_cone [W]

## Active Strategy as of [09/05/2025]

- Strategy 3 for Daily timeframe
  - N250 > N150 > N150
  - N250:
    - Priority Order: only -ve \(\sigma \) :: [<-3\(\sigma \)] && [-3\(\sigma \) to -2\(\sigma \)] && [-2\(\sigma \) to -1\(\sigma \)]
  - N150:
    - Priority Order: only -ve \(\sigma \) :: [<-3\(\sigma \)] && [-3\(\sigma \) to -2\(\sigma \)] && [-2\(\sigma \) to -1\(\sigma \)]
  - N50:
    - Priority Order: only -ve \(\sigma \) :: < -3\(\sigma \)
- Strategy 5 for Weekly timeframe
  - N250 > N150 > N50
  - N250:
    - Priority Order: -ve to +ve \(\sigma \)
  - N150:
    - Priority Order: -ve to +ve \(\sigma \)
  - N50:
    - Priority Order: -ve to +ve \(\sigma \) :: only -ve zones.

## Test Run

python3 scripts/run_backtests.py --mode=combination --strategy=3,4 --universe=N50 --range=40,49 --chunk-size=5 --max-workers=4 --min-negative-sigma=-0.68
python3 scripts/run_strategies.py --mode=combination --strategy=5,6 --min-negative-sigma=2.0
python3 scripts/run_backtests.py --mode=combination --strategy=4 --universe=N150 --range=0,149 --chunk-size=2 --max-workers=2 --min-negative-sigma=-0.68

python3 scripts/run_tw_combinations.py --mode=combination --strategy c5,c6 --cone-threshold 2.0 --refresh-data
