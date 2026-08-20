import React, { useState, useEffect } from 'react';
import { Scale, Trophy, Sparkles, Check, ArrowRight } from 'lucide-react';
import { StructuralPatternAnalysis } from '../types';
import { fetchStockCandles } from '../services/marketData';
import {
  analyzeStructuralPatterns,
  compareTwoStocksTieBreaker,
} from '../quant/structuralPatterns';

export const TieBreakerView: React.FC = () => {
  const [stockA, setStockA] = useState('PETRONET.NS');
  const [stockB, setStockB] = useState('HDFCBANK.NS');
  const [analysisA, setAnalysisA] = useState<StructuralPatternAnalysis | null>(null);
  const [analysisB, setAnalysisB] = useState<StructuralPatternAnalysis | null>(null);
  const [comparison, setComparison] = useState<{
    winner: string;
    rationale: string;
  } | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  const runComparison = async () => {
    if (!stockA.trim() || !stockB.trim()) return;

    setIsComparing(true);
    const normA = stockA.trim().toUpperCase().endsWith('.NS')
      ? stockA.trim().toUpperCase()
      : `${stockA.trim().toUpperCase()}.NS`;
    const normB = stockB.trim().toUpperCase().endsWith('.NS')
      ? stockB.trim().toUpperCase()
      : `${stockB.trim().toUpperCase()}.NS`;

    try {
      const [candlesA, candlesB] = await Promise.all([
        fetchStockCandles(normA, '1d', '1y'),
        fetchStockCandles(normB, '1d', '1y'),
      ]);

      const resA = analyzeStructuralPatterns(candlesA, normA);
      const resB = analyzeStructuralPatterns(candlesB, normB);
      const comp = compareTwoStocksTieBreaker(resA, resB);

      setAnalysisA(resA);
      setAnalysisB(resB);
      setComparison(comp);
    } catch {
      // Handle error
    } finally {
      setIsComparing(false);
    }
  };

  useEffect(() => {
    runComparison();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100">
              Deterministic Structural Tie-Breaker
            </h2>
            <p className="text-xs text-slate-400">
              When two stocks trigger with similar scores and you can only commit capital to one
            </p>
          </div>
        </div>
      </div>

      {/* Selectors */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Candidate Stock A
            </label>
            <input
              type="text"
              value={stockA}
              onChange={(e) => setStockA(e.target.value.toUpperCase())}
              placeholder="PETRONET.NS"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Candidate Stock B
            </label>
            <input
              type="text"
              value={stockB}
              onChange={(e) => setStockB(e.target.value.toUpperCase())}
              placeholder="HDFCBANK.NS"
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm font-mono text-slate-100 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            onClick={runComparison}
            disabled={isComparing}
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/25 transition disabled:opacity-50"
          >
            <Scale className="w-4 h-4" />
            <span>{isComparing ? 'Evaluating Patterns...' : 'Compare Head-to-Head'}</span>
          </button>
        </div>
      </div>

      {/* Comparison Results */}
      {comparison && analysisA && analysisB && (
        <div className="space-y-6">
          {/* Winner Callout Banner */}
          <div className="bg-gradient-to-r from-amber-950/40 via-slate-900 to-amber-950/40 border border-amber-500/30 p-5 rounded-2xl">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-xl bg-amber-500 text-slate-950 shadow-md shadow-amber-500/30">
                <Trophy className="w-5 h-5 font-bold" />
              </div>
              <div>
                <span className="text-xs font-mono font-semibold uppercase text-amber-400">
                  Deterministic Recommendation Verdict
                </span>
                <h3 className="text-lg font-bold text-slate-100">
                  Commit to <span className="text-amber-400 font-mono">{comparison.winner}</span>
                </h3>
              </div>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed pl-12 font-sans">
              {comparison.rationale}
            </p>
          </div>

          {/* Side-by-Side Comparison Matrix */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-950/40">
              <h3 className="text-xs font-bold font-mono text-slate-300 uppercase tracking-wider">
                5-Point Structural Pattern Matrix
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <tr>
                    <th className="py-3.5 px-4">Structural Metric</th>
                    <th className="py-3.5 px-4 font-bold text-slate-200">
                      {analysisA.ticker}
                      {comparison.winner === analysisA.ticker && (
                        <span className="ml-2 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-[10px]">
                          WINNER
                        </span>
                      )}
                    </th>
                    <th className="py-3.5 px-4 font-bold text-slate-200">
                      {analysisB.ticker}
                      {comparison.winner === analysisB.ticker && (
                        <span className="ml-2 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-[10px]">
                          WINNER
                        </span>
                      )}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  <tr className="hover:bg-slate-850/50">
                    <td className="py-3.5 px-4 text-slate-300 font-sans">Structural Score (0-100)</td>
                    <td
                      className={`py-3.5 px-4 font-bold ${
                        analysisA.structuralScore >= analysisB.structuralScore
                          ? 'text-emerald-400'
                          : 'text-slate-400'
                      }`}
                    >
                      {analysisA.structuralScore.toFixed(1)} / 100
                    </td>
                    <td
                      className={`py-3.5 px-4 font-bold ${
                        analysisB.structuralScore >= analysisA.structuralScore
                          ? 'text-emerald-400'
                          : 'text-slate-400'
                      }`}
                    >
                      {analysisB.structuralScore.toFixed(1)} / 100
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-850/50">
                    <td className="py-3.5 px-4 text-slate-300 font-sans">
                      VCP Volatility Contraction (ATR5/ATR20)
                    </td>
                    <td className="py-3.5 px-4">
                      {analysisA.vcpCompressionRatio.toFixed(2)}{' '}
                      <span className="text-[10px] text-slate-500">
                        ({analysisA.vcpCompressionRatio <= 0.8 ? '⚡ Coiled' : 'Normal'})
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {analysisB.vcpCompressionRatio.toFixed(2)}{' '}
                      <span className="text-[10px] text-slate-500">
                        ({analysisB.vcpCompressionRatio <= 0.8 ? '⚡ Coiled' : 'Normal'})
                      </span>
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-850/50">
                    <td className="py-3.5 px-4 text-slate-300 font-sans">
                      Institutional Accumulation Volume
                    </td>
                    <td
                      className={`py-3.5 px-4 font-semibold ${
                        analysisA.accumulationVolumeRatio >= 1.25 ? 'text-emerald-400' : 'text-slate-300'
                      }`}
                    >
                      {analysisA.accumulationVolumeRatio.toFixed(2)}x
                    </td>
                    <td
                      className={`py-3.5 px-4 font-semibold ${
                        analysisB.accumulationVolumeRatio >= 1.25 ? 'text-emerald-400' : 'text-slate-300'
                      }`}
                    >
                      {analysisB.accumulationVolumeRatio.toFixed(2)}x
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-850/50">
                    <td className="py-3.5 px-4 text-slate-300 font-sans">Distance to 52-Week High</td>
                    <td className="py-3.5 px-4">
                      {analysisA.distanceTo52wHighPct.toFixed(1)}% away
                    </td>
                    <td className="py-3.5 px-4">
                      {analysisB.distanceTo52wHighPct.toFixed(1)}% away
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-850/50">
                    <td className="py-3.5 px-4 text-slate-300 font-sans">
                      Cone Risk/Reward Asymmetry
                    </td>
                    <td className="py-3.5 px-4 text-cyan-400 font-bold">
                      {analysisA.coneRiskRewardRatio.toFixed(2)}x
                    </td>
                    <td className="py-3.5 px-4 text-cyan-400 font-bold">
                      {analysisB.coneRiskRewardRatio.toFixed(2)}x
                    </td>
                  </tr>

                  <tr className="hover:bg-slate-850/50">
                    <td className="py-3.5 px-4 text-slate-300 font-sans">Structural Setup Verdict</td>
                    <td className="py-3.5 px-4 font-sans text-slate-300 text-xs">
                      {analysisA.verdict}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-slate-300 text-xs">
                      {analysisB.verdict}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
