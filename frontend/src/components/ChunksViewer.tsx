import React, { useState, useEffect } from 'react';
import { Search, Edit2, Trash2, Database, ChevronLeft, ChevronRight, Save, X, Loader2, FileText, Hash, Info, Video } from 'lucide-react';
import { useAppContext } from '../store/AppContext';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';

export function ChunksViewer() {
  const { subjects, selectedSubjects, selectedSourceIdForDb, setSelectedSourceIdForDb, sources, addToast, setCurrentView } = useAppContext();
  const [chunks, setChunks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState<any>(null);
  const [editContent, setEditContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const pageSize = 10;

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
          100,
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

  // We now use chunks directly from the server-side filtered results
  const totalPages = Math.ceil(chunks.length / pageSize);
  const paginatedChunks = chunks.slice((page - 1) * pageSize, page * pageSize);

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this chunk?')) {
      try {
        await api.deleteChunk(id);
        setChunks(chunks.filter(c => c.id !== id));
      } catch (err) {
        console.error('Error deleting chunk:', err);
        alert('Failed to delete chunk.');
      }
    }
  };

  const handleEdit = (chunk: any) => {
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
      addToast('Knowledge chunk updated successfully!', 'success');
    } catch (err) {
      console.error('Error updating chunk:', err);
      addToast('Failed to update chunk.', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto h-full flex flex-col">
      {/* Navigation Breadcrumb & Back Button */}
      <div className="mb-6 flex items-center gap-4">
        <button 
          onClick={() => {
            setSelectedSourceIdForDb(null);
            setCurrentView('sources');
          }}
          className="p-2 rounded-xl bg-zinc-900 border border-border-subtle hover:border-zinc-600 text-zinc-400 hover:text-white transition-all group shadow-sm"
          title="Return to Sources"
        >
          <ChevronLeft className="w-5 h-5 group-hover:-translate-x-0.5 transition-transform" />
        </button>
        <div className="flex flex-col">
          <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
            <Database className="w-3 h-3" />
            <span>{currentSubject?.name || 'Knowledge Base'}</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-emerald-500">Chunks Explorer</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight mt-0.5">
            {currentSource?.title || 'Unknown Source'}
          </h2>
        </div>
      </div>

      <div className="mb-8 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <p className="text-zinc-400 text-sm">Managing segments stored in vector index.</p>
            {currentSource?.origin && (
              <span className="px-2 py-0.5 rounded bg-zinc-800/50 border border-zinc-700/50 text-[10px] text-zinc-500 font-mono truncate max-w-[200px]">
                {currentSource.origin}
              </span>
            )}
          </div>
        </div>
        <div className="relative w-full lg:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input 
            type="text" 
            placeholder="Search in these chunks..." 
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            className="w-full bg-black/40 border border-border-subtle rounded-xl pl-9 pr-4 py-2 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-colors"
          />
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="overflow-y-auto flex-1 custom-scrollbar space-y-4 pr-2">
          {paginatedChunks.length === 0 ? (
            <div className="p-12 text-center text-zinc-500 bg-[#121212] border border-border-subtle rounded-2xl">
              No chunks found matching your criteria.
            </div>
          ) : (
            paginatedChunks.map((chunk, index) => (
              <div key={chunk.id} className="bg-[#121212] border border-border-subtle rounded-xl p-5 hover:border-zinc-700 transition-colors group">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                    <h3 className="text-sm font-bold text-white truncate max-w-[300px]">
                      {sourceMap.get(chunk.content_source_id)?.title || 'Unknown Source'} 
                      <span className="ml-2 text-zinc-500 font-normal">#{(page - 1) * pageSize + index + 1}</span>
                    </h3>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-zinc-800/50 border border-zinc-700/50 text-[10px] text-zinc-400 whitespace-nowrap">
                        {chunk.content.length} chars
                      </span>
                      <span className="px-2 py-0.5 rounded bg-zinc-800/50 border border-zinc-700/50 text-[10px] text-zinc-400 whitespace-nowrap">
                        {chunk.tokens_count || 0} tokens
                      </span>
                      <span className="px-2 py-0.5 rounded bg-zinc-800/50 border border-zinc-700/50 text-[10px] text-zinc-400 uppercase">
                        pt
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between md:justify-end gap-4">
                    <span className="text-[10px] text-zinc-600 font-mono">ID: {chunk.id}</span>
                    <div className="flex items-center gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                      <button onClick={() => handleEdit(chunk)} className="p-1.5 bg-blue-500/10 text-blue-400 hover:bg-blue-400/20 rounded transition-colors" title="Edit Chunk">
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button onClick={() => handleDelete(chunk.id)} className="p-1.5 bg-red-500/10 text-red-400 hover:bg-red-400/20 rounded transition-colors" title="Delete Chunk">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
                
                <p className="text-sm text-zinc-400 leading-relaxed">
                  {chunk.content}
                </p>
              </div>
            ))
          )}
        </div>
        
        {/* Pagination */}
        {chunks.length > 0 && (
          <div className="pt-4 mt-4 border-t border-border-subtle flex items-center justify-between shrink-0">
            <span className="text-xs text-zinc-500">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, chunks.length)} of {chunks.length} chunks
            </span>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs font-medium text-zinc-300 px-2">
                Page {page} of {Math.max(1, totalPages)}
              </span>
              <button 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
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
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-4xl bg-[#121212] border border-border-subtle rounded-2xl shadow-2xl flex flex-col h-[85vh] min-h-[600px] overflow-hidden"
            >
              {/* Header */}
              <div className="p-6 border-b border-border-subtle flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <Edit2 className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white tracking-tight">Edit Knowledge Chunk</h3>
                    <p className="text-xs text-zinc-500 mt-0.5 font-mono">ID: {selectedChunk.id}</p>
                  </div>
                </div>
                <button 
                  onClick={() => setIsModalOpen(false)}
                  className="p-2 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Source Info Bar */}
              <div className="px-6 py-3 bg-black/20 border-b border-border-subtle flex items-center gap-4 text-xs">
                <div className="flex items-center gap-2.5 text-zinc-400">
                  {['video', 'youtube'].includes(sourceMap.get(selectedChunk.content_source_id)?.type.toLowerCase() || '') ? (
                    <Video className="w-4 h-4" />
                  ) : (
                    <FileText className="w-4 h-4" />
                  )}
                  <span className="font-medium text-zinc-300">
                    {sourceMap.get(selectedChunk.content_source_id)?.title || 'Unknown Source'}
                  </span>
                </div>
                <div className="w-px h-3 bg-zinc-800" />
                <div className="flex items-center gap-1.5 text-zinc-400">
                  <Hash className="w-3.5 h-3.5" />
                  <span>{selectedChunk.tokens_count || 0} tokens</span>
                </div>
              </div>

              {/* Editor Body */}
              <div className="p-6 flex-1 overflow-hidden flex flex-col gap-4">
                <div className="flex-1 flex flex-col">
                  <label className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                    <FileText className="w-3 h-3" />
                    Content
                  </label>
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="flex-1 bg-black/50 border border-border-subtle rounded-xl p-4 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-all resize-none custom-scrollbar font-serif leading-relaxed"
                    placeholder="Enter chunk content..."
                  />
                </div>

                <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl flex items-start gap-3">
                  <Info className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <p className="text-[11px] text-emerald-500/80 leading-relaxed">
                    Editing this content will trigger a re-indexing in the vector database (Weaviate). This ensures that future semantic searches will reflect the updated text.
                  </p>
                </div>
              </div>

              {/* Footer */}
              <div className="p-6 border-t border-border-subtle bg-black/20 flex items-center justify-between">
                <div className="text-xs text-zinc-500">
                  Characters: <span className="text-zinc-300 font-medium">{editContent.length}</span>
                </div>
                <div className="flex items-center gap-3">
                  <button 
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={handleSave}
                    disabled={isSaving || !editContent.trim()}
                    className="flex items-center gap-2 px-6 py-2 bg-emerald-500 hover:bg-emerald-400 text-black text-sm font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        Save Changes
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
