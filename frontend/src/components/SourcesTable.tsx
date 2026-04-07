import React, { useState } from 'react';
import { ContentSource } from '../types';
import { useTranslation } from 'react-i18next';
import { FileText, ChevronLeft, ChevronRight, Search, Database, SquarePlay, BookOpen, Globe, Newspaper, RotateCcw, Trash2, Edit3, FileCode, FileSpreadsheet, FileImage, Presentation, FileAudio, FileVideo, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useAppContext } from '../store/AppContext';
import { api } from '../services/api';
import { EditSourceModal } from './EditSourceModal';

interface SourcesTableProps {
  readonly sources: ContentSource[];
  readonly totalCount: number;
  readonly page: number;
  readonly pageSize: number;
  readonly onPageChange: (newPage: number) => void;
  readonly onPageSizeChange?: (newSize: number) => void;
  readonly onRowClick: (source: ContentSource) => void;
  readonly searchQuery: string;
  readonly onSearchChange: (query: string) => void;
  readonly onSearchSubmit: () => void;
  readonly typeFilter: string;
  readonly onTypeFilterChange: (type: string) => void;
  readonly emptyMessage?: string;
}

const getIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case 'youtube': return SquarePlay;
    case 'article': return Newspaper;
    case 'pdf': return FileText;
    case 'docx':
    case 'doc':
    case 'file':
    case 'txt': return FileText;
    case 'pptx':
    case 'ppt': return Presentation;
    case 'xlsx':
    case 'xls':
    case 'csv': return FileSpreadsheet;
    case 'markdown':
    case 'md':
    case 'html':
    case 'asciidoc':
    case 'latex': return FileCode;
    case 'image': return FileImage;
    case 'video': return FileVideo;
    case 'audio': return FileAudio;
    case 'wikipedia': return BookOpen;
    case 'web': return Globe;
    case 'notion': return Database;
    case 'all': return Layers;
    default: return FileText;
  }
};

const getStatusIconBgClass = (isDone: boolean, isFailed: boolean, isCancelled: boolean, isAwaiting: boolean) => {
  if (isDone) return 'bg-emerald-500/10 text-emerald-400/80 group-hover:text-emerald-400';
  if (isFailed) return 'bg-rose-500/10 text-rose-400/80 group-hover:text-rose-400';
  if (isCancelled) return 'bg-zinc-500/10 text-zinc-500 group-hover:text-zinc-400';
  if (isAwaiting) return 'bg-blue-500/10 text-blue-400/80 group-hover:text-blue-400';
  return 'bg-amber-500/10 text-amber-400/80 group-hover:text-amber-400';
};

const getStatusBadgeClass = (isDone: boolean, isFailed: boolean, isCancelled: boolean, isAwaiting: boolean) => {
  if (isDone) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/10 shadow-[0_4px_12px_rgba(16,185,129,0.1)]';
  if (isFailed) return 'bg-rose-500/10 text-rose-400 border-rose-500/10';
  if (isCancelled) return 'bg-zinc-500/10 text-zinc-500 border-zinc-500/10';
  if (isAwaiting) return 'bg-blue-500/10 text-blue-400 border-blue-500/10 animate-pulse animate-glow';
  return 'bg-amber-500/10 text-amber-400 border-amber-500/10 animate-pulse animate-glow';
};


export function SourcesTable({
  sources, totalCount, page, pageSize, onPageChange, onPageSizeChange, onRowClick,
  searchQuery, onSearchChange, onSearchSubmit, typeFilter, onTypeFilterChange,
  emptyMessage
}: SourcesTableProps) {
  const { t } = useTranslation();
  const { addToast, refreshJobs, refreshSources, deleteSource } = useAppContext();
  const [reprocessingIds, setReprocessingIds] = useState<Set<string>>(new Set());
  const [editingSource, setEditingSource] = useState<ContentSource | null>(null);

  const handleReprocess = async (e: React.MouseEvent, source: ContentSource) => {
    e.stopPropagation();
    
    if (reprocessingIds.has(source.id)) return;
    
    if (source.type.toLowerCase() !== 'youtube' && source.type.toLowerCase() !== 'web') return;

    if (!source.origin) {
      addToast(t('ingestion.youtube.missing_origin'), 'error');
      return;
    }

    setReprocessingIds(prev => new Set(prev).add(source.id));
    try {
      if (source.type.toLowerCase() === 'youtube') {
        await api.ingestYoutube({
          video_url: source.origin,
          reprocess: true,
          subject_id: source.subjectId
        });
      } else if (source.type.toLowerCase() === 'web') {
        await api.ingestWeb({
          url: source.origin,
          reprocess: true,
          subject_id: source.subjectId
        });
      }
      addToast(t('ingestion.url.reprocess_started'), 'success');
      refreshJobs();
      refreshSources();
    } catch (err: any) {
      let errorMessage = err.message || t('ingestion.youtube.reprocess_error');
      
      // Map backend error messages to localized keys
      if (errorMessage.includes('Transcripts are disabled')) {
        errorMessage = t('ingestion.youtube.errors.disabled_transcripts');
      } else if (errorMessage.includes('No transcript found')) {
        errorMessage = t('ingestion.youtube.errors.no_transcript');
      } else if (errorMessage.includes('unavailable')) {
        errorMessage = t('ingestion.youtube.errors.unavailable');
      }
      
      addToast(errorMessage, 'error');
    } finally {
      setReprocessingIds(prev => {
        const next = new Set(prev);
        next.delete(source.id);
        return next;
      });
    }
  };

  const handleDelete = async (e: React.MouseEvent, source: ContentSource) => {
    e.stopPropagation();
    if (!globalThis.confirm(t('sources.delete_confirm'))) return;

    try {
      await deleteSource(source.id);
    } catch (err) {
      console.error('Failed to delete source:', err);
    }
  };

  const handleEdit = (e: React.MouseEvent, source: ContentSource) => {
    e.stopPropagation();
    setEditingSource(source);
  };
  const totalPages = Math.ceil(totalCount / pageSize);
  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalCount);

  return (
    <div className="flex flex-col h-full bg-zinc-900/40 border border-white/5 rounded-2xl relative shadow-2xl backdrop-blur-sm overflow-hidden transition-all duration-500 hover:shadow-emerald-500/5">

      {/* Table Content */}
      <div className="flex-1 overflow-x-hidden overflow-y-auto custom-scrollbar">
        <table className="w-full text-left border-separate border-spacing-0 table-fixed">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-white/5 text-[10px] font-black text-zinc-500 uppercase tracking-widest bg-black/20">
              <th className="w-14 pl-5 py-4 text-center">{t('sources.table.headers.icon')}</th>
              <th className="w-[32%] pl-2 pr-4 py-4 text-left">{t('sources.table.title')}</th>
              <th className="w-32 px-4 py-4 text-left">{t('sources.table.headers.type_date')}</th>
              <th className="w-32 px-4 py-4 text-center">{t('sources.table.status')}</th>
              <th className="w-auto px-4 py-4 text-left">{t('sources.table.headers.model_dims')}</th>
              <th className="w-28 px-4 py-4 text-right">{t('sources.table.headers.volume')}</th>
              <th className="w-36 px-6 py-4 text-center">{t('sources.table.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            <AnimatePresence mode="popLayout">
              {sources.length === 0 ? (
                <motion.tr
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <td colSpan={7} className="py-24 text-center">
                    <div className="flex flex-col items-center justify-center gap-6">
                      <div className="relative">
                        <div className="w-16 h-16 rounded-2xl bg-zinc-900/50 border border-white/5 flex items-center justify-center shadow-inner">
                          <Search className="w-6 h-6 text-zinc-700" />
                        </div>
                      </div>
                      <div className="max-w-md mx-auto space-y-2">
                        <p className="text-zinc-200 font-semibold">{t('sources.table.none')}</p>
                        <p className="text-[10px] font-black uppercase tracking-widest text-zinc-600 mt-2">{t('sources.table.empty_hint')}</p>
                      </div>
                    </div>
                  </td>
                </motion.tr>
              ) : (
                sources.map((source, index) => {
                  const Icon = getIcon(source.type);
                  const isFailed = ['failed', 'error'].includes(source.processingStatus.toLowerCase());
                  const isDone = ['done', 'finished', 'active', 'ingested'].includes(source.processingStatus.toLowerCase());
                  const isCancelled = source.processingStatus.toLowerCase() === 'cancelled';
                  const isAwaiting = source.processingStatus.toLowerCase() === 'awaiting_verification';

                  return (
                    <motion.tr
                      key={source.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                      onClick={() => onRowClick(source)}
                      className="hover:bg-white/5 cursor-pointer transition-all group relative border-b border-transparent hover:border-white/5"
                    >
                      <td className="pl-5 pr-2 py-3">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all ${getStatusIconBgClass(isDone, isFailed, isCancelled, isAwaiting)}`}>
                           <Icon className="w-4 h-4 transition-transform group-hover:scale-110" />
                        </div>
                      </td>
                      <td className="pl-2 pr-4 py-3">
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <span className="text-sm font-bold text-zinc-100 group-hover:text-white transition-colors truncate block">
                            {source.title}
                          </span>
                          <span className="text-[9px] font-black uppercase tracking-widest text-zinc-600 group-hover:text-zinc-500 truncate" title={source.origin || ''}>
                            {source.origin || 'no-origin'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-1.5">
                           <span className="shrink-0 w-fit inline-flex items-center px-1.5 py-0.5 rounded bg-white/5 border border-white/5 text-[9px] font-black text-emerald-500/70 uppercase tracking-widest leading-none">
                            {source.type}
                          </span>
                          <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest font-mono">
                            {new Date(source.date).toLocaleDateString()}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col items-center gap-1">
                           <span 
                            title={source.errorMessage || source.statusMessage || source.processingStatus}
                            className={`inline-flex items-center px-2 py-1 rounded-full text-[9px] font-black uppercase tracking-wider whitespace-nowrap border transition-all ${getStatusBadgeClass(isDone, isFailed, isCancelled, isAwaiting)}`}
                          >
                            {isAwaiting ? t('common.status.awaiting_verification') : 
                             isDone ? t('common.status.done') :
                             isFailed ? t('common.status.failed') :
                             isCancelled ? t('common.status.cancelled') :
                             source.processingStatus.toUpperCase()}
                          </span>
                          {(isFailed || source.statusMessage) && (
                            <span className={`text-[8px] font-black uppercase tracking-tight text-center max-w-[100px] truncate ${isFailed ? 'text-rose-500' : 'text-blue-400'}`}>
                              {source.errorMessage || source.statusMessage}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 min-w-0 overflow-hidden">
                        <div className="flex flex-col gap-1 min-w-0">
                           <div className="flex items-center gap-2 min-w-0">
                             <Database className="w-3 h-3 text-zinc-600 shrink-0" />
                             <span className="text-[10px] text-zinc-300 font-black uppercase tracking-widest truncate">{source.model || 'N/A'}</span>
                           </div>
                            <span className="text-[10px] text-zinc-500 font-black uppercase tracking-widest font-mono pl-5">{source.dimensions || '0'} {t('sources.chunks.sidebar.dims')}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex flex-col gap-1 items-end">
                           <div className="flex items-center gap-1.5">
                             <span className="text-[10px] text-white font-mono font-black leading-none">{source.totalTokens?.toLocaleString() || '0'}</span>
                             <span className="text-[8px] text-zinc-600 font-black uppercase tracking-widest">{t('sources.table.headers.tok')}</span>
                           </div>
                            <div className="flex flex-col items-end gap-0.5 opacity-60 group-hover:opacity-100 transition-opacity">
                              <span className="text-[10px] text-zinc-400 font-mono leading-none">{source.chunkCount || '0'} {t('sources.table.chunks').toLowerCase()}</span>
                              <span className="text-[10px] text-zinc-500 font-mono leading-none">{source.maxTokensPerChunk || '0'} t/c</span>
                            </div>
                        </div>
                      </td>
                      <td className="px-6 py-3">
                        <div className="flex items-center justify-center gap-1.5 p-1 bg-white/[0.03] border border-white/5 rounded-2xl shadow-inner">
                          {['youtube', 'web'].includes(source.type.toLowerCase()) && (
                            <button
                              onClick={(e) => handleReprocess(e, source)}
                              disabled={reprocessingIds.has(source.id)}
                              className="flex items-center justify-center w-10 h-10 rounded-xl hover:bg-orange-500/20 text-orange-400/70 hover:text-orange-400 transition-all duration-300 active:scale-90"
                              title={t('common.actions.reprocess')}
                            >
                              <RotateCcw className={`w-4.5 h-4.5 ${reprocessingIds.has(source.id) ? 'animate-spin' : ''}`} />
                            </button>
                          )}
                          <button
                            onClick={(e) => handleEdit(e, source)}
                            className="flex items-center justify-center w-10 h-10 rounded-xl hover:bg-emerald-500/20 text-emerald-400/70 hover:text-emerald-400 transition-all duration-300 active:scale-90"
                            title={t('sources.notifications.edit_title')}
                          >
                            <Edit3 className="w-4.5 h-4.5" />
                          </button>
                          <button
                            onClick={(e) => handleDelete(e, source)}
                            className="flex items-center justify-center w-10 h-10 rounded-xl hover:bg-rose-500/20 text-rose-400/70 hover:text-rose-400 transition-all duration-300 active:scale-90"
                            title={t('common.actions.delete')}
                          >
                            <Trash2 className="w-4.5 h-4.5" />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  );
                })
              )}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-5 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between gap-4 bg-black/40 backdrop-blur-xl z-20">
        <div className="flex items-center gap-8">
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest">{t('sources.table.showing')}</span>
            <span className="text-xs text-zinc-400 font-medium">
              <span className="text-white font-bold">{totalCount > 0 ? startIndex + 1 : 0}</span> to <span className="text-white font-bold">{endIndex}</span> of <span className="text-white font-bold">{totalCount}</span>
            </span>
          </div>

          {onPageSizeChange && (
            <div className="hidden md:flex items-center gap-3 border-l border-white/5 pl-8">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">{t('sources.table.rows_per_page')}</span>
              <div className="flex items-center gap-1.5 bg-white/5 rounded-xl p-1 border border-white/5">
                {[10, 20, 30, 50].map((size) => (
                  <button
                    key={size}
                    onClick={() => onPageSizeChange(size)}
                    className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-all duration-300 ${
                      pageSize === size 
                        ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' 
                        : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="p-2.5 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 hover:border-white/20 disabled:opacity-20 disabled:cursor-not-allowed transition-all duration-300 active:scale-90"
          >
            <ChevronLeft className="w-4 h-4 text-zinc-300" />
          </button>
          
          <div className="flex items-center gap-2 px-3">
            <span className="text-xs font-bold text-white">{page}</span>
            <span className="text-zinc-600 font-bold text-[10px]">/</span>
            <span className="text-xs font-bold text-zinc-500">{totalPages || 1}</span>
          </div>

          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page === totalPages || totalPages === 0}
            className="p-2.5 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 hover:border-white/20 disabled:opacity-20 disabled:cursor-not-allowed transition-all duration-300 active:scale-90"
          >
            <ChevronRight className="w-4 h-4 text-zinc-300" />
          </button>
        </div>
      </div>

      <EditSourceModal
        isOpen={!!editingSource}
        onClose={() => setEditingSource(null)}
        source={editingSource}
      />
    </div>
  );
}
