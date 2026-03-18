import React from 'react';
import { useTranslation } from 'react-i18next';
import { IngestionTask } from '../types';
import { CheckCircle2, CircleDashed, Loader2, XCircle, ExternalLink } from 'lucide-react';
import { ErrorDetailModal } from './ErrorDetailModal';

// 2. Componente de 'Task Card' dinâmico
// Muda de cor e ícone baseando-se no enum de status.

interface TaskCardProps {
  task: IngestionTask;
  key?: string | number;
}

export function TaskCard({ task }: TaskCardProps) {
  const { t } = useTranslation();
  const [isErrorModalOpen, setIsErrorModalOpen] = React.useState(false);
  const statusConfig = {
    pending: {
      icon: CircleDashed,
      textColor: 'text-zinc-400',
      bgColor: 'bg-zinc-500/10',
      borderColor: 'border-zinc-500/20',
      label: t('common.status.pending'),
      spin: false,
    },
    started: {
      icon: CircleDashed,
      textColor: 'text-zinc-400',
      bgColor: 'bg-zinc-500/10',
      borderColor: 'border-zinc-500/20',
      label: t('common.status.started'),
      spin: false,
    },
    processing: {
      icon: Loader2,
      textColor: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
      label: t('common.status.processing'),
      spin: true,
    },
    finished: {
      icon: CheckCircle2,
      textColor: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
      label: t('common.status.completed'),
      spin: false,
    },
    done: {
      icon: CheckCircle2,
      textColor: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
      label: t('common.status.completed'),
      spin: false,
    },
    failed: {
      icon: XCircle,
      textColor: 'text-rose-400',
      bgColor: 'bg-rose-500/10',
      borderColor: 'border-rose-500/20',
      label: t('common.status.failed'),
      spin: false,
    },
    error: {
      icon: XCircle,
      textColor: 'text-rose-400',
      bgColor: 'bg-rose-500/10',
      borderColor: 'border-rose-500/20',
      label: t('common.status.failed'),
      spin: false,
    },
    cancelled: {
      icon: XCircle,
      textColor: 'text-zinc-500',
      bgColor: 'bg-zinc-500/10',
      borderColor: 'border-zinc-500/20',
      label: t('common.status.cancelled'),
      spin: false,
    },
  };

  const config = statusConfig[task.status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <>
      <div 
        onClick={() => (task.status === 'failed' || task.status === 'error') && setIsErrorModalOpen(true)}
        className={`p-4 rounded-xl border border-border-subtle bg-panel-bg flex flex-col gap-3 transition-all ${
          (task.status === 'failed' || task.status === 'error') 
            ? 'hover:bg-rose-500/5 hover:border-rose-500/30 cursor-pointer group' 
            : 'hover:bg-panel-hover'
        }`}
      >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.bgColor} ${config.borderColor} border`}>
            <Icon className={`w-5 h-5 ${config.textColor} ${config.spin ? 'animate-spin' : ''}`} />
          </div>
          <div>
            <h4 className="text-sm font-medium text-zinc-200">{task.title}</h4>
            <p className="text-xs text-zinc-500 mt-0.5">ID: {task.id} • {new Date(task.createdAt).toLocaleTimeString()}</p>
            {((task.status === 'failed' || task.status === 'error')) && task.errorMessage && (
              <div className="mt-2 flex flex-col gap-1">
                <p className="text-xs text-rose-400/80 line-clamp-2">{task.errorMessage}</p>
                <span className="flex items-center gap-1.5 text-[10px] font-bold text-rose-500/60 group-hover:text-rose-400 uppercase tracking-widest transition-colors mt-1">
                  <ExternalLink className="w-3 h-3" />
                  View details
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {task.ingestionType && (
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700 uppercase tracking-wider">
              {task.ingestionType}
            </span>
          )}
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${config.bgColor} ${config.textColor} border ${config.borderColor}`}>
            {config.label}
          </span>
        </div>
      </div>

      {/* Progress Bar for Processing State */}
      {task.status === 'processing' && (
        <div className="w-full bg-zinc-800 rounded-full h-1.5 mt-2 overflow-hidden">
          <div
            className="bg-blue-500 h-1.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${task.progress}%` }}
          ></div>
        </div>
      )}
      </div>
      <ErrorDetailModal 
        isOpen={isErrorModalOpen}
        onClose={() => setIsErrorModalOpen(false)}
        task={task}
      />
    </>
  );
}
