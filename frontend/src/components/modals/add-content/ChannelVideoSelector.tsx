import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckSquare, Square, CheckCheck, XSquare, Search, Clock } from 'lucide-react';
import { motion } from 'motion/react';

interface ChannelVideo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  thumbnail: string | null;
  already_ingested: boolean;
}

interface ChannelVideoSelectorProps {
  readonly channelName: string;
  readonly videos: ChannelVideo[];
  readonly selectedIds: Set<string>;
  readonly onToggle: (videoId: string) => void;
  readonly onSelectAllNew: () => void;
  readonly onDeselectAll: () => void;
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '--:--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function ChannelVideoSelector({
  channelName,
  videos,
  selectedIds,
  onToggle,
  onSelectAllNew,
  onDeselectAll,
}: ChannelVideoSelectorProps) {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');

  const newCount = useMemo(() => videos.filter(v => !v.already_ingested).length, [videos]);
  const ingestedCount = videos.length - newCount;

  const filteredVideos = useMemo(() => {
    if (!searchQuery.trim()) return videos;
    const q = searchQuery.toLowerCase();
    return videos.filter(v => v.title.toLowerCase().includes(q));
  }, [videos, searchQuery]);

  if (videos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-sm text-zinc-400">{t('ingestion.channel.no_videos')}</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-3"
    >
      {/* Header with channel name and stats */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-zinc-200">{channelName}</h4>
          <p className="text-[11px] text-zinc-500">
            {t('ingestion.channel.selected_count', {
              count: selectedIds.size,
              total: videos.length,
            })}
            {ingestedCount > 0 && (
              <span className="ml-2 text-amber-500/80">
                • {ingestedCount} {t('ingestion.channel.already_ingested').toLowerCase()}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onSelectAllNew}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 rounded-lg hover:bg-emerald-500/20 transition-colors uppercase tracking-wider"
          >
            <CheckCheck className="w-3 h-3" />
            {t('ingestion.channel.select_all_new')}
          </button>
          <button
            type="button"
            onClick={onDeselectAll}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-bold text-zinc-400 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors uppercase tracking-wider"
          >
            <XSquare className="w-3 h-3" />
            {t('ingestion.channel.deselect_all')}
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('common.actions.search')}
          className="w-full bg-black/40 border border-zinc-800/50 rounded-lg pl-9 pr-3 py-2 text-xs text-zinc-300 focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-zinc-600"
        />
      </div>

      {/* Video list */}
      <div className="max-h-[340px] overflow-y-auto custom-scrollbar space-y-1 pr-1">
        {filteredVideos.map((video) => {
          const isSelected = selectedIds.has(video.video_id);
          const isDisabled = video.already_ingested;

          const rowClass = isDisabled
            ? 'opacity-40 cursor-not-allowed'
            : isSelected
              ? 'bg-emerald-500/10 border border-emerald-500/20'
              : 'bg-black/20 border border-transparent hover:bg-zinc-800/50 hover:border-zinc-700/50';

          return (
            <button
              key={video.video_id}
              type="button"
              onClick={() => !isDisabled && onToggle(video.video_id)}
              disabled={isDisabled}
              className={`w-full flex items-center gap-3 p-2 rounded-lg text-left transition-all group ${rowClass}`}
            >
              {/* Checkbox */}
              <div className="flex-shrink-0">
                {isDisabled && (
                  <CheckSquare className="w-4 h-4 text-zinc-600" />
                )}
                {!isDisabled && isSelected && (
                  <CheckSquare className="w-4 h-4 text-emerald-400" />
                )}
                {!isDisabled && !isSelected && (
                  <Square className="w-4 h-4 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
                )}
              </div>

              {/* Thumbnail */}
              <div className="w-16 h-9 rounded overflow-hidden flex-shrink-0 bg-zinc-900">
                {video.thumbnail && (
                  <img
                    src={video.thumbnail}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-medium truncate ${isDisabled ? 'text-zinc-500' : 'text-zinc-200'}`}>
                  {video.title}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="flex items-center gap-1 text-[10px] text-zinc-500">
                    <Clock className="w-2.5 h-2.5" />
                    {formatDuration(video.duration)}
                  </span>
                  {isDisabled && (
                    <span className="text-[9px] font-bold text-amber-500/70 uppercase tracking-wider">
                      {t('ingestion.channel.already_ingested')}
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </motion.div>
  );
}
