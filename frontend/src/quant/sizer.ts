import { Candle, SizingRecommendation } from '../types';
import { atr } from './indicators';

export function calculatePositionSize(
  ticker: string,
  dailyCandles: Candle[],
  totalBudget: number,
  availableCash: number,
  holdingPeriod: string = 'Positional (1-6m)',
  riskPerTradePct: number = 1.0,
  maxPositionCapPct: number = 12.0
): SizingRecommendation {
  const n = dailyCandles.length;
  const close = dailyCandles.map((c) => c.close);
  const high = dailyCandles.map((c) => c.high);
  const low = dailyCandles.map((c) => c.low);

  const currentPrice = n > 0 ? close[n - 1] : 100.0;
  const atrArr = atr(high, low, close, 14);
  const atr14 = atrArr.length > 0 ? atrArr[atrArr.length - 1] : currentPrice * 0.03;

  let stopMult = 2.5;
  let coneTargetSigma = 2.0;
  let periodCapPct = Math.min(maxPositionCapPct, 12.0);
  let riskPct = riskPerTradePct;

  if (holdingPeriod.includes('Swing')) {
    stopMult = 1.8;
    coneTargetSigma = 1.8;
    periodCapPct = Math.min(maxPositionCapPct, 10.0);
    riskPct = Math.min(riskPerTradePct, 1.0);
  } else if (holdingPeriod.includes('Long-Term')) {
    stopMult = 3.5;
    coneTargetSigma = 2.5;
    periodCapPct = Math.min(maxPositionCapPct, 15.0);
    riskPct = Math.min(riskPerTradePct, 1.5);
  }

  const stopDistancePts = Math.max(atr14 * stopMult, currentPrice * 0.04);
  const suggestedStop = Math.max(1.0, currentPrice - stopDistancePts);
  const stopPct = ((currentPrice - suggestedStop) / currentPrice) * 100.0;

  const targetPrice = currentPrice * (1.0 + (coneTargetSigma * 0.08));
  const upsidePct = ((targetPrice - currentPrice) / currentPrice) * 100.0;
  const rrRatio = (targetPrice - currentPrice) / Math.max(1.0, currentPrice - suggestedStop);

  const maxRiskAmount = totalBudget * (riskPct / 100.0);
  const sharesByRisk = Math.floor(maxRiskAmount / Math.max(1.0, currentPrice - suggestedStop));

  const maxCapitalForPos = totalBudget * (periodCapPct / 100.0);
  const sharesByCap = Math.floor(maxCapitalForPos / currentPrice);
  const sharesByCash = availableCash > 0 ? Math.floor(availableCash / currentPrice) : 0;

  let recommendedShares = Math.max(0, Math.min(sharesByRisk, sharesByCap, sharesByCash));
  if (recommendedShares === 0 && availableCash >= currentPrice) {
    recommendedShares = 1;
  }

  const totalInvestment = recommendedShares * currentPrice;
  const actualRiskAmt = recommendedShares * (currentPrice - suggestedStop);
  const actualRiskPct = totalBudget > 0 ? (actualRiskAmt / totalBudget) * 100.0 : 0.0;
  const allocPct = totalBudget > 0 ? (totalInvestment / totalBudget) * 100.0 : 0.0;

  const notes: string[] = [
    `Horizon: ${holdingPeriod} (Stop: ${stopMult.toFixed(1)}x ATR = ₹${stopDistancePts.toFixed(2)} / -${stopPct.toFixed(1)}%)`,
    `Risk Budget: ${riskPct.toFixed(1)}% (₹${maxRiskAmount.toLocaleString('en-IN')}) | Actual Risk: ₹${actualRiskAmt.toLocaleString('en-IN', { maximumFractionDigits: 2 })} (${actualRiskPct.toFixed(2)}%)`,
    `Max Allocation Cap: ${periodCapPct.toFixed(1)}% (₹${maxCapitalForPos.toLocaleString('en-IN')}) | Allocated: ₹${totalInvestment.toLocaleString('en-IN', { maximumFractionDigits: 2 })} (${allocPct.toFixed(1)}%)`,
  ];

  if (recommendedShares === sharesByCash && sharesByCash < sharesByRisk) {
    notes.push('⚠️ Position sized down to match available cash balance.');
  } else if (recommendedShares === sharesByCap && sharesByCap < sharesByRisk) {
    notes.push('ℹ️ Position size capped by maximum single-stock allocation limit.');
  } else {
    notes.push('✅ Position precisely calibrated to 1% Fixed Fractional Account Risk.');
  }

  const rationale = `For a **${holdingPeriod}** horizon, recommended size is **${recommendedShares} shares** (₹${totalInvestment.toLocaleString('en-IN', { maximumFractionDigits: 2 })} / ${allocPct.toFixed(1)}% portfolio weight). This limits total portfolio risk to **₹${actualRiskAmt.toLocaleString('en-IN', { maximumFractionDigits: 2 })} (${actualRiskPct.toFixed(2)}%)** with a **${rrRatio.toFixed(2)}x Risk/Reward** toward the +${coneTargetSigma.toFixed(1)}σ target of ₹${targetPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}.`;

  return {
    ticker,
    holdingPeriod,
    currentPrice,
    suggestedStopLoss: suggestedStop,
    stopDistancePct: stopPct,
    targetPrice,
    upsidePotentialPct: upsidePct,
    riskRewardRatio: rrRatio,
    recommendedShares,
    totalInvestmentAmount: totalInvestment,
    portfolioAllocationPct: allocPct,
    capitalAtRiskAmount: actualRiskAmt,
    capitalAtRiskPct: actualRiskPct,
    sizingRationale: rationale,
    riskNotes: notes,
  };
}
