export type ActionDecision = 'ADD' | 'HOLD' | 'TRIM' | 'EXIT';

export interface Holding {
  ticker: string;
  quantity: number;
  avgBuyPrice: number;
  buyDate: string;
  stopLoss?: number;
  targetPrice?: number;
  notes?: string;
  pyramidCount?: number;
}

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PositionEvaluation {
  ticker: string;
  quantity: number;
  avgBuyPrice: number;
  currentPrice: number;
  investedValue: number;
  currentValue: number;
  pnlAmount: number;
  pnlPercent: number;
  holdingDays: number;

  dailySigma: number;
  weeklyBull: boolean;
  dailyStBull: boolean;
  above200Sma: boolean;
  adxValue: number;

  action: ActionDecision;
  suggestedStopLoss: number;
  suggestedTargetPrice: number;
  riskRewardRatio: number;
  healthScore: number;

  reasoningSummary: string;
  structuralDetails: string[];
}

export interface SizingRecommendation {
  ticker: string;
  holdingPeriod: string;
  currentPrice: number;
  suggestedStopLoss: number;
  stopDistancePct: number;
  targetPrice: number;
  upsidePotentialPct: number;
  riskRewardRatio: number;
  recommendedShares: number;
  totalInvestmentAmount: number;
  portfolioAllocationPct: number;
  capitalAtRiskAmount: number;
  capitalAtRiskPct: number;
  sizingRationale: string;
  riskNotes: string[];
}

export interface StructuralPatternAnalysis {
  ticker: string;
  vcpCompressionRatio: number;
  accumulationVolumeRatio: number;
  rsMomentumPct: number;
  distanceTo52wHighPct: number;
  coneRiskRewardRatio: number;
  structuralScore: number;
  keyStrengths: string[];
  keyRisks: string[];
  verdict: string;
}

export interface ScanResult {
  timeframe: 'Daily' | 'Weekly';
  segment: string;
  ticker: string;
  barDate: string;
  closePrice: number;
  sigmaMove: number;
  adxValue: number;
  volumeRatio: number;
  score: number;
  signalDetails: string;
}
