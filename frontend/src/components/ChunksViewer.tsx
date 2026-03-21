import React, {useEffect, useState} from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Database,
  Edit2,
  FileText,
  Hash,
  Info,
  Loader2,
  Save,
  Search,
  Trash2,
  Video,
  X,
  Youtube,
  BookOpen,
  Filter,
  Globe,
  Newspaper,
  Copy
} from 'lucide-react';
import {useAppContext} from '../store/AppContext';
import { useTranslation } from 'react-i18next';
import {AnimatePresence, motion} from 'motion/react';
import { api } from '../services/api';
import { Chunk } from '../types';

const getIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case 'youtube': return Youtube;
    case 'article': return Newspaper;
    case 'pdf': return FileText;
    case 'wikipedia': return BookOpen;
    case 'web': return Globe;
    default: return Filter;
  }
};

export function ChunksViewer() {
  const { t } = useTranslation();
  const { 
    subjects, 
    selectedSourceIdForDb, 
    setSelectedSourceIdForDb, 
    sources, 
    addToast, 
    goBack,
  } = useAppContext();
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState<Chunk | null>(null);
  const [editContent, setEditContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const pageSize = 20;

  const currentSource = React.useMemo(() => {
    return sources.find(s => s.id === selectedSourceIdForDb);
  }, [sources, selectedSourceIdForDb]);

  const currentSubject = React.useMemo(() => {
    if (!currentSource) return null;
    return subjects.find(s => s.id === currentSource.subjectId);
  }, [subjects, currentSource]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const chunksData = await api.fetchChunks(
          selectedSourceIdForDb || undefined,
          1000,
          0,
          searchQuery
        );
        setChunks(chunksData);
      } catch (err) {
        console.error('Error loading chunks:', err);
      } finally {
        setLoading(false);
      }
    };

    const debounceTimer = setTimeout(() => {
      loadData();
    }, 400);

    return () => clearTimeout(debounceTimer);
  }, [selectedSourceIdForDb, searchQuery]);

  const sourceMap = React.useMemo(() => {
    return new Map(sources.map(s => [s.id, s]));
  }, [sources]);

  const totalPages = Math.ceil(chunks.length / pageSize);
  const paginatedChunks = chunks.slice((page - 1) * pageSize, page * pageSize);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this chunk?')) {
      try {
        await api.deleteChunk(id);
        setChunks(chunks.filter(c => c.id !== id));
        addToast(t('notifications.chunk.deleted'), 'success');
      } catch (err) {
        console.error('Error deleting chunk:', err);
        addToast(t('notifications.chunk.error'), 'error');
      }
    }
  };

  const handleEdit = (chunk: Chunk, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedChunk(chunk);
    setEditContent(chunk.content);
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    if (!selectedChunk || isSaving) return;
    
    setIsSaving(true);
    try {
      await api.updateChunk(selectedChunk.id, editContent);
      setChunks(chunks.map(c => c.id === selectedChunk.id ? { ...c, content: editContent } : c));
      setIsModalOpen(false);
      setSelectedChunk(null);
      addToast(t('notifications.chunk.updated'), 'success');
    } catch (err) {
      console.error('Error updating chunk:', err);
      addToast(t('notifications.chunk.error'), 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    addToast(t('common.actions.copied'), 'success');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-black/20 backdrop-blur-sm">
        <div className="relative">
          <div className="w-12 h-12 rounded-full border-2 border-emerald-500/20 border-t-emerald-500 animate-spin" />
          <Loader2 className="w-6 h-6 text-emerald-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-8 max-w-[1600px] mx-auto h-full flex flex-col gap-6 overflow-hidden">
      {/* Top Navigation */}
      <div className="flex items-center gap-4 shrink-0">
        <button 
          onClick={() => {
            setSelectedSourceIdForDb(null);
            goBack();
          }}
          className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold text-zinc-100 tracking-tight">
          {currentSource?.title || t('sources.chunks.segment_prefix')}
        </h1>
      </div>

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8">
        {/* Main Content: Search + List */}
        <div className="flex flex-col gap-6 min-h-0">
          <div className="relative group shrink-0">
            <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-emerald-500 transition-colors" />
            <input 
              type="text" 
              placeholder={t('sources.chunks.search_placeholder')} 
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
              className="w-full bg-zinc-900/40 border border-white/5 rounded-xl pl-12 pr-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-white/10 focus:bg-zinc-900/60 transition-all"
            />
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar-premium pr-2 space-y-4">
            <AnimatePresence mode="popLayout">
              {paginatedChunks.length === 0 ? (
                <div className="py-20 text-center text-zinc-500">
                  <p>{t('search.results.none')}</p>
                </div>
              ) : (
                paginatedChunks.map((chunk, index) => (
                  <motion.div
                    key={chunk.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: (index % pageSize) * 0.02 }}
                    className="group bg-zinc-900/30 border border-white/[0.03] rounded-xl p-5 hover:bg-zinc-900/50 hover:border-white/[0.06] transition-all"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-zinc-100">
                          {t('sources.chunks.segment_prefix')} {chunk.index !== undefined ? chunk.index + 1 : (page - 1) * pageSize + index + 1}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-zinc-500 font-mono">
                          {chunk.content.length} {t('sources.chunks.chars').toLowerCase()}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-zinc-500 font-mono">
                          {chunk.tokens_count || 0} {t('sources.chunks.tokens').toLowerCase()}
                        </span>
                        <button 
                          onClick={() => copyToClipboard(chunk.content)}
                          className="p-1 rounded hover:bg-white/10 text-zinc-500 hover:text-zinc-300 transition-colors"
                          title="Copy to clipboard"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={(e) => handleEdit(chunk, e)} 
                          className="p-1.5 text-zinc-500 hover:text-emerald-400 hover:bg-emerald-400/10 rounded transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button 
                          onClick={(e) => handleDelete(chunk.id, e)} 
                          className="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-400/10 rounded transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    
                    <p className="text-[15px] text-zinc-400 leading-relaxed font-serif selection:bg-emerald-500/20">
                      {chunk.content}
                    </p>
                  </motion.div>
                ))
              )}
            </AnimatePresence>
          </div>

          {/* Local Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between py-4 border-t border-white/5 mt-auto shrink-0">
              <span className="text-[11px] text-zinc-500 font-medium">
                {t('sources.chunks.pagination', { 
                  start: Math.min(chunks.length, (page - 1) * pageSize + 1), 
                  end: Math.min(chunks.length, page * pageSize), 
                  total: chunks.length 
                })}
              </span>
              <div className="flex items-center gap-1.5">
                <button 
                  onClick={() => setPage(page - 1)} 
                  disabled={page === 1}
                  className="p-1.5 rounded-lg border border-white/5 bg-zinc-900/50 text-zinc-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <div className="flex items-center gap-1 mx-2">
                  {[...Array(totalPages)].map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setPage(i + 1)}
                      className={`w-6 h-6 rounded-md text-[10px] font-bold transition-all ${
                        page === i + 1 
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20' 
                        : 'text-zinc-600 hover:text-zinc-300'
                      }`}
                    >
                      {i + 1}
                    </button>
                  ))}
                </div>
                <button 
                  onClick={() => setPage(page + 1)} 
                  disabled={page === totalPages}
                  className="p-1.5 rounded-lg border border-white/5 bg-zinc-900/50 text-zinc-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar: Metadata */}
        <div className="hidden lg:flex flex-col gap-10 py-4 pr-4 overflow-y-auto custom-scrollbar-premium">
          <section className="space-y-4">
            <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-zinc-500">{t('sources.chunks.sidebar.title_tech')}</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-zinc-500">{t('sources.chunks.sidebar.total_chunks')}</span>
                <span className="text-sm text-zinc-200 font-mono font-medium">{currentSource?.chunkCount || 0}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-zinc-500">{t('sources.chunks.sidebar.total_tokens')}</span>
                <span className="text-sm text-zinc-200 font-mono font-medium">{currentSource?.totalTokens?.toLocaleString() || 0}</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-zinc-500">{t('sources.chunks.sidebar.tokens_per_chunk')}</span>
                <span className="text-sm text-zinc-200 font-mono font-medium">
                  {currentSource?.maxTokensPerChunk || 0} t/c
                </span>
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-zinc-500">{t('sources.chunks.sidebar.title_doc')}</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-zinc-500">{t('sources.chunks.sidebar.type')}</span>
                <span className="text-sm text-zinc-200 font-medium uppercase tracking-wider">
                  {currentSource?.type ? t(`ingestion.sources.${currentSource.type.toLowerCase()}`, { defaultValue: currentSource.type.toUpperCase() }) : 'N/A'}
                </span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-zinc-500">{t('sources.chunks.sidebar.model')}</span>
                <span className="text-sm text-zinc-200 font-mono truncate max-w-[180px]" title={currentSource?.model}>
                  {currentSource?.model || 'BAAI/bge-m3'}
                </span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-zinc-500">{t('sources.chunks.sidebar.size')}</span>
                <span className="text-sm text-zinc-200 font-mono">{currentSource?.dimensions || '1024'} {t('sources.chunks.sidebar.dims')}</span>
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <h3 className="text-[11px] font-black uppercase tracking-[0.2em] text-zinc-500">{t('sources.chunks.sidebar.title_access')}</h3>
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm text-zinc-500">{t('sources.chunks.sidebar.subject')}</span>
              <div className="flex items-center gap-2 max-w-[180px]">
                <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-[10px] font-black text-emerald-400 shrink-0">
                  {currentSubject?.name?.[0].toUpperCase() || 'S'}
                </div>
                <span className="text-sm text-zinc-300 truncate font-medium">{currentSubject?.name || t('sidebar.contexts.none')}</span>
              </div>
            </div>
          </section>

          {currentSource?.origin && (
            <section className="space-y-4 mt-auto">
               <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-2">
                 <p className="text-[10px] font-black uppercase tracking-widest text-zinc-600">{t('sources.chunks.sidebar.origin_url')}</p>
                 <a 
                   href={currentSource.origin} 
                   target="_blank" 
                   rel="noopener noreferrer"
                   className="text-xs text-emerald-500/70 hover:text-emerald-400 transition-colors break-all font-mono line-clamp-2"
                 >
                   {currentSource.origin}
                 </a>
               </div>
            </section>
          )}

          {/* Source Metadata Section */}
          {currentSource?.sourceMetadata && Object.keys(currentSource.sourceMetadata).length > 0 && (
            <section className="space-y-3 pt-6 border-t border-white/10">
              <h3 className="text-[10px] font-bold text-white/30 uppercase tracking-[0.1em] flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50" />
                {t('common.source_details', 'Source Details')}
              </h3>
              <div className="grid grid-cols-1 gap-2">
                {Object.entries(currentSource.sourceMetadata).map(([key, value]) => (
                  <div key={key} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] group hover:bg-white/[0.04] transition-all duration-300">
                    <span className="text-[10px] text-zinc-500 font-mono block uppercase mb-1.5 tracking-wider">{key.replace(/_/g, ' ')}</span>
                    <span className="text-[11px] text-zinc-300 font-medium break-all block leading-relaxed selection:bg-emerald-500/30">
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* Edit Modal */}
      <AnimatePresence>
        {isModalOpen && selectedChunk && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsModalOpen(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-xl"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 40 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 40 }}
              className="relative w-full max-w-4xl bg-zinc-950 border border-white/[0.08] rounded-[2.5rem] shadow-[0_32px_128px_-16px_rgba(0,0,0,0.8)] flex flex-col h-[85vh] min-h-[600px] overflow-hidden"
            >
              {/* Header */}
              <div className="p-8 border-b border-white/[0.05] flex items-center justify-between bg-white/[0.01]">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/10">
                    <Edit2 className="w-6 h-6 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-white tracking-tight">{t('common.actions.save')}</h3>
                    <p className="text-[10px] text-zinc-500 mt-0.5 font-mono font-bold tracking-widest flex items-center gap-2">
                       <span className="w-1 h-1 rounded-full bg-zinc-800" />
                       ID: {selectedChunk.id}
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="p-3 rounded-2xl text-zinc-500 hover:text-white hover:bg-white/5 transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Source Info Bar */}
              <div className="px-8 py-4 bg-black/40 border-b border-white/[0.05] flex flex-wrap items-center gap-6 text-xs">
                <div className="flex items-center gap-3 text-zinc-400">
                  <div className="p-1.5 rounded-lg bg-zinc-900 border border-white/5">
                    {React.createElement(getIcon(sourceMap.get(selectedChunk.content_source_id)?.type || ''), { className: "w-4 h-4 text-emerald-500/50" })}
                  </div>
                  <span className="font-bold text-zinc-200 tracking-tight">
                    {sourceMap.get(selectedChunk.content_source_id)?.title || 'Unknown Source'}
                  </span>
                </div>
                <div className="w-px h-4 bg-white/5 hidden sm:block" />
                <div className="flex items-center gap-2 text-zinc-500 font-mono font-bold">
                  <Hash className="w-3.5 h-3.5 opacity-40" />
                  <span>{selectedChunk.tokens_count || 0} tokens</span>
                </div>
              </div>

              {/* Editor Body */}
              <div className="p-8 flex-1 overflow-hidden flex flex-col gap-6">
                <div className="flex-1 flex flex-col">
                  <label className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.2em] mb-4 flex items-center gap-2 px-1">
                    <FileText className="w-3 h-3" />
                    {t('sources.chunks.content_label')}
                  </label>
                  <div className="flex-1 relative group/editor">
                    <div className="absolute inset-0 bg-emerald-500/5 blur-2xl opacity-0 group-focus-within/editor:opacity-100 transition-opacity pointer-events-none" />
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="relative z-10 w-full h-full bg-black/40 border border-white/[0.08] rounded-3xl p-6 text-base text-zinc-200 focus:outline-none focus:border-emerald-500/30 focus:bg-black/60 transition-all resize-none custom-scrollbar-premium font-serif leading-loose"
                      placeholder={t('sources.chunks.content_placeholder')}
                    />
                  </div>
                </div>

                <div className="p-5 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl flex items-start gap-4">
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/10 flex items-center justify-center shrink-0">
                    <Info className="w-4 h-4 text-emerald-500" />
                  </div>
                  <p className="text-xs text-emerald-500/70 leading-relaxed font-medium">
                    {t('sources.chunks.edit_warning')}
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="p-8 border-t border-white/[0.05] bg-black/40 flex items-center justify-between">
                <div className="flex items-center gap-4 px-4 py-2 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                  <span className="text-[10px] text-zinc-500 font-black uppercase tracking-widest">{t('sources.chunks.chars')}</span>
                  <span className="text-sm text-white font-black font-mono">{editContent.length.toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-4">
                  <button 
                    onClick={() => setIsModalOpen(false)}
                    className="px-6 py-2 text-sm font-bold text-zinc-500 hover:text-white transition-colors"
                  >
                    {t('common.actions.cancel')}
                  </button>
                  <button 
                    onClick={handleSave}
                    disabled={isSaving || !editContent.trim()}
                    className="group relative flex items-center gap-3 px-8 py-3 bg-emerald-500 hover:bg-emerald-400 text-black text-sm font-black rounded-2xl transition-all shadow-[0_12px_32px_-8px_rgba(16,185,129,0.3)] disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {t('common.actions.syncing')}
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        {t('common.actions.save')}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
