import React from 'react';
import { useTranslation } from 'react-i18next';
import { 
    Video, 
    FileText, 
    Globe, 
    Calendar, 
    Clock, 
    Database as DbIcon,
    Tags,
    Info,
    RefreshCw
} from 'lucide-react';
import { DiarizationJob } from './types';

interface DiarizationMetadataPanelProps {
    readonly job: DiarizationJob;
    readonly onReprocess?: (id: string) => void;
}

export const DiarizationMetadataPanel: React.FC<DiarizationMetadataPanelProps> = ({ job, onReprocess }) => {
    const { t } = useTranslation();

    // Helper to format metadata keys
    const formatKey = (key: string) => key.replaceAll('_', ' ');

    // Helper to format values
    const formatValue = (value: any) => {
        if (typeof value === 'string' || typeof value === 'number') {
            return String(value);
        }
        return JSON.stringify(value);
    };

    return (
        <div className="flex flex-col h-full bg-black/20 border-l border-white/5 w-[320px]">
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/40">
                <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs font-black text-white uppercase tracking-widest">{t('diarization.detail.file_details')}</h3>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-8">
                {/* PRIMARY INFO */}
                <div className="space-y-4">
                    <div className="flex items-center gap-3 p-4 rounded-2xl bg-zinc-900/40 border border-white/5">
                        <div className={`p-2.5 rounded-xl flex items-center justify-center transition-all ${job.sourceType === 'youtube' ? 'bg-rose-500/10 text-rose-400' : 'bg-blue-500/10 text-blue-400'}`}>
                            {job.sourceType === 'youtube' ? <Video className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
                        </div>
                        <div className="min-w-0">
                            <p className="text-[10px] font-black text-zinc-600 uppercase tracking-widest mb-0.5">{t('diarization.table.type')}</p>
                            <p className="text-xs font-bold text-white uppercase">{job.sourceType || 'unknown'}</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-3">
                         {/* Original Source */}
                         <div className="p-4 rounded-2xl bg-zinc-900/20 border border-white/5 space-y-2">
                            <div className="flex items-center gap-2 text-zinc-500">
                                <Globe className="w-3 h-3" />
                                <p className="text-[10px] font-black uppercase tracking-widest">{t('diarization.detail.original_source')}</p>
                            </div>
                            <p className="text-xs font-bold text-zinc-300 break-all leading-relaxed bg-black/20 p-2 rounded-lg border border-white/5">
                                {job.externalSource || 'N/A'}
                            </p>
                        </div>

                        {/* Date & Duration */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="p-4 rounded-2xl bg-zinc-900/20 border border-white/5 space-y-2">
                                <div className="flex items-center gap-2 text-zinc-500">
                                    <Calendar className="w-3 h-3" />
                                    <p className="text-[10px] font-black uppercase tracking-widest">{t('diarization.detail.process_date')}</p>
                                </div>
                                <p className="text-xs font-bold text-zinc-300">{job.date}</p>
                            </div>
                            <div className="p-4 rounded-2xl bg-zinc-900/20 border border-white/5 space-y-2">
                                <div className="flex items-center gap-2 text-zinc-500">
                                    <Clock className="w-3 h-3" />
                                    <p className="text-[10px] font-black uppercase tracking-widest">{t('diarization.table.duration')}</p>
                                </div>
                                <p className="text-xs font-bold text-zinc-300">{job.duration || '--:--'}</p>
                            </div>
                        </div>

                        {/* Technical ID */}
                        <div className="p-4 rounded-2xl bg-zinc-950/40 border border-emerald-500/10 space-y-2">
                            <div className="flex items-center gap-2 text-emerald-500/50">
                                <DbIcon className="w-3 h-3" />
                                <p className="text-[10px] font-black uppercase tracking-widest">{t('diarization.detail.unique_id')}</p>
                            </div>
                            <p className="text-[10px] font-mono text-emerald-400/70 select-all break-all">{job.id}</p>
                        </div>
                    </div>
                </div>

                {/* ADVANCED METADATA */}
                {job.sourceMetadata && Object.entries(job.sourceMetadata).length > 0 && (
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 px-2">
                            <Tags className="w-3 h-3 text-zinc-600" />
                            <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">{t('search.results.metadata')}</h4>
                        </div>
                        
                        <div className="p-4 rounded-2xl bg-black/40 border border-white/5 space-y-5">
                            {Object.entries(job.sourceMetadata)
                                .filter(([k]) => !['id', 'name', 'status', 'segments'].includes(k))
                                .map(([key, value]) => (
                                    <div key={key} className="space-y-1.5">
                                        <p className="text-[9px] font-black uppercase tracking-widest text-zinc-600 leading-none">{formatKey(key)}</p>
                                        <p className="text-xs font-bold text-zinc-300 leading-normal" title={formatValue(value)}>
                                            {formatValue(value)}
                                        </p>
                                    </div>
                                ))
                            }
                        </div>
                    </div>
                )}

                {/* QUICK ACTIONS */}
                {onReprocess && (
                    <div className="space-y-4 pt-4 border-t border-white/5">
                        <button
                            onClick={() => onReprocess(job.id)}
                            className="w-full flex items-center justify-center gap-3 p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500 hover:bg-amber-500/20 transition-all font-black uppercase text-[10px] tracking-widest shadow-[0_0_20px_rgba(245,158,11,0.05)]"
                        >
                            <RefreshCw className="w-4 h-4" />
                            {t('common.actions.reprocess')}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
