import React from 'react';
import { useTranslation } from 'react-i18next';
import { Clock, Loader2, CheckCircle2, AlertCircle, Play } from 'lucide-react';

interface StatusBadgeProps {
    readonly status: 'completed' | 'pending' | 'processing' | 'failed' | 'awaiting_verification';
    readonly message?: string;
    readonly size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, message, size = 'md' }) => {
    const { t } = useTranslation();
    const isSm = size === 'sm';

    const renderBadge = () => {
        switch (status) {
            case 'completed':
                return (
                    <div className={`inline-flex items-center gap-1.5 ${isSm ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-black uppercase ${isSm ? 'text-[8px]' : 'text-[10px]'} tracking-widest`}>
                        <CheckCircle2 className={isSm ? 'w-2.5 h-2.5' : 'w-3.5 h-3.5'} />
                        {t('diarization.status.completed')}
                    </div>
                );
            case 'awaiting_verification':
                return (
                    <div className={`inline-flex items-center gap-1.5 ${isSm ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-black uppercase ${isSm ? 'text-[8px]' : 'text-[10px]'} tracking-widest animate-pulse`}>
                        <Play className={isSm ? 'w-2.5 h-2.5' : 'w-3.5 h-3.5'} />
                        {t('diarization.status.awaiting_verification')}
                    </div>
                );
            case 'processing':
                return (
                    <div className={`inline-flex items-center gap-1.5 ${isSm ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 font-black uppercase ${isSm ? 'text-[8px]' : 'text-[10px]'} tracking-widest transition-all shadow-[0_0_10px_rgba(245,158,11,0.1)]`}>
                        <Loader2 className={`${isSm ? 'w-2.5 h-2.5' : 'w-3.5 h-3.5'} animate-spin`} />
                        {t('common.status.processing')}
                    </div>
                );
            case 'failed':
                return (
                    <div className={`inline-flex items-center gap-1.5 ${isSm ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 font-black uppercase ${isSm ? 'text-[8px]' : 'text-[10px]'} tracking-widest`}>
                        <AlertCircle className={isSm ? 'w-2.5 h-2.5' : 'w-3.5 h-3.5'} />
                        {t('common.status.failed')}
                    </div>
                );
            default:
                return (
                    <div className={`inline-flex items-center gap-1.5 ${isSm ? 'px-2 py-0.5' : 'px-3 py-1'} rounded-full bg-zinc-500/10 border border-zinc-500/20 text-zinc-400 font-black uppercase ${isSm ? 'text-[8px]' : 'text-[10px]'} tracking-widest`}>
                        <Clock className={isSm ? 'w-2.5 h-2.5' : 'w-3.5 h-3.5'} />
                        {t('common.status.pending')}
                    </div>
                );
        }
    };

    return (
        <div className={`flex flex-col gap-1.5 items-start ${isSm ? '' : 'min-w-[120px]'}`}>
            {renderBadge()}
        </div>
    );
};


