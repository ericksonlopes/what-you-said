import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Server, 
  RefreshCw, 
  Clock, 
  Code, 
  ChevronDown, 
  ChevronUp, 
  Terminal,
  Trash2,
  Activity,
  Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppContext } from '../store/AppContext';
import { RawQueueTask } from '../types';
import { api } from '../services/api';


function TaskCard({ task, index, onRemove }: Readonly<{ task: RawQueueTask, index: number, onRemove: (idx: number) => Promise<void> }>) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRemoving, setIsRemoving] = useState(false);

  // Format timestamp (Redis uses unix seconds)
  const enqueuedDate = new Date(task.enqueued_at * 1000);
  const timeAgo = Math.floor((Date.now() - enqueuedDate.getTime()) / 1000);
  const timeStr = timeAgo < 60 ? `${timeAgo}s` : `${Math.floor(timeAgo / 60)}m`;

  return (
    <motion.div 
      layout
      className="bg-zinc-900/40 border border-white/5 rounded-2xl overflow-hidden hover:border-emerald-500/30 transition-all font-sans"
    >
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-emerald-500/10">
            <Terminal className="w-4 h-4 text-emerald-400" />
          </div>
          <div>
            <h4 className="text-sm font-black text-white truncate max-w-[200px]">
              {task.task_title || task.func_name}
            </h4>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] font-mono text-zinc-500 bg-black/30 px-1.5 py-0.5 rounded border border-white/5">
                {task.func_name}
              </span>
              <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {timeStr} ago
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button 
            onClick={async () => {
              setIsRemoving(true);
              await onRemove(index);
              setIsRemoving(false);
            }}
            disabled={isRemoving}
            className="p-2 rounded-lg hover:bg-rose-500/10 text-zinc-500 hover:text-rose-400 transition-all outline-none disabled:opacity-50"
            title={t('common.actions.delete')}
          >
            {isRemoving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
          </button>
          <button 
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 rounded-lg hover:bg-white/5 text-zinc-500 hover:text-white transition-all outline-none"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-white/5 bg-black/20"
          >
            <div className="p-4 space-y-4">
              {/* Arguments */}
              {task.args && task.args.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                    <Code className="w-3 h-3" />
                    {t('queue.task.arguments')}
                  </div>
                  <pre className="text-[11px] font-mono p-3 bg-black/40 rounded-xl border border-white/5 text-emerald-400/80 overflow-x-auto custom-scrollbar">
                    {JSON.stringify(task.args, null, 2)}
                  </pre>
                </div>
              )}

              {/* Kwargs */}
              {task.kwargs && Object.keys(task.kwargs).length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                    <Code className="w-3 h-3" />
                    {t('queue.task.kwargs')}
                  </div>
                  <pre className="text-[11px] font-mono p-3 bg-black/40 rounded-xl border border-white/5 text-blue-400/80 overflow-x-auto custom-scrollbar">
                    {JSON.stringify(task.kwargs, null, 2)}
                  </pre>
                </div>
              )}

              {/* Metadata */}
              {task.metadata && Object.keys(task.metadata).length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                    <Activity className="w-3 h-3" />
                    {t('queue.task.metadata')}
                  </div>
                  <pre className="text-[11px] font-mono p-3 bg-black/40 rounded-xl border border-white/5 text-amber-400/80 overflow-x-auto custom-scrollbar">
                    {JSON.stringify(task.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export function QueueMonitorView() {
  const { t } = useTranslation();
  const { queueTasks, isQueueLoaded, refreshQueue, addToast } = useAppContext();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  React.useEffect(() => {
    refreshQueue();
  }, [refreshQueue]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await refreshQueue();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const handleRemoveTask = async (index: number) => {
    try {
      await api.removeQueueTask(index);
      await refreshQueue();
      addToast(t('notifications.queue.task_removed'), 'success');
    } catch (err) {
      console.error('[QueueMonitor] Failed to remove task:', err);
      addToast(t('notifications.queue.remove_error'), 'error');
    }
  };

  const handleClearQueue = async () => {
    setIsClearing(true);
    try {
      await api.clearQueue();
      await refreshQueue();
      setConfirmClear(false);
      addToast(t('notifications.queue.cleared'), 'success');
    } catch (err) {
      console.error('[QueueMonitor] Failed to clear queue:', err);
      addToast(t('notifications.queue.clear_error'), 'error');
    } finally {
      setIsClearing(false);
    }
  };

  const renderContent = () => {
    if (!isQueueLoaded) {
      return (
        <div className="flex flex-col items-center justify-center py-40 gap-4">
          <RefreshCw className="w-10 h-10 text-emerald-500 animate-spin opacity-20" />
          <span className="text-[10px] font-black uppercase tracking-widest text-zinc-600 animate-pulse">Syncing Redis State...</span>
        </div>
      );
    }

    if (queueTasks.length === 0) {
      return (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center justify-center py-32 text-center bg-zinc-900/20 border border-dashed border-white/5 rounded-[32px]"
        >
          <div className="w-24 h-24 rounded-full bg-black/40 border border-white/5 flex items-center justify-center mb-8 shadow-2xl relative">
            <Server className="w-10 h-10 text-zinc-800" />
            <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500/20 rounded-full flex items-center justify-center">
              <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping" />
            </div>
          </div>
          <h3 className="text-zinc-200 font-bold text-2xl mb-3">{t('queue.empty')}</h3>
          <div className="flex items-center gap-2 justify-center py-1.5 px-3 bg-emerald-500/5 rounded-full border border-emerald-500/10">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-[10px] font-black uppercase tracking-widest text-emerald-500/80">Worker listening...</span>
          </div>
        </motion.div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {queueTasks.map((task, idx) => (
          <TaskCard 
            key={`${task.func_name}-${task.enqueued_at}-${idx}`} 
            task={task} 
            index={idx}
            onRemove={handleRemoveTask}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="p-8 pt-10 max-w-7xl mx-auto h-full flex flex-col font-sans">
      {/* Header */}
      <div className="mb-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
            <Server className="w-7 h-7 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-3xl font-black text-white tracking-tight leading-none">{t('queue.title')}</h2>
            <p className="text-zinc-500 text-sm mt-2 font-medium">{t('queue.subtitle')}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {queueTasks.length > 0 && (
            <div className="relative">
              <AnimatePresence mode="wait">
                {confirmClear ? (
                  <motion.div
                    key="confirm-box"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="flex items-center gap-2 p-1 bg-rose-500/10 border border-rose-500/20 rounded-xl"
                  >
                    <button
                      onClick={handleClearQueue}
                      disabled={isClearing}
                      className="px-4 py-2 bg-rose-500 text-white text-[10px] font-black uppercase tracking-widest rounded-lg hover:bg-rose-400 transition-all disabled:opacity-50"
                    >
                      {isClearing ? <Loader2 className="w-4 h-4 animate-spin" /> : t('common.actions.confirm')}
                    </button>
                    <button
                      onClick={() => setConfirmClear(false)}
                      className="px-4 py-2 text-zinc-400 hover:text-white text-[10px] font-black uppercase tracking-widest transition-all"
                    >
                      {t('common.actions.cancel')}
                    </button>
                  </motion.div>
                ) : (
                  <motion.button
                    key="clear-btn"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    onClick={() => setConfirmClear(true)}
                    className="flex items-center gap-2 px-4 py-3 bg-zinc-900 border border-white/5 hover:border-rose-500/30 text-zinc-500 hover:text-rose-400 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all outline-none"
                  >
                    <Trash2 className="w-4 h-4" />
                    {t('queue.actions.clear')}
                  </motion.button>
                )}
              </AnimatePresence>
            </div>
          )}

          <div className="bg-zinc-900 border border-white/5 rounded-xl px-4 py-2 flex flex-col items-end">
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-600 leading-none mb-1">
              {t('queue.stats.total')}
            </span>
            <span className="text-xl font-mono font-black text-white leading-none">
              {queueTasks.length}
            </span>
          </div>
          <button 
            onClick={handleManualRefresh}
            disabled={isRefreshing}
            className="p-3 rounded-xl bg-zinc-900 border border-white/5 hover:border-emerald-500/30 text-zinc-400 hover:text-emerald-400 transition-all disabled:opacity-50 outline-none"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin text-emerald-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Area */}
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1">
        {renderContent()}
      </div>

      {/* Footer Info */}
      <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] text-zinc-500 font-black uppercase tracking-widest leading-none">
            Real-time Polling Active (10s)
          </span>
        </div>
        <span className="text-[10px] font-mono text-zinc-700">
           wys_task_queue @ redis:local
        </span>
      </div>
    </div>
  );
}
