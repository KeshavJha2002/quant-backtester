import { Holding } from '../types';
import { INITIAL_HOLDINGS } from './constants';

const KEY_HOLDINGS = 'quantum_holdings_v1';
const KEY_BUDGET = 'quantum_total_budget_v1';
const KEY_CASH = 'quantum_cash_balance_v1';

export function getStoredHoldings(): Holding[] {
  try {
    const raw = localStorage.getItem(KEY_HOLDINGS);
    if (!raw) {
      localStorage.setItem(KEY_HOLDINGS, JSON.stringify(INITIAL_HOLDINGS));
      return INITIAL_HOLDINGS;
    }
    return JSON.parse(raw);
  } catch {
    return INITIAL_HOLDINGS;
  }
}

export function saveHoldings(holdings: Holding[]): void {
  try {
    localStorage.setItem(KEY_HOLDINGS, JSON.stringify(holdings));
  } catch (err) {
    console.error('Failed to save holdings to localStorage:', err);
  }
}

export function addOrUpdateHolding(holding: Holding): Holding[] {
  const current = getStoredHoldings();
  const idx = current.findIndex((h) => h.ticker === holding.ticker);

  if (idx >= 0) {
    const existing = current[idx];
    const totalQty = existing.quantity + holding.quantity;
    const newAvg = totalQty > 0 ? ((existing.quantity * existing.avgBuyPrice) + (holding.quantity * holding.avgBuyPrice)) / totalQty : holding.avgBuyPrice;

    current[idx] = {
      ...existing,
      quantity: totalQty,
      avgBuyPrice: newAvg,
      notes: holding.notes || existing.notes,
      pyramidCount: (existing.pyramidCount || 0) + 1,
    };
  } else {
    current.push(holding);
  }

  saveHoldings(current);
  return current;
}

export function deleteHolding(ticker: string): Holding[] {
  const current = getStoredHoldings();
  const updated = current.filter((h) => h.ticker !== ticker);
  saveHoldings(updated);
  return updated;
}

export function getStoredBudget(): { totalBudget: number; cashBalance: number } {
  try {
    const bRaw = localStorage.getItem(KEY_BUDGET);
    const cRaw = localStorage.getItem(KEY_CASH);
    const totalBudget = bRaw ? parseFloat(bRaw) : 500000;
    const cashBalance = cRaw ? parseFloat(cRaw) : 150000;
    return { totalBudget, cashBalance };
  } catch {
    return { totalBudget: 500000, cashBalance: 150000 };
  }
}

export function saveBudget(totalBudget: number, cashBalance: number): void {
  try {
    localStorage.setItem(KEY_BUDGET, totalBudget.toString());
    localStorage.setItem(KEY_CASH, cashBalance.toString());
  } catch (err) {
    console.error('Failed to save budget to localStorage:', err);
  }
}

export function exportHoldingsCsv(holdings: Holding[]): string {
  const headers = ['ticker', 'quantity', 'avg_buy_price', 'buy_date', 'current_stop_loss', 'target_price', 'notes'];
  const rows = holdings.map((h) => [
    h.ticker,
    h.quantity,
    h.avgBuyPrice,
    h.buyDate || new Date().toISOString().split('T')[0],
    h.stopLoss || 0,
    h.targetPrice || 0,
    `"${(h.notes || '').replace(/"/g, '""')}"`,
  ]);
  return [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
}

export function parseHoldingsCsv(csvText: string): Holding[] {
  const lines = csvText.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length <= 1) return [];

  const holdings: Holding[] = [];
  const header = lines[0].toLowerCase();
  const isHeader = header.includes('ticker');
  const startIdx = isHeader ? 1 : 0;

  for (let i = startIdx; i < lines.length; i++) {
    const cols = lines[i].split(',').map((c) => c.trim().replace(/^"|"$/g, ''));
    if (cols.length < 3) continue;

    const ticker = cols[0].toUpperCase();
    const qty = parseInt(cols[1], 10) || 1;
    const price = parseFloat(cols[2]) || 0;
    const dateStr = cols[3] || new Date().toISOString().split('T')[0];
    const notes = cols[6] || cols[4] || '';

    if (ticker && price > 0) {
      holdings.push({
        ticker: ticker.endsWith('.NS') ? ticker : `${ticker}.NS`,
        quantity: qty,
        avgBuyPrice: price,
        buyDate: dateStr,
        notes,
      });
    }
  }
  return holdings;
}
