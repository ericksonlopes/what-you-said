import React from 'react';
import { X, Copy, Check, AlertCircle, Clock, Hash, RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IngestionTask } from '../types';
import { motion, AnimatePresence } from 'motion/react';

interface ErrorDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: IngestionTask;
  onReprocess?: () => void;
  isReprocessing?: boolean;
}

export function ErrorDetailModal({ isOpen, onClose, task, onReprocess, isReprocessing }: ErrorDetailModalProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    if (task.errorMessage) {
      navigator.clipboard.writeText(task.errorMessage);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-md p-4" onClick={onClose}>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0"
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="w-full max-w-2xl bg-zinc-900 border border-border-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col relative z-10"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-border-subtle bg-rose-500/5">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
                  <AlertCircle className="w-5 h-5" />
                </div>
                <div>
                   <h2 className="text-lg font-semibold text-zinc-100 italic">{t('error_modal.title')}</h2>
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-zinc-500 font-medium">
                    <span className="flex items-center gap-1"><Hash className="w-3 h-3" /> {task.id.substring(0, 8)}</span>
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {new Date(task.createdAt).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 flex-1 overflow-y-auto custom-scrollbar bg-[#09090b]">
               <div className="mb-4">
                  <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-2">{t('error_modal.original_task')}</h3>
                  <p className="text-sm font-medium text-zinc-300 bg-zinc-900/50 p-3 rounded-lg border border-zinc-800/50">
                    {task.title}
                  </p>
               </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-rose-400/80 uppercase tracking-widest">{t('error_modal.full_error')}</h3>
                  <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 px-2 py-1 rounded md hover:bg-zinc-800 text-zinc-500 hover:text-emerald-400 transition-all text-[10px] font-bold uppercase tracking-wider border border-transparent hover:border-zinc-700"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-500" />
                        {t('error_modal.copied')}
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        {t('error_modal.copy')}
                      </>
                    )}
                  </button>
                </div>
                
                <div className="mt-1 relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-b from-rose-500/10 to-transparent rounded-xl opacity-50 blur-sm pointer-events-none"></div>
                  <pre className="relative w-full bg-black/60 border border-rose-500/20 rounded-xl p-5 text-zinc-400 text-sm font-mono overflow-x-auto custom-scrollbar leading-relaxed selection:bg-rose-500/30">
                    {task.errorMessage || t('error_modal.no_message')}
                  </pre>
                </div>
              </div>
              
              <div className="mt-8 p-4 bg-zinc-900/30 border border-zinc-800 rounded-xl flex items-center gap-3">
                 <div className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
                 <p className="text-[11px] text-zinc-500 leading-tight">
                   {t('error_modal.support_hint')}
                 </p>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border-subtle bg-zinc-900/50 flex justify-between gap-3">
              {onReprocess && task.externalSource && (
                <button
                  onClick={onReprocess}
                  disabled={isReprocessing}
                  className={`flex items-center gap-2 px-5 py-2 text-sm font-bold rounded-xl transition-all active:scale-95 disabled:opacity-50 ${
                    isReprocessing 
                      ? 'bg-zinc-800 text-emerald-400 border border-emerald-500/20' 
                      : 'bg-emerald-500 hover:bg-emerald-400 text-black shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                  }`}
                >
                  <RotateCcw className={`w-4 h-4 ${isReprocessing ? 'animate-spin' : ''}`} />
                  {isReprocessing ? t('common.actions.syncing') : t('common.actions.reprocess')}
                </button>
              )}
              <button
                onClick={onClose}
                className="px-5 py-2 text-sm font-bold text-zinc-200 bg-zinc-800 hover:bg-zinc-700 rounded-xl transition-all border border-zinc-700 hover:border-zinc-600 active:scale-95 ml-auto"
              >
                {t('common.actions.close')}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
