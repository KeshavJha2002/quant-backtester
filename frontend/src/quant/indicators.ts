/**
 * Client-Side Quantitative Indicators in Pure TypeScript
 */

export function trueRange(high: number[], low: number[], close: number[]): number[] {
  const n = close.length;
  const tr = new Array<number>(n);
  tr[0] = high[0] - low[0];
  for (let i = 1; i < n; i++) {
    const hl = high[i] - low[i];
    const hc = Math.abs(high[i] - close[i - 1]);
    const lc = Math.abs(low[i] - close[i - 1]);
    tr[i] = Math.max(hl, hc, lc);
  }
  return tr;
}

export function rma(values: number[], length: number): number[] {
  const n = values.length;
  const out = new Array<number>(n);
  if (n === 0) return out;

  const alpha = 1.0 / length;
  let sum = 0;
  for (let i = 0; i < Math.min(length, n); i++) {
    sum += values[i];
    out[i] = sum / (i + 1);
  }

  for (let i = length; i < n; i++) {
    out[i] = alpha * values[i] + (1 - alpha) * out[i - 1];
  }
  return out;
}

export function sma(values: number[], length: number): number[] {
  const n = values.length;
  const out = new Array<number>(n);
  let sum = 0;
  for (let i = 0; i < n; i++) {
    sum += values[i];
    if (i >= length) {
      sum -= values[i - length];
      out[i] = sum / length;
    } else {
      out[i] = sum / (i + 1);
    }
  }
  return out;
}

export function atr(high: number[], low: number[], close: number[], length: number = 14): number[] {
  const tr = trueRange(high, low, close);
  return rma(tr, length);
}

export interface SupertrendResult {
  trend: number[]; // 1 for Bullish, -1 for Bearish
  upperBand: number[];
  lowerBand: number[];
}

export function computeSupertrend(
  close: number[],
  high: number[],
  low: number[],
  length: number = 10,
  multiplier: number = 3.0
): SupertrendResult {
  const n = close.length;
  const atrArr = atr(high, low, close, length);
  const trend = new Array<number>(n).fill(1);
  const upperBand = new Array<number>(n).fill(0);
  const lowerBand = new Array<number>(n).fill(0);

  let prevUpper = 0;
  let prevLower = 0;
  let prevTrend = 1;

  for (let i = 0; i < n; i++) {
    const hl2 = (high[i] + low[i]) / 2.0;
    const basicUpper = hl2 + multiplier * atrArr[i];
    const basicLower = hl2 - multiplier * atrArr[i];

    let currUpper = basicUpper;
    let currLower = basicLower;

    if (i > 0) {
      currLower = (basicLower > prevLower || close[i - 1] < prevLower) ? basicLower : prevLower;
      currUpper = (basicUpper < prevUpper || close[i - 1] > prevUpper) ? basicUpper : prevUpper;
    }

    let currTrend = prevTrend;
    if (currTrend === 1 && close[i] < currLower) {
      currTrend = -1;
    } else if (currTrend === -1 && close[i] > currUpper) {
      currTrend = 1;
    }

    trend[i] = currTrend;
    upperBand[i] = currUpper;
    lowerBand[i] = currLower;

    prevUpper = currUpper;
    prevLower = currLower;
    prevTrend = currTrend;
  }

  return { trend, upperBand, lowerBand };
}

export function computeTripleSupertrend(
  close: number[],
  high: number[],
  low: number[]
): [number[], number[], number[]] {
  const st1 = computeSupertrend(close, high, low, 10, 1.0);
  const st2 = computeSupertrend(close, high, low, 11, 2.0);
  const st3 = computeSupertrend(close, high, low, 12, 3.0);
  return [st1.trend, st2.trend, st3.trend];
}

export function computeADX(high: number[], low: number[], close: number[], length: number = 14): number {
  const n = close.length;
  if (n < length * 2) return 20.0;

  const upMove = new Array<number>(n).fill(0);
  const downMove = new Array<number>(n).fill(0);

  for (let i = 1; i < n; i++) {
    const up = high[i] - high[i - 1];
    const down = low[i - 1] - low[i];
    upMove[i] = (up > down && up > 0) ? up : 0;
    downMove[i] = (down > up && down > 0) ? down : 0;
  }

  const tr = trueRange(high, low, close);
  const trSmooth = rma(tr, length);
  const plusDmSmooth = rma(upMove, length);
  const minusDmSmooth = rma(downMove, length);

  const dx = new Array<number>(n).fill(0);
  for (let i = 0; i < n; i++) {
    const plusDi = trSmooth[i] > 0 ? (100.0 * plusDmSmooth[i]) / trSmooth[i] : 0;
    const minusDi = trSmooth[i] > 0 ? (100.0 * minusDmSmooth[i]) / trSmooth[i] : 0;
    const denom = plusDi + minusDi;
    dx[i] = denom > 0 ? (100.0 * Math.abs(plusDi - minusDi)) / denom : 0;
  }

  const adxArr = rma(dx, length);
  const lastVal = adxArr[adxArr.length - 1];
  return isNaN(lastVal) ? 20.0 : lastVal;
}
