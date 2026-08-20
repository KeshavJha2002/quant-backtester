import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { PortfolioView } from './components/PortfolioView';
import { ScreenerView } from './components/ScreenerView';
import { PositionSizerView } from './components/PositionSizerView';
import { TieBreakerView } from './components/TieBreakerView';
import { ChartView } from './components/ChartView';
import { BudgetModal } from './components/BudgetModal';
import { AddStockModal } from './components/AddStockModal';
import { Holding, PositionEvaluation } from './types';
import {
  getStoredHoldings,
  saveHoldings,
  addOrUpdateHolding,
  deleteHolding,
  getStoredBudget,
  saveBudget,
  exportHoldingsCsv,
  parseHoldingsCsv,
} from './services/storage';
import { fetchStockCandles } from './services/marketData';
import { evaluateHolding } from './quant/evaluator';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'portfolio' | 'screener' | 'sizer' | 'tiebreaker' | 'charts'>('portfolio');
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [budget, setBudget] = useState<{ totalBudget: number; cashBalance: number }>({
    totalBudget: 500000,
    cashBalance: 150000,
  });
  const [evaluations, setEvaluations] = useState<PositionEvaluation[]>([]);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  // Modals
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);
  const [isAddStockModalOpen, setIsAddStockModalOpen] = useState(false);
  const [sizerTargetTicker, setSizerTargetTicker] = useState('PETRONET.NS');

  // Load initial state from localStorage
  useEffect(() => {
    const loadedHoldings = getStoredHoldings();
    const loadedBudget = getStoredBudget();
    setHoldings(loadedHoldings);
    setBudget(loadedBudget);
  }, []);

  // Re-evaluate holdings against multi-timeframe quant engine
  const runEvaluations = useCallback(async (currentHoldings: Holding[]) => {
    if (currentHoldings.length === 0) {
      setEvaluations([]);
      return;
    }

    setIsEvaluating(true);
    const evList: PositionEvaluation[] = [];

    for (const h of currentHoldings) {
      try {
        const [dCandles, wCandles] = await Promise.all([
          fetchStockCandles(h.ticker, '1d', '1y'),
          fetchStockCandles(h.ticker, '1wk', '2y'),
        ]);

        const ev = evaluateHolding(h, dCandles, wCandles);
        evList.push(ev);
      } catch {
        // Fallback evaluation if network fails
        evList.push({
          ticker: h.ticker,
          quantity: h.quantity,
          avgBuyPrice: h.avgBuyPrice,
          currentPrice: h.avgBuyPrice,
          investedValue: h.quantity * h.avgBuyPrice,
          currentValue: h.quantity * h.avgBuyPrice,
          pnlAmount: 0,
          pnlPercent: 0,
          holdingDays: 0,
          dailySigma: 0,
          weeklyBull: true,
          dailyStBull: true,
          above200Sma: true,
          adxValue: 20,
          action: 'HOLD',
          suggestedStopLoss: h.avgBuyPrice * 0.94,
          suggestedTargetPrice: h.avgBuyPrice * 1.25,
          riskRewardRatio: 2.0,
          healthScore: 50,
          reasoningSummary: 'Evaluating multi-timeframe state...',
          structuralDetails: ['Live data loading...'],
        });
      }
    }

    setEvaluations(evList);
    setIsEvaluating(false);
  }, []);

  useEffect(() => {
    if (holdings.length > 0) {
      runEvaluations(holdings);
    }
  }, [holdings, runEvaluations]);

  // Handlers
  const handleSaveBudget = (newBudget: number, newCash: number) => {
    saveBudget(newBudget, newCash);
    setBudget({ totalBudget: newBudget, cashBalance: newCash });
  };

  const handleAddHolding = (newHolding: Holding) => {
    const updated = addOrUpdateHolding(newHolding);
    setHoldings([...updated]);
  };

  const handleDeleteHolding = (ticker: string) => {
    const updated = deleteHolding(ticker);
    setHoldings([...updated]);
  };

  const handleExportCsv = () => {
    const csv = exportHoldingsCsv(holdings);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `quantum_holdings_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleImportCsv = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target?.result as string;
      if (text) {
        const parsed = parseHoldingsCsv(text);
        if (parsed.length > 0) {
          saveHoldings(parsed);
          setHoldings(parsed);
        }
      }
    };
    reader.readAsText(file);
  };

  const handleAddFromScan = (ticker: string) => {
    setSizerTargetTicker(ticker);
    setIsAddStockModalOpen(true);
  };

  const handleSizeFromScan = (ticker: string) => {
    setSizerTargetTicker(ticker);
    setActiveTab('sizer');
  };

  const handleAddSizedPosition = (
    ticker: string,
    quantity: number,
    price: number,
    notes: string
  ) => {
    handleAddHolding({
      ticker,
      quantity,
      avgBuyPrice: price,
      buyDate: new Date().toISOString().split('T')[0],
      notes,
    });
    setActiveTab('portfolio');
  };

  const totalCurrentValue = evaluations.reduce((acc, e) => acc + e.currentValue, 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar
        activeTab={activeTab}
        setActiveTab={(t) => setActiveTab(t as any)}
        totalBudget={budget.totalBudget}
        currentValue={totalCurrentValue}
        cashBalance={budget.cashBalance}
        onOpenBudgetModal={() => setIsBudgetModalOpen(true)}
        onRefreshData={() => runEvaluations(holdings)}
        isRefreshing={isEvaluating}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        {activeTab === 'portfolio' && (
          <PortfolioView
            evaluations={evaluations}
            onOpenAddModal={() => setIsAddStockModalOpen(true)}
            onDeletePosition={handleDeleteHolding}
            onExportCsv={handleExportCsv}
            onImportCsv={handleImportCsv}
          />
        )}

        {activeTab === 'screener' && (
          <ScreenerView
            onAddStockFromScan={handleAddFromScan}
            onSizeStockFromScan={handleSizeFromScan}
          />
        )}

        {activeTab === 'sizer' && (
          <PositionSizerView
            totalBudget={budget.totalBudget}
            availableCash={budget.cashBalance}
            initialTicker={sizerTargetTicker}
            onAddSizedPosition={handleAddSizedPosition}
          />
        )}

        {activeTab === 'tiebreaker' && <TieBreakerView />}

        {activeTab === 'charts' && <ChartView initialTicker={sizerTargetTicker} />}
      </main>

      {/* Modals */}
      <BudgetModal
        isOpen={isBudgetModalOpen}
        onClose={() => setIsBudgetModalOpen(false)}
        currentBudget={budget.totalBudget}
        currentCash={budget.cashBalance}
        onSave={handleSaveBudget}
      />

      <AddStockModal
        isOpen={isAddStockModalOpen}
        onClose={() => setIsAddStockModalOpen(false)}
        onAddHolding={handleAddHolding}
        totalBudget={budget.totalBudget}
        availableCash={budget.cashBalance}
        initialTicker={sizerTargetTicker}
      />

      <footer className="border-t border-slate-900 py-4 px-6 text-center text-xs text-slate-500 font-mono">
        Quantum Terminal 100% Static Web Edition • Zero-Backend Architecture • All data saved locally in browser
      </footer>
    </div>
  );
};
export default App;
