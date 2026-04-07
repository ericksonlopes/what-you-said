import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { SquarePlay, ListVideo, Radio, ArrowRight, Loader2 } from 'lucide-react';
import { api } from '../../../services/api';
import { ChannelVideoSelector } from './ChannelVideoSelector';

interface ChannelVideo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  thumbnail: string | null;
  already_ingested: boolean;
}

interface YoutubeSourceFormProps {
  readonly youtubeDataType: 'video' | 'playlist' | 'channel';
  readonly setYoutubeDataType: (val: 'video' | 'playlist' | 'channel') => void;
  readonly inputValue: string;
  readonly setInputValue: (val: string) => void;
  readonly targetSubjectId?: string;
  readonly channelVideos: ChannelVideo[];
  readonly setChannelVideos: (videos: ChannelVideo[]) => void;
  readonly selectedVideoIds: Set<string>;
  readonly setSelectedVideoIds: (ids: Set<string>) => void;
}

export function YoutubeSourceForm({
  youtubeDataType,
  setYoutubeDataType,
  inputValue,
  setInputValue,
  targetSubjectId,
  channelVideos,
  setChannelVideos,
  selectedVideoIds,
  setSelectedVideoIds,
}: YoutubeSourceFormProps) {
  const { t } = useTranslation();
  const [channelName, setChannelName] = useState('');
  const [isFetching, setIsFetching] = useState(false);
  const [fetchError, setFetchError] = useState('');

  const handleFetchChannel = useCallback(async () => {
    if (!inputValue.trim()) return;
    setIsFetching(true);
    setFetchError('');
    setChannelVideos([]);
    setSelectedVideoIds(new Set());

    try {
      const result = await api.previewYoutubeChannel({
        channel_url: inputValue.trim(),
        subject_id: targetSubjectId,
      });
      setChannelName(result.channel_name);
      setChannelVideos(result.videos);

      // Auto-select all new (non-ingested) videos
      const newIds = new Set(
        result.videos
          .filter((v) => !v.already_ingested)
          .map((v) => v.video_id)
      );
      setSelectedVideoIds(newIds);
    } catch (err: any) {
      setFetchError(err?.message || 'Failed to fetch channel videos');
    } finally {
      setIsFetching(false);
    }
  }, [inputValue, targetSubjectId, setChannelVideos, setSelectedVideoIds]);

  const handleToggleVideo = useCallback((videoId: string) => {
    const next = new Set(selectedVideoIds);
    if (next.has(videoId)) {
      next.delete(videoId);
    } else {
      next.add(videoId);
    }
    setSelectedVideoIds(next);
  }, [selectedVideoIds, setSelectedVideoIds]);

  const handleSelectAllNew = useCallback(() => {
    const newIds = new Set(
      channelVideos
        .filter((v) => !v.already_ingested)
        .map((v) => v.video_id)
    );
    setSelectedVideoIds(newIds);
  }, [channelVideos, setSelectedVideoIds]);

  const handleDeselectAll = useCallback(() => {
    setSelectedVideoIds(new Set());
  }, [setSelectedVideoIds]);

  const typeButtons = [
    { id: 'video' as const, icon: SquarePlay, label: t('ingestion.options.types.video') },
    { id: 'playlist' as const, icon: ListVideo, label: t('ingestion.options.types.playlist') },
    { id: 'channel' as const, icon: Radio, label: t('ingestion.options.types.channel') },
  ];

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex p-0.5 bg-black/40 rounded-xl border border-zinc-800/50 w-full">
        {typeButtons.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setYoutubeDataType(id);
              // Reset channel state when switching tabs
              if (id !== 'channel') {
                setChannelVideos([]);
                setSelectedVideoIds(new Set());
              }
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-lg transition-all ${
              youtubeDataType === id ? 'bg-zinc-800 text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {youtubeDataType === 'channel' ? (
        <>
          {/* Channel URL input */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300" htmlFor="channel-url">
              {t('ingestion.options.types.channel_url')}
            </label>
            <div className="flex gap-2">
              <input
                id="channel-url"
                type="url"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="https://www.youtube.com/@channel"
                className="flex-1 bg-black/40 border border-border-subtle rounded-xl px-4 py-3 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all placeholder:text-zinc-600 shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)]"
              />
              <button
                type="button"
                onClick={handleFetchChannel}
                disabled={!inputValue.trim() || isFetching}
                className="flex items-center gap-2 px-5 py-3 text-sm font-bold text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {isFetching ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('ingestion.channel.fetching')}
                  </>
                ) : (
                  t('ingestion.channel.fetch_btn')
                )}
              </button>
            </div>
          </div>

          {/* Error */}
          {fetchError && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-xs text-red-400">{fetchError}</p>
            </div>
          )}

          {/* Info hint (before fetch) */}
          {channelVideos.length === 0 && !isFetching && !fetchError && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
              <ArrowRight className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-zinc-400 leading-relaxed">
                {t('ingestion.options.types.channel_desc')}
              </p>
            </div>
          )}

          {/* All ingested message */}
          {channelVideos.length > 0 && channelVideos.every(v => v.already_ingested) && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <ArrowRight className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-amber-300 leading-relaxed">
                {t('ingestion.channel.no_new_videos')}
              </p>
            </div>
          )}

          {/* Video selector */}
          {channelVideos.length > 0 && (
            <ChannelVideoSelector
              channelName={channelName}
              videos={channelVideos}
              selectedIds={selectedVideoIds}
              onToggle={handleToggleVideo}
              onSelectAllNew={handleSelectAllNew}
              onDeselectAll={handleDeselectAll}
            />
          )}
        </>
      ) : (
        <>
          {/* Video/Playlist URL input */}
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
        </>
      )}
    </div>
  );
}
