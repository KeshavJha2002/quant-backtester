import React from 'react';
import {
  Activity,
  Compass,
  PieChart,
  RefreshCw,
  Scale,
  Sliders,
  Wallet,
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  totalBudget: number;
  currentValue: number;
  cashBalance: number;
  onOpenBudgetModal: () => void;
  onRefreshData: () => void;
  isRefreshing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  totalBudget,
  currentValue,
  cashBalance,
  onOpenBudgetModal,
  onRefreshData,
  isRefreshing,
}) => {
  const utilPct = totalBudget > 0 ? (currentValue / totalBudget) * 100 : 0;

  return (
    <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-4 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-xl text-white shadow-lg shadow-cyan-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-slate-100 flex items-center gap-2">
              <span>QUANTUM</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 font-mono border border-cyan-500/20">
                TERMINAL
              </span>
            </h1>
            <p className="text-xs text-slate-400">Multi-Timeframe Portfolio & Decision Engine</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-xl border border-slate-800/80">
          <button
            onClick={() => setActiveTab('portfolio')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'portfolio'
                ? 'bg-cyan-500 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <PieChart className="w-4 h-4" />
            <span>Portfolio</span>
          </button>
          <button
            onClick={() => setActiveTab('screener')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'screener'
                ? 'bg-cyan-500 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Compass className="w-4 h-4" />
            <span>Screener</span>
          </button>
          <button
            onClick={() => setActiveTab('sizer')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'sizer'
                ? 'bg-cyan-500 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>Position Sizer</span>
          </button>
          <button
            onClick={() => setActiveTab('tiebreaker')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'tiebreaker'
                ? 'bg-cyan-500 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Scale className="w-4 h-4" />
            <span>Tie-Breaker</span>
          </button>
          <button
            onClick={() => setActiveTab('charts')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'charts'
                ? 'bg-cyan-500 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Charts</span>
          </button>
        </nav>

        {/* Budget Pill & Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onOpenBudgetModal}
            className="flex items-center gap-2.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-750 border border-slate-700/80 rounded-xl text-xs transition-all"
            title="Click to edit Total Budget and Cash Balance"
          >
            <Wallet className="w-4 h-4 text-cyan-400" />
            <div className="text-left font-mono">
              <span className="text-slate-400 block text-[10px] uppercase">Budget</span>
              <span className="font-semibold text-slate-100">
                ₹{totalBudget.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            </div>
            <div className="h-6 w-[1px] bg-slate-700 mx-0.5" />
            <div className="text-left font-mono">
              <span className="text-slate-400 block text-[10px] uppercase">Cash</span>
              <span className="text-emerald-400 font-semibold">
                ₹{cashBalance.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
            </div>
          </button>

          <button
            onClick={onRefreshData}
            disabled={isRefreshing}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all disabled:opacity-50"
            title="Refresh live market prices and indicators"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
