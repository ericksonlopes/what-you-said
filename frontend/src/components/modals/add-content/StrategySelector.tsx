import React from 'react';
import { useTranslation } from 'react-i18next';
import { Settings2, Zap, Scissors, Layers, Activity } from 'lucide-react';

interface Strategy {
  id: string;
  name: string;
  description: string;
  tokens: number;
  overlap: number;
  icon: React.ElementType;
}

interface StrategySelectorProps {
  readonly tokensPerChunk: number;
  readonly setTokensPerChunk: (val: number) => void;
  readonly tokensOverlap: number;
  readonly setTokensOverlap: (val: number) => void;
  readonly activeStrategy: string;
  readonly setActiveStrategy: (val: string) => void;
  readonly modelInfo: { name: string; dimensions: number; max_seq_length: number } | null;
}

export function StrategySelector({
  tokensPerChunk,
  setTokensPerChunk,
  tokensOverlap,
  setTokensOverlap,
  activeStrategy,
  setActiveStrategy,
  modelInfo
}: StrategySelectorProps) {
  const { t } = useTranslation();

  const STRATEGIES: Strategy[] = [
    { id: 'balanced', name: t('ingestion.options.strategies.balanced.name'), description: t('ingestion.options.strategies.balanced.description'), tokens: 512, overlap: 50, icon: Zap },
    { id: 'granular', name: t('ingestion.options.strategies.granular.name'), description: t('ingestion.options.strategies.granular.description'), tokens: 300, overlap: 30, icon: Scissors },
    { id: 'context', name: t('ingestion.options.strategies.context.name'), description: t('ingestion.options.strategies.context.description'), tokens: 800, overlap: 100, icon: Layers },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Settings2 className="w-3.5 h-3.5 text-emerald-400" />
          <h4 className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">{t('ingestion.options.strategy')}</h4>
        </div>
        <span className="text-[9px] bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded-full font-medium border border-emerald-500/20">
          {t('ingestion.options.optimized')}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {STRATEGIES.map((strategy) => {
          const Icon = strategy.icon;
          const cappedTokens = Math.min(strategy.tokens, modelInfo?.max_seq_length || 2000);
          const isSelected = activeStrategy === strategy.id;

          return (
            <button
              key={strategy.id}
              type="button"
              onClick={() => {
                setActiveStrategy(strategy.id);
                setTokensPerChunk(cappedTokens);
                setTokensOverlap(strategy.overlap);
              }}
              className={`flex flex-col items-center gap-2.5 p-3.5 rounded-xl border transition-all duration-300 ${
                isSelected
                  ? 'bg-emerald-500/10 border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                  : 'bg-black/40 border-zinc-800 hover:border-zinc-700/80 hover:bg-black/20'
              }`}
            >
              <div className={`p-2 rounded-xl ${isSelected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-800/80 text-zinc-500'}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="text-center space-y-0.5">
                <div className={`text-[12px] font-bold tracking-wide ${isSelected ? 'text-zinc-100' : 'text-zinc-400'}`}>{strategy.name}</div>
                <div className="text-[10px] text-zinc-500 font-medium leading-tight line-clamp-2 px-1">{strategy.description}</div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="space-y-4 bg-black/40 rounded-xl p-4 border border-zinc-800/50">
        <div className="space-y-3">
          <div className="flex justify-between items-end">
            <div className="space-y-1">
              <label className="text-[12px] font-bold text-zinc-200 flex items-center gap-2 w-full">
                <Scissors className="w-3.5 h-3.5 text-emerald-500 opacity-80" />
                {t('ingestion.options.max_tokens')}
                {!!modelInfo?.max_seq_length && (
                  <span className="text-[10px] px-2 py-0.5 bg-zinc-800/80 text-zinc-400 rounded-lg border border-zinc-700/50 ml-auto font-mono font-bold">
                    {t('ingestion.options.model_limit')}: {modelInfo.max_seq_length}
                  </span>
                )}
              </label>
              <p className="text-[11px] text-zinc-500 font-medium leading-tight">{t('ingestion.options.tokens_fragment')}</p>
            </div>
            <div className="flex items-baseline gap-1 bg-black/30 px-2 py-0.5 rounded-lg border border-zinc-800/50">
              <span className="text-base font-mono font-bold text-emerald-400 leading-none">{tokensPerChunk}</span>
              <span className="text-[10px] text-zinc-600 font-bold uppercase tracking-tighter">{t('ingestion.options.tokens_label')}</span>
            </div>
          </div>
          <input
            type="range"
            min="64"
            max={modelInfo?.max_seq_length || 2000}
            step={1}
            value={tokensPerChunk}
            onChange={(e) => {
              setTokensPerChunk(Number.parseInt(e.target.value, 10));
              setActiveStrategy('custom');
            }}
            className="w-full h-1 bg-zinc-800 rounded-full appearance-none cursor-pointer accent-emerald-500 hover:accent-emerald-400 transition-all"
          />
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-end">
            <div className="space-y-1">
              <label className="text-[12px] font-bold text-zinc-200 flex items-center gap-2">
                <Layers className="w-3.5 h-3.5 text-emerald-500 opacity-80" />
                {t('ingestion.options.context_overlap')}
              </label>
              <p className="text-[11px] text-zinc-500 font-medium leading-tight">{t('ingestion.options.shared_context')}</p>
            </div>
            <div className="flex items-baseline gap-1 bg-black/30 px-2 py-0.5 rounded-lg border border-zinc-800/50">
              <span className="text-base font-mono font-bold text-emerald-400 leading-none">{tokensOverlap}</span>
              <span className="text-[10px] text-zinc-600 font-bold uppercase tracking-tighter">{t('ingestion.options.tokens_label')}</span>
            </div>
          </div>
          <input
            type="range"
            min="0"
            max="300"
            step={1}
            value={tokensOverlap}
            onChange={(e) => {
              setTokensOverlap(Number.parseInt(e.target.value, 10));
              setActiveStrategy('custom');
            }}
            className="w-full h-1 bg-zinc-800 rounded-full appearance-none cursor-pointer accent-emerald-500 hover:accent-emerald-400 transition-all"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 px-4 py-3 bg-emerald-500/5 rounded-xl border border-emerald-500/10 transition-colors duration-500 shadow-[inset_0_1px_1px_rgba(16,185,129,0.05)]">
        <Activity className="w-4 h-4 text-emerald-500/50 flex-shrink-0 animate-pulse" />
        <div className="flex-1">
          <p className="text-[11px] text-zinc-400 italic leading-snug">
            {t('ingestion.options.optimized_tip', { 
              strategy: activeStrategy === 'custom' 
                ? t('ingestion.options.strategies.custom.name') 
                : t(`ingestion.options.strategies.${activeStrategy}.name`)
            })}
            <span className="block mt-1 opacity-70 text-[10px] not-italic">
              {activeStrategy === 'balanced' && t('ingestion.options.strategies.balanced.long_description')}
              {activeStrategy === 'granular' && t('ingestion.options.strategies.granular.long_description')}
              {activeStrategy === 'context' && t('ingestion.options.strategies.context.long_description')}
              {activeStrategy === 'custom' && t('ingestion.options.strategies.custom.long_description')}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
