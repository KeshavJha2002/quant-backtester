# Combined Results

## Combination Strategy 1

### TEMA-MACD MTF Performance

#### N50

- Trade Count: `5430`
- Avg Return per Trade: `1.12%`
- Win Rate: `42.10%`
- Median Trade Duration: `13.00 days`

#### N150

- Trade Count: `11121`
- Avg Return per Trade: `1.86%`
- Win Rate: `40.81%`
- Median Trade Duration: `13.00 days`

#### N250

- Trade Count: `14755`
- Avg Return per Trade: `2.53%`
- Win Rate: `40.43%`
- Median Trade Duration: `13.00 days`

### Supertrend MTF Performance

#### N50

- Trade Count: `909`
- Avg Return per Trade: `4.92%`
- Win Rate: `47.19%`
- Median Trade Duration: `47.00 days`

#### N150

- Trade Count: `1749`
- Avg Return per Trade: `9.05%`
- Win Rate: `47.23%`
- Median Trade Duration: `54.00 days`

#### N250

- Trade Count: `2239`
- Avg Return per Trade: `12.18%`
- Win Rate: `48.19%`
- Median Trade Duration: `56.00 days`

## Combination Strategy 3

# TEMA-MACD MTF with Projection Cone Filter

Rule:
- `D` fresh buy
- `W` already bullish
- Daily cone sigma deviation `< -1`

## N50

| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |
|---|---|---:|---:|---:|---:|
| N50 | -2σ to -1σ | 499 | 2.65 | 44.69 | ~14.12 |
| N50 | -3σ to -2σ | 44 | 1.43 | 43.18 | ~15.32 |
| N50 | < -3σ | 28 | 4.14 | 42.86 | ~14.82 |
| N50 | excluded | 602 | 1.99 | 45.35 | ~14.11 |

## Total

- Total trades analyzed: `1173`

## N150

| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |
|---|---|---:|---:|---:|---:|
| N150 | -2σ to -1σ | 1418 | 2.78 | 39.63 | ~14.49 |
| N150 | -3σ to -2σ | 187 | 6.72 | 45.45 | ~17.63 |
| N150 | < -3σ | 38 | 4.74 | 44.74 | ~18.63 |
| N150 | excluded | 1396 | 1.72 | 37.97 | ~13.15 |

## Total

- Total trades analyzed: `3039`

## N250

| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |
|---|---|---:|---:|---:|---:|
| N250 | -2σ to -1σ | 1898 | 3.35 | 40.73 | ~14.60 |
| N250 | -3σ to -2σ | 295 | 7.46 | 51.19 | ~19.11 |
| N250 | < -3σ | 75 | 5.64 | 41.33 | ~22.20 |
| N250 | excluded | 1993 | 2.39 | 39.44 | ~13.22 |

## Total

- Total trades analyzed: `4261`

## Combination Strategy 5

### TEMA MACD W + Projection Cone W

#### Universe Summary

- N50 trades: `2348`
- N150 trades: `5014`
- N250 trades: `6564`

| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |
|---|---|---:|---:|---:|---:|
| N50 | +1sigma to +2sigma | 109 | 4.79 | 53.21 | 63.00 |
| N50 | +2sigma to +3sigma | 39 | 3.66 | 43.59 | 56.00 |
| N50 | -1sigma to 0sigma | 1153 | 6.16 | 43.10 | 77.00 |
| N50 | -2sigma to -1sigma | 525 | 11.64 | 47.24 | 98.00 |
| N50 | -3sigma to -2sigma | 56 | 19.95 | 44.64 | 129.50 |
| N50 | 0sigma to +1sigma | 423 | 9.14 | 51.30 | 70.00 |
| N50 | < -3sigma | 37 | 19.76 | 62.16 | 91.00 |
| N50 | > +3sigma | 6 | 9.51 | 50.00 | 77.00 |
| N150 | +1sigma to +2sigma | 194 | 6.77 | 52.58 | 63.00 |
| N150 | +2sigma to +3sigma | 71 | 12.41 | 42.25 | 42.00 |
| N150 | -1sigma to 0sigma | 2229 | 8.41 | 42.98 | 70.00 |
| N150 | -2sigma to -1sigma | 1366 | 10.37 | 42.68 | 98.00 |
| N150 | -3sigma to -2sigma | 232 | 19.28 | 44.83 | 122.50 |
| N150 | 0sigma to +1sigma | 859 | 8.00 | 47.26 | 63.00 |
| N150 | < -3sigma | 44 | 13.86 | 38.64 | 105.00 |
| N150 | > +3sigma | 19 | 4.21 | 47.37 | 56.00 |
| N250 | +1sigma to +2sigma | 248 | 10.78 | 47.98 | 56.00 |
| N250 | +2sigma to +3sigma | 51 | 4.92 | 50.98 | 56.00 |
| N250 | -1sigma to 0sigma | 2718 | 10.59 | 41.83 | 70.00 |
| N250 | -2sigma to -1sigma | 1934 | 11.28 | 41.52 | 98.00 |
| N250 | -3sigma to -2sigma | 395 | 15.44 | 40.76 | 119.00 |
| N250 | 0sigma to +1sigma | 1115 | 13.09 | 45.92 | 63.00 |
| N250 | < -3sigma | 91 | 25.44 | 51.65 | 119.00 |
| N250 | > +3sigma | 12 | 10.94 | 58.33 | 66.50 |

## Combination Strategy 6

### Trend Supertrend W + Projection Cone W

#### Universe Summary

- N50 trades: `448`
- N150 trades: `938`
- N250 trades: `1295`

| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |
|---|---|---:|---:|---:|---:|
| N50 | +1sigma to +2sigma | 4 | 414.84 | 50.00 | 234.50 |
| N50 | -1sigma to 0sigma | 282 | 57.82 | 56.03 | 525.00 |
| N50 | -2sigma to -1sigma | 49 | 120.53 | 63.27 | 532.00 |
| N50 | -3sigma to -2sigma | 6 | 19.56 | 33.33 | 231.00 |
| N50 | 0sigma to +1sigma | 99 | 176.77 | 58.59 | 413.00 |
| N50 | < -3sigma | 8 | 189.20 | 62.50 | 703.50 |
| N150 | +1sigma to +2sigma | 3 | 266.36 | 66.67 | 1043.00 |
| N150 | -1sigma to 0sigma | 596 | 87.90 | 51.68 | 504.00 |
| N150 | -2sigma to -1sigma | 137 | 73.17 | 53.28 | 469.00 |
| N150 | -3sigma to -2sigma | 11 | 43.22 | 63.64 | 609.00 |
| N150 | 0sigma to +1sigma | 186 | 168.47 | 51.08 | 458.50 |
| N150 | < -3sigma | 5 | 23.01 | 40.00 | 336.00 |
| N250 | +1sigma to +2sigma | 5 | 134.58 | 80.00 | 882.00 |
| N250 | -1sigma to 0sigma | 812 | 98.36 | 49.75 | 413.00 |
| N250 | -2sigma to -1sigma | 197 | 83.81 | 50.25 | 476.00 |
| N250 | -3sigma to -2sigma | 15 | 128.98 | 66.67 | 392.00 |
| N250 | 0sigma to +1sigma | 264 | 86.10 | 57.20 | 553.00 |
| N250 | < -3sigma | 2 | 36.05 | 50.00 | 637.00 |
