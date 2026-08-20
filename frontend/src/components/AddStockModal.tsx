import React, { useState, useEffect } from 'react';
import { X, Plus, Sparkles } from 'lucide-react';
import { Holding } from '../types';
import { fetchStockCandles } from '../services/marketData';
import { calculatePositionSize } from '../quant/sizer';

interface AddStockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddHolding: (holding: Holding) => void;
  totalBudget: number;
  availableCash: number;
  initialTicker?: string;
}

export const AddStockModal: React.FC<AddStockModalProps> = ({
  isOpen,
  onClose,
  onAddHolding,
  totalBudget,
  availableCash,
  initialTicker = '',
}) => {
  const [ticker, setTicker] = useState(initialTicker);
  const [quantity, setQuantity] = useState('10');
  const [buyPrice, setBuyPrice] = useState('100');
  const [notes, setNotes] = useState('C7 Quantum ST');
  const [horizon, setHorizon] = useState('Positional (1-6m)');
  const [isAutoSizing, setIsAutoSizing] = useState(false);
  const [suggestedShares, setSuggestedShares] = useState<number | null>(null);

  useEffect(() => {
    if (initialTicker) {
      setTicker(initialTicker);
    }
  }, [initialTicker]);

  useEffect(() => {
    if (!isOpen || !ticker.trim()) return;

    let mounted = true;
    const computeAutoSizing = async () => {
      const formatted = ticker.trim().toUpperCase();
      const normTicker = formatted.endsWith('.NS') ? formatted : `${formatted}.NS`;
      setIsAutoSizing(true);
      try {
        const candles = await fetchStockCandles(normTicker, '1d', '1y');
        if (!mounted || candles.length === 0) return;

        const latestClose = candles[candles.length - 1].close;
        setBuyPrice(latestClose.toFixed(2));

        const rec = calculatePositionSize(
          normTicker,
          candles,
          totalBudget,
          availableCash,
          horizon,
          1.0
        );
        setSuggestedShares(rec.recommendedShares);
        setQuantity(rec.recommendedShares.toString());
      } catch {
        // Fallback
      } finally {
        if (mounted) setIsAutoSizing(false);
      }
    };

    const timer = setTimeout(computeAutoSizing, 400);
    return () => {
      mounted = false;
      clearTimeout(timer);
    };
  }, [ticker, horizon, totalBudget, availableCash, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formatted = ticker.trim().toUpperCase();
    const normTicker = formatted.endsWith('.NS') ? formatted : `${formatted}.NS`;
    const qty = parseInt(quantity, 10) || 1;
    const price = parseFloat(buyPrice) || 100;

    onAddHolding({
      ticker: normTicker,
      quantity: qty,
      avgBuyPrice: price,
      buyDate: new Date().toISOString().split('T')[0],
      notes,
    });
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
          <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Plus className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Add Stock Holding</h3>
            <p className="text-xs text-slate-400">Add position to track live 4-state decisions</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Ticker Symbol (e.g. RELIANCE.NS, PETRONET.NS)
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              placeholder="PETRONET.NS"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Target Holding Horizon
            </label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="Swing (1-4w)">Swing Trade (1–4 Weeks, Tight 1.8x ATR Stop)</option>
              <option value="Positional (1-6m)">Positional Trend (1–6 Months, 2.5x ATR Stop)</option>
              <option value="Long-Term (>6m)">Long-Term Compounder (6+ Months, 3.5x ATR Stop)</option>
            </select>
          </div>

          {suggestedShares !== null && (
            <div className="p-3 bg-cyan-950/40 border border-cyan-500/30 rounded-xl text-xs flex items-center justify-between text-cyan-300">
              <span className="flex items-center gap-1.5 font-medium">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>Auto Sizer Recommended:</span>
              </span>
              <span className="font-mono font-bold text-cyan-200">{suggestedShares} Shares</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Quantity (Shares)
              </label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                min="1"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Avg Buy Price (₹)
              </label>
              <input
                type="number"
                step="0.05"
                value={buyPrice}
                onChange={(e) => setBuyPrice(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
                min="0.1"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Notes / Setup Tag
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
              placeholder="e.g. C7 Supertrend Pullback Buy"
            />
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
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-500/25 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Save to Portfolio</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
