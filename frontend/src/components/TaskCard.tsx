import React from 'react';
import { useTranslation } from 'react-i18next';
import { IngestionTask } from '../types';
import { 
  CheckCircle2, Loader2, XCircle, ExternalLink, 
  Youtube, FileText, Newspaper, BookOpen, Globe, Database, Clock, 
  Layers, ChevronRight, AlertCircle, Calendar, Hash, Activity, RotateCcw
} from 'lucide-react';
import { ErrorDetailModal } from './ErrorDetailModal';
import { useAppContext } from '../store/AppContext';
import { api } from '../services/api';
import { motion } from 'motion/react';

interface TaskCardProps {
  task: IngestionTask;
}

const getSourceIcon = (type?: string) => {
  switch (type?.toLowerCase()) {
    case 'youtube': return Youtube;
    case 'article': return Newspaper;
    case 'pdf': return FileText;
    case 'file': return FileText;
    case 'wikipedia': return BookOpen;
    case 'web': return Globe;
    default: return Database;
  }
};

const formatRelativeTime = (dateString: string, t: any) => {
  const normalizedDate = dateString.endsWith('Z') || dateString.includes('+') ? dateString : `${dateString}Z`;
  const date = new Date(normalizedDate);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 5) return t('common.time.now');
  if (diffInSeconds < 60) return `${diffInSeconds}s ${t('common.time.ago')}`;
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ${t('common.time.ago')}`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ${t('common.time.ago')}`;
  return date.toLocaleDateString();
};

const formatDuration = (start: string, end?: string) => {
  if (!end) return null;
  const startTime = new Date(start.endsWith('Z') || start.includes('+') ? start : `${start}Z`).getTime();
  const endTime = new Date(end.endsWith('Z') || end.includes('+') ? end : `${end}Z`).getTime();
  const diffInSeconds = Math.floor((endTime - startTime) / 1000);
  
  if (diffInSeconds < 0) return null;
  if (diffInSeconds < 60) return `${diffInSeconds}s`;
  const minutes = Math.floor(diffInSeconds / 60);
  const seconds = diffInSeconds % 60;
  return `${minutes}m ${seconds}s`;
};

export function TaskCard({ task }: TaskCardProps) {
  const { t } = useTranslation();
  const { setSelectedSourceIdForDb, setCurrentView, addToast, refreshJobs } = useAppContext();
  const [isErrorModalOpen, setIsErrorModalOpen] = React.useState(false);
  const [isReprocessing, setIsReprocessing] = React.useState(false);
  
  const statusConfig: Record<string, { color: string, bg: string, border: string, icon: any, label: string, animate?: boolean }> = {
    pending: { color: 'text-zinc-500', bg: 'bg-zinc-500/10', border: 'border-zinc-500/20', icon: Clock, label: t('common.status.pending') },
    started: { color: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/20', icon: Loader2, label: t('common.status.started'), animate: true },
    processing: { color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20', icon: Loader2, label: t('common.status.processing'), animate: true },
    finished: { color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20', icon: CheckCircle2, label: t('common.status.completed') },
    done: { color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20', icon: CheckCircle2, label: t('common.status.completed') },
    failed: { color: 'text-rose-400', bg: 'bg-rose-400/10', border: 'border-rose-400/20', icon: AlertCircle, label: t('common.status.failed') },
    error: { color: 'text-rose-400', bg: 'bg-rose-400/10', border: 'border-rose-400/20', icon: AlertCircle, label: t('common.status.failed') },
    cancelled: { color: 'text-zinc-500', bg: 'bg-zinc-500/10', border: 'border-zinc-500/20', icon: XCircle, label: t('common.status.cancelled') }
  };

  const config = React.useMemo(() => {
    const baseConfig = statusConfig[task.status] || statusConfig.pending;
    const isDuplicate = task.errorMessage?.includes('Duplicate') || task.statusMessage?.includes('Duplicate');
    
    if (isDuplicate && (['failed', 'error'].includes(task.status))) {
      return {
        ...baseConfig,
        color: 'text-orange-400',
        bg: 'bg-orange-400/10',
        border: 'border-orange-400/30',
        label: t('common.status.duplicate') || 'DUPLICATE'
      };
    }
    return baseConfig;
  }, [task.status, task.errorMessage, task.statusMessage, t]);

  const isFailed = ['failed', 'error'].includes(task.status);
  const isDuplicate = task.errorMessage?.includes('Duplicate') || task.statusMessage?.includes('Duplicate');
  const isProcessing = ['processing', 'started'].includes(task.status);
  const isCompleted = ['done', 'finished'].includes(task.status);
  const SourceIcon = getSourceIcon(task.ingestionType);

  const handleReprocess = async (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (isReprocessing || !task.externalSource) return;
    
    setIsReprocessing(true);
    try {
      if (task.ingestionType === 'youtube') {
        await api.ingestYoutube({
          video_url: task.externalSource,
          reprocess: true,
          subject_id: task.subjectId
        });
      } else {
        // Fallback for other types if they support reprocess via the same or similar logic
        // For now, most use cases are covered by the generic reprocess flag if implemented in backend
        addToast("Reprocessing of this type is not yet fully implemented", "info");
        return;
      }
      addToast(t('ingestion.url.reprocess_started'), 'success');
      refreshJobs();
    } catch (err) {
      addToast(t('ingestion.url.reprocess_error'), 'error');
    } finally {
      setIsReprocessing(false);
    }
  };

  const handleClick = () => {
    if (isDuplicate && task.contentSourceId) {
      setSelectedSourceIdForDb(task.contentSourceId);
      setCurrentView('database');
    } else if (isFailed) {
      setIsErrorModalOpen(true);
    } else if (isCompleted && task.contentSourceId) {
      setSelectedSourceIdForDb(task.contentSourceId);
      setCurrentView('database');
    }
  };

  const getLocalizedError = (error?: string) => {
    if (!error) return 'Unknown system failure during ingestion.';
    if (error.includes('Transcripts are disabled')) return t('ingestion.youtube.errors.disabled_transcripts');
    if (error.includes('No transcript found')) return t('ingestion.youtube.errors.no_transcript');
    if (error.includes('unavailable')) return t('ingestion.youtube.errors.unavailable');
    if (error.includes('Duplicate')) return t('ingestion.messages.duplicate');
    return error;
  };

  return (
    <>
      <motion.div 
        layout
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ y: -2 }}
        onClick={handleClick}
        className={`group relative flex flex-col bg-zinc-900/40 backdrop-blur-md border ${config.border} rounded-2xl p-4 transition-all duration-300 ${
          isFailed || (isCompleted && task.contentSourceId) || (isDuplicate && task.contentSourceId) ? 'cursor-pointer hover:bg-zinc-800/60' : ''
        }`}
      >
        {/* Top Section: Icon & Identity */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`p-2.5 rounded-xl bg-zinc-950 border border-white/5 shadow-inner text-zinc-400 group-hover:text-zinc-200 transition-colors`}>
              <SourceIcon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h4 className="text-[13px] font-bold text-zinc-100 truncate leading-tight tracking-tight mb-1" title={task.title}>
                {task.title}
              </h4>
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-black px-1.5 py-0.5 rounded-md bg-white/5 text-zinc-500 border border-white/5 uppercase tracking-tighter">
                  {task.ingestionType || 'Unknown'}
                </span>
                {task.subjectName && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-tighter">
                    {task.subjectName}
                  </span>
                )}
                <span className="text-[9px] font-mono text-zinc-600">
                  {task.id.substring(0, 8)}
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end shrink-0">
            <div className="flex items-center gap-2">
              <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border ${config.border} ${config.bg} ${config.color} text-[9px] font-black uppercase tracking-widest shadow-sm`}>
                {config.animate && <config.icon className="w-2.5 h-2.5 animate-spin" />}
                {!config.animate && <config.icon className="w-2.5 h-2.5" />}
                {config.label}
              </div>
            </div>
          </div>
        </div>

        {/* Content Section: Progress or Result */}
        <div className="flex-1">
          {isProcessing ? (
            <div className="space-y-3">
              <div className="flex justify-between items-center text-[10px] font-bold text-zinc-400">
                <div className="flex items-center gap-1.5">
                  <Activity className="w-3 h-3 text-amber-500 animate-pulse" />
                  <span className="uppercase tracking-wide">{task.statusMessage || t('common.status.processing')}</span>
                </div>
                <span className="text-amber-400 font-mono">{task.progress}%</span>
              </div>
              <div className="relative h-1.5 w-full bg-zinc-950 rounded-full overflow-hidden border border-white/5 shadow-inner">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${task.progress}%` }}
                  className="absolute h-full bg-gradient-to-r from-amber-500 to-orange-400 rounded-full shadow-[0_0_10px_rgba(245,158,11,0.4)]"
                />
              </div>
              <div className="flex items-center justify-between">
                {task.currentStep && (
                  <div className="flex items-center gap-1 text-[9px] font-bold text-zinc-600 uppercase tracking-widest">
                    <Layers className="w-2.5 h-2.5" />
                    <span>{t('activity.phase')} {task.currentStep} <ChevronRight className="inline w-2 h-2" /> {task.totalSteps}</span>
                  </div>
                )}
                <div className="flex items-center gap-1.5 text-[9px] text-zinc-600 font-bold ml-auto uppercase tracking-tighter">
                  <Clock className="w-3 h-3" />
                  {formatRelativeTime(task.createdAt, t)}
                </div>
              </div>
            </div>
          ) : isFailed ? (
            <div className={`p-3 rounded-xl border transition-colors ${
              isDuplicate 
                ? 'bg-orange-500/5 border-orange-500/10 group-hover:border-orange-500/30' 
                : 'bg-rose-500/5 border-rose-500/10 group-hover:border-rose-500/30'
            }`}>
              <p className={`text-[11px] leading-relaxed line-clamp-2 italic font-serif ${
                isDuplicate ? 'text-orange-400/80' : 'text-rose-400/80'
              }`}>
                "{getLocalizedError(task.errorMessage)}"
              </p>
              <div className="mt-2.5 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[9px] text-zinc-500/60 font-bold uppercase tracking-tighter">
                  <Clock className="w-3 h-3" />
                  {formatRelativeTime(task.createdAt, t)}
                </div>
                <div className={`flex items-center gap-1 text-[9px] font-black uppercase tracking-widest ${
                  isDuplicate ? 'text-orange-500/60' : 'text-rose-500/60'
                }`}>
                  <AlertCircle className="w-3 h-3" />
                  {isDuplicate && task.contentSourceId ? t('common.actions.go_to_source') : t('common.actions.view_details')}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-3 rounded-xl border border-emerald-500/10 bg-emerald-500/[0.02] group-hover:border-emerald-500/30 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
                  <span className="text-[11px] text-emerald-400/80 font-medium">{t('activity.pipeline_optimized')}</span>
                </div>
                {task.chunksCount && (
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-zinc-900 border border-white/5 text-[10px] font-bold text-emerald-400">
                    <Database className="w-3 h-3" />
                    <span>{task.chunksCount}</span>
                  </div>
                )}
              </div>
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-1.5 text-[9px] text-zinc-500/60 font-bold uppercase tracking-tighter">
                    <Clock className="w-3 h-3" />
                    {formatRelativeTime(task.createdAt, t)}
                  </div>
                  {isCompleted && task.finishedAt && (
                    <div className="flex items-center gap-1.5 text-[9px] text-emerald-500/60 font-bold tracking-tighter">
                      <Clock className="w-3 h-3" />
                      {t('activity.duration')}: {formatDuration(task.createdAt, task.finishedAt)}
                    </div>
                  )}
                </div>
                {isCompleted && task.contentSourceId && (
                  <div className="flex items-center gap-1 text-[9px] font-black uppercase tracking-widest text-emerald-500/60">
                    <Database className="w-3 h-3" />
                    {t('common.actions.go_to_source')}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Hover Action Indicator */}
        {(isFailed || (isCompleted && task.contentSourceId) || (isDuplicate && task.contentSourceId)) && (
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="p-1 rounded-full bg-white/10 text-white backdrop-blur-md">
              <ChevronRight className="w-3 h-3" />
            </div>
          </div>
        )}
      </motion.div>

      <ErrorDetailModal 
        isOpen={isErrorModalOpen}
        onClose={() => setIsErrorModalOpen(false)}
        task={task}
        onReprocess={() => handleReprocess()}
        isReprocessing={isReprocessing}
      />
    </>
  );
}
