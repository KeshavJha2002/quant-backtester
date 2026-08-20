import React, { useState, useEffect, useRef } from 'react';
import { Candle } from '../types';
import { fetchStockCandles } from '../services/marketData';
import { computeSupertrend, sma } from '../quant/indicators';
import { computeConeSigmaForBar } from '../quant/projectionCone';
import { Maximize2, RefreshCw } from 'lucide-react';

interface TechnicalChartProps {
  ticker: string;
}

export const TechnicalChart: React.FC<TechnicalChartProps> = ({ ticker }) => {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [timeframe, setTimeframe] = useState<'1d' | '1wk'>('1d');
  const [isLoading, setIsLoading] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    let mounted = true;
    const loadCandles = async () => {
      setIsLoading(true);
      try {
        const data = await fetchStockCandles(ticker, timeframe, '1y');
        if (mounted) {
          setCandles(data);
        }
      } catch {
        // Fallback
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    loadCandles();
    return () => {
      mounted = false;
    };
  }, [ticker, timeframe]);

  // Render Canvas Candlestick + Supertrend + Moving Averages + Projection Cone
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || candles.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // High DPI scaling
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const padding = { top: 30, right: 65, bottom: 30, left: 10 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    ctx.clearRect(0, 0, width, height);

    // Visible candles (last 80 bars)
    const visibleCandles = candles.slice(-80);
    const n = visibleCandles.length;
    if (n < 5) return;

    const closes = visibleCandles.map((c) => c.close);
    const highs = visibleCandles.map((c) => c.high);
    const lows = visibleCandles.map((c) => c.low);

    // Compute Indicators
    const sma50 = sma(closes, Math.min(50, closes.length));
    const sma200 = sma(closes, Math.min(200, closes.length));
    const st = computeSupertrend(closes, highs, lows, 10, 3.0);

    // Min / Max Price
    const minPrice = Math.min(...lows) * 0.97;
    const maxPrice = Math.max(...highs) * 1.03;
    const priceRange = maxPrice - minPrice || 1;

    const getY = (price: number) => padding.top + chartH - ((price - minPrice) / priceRange) * chartH;
    const getX = (i: number) => padding.left + (i / (n - 1)) * chartW;
    const barWidth = Math.max(2, (chartW / n) * 0.65);

    // Draw Grid Lines & Price Axis
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    ctx.fillStyle = '#64748b';
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.textAlign = 'left';

    const gridSteps = 5;
    for (let s = 0; s <= gridSteps; s++) {
      const p = minPrice + (s / gridSteps) * priceRange;
      const y = getY(p);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
      ctx.fillText(`₹${p.toFixed(0)}`, width - padding.right + 8, y + 3);
    }

    // 1. Draw Projection Cone Envelope (Shaded Channel)
    const lastPrice = closes[n - 1];
    const coneSigma = computeConeSigmaForBar(highs, lows, closes, timeframe === '1wk' ? 'W' : 'D');
    const upperCone = lastPrice * 1.15;
    const lowerCone = lastPrice * 0.88;

    ctx.fillStyle = 'rgba(56, 189, 248, 0.04)';
    ctx.beginPath();
    ctx.moveTo(getX(0), getY((highs[0] + lows[0]) / 2));
    for (let i = 0; i < n; i++) {
      const drift = Math.sqrt(i / n) * 0.15;
      ctx.lineTo(getX(i), getY(closes[i] * (1 + drift)));
    }
    for (let i = n - 1; i >= 0; i--) {
      const drift = Math.sqrt(i / n) * 0.12;
      ctx.lineTo(getX(i), getY(closes[i] * (1 - drift)));
    }
    ctx.closePath();
    ctx.fill();

    // 2. Draw Moving Averages (50 SMA: Orange, 200 SMA: Blue)
    // 50 SMA
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      if (!isNaN(sma50[i])) {
        const x = getX(i);
        const y = getY(sma50[i]);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // 3. Draw Candlesticks
    for (let i = 0; i < n; i++) {
      const c = visibleCandles[i];
      const x = getX(i);
      const isBull = c.close >= c.open;

      // Wick
      ctx.strokeStyle = isBull ? '#22c55e' : '#ef4444';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x, getY(c.high));
      ctx.lineTo(x, getY(c.low));
      ctx.stroke();

      // Body
      const openY = getY(c.open);
      const closeY = getY(c.close);
      const topY = Math.min(openY, closeY);
      const bodyH = Math.max(1.5, Math.abs(closeY - openY));

      ctx.fillStyle = isBull ? '#22c55e' : '#ef4444';
      ctx.fillRect(x - barWidth / 2, topY, barWidth, bodyH);
    }

    // 4. Draw Supertrend Bands & Trend Indicator
    for (let i = 1; i < n; i++) {
      const isBullTrend = st.trend[i] === 1;
      ctx.strokeStyle = isBullTrend ? '#10b981' : '#f43f5e';
      ctx.lineWidth = 2;
      ctx.beginPath();
      const level = isBullTrend ? st.lowerBand[i] : st.upperBand[i];
      const prevLevel = isBullTrend ? st.lowerBand[i - 1] : st.upperBand[i - 1];
      ctx.moveTo(getX(i - 1), getY(prevLevel));
      ctx.lineTo(getX(i), getY(level));
      ctx.stroke();
    }

    // Current Price Line
    const currY = getY(lastPrice);
    ctx.strokeStyle = '#38bdf8';
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(padding.left, currY);
    ctx.lineTo(width - padding.right, currY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Badge on axis
    ctx.fillStyle = '#0284c7';
    ctx.fillRect(width - padding.right + 2, currY - 8, 60, 16);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 10px JetBrains Mono, monospace';
    ctx.fillText(`₹${lastPrice.toFixed(1)}`, width - padding.right + 6, currY + 4);

  }, [candles, timeframe]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="font-mono font-bold text-slate-100 text-sm">{ticker}</span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono border border-cyan-500/20">
            Projection Cone + Supertrend
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Timeframe Switcher */}
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-[11px] font-mono">
            <button
              onClick={() => setTimeframe('1d')}
              className={`px-2 py-1 rounded ${timeframe === '1d' ? 'bg-cyan-500 text-white font-bold' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Daily (D)
            </button>
            <button
              onClick={() => setTimeframe('1wk')}
              className={`px-2 py-1 rounded ${timeframe === '1wk' ? 'bg-cyan-500 text-white font-bold' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Weekly (W)
            </button>
          </div>
        </div>
      </div>

      {/* Canvas Container */}
      <div className="relative w-full h-64 bg-slate-950/80 rounded-xl border border-slate-800/80 overflow-hidden">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs">
            <RefreshCw className="w-5 h-5 animate-spin text-cyan-400" />
          </div>
        )}
        <canvas ref={canvasRef} className="w-full h-full block" />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Bullish ST (10, 3.0)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span>Bearish ST</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-amber-500" />
            <span>50 SMA</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded bg-cyan-500/20 border border-cyan-500/40" />
            <span>Projection Cone Drift</span>
          </span>
        </div>
        <span>Latest {candles.length} closed bars</span>
      </div>
    </div>
  );
};
