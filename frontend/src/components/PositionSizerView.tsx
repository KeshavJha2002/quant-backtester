import React, { useState, useEffect } from 'react';
import {
  Sliders,
  ShieldAlert,
  Target,
  Sparkles,
  Plus,
  Info,
  CheckCircle,
} from 'lucide-react';
import { SizingRecommendation } from '../types';
import { fetchStockCandles } from '../services/marketData';
import { calculatePositionSize } from '../quant/sizer';

interface PositionSizerViewProps {
  totalBudget: number;
  availableCash: number;
  initialTicker?: string;
  onAddSizedPosition: (ticker: string, quantity: number, price: number, notes: string) => void;
}

export const PositionSizerView: React.FC<PositionSizerViewProps> = ({
  totalBudget,
  availableCash,
  initialTicker = 'PETRONET.NS',
  onAddSizedPosition,
}) => {
  const [ticker, setTicker] = useState(initialTicker);
  const [horizon, setHorizon] = useState('Positional (1-6m)');
  const [riskPct, setRiskPct] = useState('1.0');
  const [maxCapPct, setMaxCapPct] = useState('12.0');
  const [recommendation, setRecommendation] = useState<SizingRecommendation | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [addedSuccess, setAddedSuccess] = useState(false);

  useEffect(() => {
    if (initialTicker) {
      setTicker(initialTicker);
    }
  }, [initialTicker]);

  useEffect(() => {
    if (!ticker.trim()) return;

    let active = true;
    const runSizing = async () => {
      setIsLoading(true);
      const formatted = ticker.trim().toUpperCase();
      const normTicker = formatted.endsWith('.NS') ? formatted : `${formatted}.NS`;

      try {
        const candles = await fetchStockCandles(normTicker, '1d', '1y');
        if (!active || candles.length === 0) return;

        const rec = calculatePositionSize(
          normTicker,
          candles,
          totalBudget,
          availableCash,
          horizon,
          parseFloat(riskPct) || 1.0,
          parseFloat(maxCapPct) || 12.0
        );

        setRecommendation(rec);
      } catch {
        // Handle error
      } finally {
        if (active) setIsLoading(false);
      }
    };

    const debounce = setTimeout(runSizing, 300);
    return () => {
      active = false;
      clearTimeout(debounce);
    };
  }, [ticker, horizon, riskPct, maxCapPct, totalBudget, availableCash]);

  const handleAddPosition = () => {
    if (!recommendation || recommendation.recommendedShares <= 0) return;
    onAddSizedPosition(
      recommendation.ticker,
      recommendation.recommendedShares,
      recommendation.currentPrice,
      `Horizon: ${horizon} | Stop: ₹${recommendation.suggestedStopLoss.toFixed(1)}`
    );
    setAddedSuccess(true);
    setTimeout(() => setAddedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">Holding-Period Position Sizer</h2>
            <p className="text-xs text-slate-400">
              Mathematically sizes stock quantity using ATR volatility, holding horizon, and 1% risk rule
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sizing Controls */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
          <h3 className="text-xs font-semibold uppercase text-slate-400 font-mono tracking-wider">
            Trade & Horizon Parameters
          </h3>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Stock Ticker Symbol
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="PETRONET.NS"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Target Holding Horizon
            </label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-sans"
            >
              <option value="Swing (1-4w)">Swing Trade (1–4 Weeks, Tight 1.8x ATR Stop)</option>
              <option value="Positional (1-6m)">Positional Trend (1–6 Months, 2.5x ATR Stop)</option>
              <option value="Long-Term (>6m)">Long-Term Compounder (6+ Months, 3.5x ATR Stop)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Risk Per Trade (%)
              </label>
              <input
                type="number"
                step="0.1"
                min="0.2"
                max="3.0"
                value={riskPct}
                onChange={(e) => setRiskPct(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Max Stock Cap (%)
              </label>
              <input
                type="number"
                step="1"
                min="5"
                max="25"
                value={maxCapPct}
                onChange={(e) => setMaxCapPct(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 text-xs text-slate-500 space-y-1">
            <div className="flex justify-between">
              <span>Account Budget:</span>
              <span className="font-mono text-slate-300">
                ₹{totalBudget.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Available Cash:</span>
              <span className="font-mono text-emerald-400">
                ₹{availableCash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            </div>
          </div>
        </div>

        {/* Results Card */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col justify-between">
          {recommendation ? (
            <div className="space-y-5">
              {/* Highlight Pill */}
              <div className="bg-gradient-to-r from-cyan-950/40 to-blue-950/40 border border-cyan-500/30 p-4 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                  <span className="text-xs text-cyan-400 font-mono font-semibold uppercase">
                    Mathematically Optimal Allocation
                  </span>
                  <div className="text-3xl font-bold font-mono text-slate-100 mt-0.5">
                    {recommendation.recommendedShares} Shares
                    <span className="text-sm font-normal text-slate-400 ml-2">
                      @ ₹{recommendation.currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>

                <button
                  onClick={handleAddPosition}
                  disabled={recommendation.recommendedShares <= 0}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-xs bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-500/25 transition disabled:opacity-50"
                >
                  {addedSuccess ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      <span>Added to Portfolio!</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      <span>Add This Position</span>
                    </>
                  )}
                </button>
              </div>

              {/* 4 Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Total Capital</span>
                  <span className="text-sm font-bold text-slate-100 mt-1 block">
                    ₹{recommendation.totalInvestmentAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                  <span className="text-[10px] text-slate-500">
                    {recommendation.portfolioAllocationPct.toFixed(1)}% Weight
                  </span>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block flex items-center gap-1">
                    <ShieldAlert className="w-3 h-3 text-rose-400" />
                    Stop Floor
                  </span>
                  <span className="text-sm font-bold text-rose-400 mt-1 block">
                    ₹{recommendation.suggestedStopLoss.toLocaleString('en-IN', { maximumFractionDigits: 1 })}
                  </span>
                  <span className="text-[10px] text-rose-500 font-semibold">
                    -{recommendation.stopDistancePct.toFixed(1)}% Distance
                  </span>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block flex items-center gap-1">
                    <Target className="w-3 h-3 text-cyan-400" />
                    Cone Target
                  </span>
                  <span className="text-sm font-bold text-cyan-400 mt-1 block">
                    ₹{recommendation.targetPrice.toLocaleString('en-IN', { maximumFractionDigits: 1 })}
                  </span>
                  <span className="text-[10px] text-cyan-500 font-semibold">
                    +{recommendation.upsidePotentialPct.toFixed(1)}% Upside
                  </span>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase block">Risk/Reward</span>
                  <span className="text-sm font-bold text-emerald-400 mt-1 block">
                    {recommendation.riskRewardRatio.toFixed(2)}x
                  </span>
                  <span className="text-[10px] text-slate-500">
                    ₹{recommendation.capitalAtRiskAmount.toFixed(0)} at risk
                  </span>
                </div>
              </div>

              {/* Sizing Rationale & Risk Notes */}
              <div className="space-y-2">
                <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs leading-relaxed text-slate-300 font-sans">
                  <div className="font-bold text-slate-100 flex items-center gap-1.5 mb-1">
                    <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Quantitative Sizing Verdict</span>
                  </div>
                  <p>{recommendation.sizingRationale}</p>
                </div>

                <div className="space-y-1">
                  {recommendation.riskNotes.map((note, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-xs text-slate-400">
                      <Info className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span>{note}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-16 text-xs text-slate-500">
              {isLoading ? 'Calculating optimal position sizing...' : 'Enter a stock ticker to calculate position sizing.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
