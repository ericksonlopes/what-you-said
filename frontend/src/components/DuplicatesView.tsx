import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Copy, 
  Trash2, 
  CheckCircle, 
  AlertTriangle, 
  RefreshCw,
  ExternalLink,
  Loader2,
  Clock,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useAppContext } from '../store/AppContext';
import { api } from '../services/api';
import { ChunkDuplicate } from '../types';

export function DuplicatesView() {
  const { t } = useTranslation();
  const { addToast, selectedSubjects } = useAppContext();
  const [duplicates, setDuplicates] = useState<ChunkDuplicate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [filterStatus, setFilterStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;

  const fetchDuplicates = useCallback(async (isRefresh = false) => {
    if (isRefresh) setIsSyncing(true);
    else setIsLoading(true);
    
    try {
      const subject_ids = selectedSubjects.map(s => s.id);
      const offset = (page - 1) * pageSize;
      const { results, total: totalCount } = await api.fetchDuplicates(filterStatus, subject_ids, pageSize, offset);
      setDuplicates(results);
      setTotal(totalCount);
    } catch (err) {
      console.error('Failed to fetch duplicates:', err);
      addToast(t('common.errors.generic'), 'error');
    } finally {
      setIsLoading(false);
      setIsSyncing(false);
    }
  }, [filterStatus, selectedSubjects, addToast, t, page, pageSize]);

  useEffect(() => {
    fetchDuplicates();
  }, [fetchDuplicates]);

  // Reset page when filter or subjects change
  useEffect(() => {
    setPage(1);
  }, [filterStatus, selectedSubjects]);

  const handleUpdateStatus = async (id: string, status: string) => {
    try {
      await api.updateDuplicateStatus(id, status);
      addToast(t('common.actions.success'), 'success');
      fetchDuplicates();
    } catch (err) {
      console.error('Failed to update status:', err);
      addToast(t('common.errors.generic'), 'error');
    }
  };

  const handleDeactivate = async (chunkId: string) => {
    try {
      await api.deactivateChunk(chunkId);
      addToast(t('common.actions.success'), 'success');
      fetchDuplicates();
    } catch (err) {
      console.error('Failed to deactivate chunk:', err);
      addToast(t('common.errors.generic'), 'error');
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 }
  };

  return (
    <div className="p-8 pt-10 max-w-7xl mx-auto h-full flex flex-col overflow-hidden">
      <div className="mb-10 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-2xl bg-amber-500/10 border border-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.1)]">
              <Copy className="w-7 h-7 text-amber-400" />
            </div>
            <div>
              <h2 className="text-3xl font-black text-white tracking-tight leading-none">{t('operations.duplicatesTitle')}</h2>
              <p className="text-zinc-500 text-sm mt-2 font-medium">{t('operations.duplicatesDesc')}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
             <div className="flex p-1 bg-zinc-900 border border-white/5 rounded-xl">
                {['pending', 'reviewed', 'ignored'].map((status) => (
                  <button
                    key={status}
                    onClick={() => setFilterStatus(status)}
                    className={`px-4 py-1.5 rounded-lg text-xs font-black uppercase tracking-widest transition-all ${filterStatus === status ? 'bg-zinc-800 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
                  >
                    {t(`operations.${status}`)}
                  </button>
                ))}
             </div>

             <button 
                onClick={() => fetchDuplicates(true)}
                disabled={isSyncing}
                className="group p-2.5 text-zinc-400 bg-zinc-900 border border-white/5 rounded-xl hover:bg-zinc-800 hover:text-white transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${isSyncing ? 'animate-spin text-amber-500' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
              </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar pr-1 pb-10">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <Loader2 className="w-10 h-10 text-amber-500 animate-spin opacity-20" />
            <span className="text-[10px] font-black uppercase tracking-widest text-zinc-600">Analisando redundâncias...</span>
          </div>
        ) : duplicates.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-32 text-center bg-zinc-900/20 border border-dashed border-white/5 rounded-3xl"
          >
            <div className="w-20 h-20 rounded-full bg-zinc-900 border border-white/5 flex items-center justify-center mb-6 shadow-2xl">
              <CheckCircle className="w-10 h-10 text-emerald-500/20" />
            </div>
            <h3 className="text-zinc-200 font-bold text-xl mb-2">{t('operations.noDuplicates')}</h3>
            <p className="text-zinc-500 text-sm max-w-sm mx-auto leading-relaxed">Sua base de conhecimento parece estar limpa e sem redundâncias óbvias.</p>
          </motion.div>
        ) : (
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 gap-6"
          >
            {duplicates.map((dup) => (
              <motion.div 
                key={dup.id} 
                variants={itemVariants}
                className="group relative bg-[#121212]/40 backdrop-blur-md border border-white/5 rounded-2xl overflow-hidden hover:border-white/10 transition-all"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-amber-500/50 group-hover:bg-amber-500 transition-colors" />
                
                <div className="p-6">
                  {/* Header do Card */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2 px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-full">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-amber-500">Conflito de Similaridade</span>
                      </div>
                      <div className="flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/10 rounded-full">
                        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">Score:</span>
                        <span className="text-[10px] font-black text-white">{(dup.similarity * 100).toFixed(1)}%</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                       <button 
                         onClick={() => handleUpdateStatus(dup.id, 'ignored')}
                         className="px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest text-zinc-500 hover:text-white hover:bg-white/5 transition-all"
                       >
                         {t('operations.ignore')}
                       </button>
                       <button 
                         onClick={() => handleUpdateStatus(dup.id, 'reviewed')}
                         className="px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest bg-emerald-500 text-black hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/10"
                       >
                         Marcar como Revisado
                       </button>
                    </div>
                  </div>

                  {/* Comparação Lado a Lado */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                     {dup.chunks?.map((chunk, idx) => (
                       <div key={chunk.id} className="flex flex-col h-full bg-black/40 rounded-xl border border-white/5 overflow-hidden">
                          <div className="px-4 py-3 bg-white/5 border-b border-white/5 flex items-center justify-between">
                             <div className="flex items-center gap-2">
                                <span className="w-5 h-5 flex items-center justify-center rounded-md bg-zinc-800 text-[10px] font-black text-zinc-400">#{(idx + 1).toString().padStart(2, '0')}</span>
                                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-300 truncate max-w-[150px]">{chunk.source_title}</span>
                             </div>
                             <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleDeactivate(chunk.id)}
                                  className="p-1.5 rounded-md hover:bg-rose-500/20 text-zinc-500 hover:text-rose-400 transition-all"
                                  title={t('operations.deactivate')}
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                             </div>
                          </div>
                          <div className="p-4 flex-1">
                             <p className="text-zinc-400 text-[13px] leading-relaxed line-clamp-6 italic font-serif">
                                "{chunk.content}"
                             </p>
                          </div>
                          <div className="px-4 py-2 bg-white/[0.02] mt-auto flex items-center justify-between">
                             <span className="text-[9px] font-black uppercase tracking-widest text-zinc-600">ID: {chunk.id.slice(0, 8)}...</span>
                             <button className="text-[9px] font-black uppercase tracking-widest text-primary-500 flex items-center gap-1 hover:underline">
                                Ver Fonte <ExternalLink className="w-2.5 h-2.5" />
                             </button>
                          </div>
                       </div>
                     ))}
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>

      <div className="mt-auto pt-6 border-t border-white/5 flex items-center justify-between">
         <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
               <Clock className="w-3.5 h-3.5 text-zinc-600" />
               <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Total: {total} encontrados</span>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center gap-1 p-1 bg-zinc-900 rounded-xl border border-white/5">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-white disabled:opacity-20 transition-all"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <div className="text-[10px] font-black px-3 text-zinc-400 tabular-nums">
                  {page} <span className="mx-1 text-zinc-700">/</span> {totalPages}
                </div>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-white disabled:opacity-20 transition-all"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
         </div>
         
         <button 
           className="px-6 py-2 rounded-xl bg-zinc-900 border border-white/10 text-xs font-black uppercase tracking-widest text-zinc-300 hover:bg-zinc-800 hover:border-white/20 transition-all"
           onClick={async () => {
              setIsSyncing(true);
              try {
                await api.analyzeAllDuplicates();
                addToast('Análise global iniciada na fila de tarefas', 'info');
              } catch (err) {
                console.error('Analysis error:', err);
                addToast('Erro ao iniciar análise', 'error');
              } finally {
                setIsSyncing(false);
              }
           }}
          >
           Forçar Re-análise Global
         </button>
      </div>
    </div>
  );
}
