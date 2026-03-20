import React, { useState } from 'react';
import { ContentSource } from '../types';
import { useTranslation } from 'react-i18next';
import { FileText, ChevronLeft, ChevronRight, Search, Filter, ChevronDown, Check, Database, Youtube, BookOpen, Globe, Newspaper, RotateCcw, Plus, Trash2, FileCode, FileSpreadsheet, FileImage, Presentation, FileAudio, FileVideo, Terminal, Share2, Layers } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useAppContext } from '../store/AppContext';
import { api } from '../services/api';

interface SourcesTableProps {
  sources: ContentSource[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  onPageSizeChange?: (newSize: number) => void;
  onRowClick: (source: ContentSource) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSearchSubmit: () => void;
  typeFilter: string;
  onTypeFilterChange: (type: string) => void;
  emptyMessage?: string;
}

const getIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case 'youtube': return Youtube;
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
    default: return Filter;
  }
};

export function SourcesTable({
  sources, totalCount, page, pageSize, onPageChange, onPageSizeChange, onRowClick,
  searchQuery, onSearchChange, onSearchSubmit, typeFilter, onTypeFilterChange,
  emptyMessage
}: SourcesTableProps) {
  const { t } = useTranslation();
  const { sourceTypes, addToast, refreshJobs, refreshSources, setIsAddModalOpen, deleteSource } = useAppContext();
  const [reprocessingIds, setReprocessingIds] = useState<Set<string>>(new Set());

  const handleReprocess = async (e: React.MouseEvent, source: ContentSource) => {
    e.stopPropagation();
    
    if (reprocessingIds.has(source.id)) return;
    
    if (source.type.toLowerCase() !== 'youtube') return;

    if (!source.origin) {
      addToast(t('ingestion.youtube.missing_origin'), 'error');
      return;
    }

    setReprocessingIds(prev => new Set(prev).add(source.id));
    try {
      await api.ingestYoutube({
        video_url: source.origin,
        reprocess: true,
        subject_id: source.subjectId
      });
      addToast(t('ingestion.youtube.reprocess_started'), 'success');
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
    if (!window.confirm(t('sources.delete_confirm'))) return;

    try {
      await deleteSource(source.id);
    } catch (err) {
      // Error handled in AppContext
    }
  };
  const typeOptions = [
    { value: 'all', label: t('sources.table.types.all'), icon: getIcon('all') },
    ...sourceTypes.map(type => ({
      value: type,
      label: t(`ingestion.sources.${type.toLowerCase()}`, { defaultValue: type.toUpperCase() }),
      icon: getIcon(type)
    }))
  ];

  const [isTypeOpen, setIsTypeOpen] = useState(false);
  const totalPages = Math.ceil(totalCount / pageSize);
  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalCount);

  const activeType = typeOptions.find(opt => opt.value === typeFilter) || typeOptions[0];

  return (
    <div className="flex flex-col h-full glass-card rounded-2xl relative shadow-2xl transition-all duration-500 hover:shadow-emerald-500/5">
      {/* Decorative top glow */}
      <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-emerald-500/20 to-transparent z-20" />

      {/* Table Header / Toolbar */}
      <div className="p-5 border-b border-white/5 flex flex-col lg:flex-row lg:items-center justify-between gap-6 bg-black/40 backdrop-blur-xl z-20">
        <div className="flex items-center gap-4">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 border border-emerald-500/30 shadow-lg shadow-emerald-500/10">
            <Layers className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white tracking-tight leading-tight">{t('sources.title')}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] text-zinc-500 font-medium uppercase tracking-widest">
                {totalCount} {t('search.results.total')}
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {/* Custom Type Filter Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsTypeOpen(!isTypeOpen)}
              onBlur={() => setTimeout(() => setIsTypeOpen(false), 200)}
              className="flex items-center gap-2.5 bg-white/5 border border-white/10 hover:border-emerald-500/40 rounded-xl px-4 py-2 transition-all duration-300 min-w-[160px] group glass-shine"
            >
              <activeType.icon className="w-4 h-4 text-emerald-400/70 group-hover:text-emerald-400 transition-colors" />
              <span className="text-sm text-zinc-300 flex-1 text-left font-medium">
                {activeType.label}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-zinc-500 transition-transform duration-300 ${isTypeOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {isTypeOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.95 }}
                  transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
                  className="absolute top-full right-0 mt-3 w-56 bg-zinc-950/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-50 py-2 p-1.5 max-h-[60vh] overflow-y-auto custom-scrollbar"
                >
                  {typeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        onTypeFilterChange(option.value);
                        setIsTypeOpen(false);
                      }}
                      className={`w-full flex items-center gap-3.5 px-3 py-2.5 text-sm rounded-xl transition-all duration-200 ${typeFilter === option.value
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'text-zinc-400 hover:bg-white/5 hover:text-white'
                        }`}
                    >
                      <div className={`p-1.5 rounded-lg transition-colors ${typeFilter === option.value ? 'bg-emerald-500/20' : 'bg-transparent'}`}>
                        <option.icon className={`w-4 h-4 ${typeFilter === option.value ? 'text-emerald-400' : 'text-zinc-500'}`} />
                      </div>
                      <span className="flex-1 text-left font-medium">{option.label}</span>
                      {typeFilter === option.value && (
                        <motion.div layoutId="active-check">
                          <Check className="w-4 h-4 text-emerald-400" />
                        </motion.div>
                      )}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Search Input + Button */}
          <div className="flex items-center bg-white/5 border border-white/10 rounded-xl overflow-hidden group focus-within:border-emerald-500/50 focus-within:ring-2 focus-within:ring-emerald-500/10 transition-all duration-300">
            <div className="relative flex items-center pl-4 py-2">
              <Search className="w-4 h-4 text-zinc-500 group-focus-within:text-emerald-400 transition-colors" />
              <input
                type="text"
                placeholder={`${t('common.actions.search')}...`}
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit()}
                className="bg-transparent pl-3 pr-4 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none w-48 lg:w-72 font-medium"
              />
            </div>
            <button
              onClick={onSearchSubmit}
              className="bg-emerald-500 hover:bg-emerald-400 text-black px-5 py-2.5 text-xs font-bold transition-all active:scale-95 flex items-center gap-2 uppercase tracking-widest glass-shine"
            >
              {t('common.actions.search')}
            </button>
          </div>

          <button
            onClick={() => setIsAddModalOpen(true)}
            className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-white hover:bg-emerald-500 hover:text-black hover:border-emerald-500 transition-all duration-300 active:scale-90 glass-shine"
            title={t('common.actions.addData')}
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="flex-1 overflow-x-hidden overflow-y-auto custom-scrollbar">
        <table className="w-full text-left border-separate border-spacing-0 table-fixed">
          <thead className="sticky top-0 z-10">
            <tr>
              <th className="w-14 pl-5 py-5 border-b border-white/5 font-semibold text-[11px] text-zinc-500 uppercase tracking-widest text-center italic">{t('sources.table.headers.icon')}</th>
              <th className="w-[32%] pl-2 pr-4 py-5 border-b border-white/5 font-semibold text-[11px] text-zinc-500 uppercase tracking-widest text-left">{t('sources.table.title')}</th>
              <th className="w-32 px-4 py-5 border-b border-white/5 font-semibold text-[11px] text-zinc-500 uppercase tracking-widest text-left">{t('sources.table.headers.type_date')}</th>
              <th className="w-24 px-4 py-5 border-b border-white/5 font-semibold text-[11px] text-zinc-500 uppercase tracking-widest text-center">{t('sources.table.status')}</th>
              <th className="w-auto px-4 py-5 border-b border-white/5 font-semibold text-[11px] text-zinc-500 uppercase tracking-widest text-left">{t('sources.table.headers.model_dims')}</th>
              <th className="w-28 px-4 py-5 border-b border-white/5 font-semibold text-[11px] text-zinc-500 uppercase tracking-widest text-right">{t('sources.table.headers.volume')}</th>
              <th className="w-24 px-6 py-5 border-b border-white/5 font-semibold text-[11px] text-zinc-500 uppercase tracking-widest text-center">
                {t('sources.table.actions')}
              </th>
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
                        <button
                          onClick={() => setIsAddModalOpen(true)}
                          className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold text-black bg-emerald-500 rounded-lg hover:bg-emerald-400 transition-all duration-300 shadow-[0_10px_20px_rgba(16,185,129,0.2)] active:scale-95 glass-shine"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          {t('common.actions.addData')}
                        </button>
                      </div>
                    </div>
                  </td>
                </motion.tr>
              ) : (
                sources.map((source, index) => {
                  const Icon = getIcon(source.type);
                  const isProcessing = !['done', 'finished', 'active', 'ingested'].includes(source.processingStatus.toLowerCase()) && 
                                     !['failed', 'error'].includes(source.processingStatus.toLowerCase());
                  const isFailed = ['failed', 'error'].includes(source.processingStatus.toLowerCase());
                  const isDone = ['done', 'finished', 'active', 'ingested'].includes(source.processingStatus.toLowerCase());

                  return (
                    <motion.tr
                      key={source.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                      onClick={() => onRowClick(source)}
                      className="hover:bg-white/[0.02] cursor-pointer transition-all duration-300 group relative"
                    >
                      <td className="pl-5 pr-2 py-5">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-300 ${
                          isDone ? 'bg-emerald-500/10 text-emerald-400/80 group-hover:text-emerald-400' :
                          isFailed ? 'bg-rose-500/10 text-rose-400/80 group-hover:text-rose-400' :
                          'bg-amber-500/10 text-amber-400/80 group-hover:text-amber-400'
                        }`}>
                           <Icon className="w-4.5 h-4.5 transition-transform duration-300 group-hover:scale-110" />
                        </div>
                      </td>
                      <td className="pl-2 pr-4 py-5">
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <span className="font-semibold text-zinc-100 group-hover:text-white transition-colors truncate text-sm">
                            {source.title}
                          </span>
                          <span className="truncate text-[11px] text-zinc-500 font-medium opacity-60" title={source.origin || ''}>
                            {source.origin || 'no-origin'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-5">
                        <div className="flex flex-col gap-1.5">
                           <span className="shrink-0 w-fit inline-flex items-center px-1.5 py-0.5 rounded bg-white/5 border border-white/5 text-[9px] font-black text-emerald-500/70 uppercase tracking-widest leading-none">
                            {source.type}
                          </span>
                          <span className="shrink-0 flex items-center gap-1.5 text-[10px] text-zinc-600 font-medium font-mono">
                             <FileText className="w-2.5 h-2.5 opacity-40" />
                            {new Date(source.date).toLocaleDateString()}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-5">
                        <div className="flex justify-center">
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border transition-all duration-300 ${
                            isDone ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/10 shadow-[0_4px_12px_rgba(16,185,129,0.1)]' :
                            isFailed ? 'bg-rose-500/10 text-rose-400 border-rose-500/10' :
                            'bg-amber-500/10 text-amber-400 border-amber-500/10 animate-pulse animate-glow'
                          }`}>
                            {source.processingStatus.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-5 min-w-0 overflow-hidden">
                        <div className="flex flex-col gap-1.5 min-w-0">
                           <div className="flex items-center gap-2 min-w-0 opacity-80 group-hover:opacity-100 transition-opacity">
                             <Database className="w-3 h-3 text-zinc-600 shrink-0" />
                             <span className="text-[11px] text-zinc-300 font-medium truncate">{source.model || 'N/A'}</span>
                           </div>
                            <span className="text-[11px] text-zinc-500 font-mono pl-5">{source.dimensions || '0'} {t('sources.chunks.sidebar.dims')}</span>
                        </div>
                      </td>
                      <td className="px-4 py-5 text-right">
                        <div className="flex flex-col gap-1.5 items-end">
                           <div className="flex items-center gap-1.5">
                             <span className="text-[11px] text-white font-mono font-bold leading-none">{source.totalTokens?.toLocaleString() || '0'}</span>
                             <span className="text-[8px] text-zinc-600 font-bold uppercase tracking-tight">{t('sources.table.headers.tok')}</span>
                           </div>
                            <div className="flex flex-col items-end gap-0.5 opacity-60 group-hover:opacity-100 transition-opacity">
                              <span className="text-[11px] text-zinc-400 font-mono italic leading-none">{source.chunkCount || '0'} {t('sources.table.chunks').toLowerCase()}</span>
                              <span className="text-[11px] text-zinc-500 font-mono leading-none">{source.maxTokensPerChunk || '0'} t/c</span>
                            </div>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex items-center justify-center gap-2.5">
                          {source.type.toLowerCase() === 'youtube' && (
                            <button
                              onClick={(e) => handleReprocess(e, source)}
                              disabled={reprocessingIds.has(source.id)}
                              className="p-1.5 rounded-lg bg-white/5 border border-white/5 text-zinc-400 hover:text-orange-400 hover:bg-orange-500/10 hover:border-orange-500/10 transition-all active:scale-95 disabled:opacity-50"
                            >
                              <RotateCcw className={`w-3.5 h-3.5 ${reprocessingIds.has(source.id) ? 'animate-spin' : ''}`} />
                            </button>
                          )}
                          <button
                            onClick={(e) => handleDelete(e, source)}
                            className="p-1.5 rounded-lg bg-white/5 border border-white/5 text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/10 transition-all active:scale-95"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
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
            <span className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest">Showing</span>
            <span className="text-xs text-zinc-400 font-medium">
              <span className="text-white font-bold">{totalCount > 0 ? startIndex + 1 : 0}</span> to <span className="text-white font-bold">{endIndex}</span> of <span className="text-white font-bold">{totalCount}</span>
            </span>
          </div>

          {onPageSizeChange && (
            <div className="hidden md:flex items-center gap-3 border-l border-white/5 pl-8">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Rows per page</span>
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
    </div>
  );
}
