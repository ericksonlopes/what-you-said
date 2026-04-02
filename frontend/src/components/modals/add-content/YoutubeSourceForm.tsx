import React from 'react';
import { useTranslation } from 'react-i18next';
import { SquarePlay, ListVideo, ArrowRight } from 'lucide-react';

interface YoutubeSourceFormProps {
  readonly youtubeDataType: 'video' | 'playlist';
  readonly setYoutubeDataType: (val: 'video' | 'playlist') => void;
  readonly inputValue: string;
  readonly setInputValue: (val: string) => void;
}

export function YoutubeSourceForm({
  youtubeDataType,
  setYoutubeDataType,
  inputValue,
  setInputValue
}: YoutubeSourceFormProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex p-0.5 bg-black/40 rounded-xl border border-zinc-800/50 w-full">
        <button
          type="button"
          onClick={() => setYoutubeDataType('video')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-lg transition-all ${
            youtubeDataType === 'video' ? 'bg-zinc-800 text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          <SquarePlay className="w-3.5 h-3.5" />
          {t('ingestion.options.types.video')}
        </button>
        <button
          type="button"
          onClick={() => setYoutubeDataType('playlist')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-lg transition-all ${
            youtubeDataType === 'playlist' ? 'bg-zinc-800 text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          <ListVideo className="w-3.5 h-3.5" />
          {t('ingestion.options.types.playlist')}
        </button>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium text-zinc-300" htmlFor="youtube-url">
          {youtubeDataType === 'playlist' ? t('ingestion.options.types.playlist_url') : t('ingestion.url.label')}
        </label>
        <input
          id="youtube-url"
          type="url"
          required
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder={youtubeDataType === 'playlist' ? t('ingestion.options.types.playlist_url') : t('ingestion.url.placeholder')}
          className="w-full bg-black/40 border border-border-subtle rounded-xl px-4 py-3 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all placeholder:text-zinc-600 shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)]"
        />
      </div>

      <div className="flex items-start gap-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
        <ArrowRight className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-zinc-400 leading-relaxed">
          {youtubeDataType === 'playlist'
            ? t('ingestion.options.types.playlist_desc')
            : t('ingestion.coming_soon.description', { name: 'YouTube' })}
        </p>
      </div>
    </div>
  );
}
