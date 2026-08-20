import React, { useState } from 'react';
import { X, Wallet, Check } from 'lucide-react';

interface BudgetModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentBudget: number;
  currentCash: number;
  onSave: (budget: number, cash: number) => void;
}

export const BudgetModal: React.FC<BudgetModalProps> = ({
  isOpen,
  onClose,
  currentBudget,
  currentCash,
  onSave,
}) => {
  const [budget, setBudget] = useState(currentBudget.toString());
  const [cash, setCash] = useState(currentCash.toString());

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const b = parseFloat(budget) || 500000;
    const c = parseFloat(cash) || 150000;
    onSave(b, c);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Wallet className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Capital & Budget Settings</h3>
            <p className="text-xs text-slate-400">Configure total account portfolio size and liquid cash</p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Total Account Budget / Capital (₹)
            </label>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              placeholder="500000"
              required
            />
            <p className="text-[11px] text-slate-500 mt-1">Used for 1% risk-based position sizing calculations.</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Available Liquid Cash Balance (₹)
            </label>
            <input
              type="number"
              value={cash}
              onChange={(e) => setCash(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              placeholder="150000"
              required
            />
            <p className="text-[11px] text-slate-500 mt-1">Liquid purchasing power for new stock allocations.</p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium bg-cyan-500 hover:bg-cyan-400 text-white shadow-lg shadow-cyan-500/25 transition"
            >
              <Check className="w-4 h-4" />
              <span>Save Budget</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
