import React, { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  Target,
  Plus,
  Trash2,
  Download,
  Upload,
  ChevronRight,
  Sparkles,
  Info,
  Search,
} from 'lucide-react';
import { PositionEvaluation } from '../types';
import { TechnicalChart } from './TechnicalChart';

interface PortfolioViewProps {
  evaluations: PositionEvaluation[];
  onOpenAddModal: () => void;
  onDeletePosition: (ticker: string) => void;
  onExportCsv: () => void;
  onImportCsv: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const PortfolioView: React.FC<PortfolioViewProps> = ({
  evaluations,
  onOpenAddModal,
  onDeletePosition,
  onExportCsv,
  onImportCsv,
}) => {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(
    evaluations.length > 0 ? evaluations[0].ticker : null
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAction, setFilterAction] = useState<string>('ALL');

  const totalInvested = evaluations.reduce((acc, e) => acc + e.investedValue, 0);
  const totalCurrent = evaluations.reduce((acc, e) => acc + e.currentValue, 0);
  const totalPnlAmt = totalCurrent - totalInvested;
  const totalPnlPct = totalInvested > 0 ? (totalPnlAmt / totalInvested) * 100 : 0;

  const countAdd = evaluations.filter((e) => e.action === 'ADD').length;
  const countHold = evaluations.filter((e) => e.action === 'HOLD').length;
  const countTrim = evaluations.filter((e) => e.action === 'TRIM').length;
  const countExit = evaluations.filter((e) => e.action === 'EXIT').length;

  const filteredEvaluations = evaluations.filter((e) => {
    const matchSearch = e.ticker.toLowerCase().includes(searchQuery.toLowerCase());
    const matchAction = filterAction === 'ALL' || e.action === filterAction;
    return matchSearch && matchAction;
  });

  const selectedEvaluation =
    evaluations.find((e) => e.ticker === selectedTicker) || (evaluations.length > 0 ? evaluations[0] : null);

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'ADD':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            ADD / PYRAMID
          </span>
        );
      case 'HOLD':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            HOLD
          </span>
        );
      case 'TRIM':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            TRIM GAINS
          </span>
        );
      case 'EXIT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            EXIT / STOP
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl">
          <span className="text-xs text-slate-400 font-medium">Total Invested Capital</span>
          <div className="text-xl font-bold font-mono text-slate-100 mt-1">
            ₹{totalInvested.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
          <span className="text-[11px] text-slate-500">{evaluations.length} Active Holdings</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl">
          <span className="text-xs text-slate-400 font-medium">Current Portfolio Value</span>
          <div className="text-xl font-bold font-mono text-slate-100 mt-1">
            ₹{totalCurrent.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
          <span className="text-[11px] text-slate-500">Live mark-to-market</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl">
          <span className="text-xs text-slate-400 font-medium">Total Unrealized P&L</span>
          <div
            className={`text-xl font-bold font-mono mt-1 flex items-center gap-1.5 ${
              totalPnlAmt >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {totalPnlAmt >= 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
            <span>
              {totalPnlAmt >= 0 ? '+' : ''}₹{totalPnlAmt.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
            </span>
          </div>
          <span className={`text-[11px] font-mono font-semibold ${totalPnlPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
          </span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-2xl">
          <span className="text-xs text-slate-400 font-medium">4-State Action Summary</span>
          <div className="flex items-center gap-2 mt-2 font-mono text-xs font-bold">
            <span className="text-emerald-400">🟢 {countAdd}</span>
            <span className="text-cyan-400">⚪ {countHold}</span>
            <span className="text-amber-400">🟡 {countTrim}</span>
            <span className="text-rose-400">🔴 {countExit}</span>
          </div>
          <span className="text-[11px] text-slate-500">Multi-timeframe signals</span>
        </div>
      </div>

      {/* Action Header with Search & Filters */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search ticker..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl pl-9 pr-3.5 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center bg-slate-950 p-0.5 rounded-xl border border-slate-800 text-[11px]">
            {['ALL', 'ADD', 'HOLD', 'TRIM', 'EXIT'].map((act) => (
              <button
                key={act}
                onClick={() => setFilterAction(act)}
                className={`px-2.5 py-1 rounded-lg font-medium transition ${
                  filterAction === act
                    ? 'bg-slate-800 text-cyan-400 font-bold shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {act}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          <label className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 cursor-pointer transition">
            <Upload className="w-3.5 h-3.5" />
            <span>Import CSV</span>
            <input type="file" accept=".csv" onChange={onImportCsv} className="hidden" />
          </label>

          <button
            onClick={onExportCsv}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          <button
            onClick={onOpenAddModal}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-medium bg-cyan-500 hover:bg-cyan-400 text-white shadow-lg shadow-cyan-500/25 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add Holding</span>
          </button>
        </div>
      </div>

      {/* Main Table + Reasoning Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Holdings Table */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase font-mono text-[10px]">
                <tr>
                  <th className="py-3 px-3.5">Action</th>
                  <th className="py-3 px-3">Ticker</th>
                  <th className="py-3 px-3 text-right">Shares</th>
                  <th className="py-3 px-3 text-right">Avg Price</th>
                  <th className="py-3 px-3 text-right">Current</th>
                  <th className="py-3 px-3 text-right">P&L (%)</th>
                  <th className="py-3 px-3 text-right">Sigma</th>
                  <th className="py-3 px-3 text-right">Stop Loss</th>
                  <th className="py-3 px-3 text-center">Score</th>
                  <th className="py-3 px-3 text-center"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredEvaluations.map((ev) => {
                  const isSelected = selectedTicker === ev.ticker;
                  return (
                    <tr
                      key={ev.ticker}
                      onClick={() => setSelectedTicker(ev.ticker)}
                      className={`cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-cyan-500/10 border-l-2 border-l-cyan-400'
                          : 'hover:bg-slate-850/60'
                      }`}
                    >
                      <td className="py-3.5 px-3.5">{getActionBadge(ev.action)}</td>
                      <td className="py-3.5 px-3 font-bold text-slate-100">
                        {ev.ticker.replace('.NS', '')}
                      </td>
                      <td className="py-3.5 px-3 text-right text-slate-300">{ev.quantity}</td>
                      <td className="py-3.5 px-3 text-right text-slate-400">
                        ₹{ev.avgBuyPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-3 text-right font-bold text-slate-100">
                        ₹{ev.currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </td>
                      <td
                        className={`py-3.5 px-3 text-right font-bold ${
                          ev.pnlPercent >= 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {ev.pnlPercent >= 0 ? '+' : ''}
                        {ev.pnlPercent.toFixed(1)}%
                      </td>
                      <td
                        className={`py-3.5 px-3 text-right font-medium ${
                          ev.dailySigma <= 0 ? 'text-cyan-400' : 'text-slate-300'
                        }`}
                      >
                        {ev.dailySigma >= 0 ? '+' : ''}
                        {ev.dailySigma.toFixed(2)}σ
                      </td>
                      <td className="py-3.5 px-3 text-right text-amber-400/90">
                        ₹{ev.suggestedStopLoss.toLocaleString('en-IN', { maximumFractionDigits: 1 })}
                      </td>
                      <td className="py-3.5 px-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                            ev.healthScore >= 70
                              ? 'bg-emerald-500/10 text-emerald-400'
                              : ev.healthScore >= 50
                              ? 'bg-cyan-500/10 text-cyan-400'
                              : 'bg-rose-500/10 text-rose-400'
                          }`}
                        >
                          {Math.round(ev.healthScore)}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeletePosition(ev.ticker);
                          }}
                          className="p-1 text-slate-500 hover:text-rose-400 transition"
                          title="Remove holding"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Holding Detailed Structural Reasoning Drawer */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex flex-col justify-between space-y-4">
          {selectedEvaluation ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                    <span>{selectedEvaluation.ticker}</span>
                    <span className="text-xs font-mono font-normal text-slate-400">
                      ({selectedEvaluation.holdingDays}d holding)
                    </span>
                  </h3>
                  <span className="text-xs text-slate-400">Position Health & Rationale</span>
                </div>
                {getActionBadge(selectedEvaluation.action)}
              </div>

              {/* Recommendation Callout */}
              <div
                className={`p-3.5 rounded-xl border text-xs leading-relaxed ${
                  selectedEvaluation.action === 'ADD'
                    ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-200'
                    : selectedEvaluation.action === 'EXIT'
                    ? 'bg-rose-950/30 border-rose-500/30 text-rose-200'
                    : selectedEvaluation.action === 'TRIM'
                    ? 'bg-amber-950/30 border-amber-500/30 text-amber-200'
                    : 'bg-cyan-950/30 border-cyan-500/30 text-cyan-200'
                }`}
              >
                <div className="font-bold flex items-center gap-1.5 mb-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Strategic Decision: {selectedEvaluation.action}</span>
                </div>
                <p>{selectedEvaluation.reasoningSummary}</p>
              </div>

              {/* Dynamic Targets & Stop Grid */}
              <div className="grid grid-cols-2 gap-3 font-mono text-xs">
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase flex items-center gap-1">
                    <ShieldAlert className="w-3 h-3 text-rose-400" />
                    Trailing Stop
                  </span>
                  <div className="text-sm font-bold text-rose-400 mt-1">
                    ₹{selectedEvaluation.suggestedStopLoss.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase flex items-center gap-1">
                    <Target className="w-3 h-3 text-cyan-400" />
                    Target (+2.0σ)
                  </span>
                  <div className="text-sm font-bold text-cyan-400 mt-1">
                    ₹{selectedEvaluation.suggestedTargetPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                  </div>
                </div>
              </div>

              {/* Key Structural Signals */}
              <div className="space-y-1.5 pt-2">
                <h4 className="text-xs font-semibold text-slate-300 flex items-center gap-1">
                  <Info className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Structural Patterns & Risk Notes:</span>
                </h4>
                <ul className="space-y-1 text-xs text-slate-400 leading-normal">
                  {selectedEvaluation.structuralDetails.map((d, i) => (
                    <li key={i} className="flex items-start gap-1.5">
                      <ChevronRight className="w-3 h-3 text-cyan-400 shrink-0 mt-0.5" />
                      <span>{d}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Embedded Technical Chart */}
              <div className="pt-2">
                <TechnicalChart ticker={selectedEvaluation.ticker} />
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500 text-xs">
              Select a position to view structural reasoning.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
