import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, Layers, Settings2, Info, X } from 'lucide-react';

interface WebSourceFormProps {
  readonly inputValue: string;
  readonly setInputValue: (val: string) => void;
  readonly webDepth: number;
  readonly setWebDepth: (val: number) => void;
  readonly cssSelector: string;
  readonly setCssSelector: (val: string) => void;
  readonly excludeLinks: boolean;
  readonly setExcludeLinks: (val: boolean) => void;
}

export function WebSourceForm({
  inputValue,
  setInputValue,
  webDepth,
  setWebDepth,
  cssSelector,
  setCssSelector,
  excludeLinks,
  setExcludeLinks
}: WebSourceFormProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="space-y-2">
        <label className="text-sm font-medium text-zinc-300" htmlFor="web-url">
          {t('ingestion.options.types.web_url')}
        </label>
        <div className="relative">
          <Globe className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            id="web-url"
            type="url"
            required
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="https://example.com"
            className="w-full bg-black/40 border border-zinc-800 rounded-xl pl-11 pr-4 py-3 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-zinc-600 shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)]"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-3 h-3" />
            {t('ingestion.options.types.depth')}
          </label>
          <div className="flex items-center gap-3 bg-black/40 border border-zinc-800 rounded-xl p-1">
            {[1, 2, 3].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setWebDepth(d)}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                  webDepth === d ? 'bg-zinc-800 text-emerald-400 border border-zinc-700/50 shadow-sm' : 'text-zinc-500 hover:text-zinc-400'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-zinc-500 font-medium leading-tight mt-1 px-1">
            {t('ingestion.options.types.depth_desc')}
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-2" htmlFor="css-selector">
            <Settings2 className="w-3 h-3" />
            {t('ingestion.options.types.css_selector')}
          </label>
          <input
            id="css-selector"
            type="text"
            value={cssSelector}
            onChange={(e) => setCssSelector(e.target.value)}
            placeholder={t('ingestion.options.types.css_selector_placeholder')}
            className="w-full bg-black/40 border border-zinc-800 rounded-xl px-4 py-2.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-zinc-600"
          />
        </div>
      </div>

      <div className="flex items-start gap-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
        <Info className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-zinc-400 leading-relaxed">
          {t('ingestion.descriptions.web')}
        </p>
      </div>

      <div className="bg-black/40 rounded-xl border border-zinc-800/50 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg transition-colors ${excludeLinks ? 'bg-emerald-500/10 text-emerald-400' : 'bg-zinc-800/80 text-zinc-500'}`}>
              <X className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">
                {t('ingestion.options.types.exclude_links')}
              </h4>
              <p className="text-xs text-zinc-400 font-medium">
                {t('ingestion.options.types.exclude_links_desc')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setExcludeLinks(!excludeLinks)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none ${
              excludeLinks ? 'bg-emerald-500' : 'bg-zinc-700'
            }`}
            aria-label={t('ingestion.options.types.exclude_links')}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                excludeLinks ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  );
}
