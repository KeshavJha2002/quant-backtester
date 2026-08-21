import { Candle } from '../types';

interface SnapshotTicker {
  d: Candle[];
  w: Candle[];
}

export interface FetchResult {
  candles: Candle[];
  isLive: boolean;
  lastUpdated: string;
}

let snapshotData: Record<string, SnapshotTicker> | null = null;
let snapshotLoadingPromise: Promise<Record<string, SnapshotTicker>> | null = null;

const memoryCache = new Map<string, { result: FetchResult; timestamp: number }>();
const CACHE_TTL_MS = 2 * 60 * 1000; // 2 minutes for live data

async function loadMarketSnapshot(): Promise<Record<string, SnapshotTicker>> {
  if (snapshotData) return snapshotData;
  if (snapshotLoadingPromise) return snapshotLoadingPromise;

  snapshotLoadingPromise = (async () => {
    try {
      const resp = await fetch('/data/market_snapshot.json');
      if (resp.ok) {
        snapshotData = await resp.json();
        return snapshotData || {};
      }
    } catch {
      // Ignore
    }
    snapshotData = {};
    return snapshotData;
  })();

  return snapshotLoadingPromise;
}

function deterministicSeed(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

export async function fetchStockCandlesWithMeta(
  ticker: string,
  interval: '1d' | '1wk' = '1d',
  range: '1y' | '2y' = '1y',
  forceLive = false
): Promise<FetchResult> {
  const normTicker = ticker.trim().toUpperCase().endsWith('.NS')
    ? ticker.trim().toUpperCase()
    : `${ticker.trim().toUpperCase()}.NS`;

  const cacheKey = `${normTicker}_${interval}_${range}`;
  const cached = memoryCache.get(cacheKey);

  if (!forceLive && cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.result;
  }

  // 1. Attempt Live Yahoo Finance Fetch via multiple CORS gateways
  const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(normTicker)}?interval=${interval}&range=${range}`;
  const proxies = [
    `https://corsproxy.io/?${encodeURIComponent(yahooUrl)}`,
    `https://api.allorigins.win/raw?url=${encodeURIComponent(yahooUrl)}`,
    `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(yahooUrl)}`,
  ];

  for (const proxyUrl of proxies) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000); // 4s timeout per proxy

      const response = await fetch(proxyUrl, {
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) continue;

      const data = await response.json();
      const result = data?.chart?.result?.[0];
      if (!result) continue;

      const timestamps: number[] = result.timestamp || [];
      const quote = result.indicators?.quote?.[0] || {};
      const opens = quote.open || [];
      const highs = quote.high || [];
      const lows = quote.low || [];
      const closes = quote.close || [];
      const volumes = quote.volume || [];

      const candles: Candle[] = [];
      for (let i = 0; i < timestamps.length; i++) {
        if (closes[i] !== null && closes[i] !== undefined && !isNaN(closes[i])) {
          candles.push({
            time: new Date(timestamps[i] * 1000).toISOString().split('T')[0],
            open: opens[i] || closes[i],
            high: highs[i] || closes[i],
            low: lows[i] || closes[i],
            close: closes[i],
            volume: volumes[i] || 100000,
          });
        }
      }

      if (candles.length >= 10) {
        const fetchRes: FetchResult = {
          candles,
          isLive: true,
          lastUpdated: new Date().toLocaleTimeString(),
        };
        memoryCache.set(cacheKey, { result: fetchRes, timestamp: Date.now() });
        return fetchRes;
      }
    } catch {
      // Try next gateway
    }
  }

  // 2. Fallback: Check local bundled verified market snapshot
  const snapshot = await loadMarketSnapshot();
  if (snapshot[normTicker]) {
    const candles = interval === '1wk' ? snapshot[normTicker].w : snapshot[normTicker].d;
    if (candles && candles.length >= 10) {
      const fetchRes: FetchResult = {
        candles,
        isLive: false,
        lastUpdated: 'Snapshot Cache',
      };
      memoryCache.set(cacheKey, { result: fetchRes, timestamp: Date.now() });
      return fetchRes;
    }
  }

  // 3. Fallback: Deterministic simulated curve (offline fallback)
  const fallback = generateDeterministicCandles(normTicker, interval === '1wk' ? 60 : 120);
  const fetchRes: FetchResult = {
    candles: fallback,
    isLive: false,
    lastUpdated: 'Offline Engine',
  };
  memoryCache.set(cacheKey, { result: fetchRes, timestamp: Date.now() });
  return fetchRes;
}

export async function fetchStockCandles(
  ticker: string,
  interval: '1d' | '1wk' = '1d',
  range: '1y' | '2y' = '1y',
  forceLive = false
): Promise<Candle[]> {
  const res = await fetchStockCandlesWithMeta(ticker, interval, range, forceLive);
  return res.candles;
}

function generateDeterministicCandles(ticker: string, count: number): Candle[] {
  let basePrice = 500.0;
  if (ticker.includes('MOREPENLAB')) basePrice = 96.47;
  else if (ticker.includes('GLAXO')) basePrice = 2999.70;
  else if (ticker.includes('HDFCSML250')) basePrice = 185.25;
  else if (ticker.includes('MAHSCOOTER')) basePrice = 13138.00;
  else if (ticker.includes('AIIL')) basePrice = 532.30;
  else if (ticker.includes('CIPLA')) basePrice = 1438.00;
  else if (ticker.includes('BHARTIARTL')) basePrice = 1941.70;
  else if (ticker.includes('MCX')) basePrice = 3126.00;
  else if (ticker.includes('ABBOTINDIA')) basePrice = 26120.00;
  else if (ticker.includes('RALLIS')) basePrice = 212.85;
  else if (ticker.includes('ETERNAL')) basePrice = 327.95;
  else if (ticker.includes('PETRONET')) basePrice = 291.40;
  else {
    const seed = deterministicSeed(ticker);
    basePrice = 100.0 + (seed % 2500);
  }

  const candles: Candle[] = [];
  const seed = deterministicSeed(ticker);
  const now = new Date('2026-08-20T10:00:00Z').getTime();
  const dayMs = 24 * 60 * 60 * 1000;
  let curr = basePrice * 0.90;

  for (let i = count; i >= 0; i--) {
    const wave = Math.sin((i + seed) * 0.15) * 0.018;
    const trend = (count - i) / count * 0.10;
    curr = basePrice * (0.90 + trend + wave);

    const high = curr * 1.012;
    const low = curr * 0.988;
    const open = low + (high - low) * 0.45;
    const vol = 100000 + ((seed * (i + 1)) % 150000);
    const dateStr = new Date(now - i * dayMs).toISOString().split('T')[0];

    candles.push({
      time: dateStr,
      open,
      high,
      low,
      close: curr,
      volume: vol,
    });
  }

  candles[candles.length - 1].close = basePrice;
  return candles;
}
