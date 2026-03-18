import React, { useState } from 'react';
import { ContentSource } from '../types';
import { useTranslation } from 'react-i18next';
import { FileText, Video, ChevronLeft, ChevronRight, Search, Filter, ChevronDown, Check, Database } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface SourcesTableProps {
  sources: ContentSource[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  onRowClick: (source: ContentSource) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSearchSubmit: () => void;
  typeFilter: string;
  onTypeFilterChange: (type: string) => void;
}

const TYPE_OPTIONS = [
  { value: 'all', label: 'All Types', icon: Filter }, // Needs i18n in rendering
  { value: 'video', label: 'Videos', icon: Video },
  { value: 'article', label: 'Articles', icon: FileText },
  { value: 'transcript', label: 'Transcripts', icon: FileText },
];

export function SourcesTable({
  sources, totalCount, page, pageSize, onPageChange, onRowClick,
  searchQuery, onSearchChange, onSearchSubmit, typeFilter, onTypeFilterChange
}: SourcesTableProps) {
  const { t } = useTranslation();
  const [isTypeOpen, setIsTypeOpen] = useState(false);
  const totalPages = Math.ceil(totalCount / pageSize);
  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalCount);

  const activeType = TYPE_OPTIONS.find(opt => opt.value === typeFilter) || TYPE_OPTIONS[0];

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
                {t(`sources.table.types.${activeType.value}`)}
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
                  {TYPE_OPTIONS.map((option) => (
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
                      <span className="flex-1 text-left">{t(`sources.table.types.${option.value}`)}</span>
                      {typeFilter === option.value && <Check className="w-4 h-4 text-emerald-400" />}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Search Input + Button */}
          <div className="flex items-center bg-zinc-900 border border-border-subtle rounded-lg overflow-hidden group focus-within:border-emerald-500/50 transition-colors">
            <div className="relative flex items-center pl-3">
              <Search className="w-4 h-4 text-zinc-500 group-focus-within:text-emerald-400 transition-colors" />
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
              className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-4 py-1.5 text-xs font-medium border-l border-border-subtle transition-colors"
            >
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
              <th className="pl-0 pr-6 py-3 font-medium text-left">{t('sources.table.title')}</th>
              <th className="px-6 py-3 font-medium text-left">{t('sources.table.origin')}</th>
              <th className="px-6 py-3 font-medium text-left">{t('sources.table.type')}</th>
              <th className="px-6 py-3 font-medium text-right">{t('sources.table.chunks')}</th>
              <th className="px-6 py-3 font-medium text-center">{t('sources.table.status')}</th>
              <th className="px-6 py-3 font-medium text-left">{t('sources.table.model')}</th>
              <th className="px-6 py-3 font-medium text-left">{t('sources.table.dimensions')}</th>
              <th className="px-6 py-3 font-medium text-left">{t('sources.table.date')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {sources.map((source) => (
              <tr
                key={source.id}
                onClick={() => onRowClick(source)}
                className="hover:bg-panel-hover cursor-pointer transition-colors group"
              >
                <td className="w-14 pl-4 pr-4 py-4 text-center">
                  {['video', 'youtube'].includes(source.type.toLowerCase()) ? (
                    <Video className="w-6 h-6 text-zinc-500 group-hover:text-blue-400 transition-colors mx-auto" />
                  ) : (
                    <FileText className="w-6 h-6 text-zinc-500 group-hover:text-amber-400 transition-colors mx-auto" />
                  )}
                </td>
                <td className="pl-0 pr-6 py-4 font-medium text-zinc-200">{source.title}</td>
                <td className="px-6 py-4 text-zinc-400 text-sm">{source.origin || 'Unknown'}</td>
                <td className="px-6 py-4">
                  <span className="text-xs text-zinc-400">
                    {source.type.toLowerCase() === 'youtube' ? 'YouTube' : t(`sources.table.types.${source.type.toLowerCase()}`, { defaultValue: source.type })}
                  </span>
                </td>
                <td className="px-6 py-4 text-right font-mono text-xs">{source.chunkCount}</td>
                <td className="px-6 py-4 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium border ${['done', 'finished', 'active', 'ingested'].includes(source.processingStatus.toLowerCase())
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : ['failed', 'error'].includes(source.processingStatus.toLowerCase())
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse'
                    }`}>
                    {source.processingStatus.toUpperCase()}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs font-mono text-zinc-400">{source.model || 'Unknown'}</td>
                <td className="px-6 py-4 text-xs font-mono text-zinc-400">{source.dimensions || '-'}</td>
                <td className="px-6 py-4">{new Date(source.date).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-border-subtle flex items-center justify-between bg-black/20">
        <span className="text-xs text-zinc-500">
          Showing <span className="text-zinc-300 font-medium">{startIndex + 1}</span> to <span className="text-zinc-300 font-medium">{endIndex}</span> of <span className="text-zinc-300 font-medium">{totalCount}</span> results
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="p-1.5 rounded-md border border-border-subtle hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-8 h-8" />
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
