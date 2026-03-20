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
    <div className="flex flex-col h-full border border-border-subtle rounded-xl bg-panel-bg overflow-hidden">
      {/* Table Header / Toolbar */}
      <div className="p-4 border-b border-border-subtle flex flex-col md:flex-row md:items-center justify-between gap-4 bg-black/20">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-zinc-200">{t('sources.title')}</h3>
          <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-[10px] text-zinc-500 font-mono border border-zinc-700/50">
            {totalCount} {t('search.results.total').toUpperCase()}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Custom Type Filter Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsTypeOpen(!isTypeOpen)}
              onBlur={() => setTimeout(() => setIsTypeOpen(false), 200)}
              className="flex items-center gap-2 bg-zinc-900 border border-border-subtle hover:border-zinc-700 rounded-lg px-3 py-1.5 transition-colors min-w-[140px]"
            >
              <activeType.icon className="w-3.5 h-3.5 text-zinc-500" />
              <span className="text-sm text-zinc-300 flex-1 text-left">
                {activeType.label}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-zinc-500 transition-transform duration-200 ${isTypeOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {isTypeOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute top-full right-0 mt-2 w-48 bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden"
                >
                  {typeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        onTypeFilterChange(option.value);
                        setIsTypeOpen(false);
                      }}
                      className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors ${typeFilter === option.value
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
                        }`}
                    >
                      <option.icon className={`w-4 h-4 ${typeFilter === option.value ? 'text-emerald-400' : 'text-zinc-500'}`} />
                      <span className="flex-1 text-left">{option.label}</span>
                      {typeFilter === option.value && <Check className="w-4 h-4 text-emerald-400" />}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Search Input + Button */}
          <div className="flex items-center bg-zinc-800 border border-border-subtle rounded-lg overflow-hidden group focus-within:border-emerald-500/50 transition-all">
            <div className="relative flex items-center pl-3">
              <Search className="w-4 h-4 text-zinc-500 group-focus-within/search:text-emerald-400 transition-colors" />
              <input
                type="text"
                placeholder={`${t('common.actions.search')}...`}
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && onSearchSubmit()}
                className="bg-transparent pl-2 pr-4 py-1.5 text-sm text-zinc-200 focus:outline-none w-48 lg:w-64"
              />
            </div>
            <button
              onClick={onSearchSubmit}
              className="bg-zinc-900 hover:bg-zinc-950 text-emerald-500 px-4 py-1.5 text-xs font-bold border-l border-border-subtle transition-all active:scale-95 flex items-center gap-2 uppercase tracking-wider group/btn"
            >
              <Search className="w-3.5 h-3.5 group-hover/btn:scale-110 transition-transform" />
              {t('common.actions.search')}
            </button>
          </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-left text-sm text-zinc-400">
          <thead className="text-xs text-zinc-500 uppercase bg-black/40 sticky top-0 backdrop-blur-md">
            <tr>
              <th className="w-14 pl-4 pr-0 py-3"></th>
              <th className="pl-0 pr-4 py-3 font-medium text-left">{t('sources.table.title')}</th>
              <th className="px-4 py-3 font-medium text-left">{t('sources.table.type')}</th>
              <th className="px-4 py-3 font-medium text-left">{t('sources.table.origin')}</th>
              <th className="px-4 py-3 font-medium text-right">{t('sources.table.chunks')}</th>
              <th className="px-4 py-3 font-medium text-center">{t('sources.table.status')}</th>
              <th className="px-4 py-3 font-medium text-left">{t('sources.table.model')}</th>
              <th className="px-4 py-3 font-medium text-right">{t('sources.table.dimensions') || 'Dimensions'}</th>
              <th className="px-4 py-3 font-medium text-right">{t('sources.table.tokens')}</th>
              <th className="px-4 py-3 font-medium text-right">{t('sources.table.tokens_chunk') || 'Tokens(Chunk)'}</th>
              <th className="px-4 py-3 font-medium text-left">{t('sources.table.date')}</th>
              <th className="px-4 py-3 font-medium text-center sticky right-0 bg-[#080808] backdrop-blur-md z-10 shadow-[-4px_0_10px_rgba(0,0,0,0.5)]">{t('sources.table.actions') || 'Actions'}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {sources.length === 0 ? (
              <tr>
                <td colSpan={12} className="py-20 text-center">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                      <Search className="w-5 h-5 text-zinc-600" />
                    </div>
                    <div className="max-w-md mx-auto">
                      <p className="text-zinc-300 font-medium">{t('sources.table.none')}</p>
                      {emptyMessage && (
                        <p className="text-sm text-zinc-500 mt-2 leading-relaxed italic">
                          {emptyMessage}
                        </p>
                      )}
                      <button
                        onClick={() => setIsAddModalOpen(true)}
                        className="mt-6 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-black bg-emerald-500 rounded-lg hover:bg-emerald-400 transition-colors shadow-lg active:scale-95"
                      >
                        <Plus className="w-4 h-4" />
                        {t('common.actions.addData')}
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              sources.map((source) => {
                const Icon = getIcon(source.type);
                return (
                  <tr
                    key={source.id}
                    onClick={() => onRowClick(source)}
                    className="hover:bg-panel-hover cursor-pointer transition-colors group"
                  >
                    <td className="w-14 pl-4 pr-4 py-4 text-center">
                      <Icon className={`w-6 h-6 text-zinc-500 group-hover:text-emerald-400 transition-colors mx-auto`} />
                    </td>
                    <td className="pl-0 pr-4 py-4 font-medium text-zinc-200">{source.title}</td>
                    <td className="px-4 py-4">
                      <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider">
                        {t(`ingestion.sources.${source.type.toLowerCase()}`, { defaultValue: source.type.toUpperCase() })}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-zinc-500 font-mono text-xs truncate max-w-[160px]" title={source.origin || ''}>
                      {source.origin || 'n/a'}
                    </td>
                    <td className="px-4 py-4 text-right font-mono text-xs">{source.chunkCount}</td>
                    <td className="px-4 py-4 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${['done', 'finished', 'active', 'ingested'].includes(source.processingStatus.toLowerCase())
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : ['failed', 'error'].includes(source.processingStatus.toLowerCase())
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse'
                        }`}>
                        {source.processingStatus.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-xs font-mono text-zinc-400">{source.model || 'Unknown'}</td>
                    <td className="px-4 py-4 text-right text-xs font-mono text-zinc-400">{source.dimensions || '-'}</td>
                    <td className="px-4 py-4 text-right text-xs font-mono text-zinc-400">{source.totalTokens || '-'}</td>
                    <td className="px-4 py-4 text-right text-xs font-mono text-zinc-400">{source.maxTokensPerChunk || '-'}</td>
                    <td className="px-4 py-4 font-mono text-xs">{new Date(source.date).toLocaleDateString()}</td>
                    <td className="px-4 py-4 sticky right-0 bg-[#121212]/95 group-hover:bg-[#1C1C1E]/95 z-10 transition-colors shadow-[-4px_0_10px_rgba(0,0,0,0.3)]">
                      <div className="flex items-center justify-center gap-2">
                        {source.type.toLowerCase() === 'youtube' && (
                          <button
                            onClick={(e) => handleReprocess(e, source)}
                            disabled={reprocessingIds.has(source.id)}
                            title={t('common.actions.reprocess')}
                            className="p-1.5 rounded-lg bg-zinc-800 border border-white/5 text-zinc-400 hover:text-orange-400 hover:bg-orange-500/10 transition-all active:scale-95 disabled:opacity-50"
                          >
                            <RotateCcw className={`w-3.5 h-3.5 ${reprocessingIds.has(source.id) ? 'animate-spin text-emerald-400' : ''}`} />
                          </button>
                        )}
                        
                        <button
                          onClick={(e) => handleDelete(e, source)}
                          title={t('common.actions.delete')}
                          className="p-1.5 rounded-lg bg-zinc-800 border border-white/5 text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all active:scale-95"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-border-subtle flex items-center justify-between bg-black/20">
        <div className="flex items-center gap-6">
          <span className="text-xs text-zinc-500">
            {t('sources.table.pagination', { 
              start: totalCount > 0 ? startIndex + 1 : 0, 
              end: endIndex, 
              total: totalCount 
            })}
          </span>

          {onPageSizeChange && (
            <div className="flex items-center gap-2 border-l border-white/5 pl-6">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest">Rows:</span>
              <div className="flex items-center gap-1 bg-zinc-900/50 rounded-lg p-0.5 border border-white/5">
                {[10, 20, 30, 50].map((size) => (
                  <button
                    key={size}
                    onClick={() => onPageSizeChange(size)}
                    className={`px-2 py-1 text-[10px] font-bold rounded-md transition-all ${
                      pageSize === size 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                        : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="p-1.5 rounded-md border border-border-subtle hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs font-medium text-zinc-400 px-2">
            {t('sources.chunks.page', { current: page, total: totalPages })}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page === totalPages}
            className="p-1.5 rounded-md border border-border-subtle hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
