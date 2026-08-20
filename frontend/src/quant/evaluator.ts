import { Candle, Holding, PositionEvaluation } from '../types';
import {
  atr,
  computeADX,
  computeSupertrend,
  computeTripleSupertrend,
  sma,
} from './indicators';
import { computeConeSigmaForBar } from './projectionCone';
import { analyzeStructuralPatterns } from './structuralPatterns';

export function evaluateHolding(
  holding: Holding,
  dailyCandles: Candle[],
  weeklyCandles: Candle[]
): PositionEvaluation {
  const dClose = dailyCandles.map((c) => c.close);
  const dHigh = dailyCandles.map((c) => c.high);
  const dLow = dailyCandles.map((c) => c.low);
  const n = dClose.length;

  const wClose = weeklyCandles.map((c) => c.close);
  const wHigh = weeklyCandles.map((c) => c.high);
  const wLow = weeklyCandles.map((c) => c.low);

  const currentPrice = n > 0 ? dClose[n - 1] : holding.avgBuyPrice;
  const investedVal = holding.quantity * holding.avgBuyPrice;
  const currentVal = holding.quantity * currentPrice;
  const pnlAmt = currentVal - investedVal;
  const pnlPct = holding.avgBuyPrice > 0 ? ((currentPrice - holding.avgBuyPrice) / holding.avgBuyPrice) * 100.0 : 0.0;

  // Holding days
  let holdingDays = 0;
  try {
    const buyTime = new Date(holding.buyDate).getTime();
    holdingDays = Math.max(0, Math.floor((Date.now() - buyTime) / (1000 * 60 * 60 * 24)));
  } catch {
    holdingDays = 0;
  }

  // 1. Technical Indicators
  const [wt1, wt2, wt3] = computeTripleSupertrend(wClose, wHigh, wLow);
  const weeklyBull = wt1.length > 0 && (wt1[wt1.length - 1] === 1 || wt2[wt2.length - 1] === 1 || wt3[wt3.length - 1] === 1);

  const dFast = computeSupertrend(dClose, dHigh, dLow, 10, 3.0);
  const dSlow = computeSupertrend(dClose, dHigh, dLow, 14, 3.5);
  const dailyStBull = dSlow.trend.length > 0 && dSlow.trend[dSlow.trend.length - 1] === 1;

  const sma200Arr = sma(dClose, Math.min(200, Math.floor(n / 2)));
  const sma200 = sma200Arr[sma200Arr.length - 1];
  const above200 = isNaN(sma200) || currentPrice >= sma200 * 0.98;

  const adxVal = computeADX(dHigh, dLow, dClose, 14);
  const sigma = computeConeSigmaForBar(dHigh, dLow, dClose, 'D', 20, 10);

  // 2. Dynamic Trailing Stop & Target
  const atrArr = atr(dHigh, dLow, dClose, 14);
  const atr14 = atrArr.length > 0 ? atrArr[atrArr.length - 1] : currentPrice * 0.03;
  let suggestedStop = Math.max(currentPrice - 2.5 * atr14, holding.avgBuyPrice * 0.94);
  if (pnlPct >= 12.0) {
    suggestedStop = Math.max(suggestedStop, holding.avgBuyPrice * 1.02); // Lock in profits
  }

  const suggestedTarget = currentPrice * (1.0 + Math.max(0.12, 0.25 - sigma * 0.05));
  const downside = Math.max(1.0, currentPrice - suggestedStop);
  const upside = Math.max(1.0, suggestedTarget - currentPrice);
  const rrRatio = upside / downside;

  // 3. Structural Patterns
  const patterns = analyzeStructuralPatterns(dailyCandles, holding.ticker, sigma);

  // 4. 4-State Decisions
  let action: 'HOLD' | 'ADD' | 'TRIM' | 'EXIT' = 'HOLD';
  let reasoning = '';
  const details: string[] = [];

  const lastFast = dFast.trend.length > 0 ? dFast.trend[dFast.trend.length - 1] : 1;
  const prevFast = dFast.trend.length > 1 ? dFast.trend[dFast.trend.length - 2] : 1;
  const lastSlow = dSlow.trend.length > 0 ? dSlow.trend[dSlow.trend.length - 1] : 1;

  // Rule 1: EXIT
  if (!weeklyBull && lastSlow === -1) {
    action = 'EXIT';
    reasoning = '🔴 EXIT: Both Weekly and Daily Supertrends are Bearish. Trend structure is broken. Exit to preserve capital.';
    details.push('Weekly macro trend broken (Triple Supertrend Bearish).');
    details.push('Daily slow Supertrend confirmed Bearish.');
  } else if (lastSlow === -1 && lastFast === -1 && prevFast === -1) {
    action = 'EXIT';
    reasoning = '🔴 EXIT: 2-Bar Daily Supertrend breakdown confirmed. Cut loss / protect capital.';
    details.push('Daily fast Supertrend has remained Bearish for >= 2 consecutive bars.');
  }
  // Rule 2: TRIM / TAKE PROFIT
  else if (sigma >= 1.9 || (pnlPct >= 25.0 && sigma >= 1.5)) {
    action = 'TRIM';
    reasoning = `🟡 TRIM (Take Profit): Price extended to +${sigma.toFixed(2)}σ near upper Projection Cone boundary. Lock in 30%-50% gains.`;
    details.push(`Price is in Upper Resistance Zone (+${sigma.toFixed(2)}σ). Mean-reversion pullback probable.`);
    details.push(`Unrealized P&L is strong (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%). Safe point to bank profits.`);
  }
  // Rule 3: ADD / PYRAMID
  else if (
    weeklyBull &&
    above200 &&
    sigma <= 0.0 &&
    lastFast === 1 &&
    pnlPct >= 0.0 &&
    (holding.pyramidCount || 0) < 3
  ) {
    action = 'ADD';
    reasoning = `🟢 ADD / PYRAMID: Stock pulled back to Discount Zone (${sigma.toFixed(2)}σ) inside Weekly Bull trend. Excellent spot to add 0.5-1.0 unit.`;
    details.push('Weekly macro trend is strong and Bullish.');
    details.push(`Valuation is in discount (${sigma.toFixed(2)}σ).`);
    details.push('Daily fast Supertrend just flipped green.');
  }
  // Rule 4: HOLD
  else {
    action = 'HOLD';
    reasoning = `⚪ HOLD: Macro trend is healthy (Weekly Bull: ${weeklyBull ? 'Yes' : 'No'}), position is within normal operating range (${sigma.toFixed(2)}σ). Let winner run.`;
    details.push(`Price is within normal trend range (${sigma.toFixed(2)}σ).`);
    details.push(`Current P&L is ${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%. Trailing stop set at ₹${suggestedStop.toLocaleString('en-IN', { maximumFractionDigits: 2 })}.`);
  }

  details.push(...patterns.keyStrengths);
  details.push(...patterns.keyRisks);

  let healthScore = patterns.structuralScore;
  if (!weeklyBull) healthScore -= 25.0;
  if (lastSlow === -1) healthScore -= 20.0;
  healthScore = Math.max(5.0, Math.min(98.0, healthScore));

  return {
    ticker: holding.ticker,
    quantity: holding.quantity,
    avgBuyPrice: holding.avgBuyPrice,
    currentPrice,
    investedValue: investedVal,
    currentValue: currentVal,
    pnlAmount: pnlAmt,
    pnlPercent: pnlPct,
    holdingDays,
    dailySigma: sigma,
    weeklyBull,
    dailyStBull,
    above200Sma: above200,
    adxValue: adxVal,
    action,
    suggestedStopLoss: suggestedStop,
    suggestedTargetPrice: suggestedTarget,
    riskRewardRatio: rrRatio,
    healthScore,
    reasoningSummary: reasoning,
    structuralDetails: details,
  };
}
