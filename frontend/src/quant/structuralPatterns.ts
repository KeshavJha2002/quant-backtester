import { Candle, StructuralPatternAnalysis } from '../types';
import { atr } from './indicators';

export function analyzeStructuralPatterns(
  dailyCandles: Candle[],
  ticker: string,
  sigmaMove: number = 0.0
): StructuralPatternAnalysis {
  const n = dailyCandles.length;
  if (n < 40) {
    return {
      ticker,
      vcpCompressionRatio: 1.0,
      accumulationVolumeRatio: 1.0,
      rsMomentumPct: 0.0,
      distanceTo52wHighPct: 50.0,
      coneRiskRewardRatio: 1.0,
      structuralScore: 50.0,
      keyStrengths: ['Building base history'],
      keyRisks: ['Limited data'],
      verdict: 'Neutral',
    };
  }

  const close = dailyCandles.map((c) => c.close);
  const high = dailyCandles.map((c) => c.high);
  const low = dailyCandles.map((c) => c.low);
  const vol = dailyCandles.map((c) => c.volume);

  // 1. Volatility Contraction Pattern (VCP)
  const atr5Arr = atr(high, low, close, 5);
  const atr20Arr = atr(high, low, close, 20);
  const atr5 = atr5Arr[atr5Arr.length - 1];
  const atr20 = atr20Arr[atr20Arr.length - 1];
  const vcpRatio = atr20 > 0 ? atr5 / atr20 : 1.0;

  // 2. Accumulation vs Distribution Volume (Last 20 bars)
  let upVol = 0;
  let downVol = 0;
  for (let i = Math.max(1, n - 20); i < n; i++) {
    if (close[i] > close[i - 1]) {
      upVol += vol[i];
    } else {
      downVol += vol[i];
    }
  }
  const accRatio = downVol > 0 ? upVol / downVol : 1.0;

  // 3. 20-Day Momentum
  const ret20d = n >= 20 ? ((close[n - 1] - close[n - 20]) / close[n - 20]) * 100.0 : 0.0;

  // 4. Distance to 52-Week High
  const high52wSlice = high.slice(-Math.min(252, n));
  const high52w = Math.max(...high52wSlice);
  const dist52wHigh = high52w > 0 ? Math.max(0.0, ((high52w - close[n - 1]) / high52w) * 100.0) : 0.0;

  // 5. Projection Cone Risk/Reward Asymmetry
  const upsideSigmas = Math.max(0.2, 2.0 - sigmaMove);
  const downsideSigmas = Math.max(0.4, sigmaMove - -1.0);
  const coneRR = upsideSigmas / downsideSigmas;

  // Compute Structural Quality Score (0 to 100)
  let score = 50.0;
  const strengths: string[] = [];
  const risks: string[] = [];

  if (vcpRatio <= 0.75) {
    score += 15.0;
    strengths.push(`Strong Volatility Contraction (VCP Ratio: ${vcpRatio.toFixed(2)}) → Energy coiled for breakout`);
  } else if (vcpRatio >= 1.25) {
    score -= 10.0;
    risks.push(`High Volatility Expansion (ATR5/ATR20: ${vcpRatio.toFixed(2)}) → Choppy conditions`);
  }

  if (accRatio >= 1.30) {
    score += 15.0;
    strengths.push(`Institutional Accumulation (Up/Down Vol: ${accRatio.toFixed(2)}x) → Smart money buying`);
  } else if (accRatio <= 0.70) {
    score -= 12.0;
    risks.push(`Distribution Warning (Up/Down Vol: ${accRatio.toFixed(2)}x) → Volume on selloffs`);
  }

  if (dist52wHigh <= 8.0) {
    score += 12.0;
    strengths.push(`Near 52-Week High (${dist52wHigh.toFixed(1)}% away) → Blue-sky breakout with low overhead resistance`);
  } else if (dist52wHigh >= 30.0) {
    score -= 10.0;
    risks.push(`Deep in Range (${dist52wHigh.toFixed(1)}% below high) → Overhead supply resistance`);
  }

  if (sigmaMove <= 0.0) {
    score += 10.0;
    strengths.push(`Discount Valuation (${sigmaMove.toFixed(2)}σ) → Favorable asymmetric entry inside trend`);
  } else if (sigmaMove >= 1.8) {
    score -= 15.0;
    risks.push(`Extended Valuation (${sigmaMove.toFixed(2)}σ) → High mean-reversion pullback risk`);
  }

  score = Math.max(5.0, Math.min(98.0, score));

  let verdict = 'Moderate Quality Setup (Standard Position)';
  if (score >= 75) {
    verdict = 'High Conviction Institutional Setup (Prime Candidate)';
  } else if (score < 55) {
    verdict = 'Sub-Optimal Structure (Higher Noise / Distribution Risk)';
  }

  return {
    ticker,
    vcpCompressionRatio: vcpRatio,
    accumulationVolumeRatio: accRatio,
    rsMomentumPct: ret20d,
    distanceTo52wHighPct: dist52wHigh,
    coneRiskRewardRatio: coneRR,
    structuralScore: score,
    keyStrengths: strengths,
    keyRisks: risks,
    verdict,
  };
}

export function compareTwoStocksTieBreaker(
  analysisA: StructuralPatternAnalysis,
  analysisB: StructuralPatternAnalysis
): { winner: string; rationale: string; stockA: StructuralPatternAnalysis; stockB: StructuralPatternAnalysis } {
  const diff = analysisA.structuralScore - analysisB.structuralScore;
  let winner = analysisA.ticker;
  let rationale = '';

  if (diff >= 5.0) {
    winner = analysisA.ticker;
    rationale = `**${analysisA.ticker}** is statistically superior (+${diff.toFixed(1)} pts higher score). Key edge: Accumulation volume (${analysisA.accumulationVolumeRatio.toFixed(2)}x vs ${analysisB.accumulationVolumeRatio.toFixed(2)}x) and VCP compression (${analysisA.vcpCompressionRatio.toFixed(2)} vs ${analysisB.vcpCompressionRatio.toFixed(2)}).`;
  } else if (diff <= -5.0) {
    winner = analysisB.ticker;
    rationale = `**${analysisB.ticker}** is statistically superior (+${Math.abs(diff).toFixed(1)} pts higher score). Key edge: Accumulation volume (${analysisB.accumulationVolumeRatio.toFixed(2)}x vs ${analysisA.accumulationVolumeRatio.toFixed(2)}x) and VCP compression (${analysisB.vcpCompressionRatio.toFixed(2)} vs ${analysisA.vcpCompressionRatio.toFixed(2)}).`;
  } else {
    if (analysisA.distanceTo52wHighPct < analysisB.distanceTo52wHighPct) {
      winner = analysisA.ticker;
      rationale = `**${analysisA.ticker}** wins the close tie-breaker due to proximity to 52-week high (${analysisA.distanceTo52wHighPct.toFixed(1)}% vs ${analysisB.distanceTo52wHighPct.toFixed(1)}% away), offering clearer blue-sky breakout room.`;
    } else {
      winner = analysisB.ticker;
      rationale = `**${analysisB.ticker}** wins the close tie-breaker due to proximity to 52-week high (${analysisB.distanceTo52wHighPct.toFixed(1)}% vs ${analysisA.distanceTo52wHighPct.toFixed(1)}% away), offering clearer blue-sky breakout room.`;
    }
  }

  return { winner, rationale, stockA: analysisA, stockB: analysisB };
}
