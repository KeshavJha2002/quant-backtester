import React, { useState } from 'react';
import { LineChart, Search, Sparkles } from 'lucide-react';
import { TechnicalChart } from './TechnicalChart';
import { NIFTY_50_TICKERS, NIFTY_MIDCAP_150_TICKERS } from '../services/constants';

interface ChartViewProps {
  initialTicker?: string;
}

export const ChartView: React.FC<ChartViewProps> = ({ initialTicker = 'PETRONET.NS' }) => {
  const [ticker, setTicker] = useState(initialTicker);
  const [activeTicker, setActiveTicker] = useState(initialTicker);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) return;
    const formatted = ticker.trim().toUpperCase();
    const norm = formatted.endsWith('.NS') ? formatted : `${formatted}.NS`;
    setActiveTicker(norm);
  };

  const quickPicks = ['PETRONET.NS', 'MOREPENLAB.NS', 'AIIL.NS', 'GLAXO.NS', 'BHARTIARTL.NS', 'ETERNAL.NS', 'HDFCBANK.NS', 'RELIANCE.NS'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <LineChart className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">Interactive Projection Cone Chart</h2>
            <p className="text-xs text-slate-400">
              High-resolution Candlestick charts with Supertrend (10, 3.0), 50 SMA, 200 SMA & Projection Cone bands
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search ticker (e.g. TCS.NS)..."
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-9 pr-3.5 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-white shadow-lg shadow-cyan-500/25 transition"
          >
            Load
          </button>
        </form>
      </div>

      {/* Quick Picks */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-400 flex items-center gap-1 text-[11px]">
          <Sparkles className="w-3 h-3 text-cyan-400" />
          <span>Quick Picks:</span>
        </span>
        {quickPicks.map((pick) => (
          <button
            key={pick}
            onClick={() => {
              setTicker(pick);
              setActiveTicker(pick);
            }}
            className={`px-2.5 py-1 rounded-lg font-mono text-[11px] border transition ${
              activeTicker === pick
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-bold'
                : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            {pick.replace('.NS', '')}
          </button>
        ))}
      </div>

      {/* Chart Canvas */}
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
        <TechnicalChart ticker={activeTicker} />
      </div>
    </div>
  );
};
