import React, { useState } from 'react';
import { X, Plus, Minus, Edit3, ArrowRight, Wallet, CheckCircle2, TrendingUp, TrendingDown } from 'lucide-react';
import { Holding, PositionEvaluation } from '../types';

interface AdjustPositionModalProps {
  isOpen: boolean;
  onClose: () => void;
  evaluation: PositionEvaluation | null;
  onAdjustPosition: (
    ticker: string,
    newQuantity: number,
    newAvgPrice: number,
    cashDelta: number,
    notes?: string
  ) => void;
  availableCash: number;
}

export const AdjustPositionModal: React.FC<AdjustPositionModalProps> = ({
  isOpen,
  onClose,
  evaluation,
  onAdjustPosition,
  availableCash,
}) => {
  const [mode, setMode] = useState<'ADD' | 'REDUCE' | 'EDIT'>('ADD');

  // Add Mode State
  const [addQty, setAddQty] = useState('10');
  const [addPrice, setAddPrice] = useState(evaluation ? evaluation.currentPrice.toFixed(2) : '100');

  // Reduce Mode State
  const [reduceQty, setReduceQty] = useState('5');
  const [reducePrice, setReducePrice] = useState(evaluation ? evaluation.currentPrice.toFixed(2) : '100');

  // Edit Mode State
  const [editQty, setEditQty] = useState(evaluation ? evaluation.quantity.toString() : '10');
  const [editPrice, setEditPrice] = useState(evaluation ? evaluation.avgBuyPrice.toFixed(2) : '100');
  const [editNotes, setEditNotes] = useState('C7 Quantum ST');

  // Sync state when evaluation changes
  React.useEffect(() => {
    if (evaluation) {
      setAddPrice(evaluation.currentPrice.toFixed(2));
      setReducePrice(evaluation.currentPrice.toFixed(2));
      setEditQty(evaluation.quantity.toString());
      setEditPrice(evaluation.avgBuyPrice.toFixed(2));
      setReduceQty(Math.max(1, Math.floor(evaluation.quantity * 0.5)).toString());
    }
  }, [evaluation]);

  if (!isOpen || !evaluation) return null;

  // Add Calculation
  const parsedAddQty = parseInt(addQty, 10) || 0;
  const parsedAddPrice = parseFloat(addPrice) || evaluation.currentPrice;
  const newTotalQty = evaluation.quantity + parsedAddQty;
  const addedCost = parsedAddQty * parsedAddPrice;
  const newWeightedAvg =
    newTotalQty > 0
      ? (evaluation.quantity * evaluation.avgBuyPrice + addedCost) / newTotalQty
      : evaluation.avgBuyPrice;

  // Reduce Calculation
  const parsedReduceQty = Math.min(evaluation.quantity, Math.max(1, parseInt(reduceQty, 10) || 1));
  const parsedReducePrice = parseFloat(reducePrice) || evaluation.currentPrice;
  const remainingQty = Math.max(0, evaluation.quantity - parsedReduceQty);
  const capitalReturned = parsedReduceQty * parsedReducePrice;
  const realizedPnlAmt = parsedReduceQty * (parsedReducePrice - evaluation.avgBuyPrice);
  const realizedPnlPct =
    evaluation.avgBuyPrice > 0 ? ((parsedReducePrice - evaluation.avgBuyPrice) / evaluation.avgBuyPrice) * 100 : 0;

  // Handlers
  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (parsedAddQty <= 0) return;
    // Cash delta is negative (deducted from cash)
    onAdjustPosition(
      evaluation.ticker,
      newTotalQty,
      newWeightedAvg,
      -addedCost,
      `Pyramided +${parsedAddQty} shares @ ₹${parsedAddPrice.toFixed(2)}`
    );
    onClose();
  };

  const handleReduceSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (parsedReduceQty <= 0) return;
    // Cash delta is positive (returned to liquid cash)
    onAdjustPosition(
      evaluation.ticker,
      remainingQty,
      evaluation.avgBuyPrice,
      capitalReturned,
      `Trimmed -${parsedReduceQty} shares @ ₹${parsedReducePrice.toFixed(2)}`
    );
    onClose();
  };

  const handleDirectEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = parseInt(editQty, 10) || 1;
    const p = parseFloat(editPrice) || evaluation.avgBuyPrice;
    onAdjustPosition(evaluation.ticker, q, p, 0, editNotes);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-slate-100 font-mono">{evaluation.ticker}</h3>
              <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 font-mono">
                CMP: ₹{evaluation.currentPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Current: {evaluation.quantity} shares @ ₹{evaluation.avgBuyPrice.toFixed(2)} (Total: ₹
              {(evaluation.quantity * evaluation.avgBuyPrice).toLocaleString('en-IN', { maximumFractionDigits: 0 })})
            </p>
          </div>
        </div>

        {/* Mode Navigation Tabs */}
        <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 mb-5">
          <button
            onClick={() => setMode('ADD')}
            className={`flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition ${
              mode === 'ADD'
                ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add / Pyramid</span>
          </button>
          <button
            onClick={() => setMode('REDUCE')}
            className={`flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition ${
              mode === 'REDUCE'
                ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Minus className="w-3.5 h-3.5" />
            <span>Reduce / Trim</span>
          </button>
          <button
            onClick={() => setMode('EDIT')}
            className={`flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition ${
              mode === 'EDIT'
                ? 'bg-cyan-500 text-white shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Direct Edit</span>
          </button>
        </div>

        {/* MODE 1: ADD / PYRAMID */}
        {mode === 'ADD' && (
          <form onSubmit={handleAddSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Shares to Add</label>
                <input
                  type="number"
                  min="1"
                  value={addQty}
                  onChange={(e) => setAddQty(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Buy Price (₹)</label>
                <input
                  type="number"
                  step="0.05"
                  value={addPrice}
                  onChange={(e) => setAddPrice(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-emerald-500"
                  required
                />
              </div>
            </div>

            {/* Live Calculation Preview Card */}
            <div className="bg-slate-950/80 border border-emerald-500/30 p-3.5 rounded-xl space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span>Capital Required:</span>
                <span className="text-emerald-400 font-bold">
                  ₹{addedCost.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>New Total Quantity:</span>
                <span className="text-slate-200 font-bold">{newTotalQty} Shares</span>
              </div>
              <div className="flex items-center justify-between text-slate-400 border-t border-slate-800/80 pt-1.5">
                <span>New Average Cost Basis:</span>
                <span className="text-cyan-400 font-bold">
                  ₹{newWeightedAvg.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-500/25 transition"
              >
                <Plus className="w-4 h-4" />
                <span>Confirm Pyramid Buy</span>
              </button>
            </div>
          </form>
        )}

        {/* MODE 2: REDUCE / TRIM */}
        {mode === 'REDUCE' && (
          <form onSubmit={handleReduceSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Quick Trim %</label>
              <div className="grid grid-cols-5 gap-1.5">
                {[
                  { label: '25%', frac: 0.25 },
                  { label: '33%', frac: 0.33 },
                  { label: '50%', frac: 0.5 },
                  { label: '75%', frac: 0.75 },
                  { label: '100% (Exit)', frac: 1.0 },
                ].map((btn) => (
                  <button
                    key={btn.label}
                    type="button"
                    onClick={() => setReduceQty(Math.max(1, Math.round(evaluation.quantity * btn.frac)).toString())}
                    className="py-1.5 rounded-lg text-xs font-mono font-medium bg-slate-950 hover:bg-slate-800 border border-slate-700 text-slate-300 transition"
                  >
                    {btn.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Shares to Sell / Trim</label>
                <input
                  type="number"
                  min="1"
                  max={evaluation.quantity}
                  value={reduceQty}
                  onChange={(e) => setReduceQty(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-amber-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Sell Price (₹)</label>
                <input
                  type="number"
                  step="0.05"
                  value={reducePrice}
                  onChange={(e) => setReducePrice(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-amber-500"
                  required
                />
              </div>
            </div>

            {/* Live Calculation Preview Card */}
            <div className="bg-slate-950/80 border border-amber-500/30 p-3.5 rounded-xl space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span>Capital Returned to Cash:</span>
                <span className="text-emerald-400 font-bold">
                  +₹{capitalReturned.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex items-center justify-between text-slate-400">
                <span>Realized Profit / Loss:</span>
                <span className={`font-bold flex items-center gap-1 ${realizedPnlAmt >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {realizedPnlAmt >= 0 ? '+' : ''}₹{realizedPnlAmt.toFixed(2)} ({realizedPnlPct >= 0 ? '+' : ''}{realizedPnlPct.toFixed(1)}%)
                </span>
              </div>
              <div className="flex items-center justify-between text-slate-400 border-t border-slate-800/80 pt-1.5">
                <span>Remaining Position:</span>
                <span className="text-slate-200 font-bold">
                  {remainingQty} Shares {remainingQty === 0 ? '(Full Exit)' : ''}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/25 transition"
              >
                <Minus className="w-4 h-4" />
                <span>Confirm Trim / Sell</span>
              </button>
            </div>
          </form>
        )}

        {/* MODE 3: DIRECT EDIT */}
        {mode === 'EDIT' && (
          <form onSubmit={handleDirectEditSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Quantity (Shares)</label>
                <input
                  type="number"
                  min="0"
                  value={editQty}
                  onChange={(e) => setEditQty(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Avg Buy Price (₹)</label>
                <input
                  type="number"
                  step="0.05"
                  value={editPrice}
                  onChange={(e) => setEditPrice(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Notes / Tags</label>
              <input
                type="text"
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-500 hover:bg-cyan-400 text-white shadow-lg shadow-cyan-500/25 transition"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Save Changes</span>
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
