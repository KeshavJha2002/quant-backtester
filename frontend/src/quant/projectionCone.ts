/**
 * Client-Side Projection Cone Calculations in Pure TypeScript
 */

export function findLastPivot(
  high: number[],
  low: number[],
  pivotLen: number = 10,
  lockToBull: boolean = false
): number | null {
  const n = high.length;
  if (n < pivotLen * 2 + 1) return null;

  for (let i = n - pivotLen - 1; i >= pivotLen; i--) {
    let isPivotLow = true;
    let isPivotHigh = true;

    for (let k = 1; k <= pivotLen; k++) {
      if (low[i] > low[i - k] || low[i] > low[i + k]) isPivotLow = false;
      if (high[i] < high[i - k] || high[i] < high[i + k]) isPivotHigh = false;
    }

    if (lockToBull && isPivotLow) return i;
    if (!lockToBull && (isPivotLow || isPivotHigh)) return i;
  }
  return null;
}

export function calculateSigmaMove(
  currentPrice: number,
  anchorPrice: number,
  currentVol: number,
  barsSinceAnchor: number,
  barsPerYear: number
): number {
  if (anchorPrice <= 0 || currentVol <= 0 || barsSinceAnchor <= 0 || barsPerYear <= 0) {
    return 0.0;
  }
  const timeFraction = barsSinceAnchor / barsPerYear;
  const expectedVolatilityDrift = Math.sqrt(timeFraction) * currentVol;
  if (expectedVolatilityDrift <= 0) return 0.0;

  const actualMovePct = (currentPrice - anchorPrice) / anchorPrice;
  return actualMovePct / expectedVolatilityDrift;
}

export function computeConeSigmaForBar(
  high: number[],
  low: number[],
  close: number[],
  freq: 'D' | 'W' = 'D',
  volLength: number = 20,
  pivotLen: number = 10
): number {
  const n = close.length;
  if (n < 40) return 0.0;

  const barsPerYear = freq === 'W' ? 52.0 : 252.0;

  // Annualized log-return standard deviation
  const logReturns: number[] = [];
  for (let i = 1; i < n; i++) {
    logReturns.push(Math.log(close[i] / close[i - 1]));
  }

  const windowSlice = logReturns.slice(-volLength);
  const mean = windowSlice.reduce((a, b) => a + b, 0) / windowSlice.length;
  const variance = windowSlice.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (windowSlice.length - 1);
  const currentVol = Math.sqrt(variance) * Math.sqrt(barsPerYear);

  if (isNaN(currentVol) || currentVol <= 0) return 0.0;

  const pivotIdx = findLastPivot(high, low, pivotLen, false);
  const anchorIdx = pivotIdx !== null ? pivotIdx : (n - 1);
  const anchorPrice = pivotIdx !== null ? high[anchorIdx] : close[n - 1];
  const barsSince = Math.max(n - 1 - anchorIdx, 1);

  return calculateSigmaMove(close[n - 1], anchorPrice, currentVol, barsSince, barsPerYear);
}
