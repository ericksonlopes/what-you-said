import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'motion/react';
import { Search, Plus, Mic, Loader2, Video, FileText, Trash2, Edit2, Check, ExternalLink, RefreshCw, Filter, Info } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { DiarizationJob } from './types';

interface DiarizationListProps {
    readonly jobs: DiarizationJob[];
    readonly isLoading: boolean;
    readonly isRefreshing?: boolean;
    readonly onRefresh?: () => void;
    readonly searchQuery: string;
    readonly onSearchChange: (q: string) => void;
    readonly statusFilter: string;
    readonly onStatusFilterChange: (s: string) => void;
    readonly onOpenJob: (job: DiarizationJob) => void;
    readonly onDeleteJob: (id: string) => void;
    readonly onReprocessJob: (id: string) => void;
    readonly onNewJob: () => void;
    readonly onEditJob: (job: DiarizationJob) => void;
    readonly editingJobId: string | null;
    readonly editingName: string;
    readonly onEditingNameChange: (n: string) => void;
    readonly onSaveEdit: (id: string) => void;
    readonly onCancelEdit: () => void;
    readonly isNewJobDisabled?: boolean;
}

export const DiarizationList: React.FC<DiarizationListProps> = ({
    jobs,
    isLoading,
    isRefreshing = false,
    onRefresh,
    searchQuery,
    onSearchChange,
    statusFilter,
    onStatusFilterChange,
    onOpenJob,
    onDeleteJob,
    onReprocessJob,
    onNewJob,
    onEditJob,
    editingJobId,
    editingName,
    onEditingNameChange,
    onSaveEdit,
    onCancelEdit,
    isNewJobDisabled = false
}) => {
    const { t } = useTranslation();
    const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);
    const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-8 h-full flex flex-col"
        >
            <div className="mb-8 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                        <Mic className="w-7 h-7 text-emerald-400" />
                    </div>
                    <div>
                        <h2 className="text-3xl font-black text-white tracking-tight leading-none">{t('diarization.title')}</h2>
                        <p className="text-zinc-500 text-sm mt-2 font-medium">{t('diarization.subtitle')}</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative group/search">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within/search:text-emerald-500 transition-colors" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => onSearchChange(e.target.value)}
                            placeholder="Buscar..."
                            className="w-48 pl-9 pr-3 py-1.5 bg-zinc-900 border border-white/5 rounded-lg text-sm text-zinc-300 focus:outline-none focus:border-emerald-500/30 transition-all font-medium"
                        />
                    </div>

                    <div className="relative dropdown-container">
                        <button
                            onClick={() => setIsStatusDropdownOpen(!isStatusDropdownOpen)}
                            className={`flex items-center gap-2 pl-4 pr-10 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all border duration-300 ${isStatusDropdownOpen ? 'bg-emerald-500/10 border-emerald-500/40 text-white shadow-[0_0_20px_rgba(16,185,129,0.1)]' : 'bg-zinc-900 border-white/5 text-zinc-400 hover:border-white/20 hover:text-white hover:bg-zinc-800'}`}
                        >
                            <Filter className={`w-3.5 h-3.5 transition-colors ${isStatusDropdownOpen ? 'text-emerald-400' : 'text-zinc-500'}`} />
                            {statusFilter === 'all' ? t('diarization.status.all') : t(`common.status.${statusFilter}`)}
                            <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none transition-transform duration-500" style={{ transform: `translateY(-50%) rotate(${isStatusDropdownOpen ? 180 : 0}deg)` }}>
                                <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                </svg>
                            </div>
                        </button>
                        
                        <AnimatePresence>
                            {isStatusDropdownOpen && (
                                <motion.div
                                    initial={{ opacity: 0, y: 15, scale: 0.9, filter: 'blur(10px)' }}
                                    animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
                                    exit={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(10px)' }}
                                    className="absolute right-0 top-full mt-3 w-56 bg-zinc-900/90 border border-white/10 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-50 overflow-hidden backdrop-blur-2xl"
                                >
                                    <div className="p-2 space-y-1">
                                        {[
                                            { value: 'all', label: t('diarization.status.all'), color: 'text-zinc-400' },
                                            { value: 'pending', label: t('common.status.pending'), color: 'text-amber-400' },
                                            { value: 'processing', label: t('common.status.processing'), color: 'text-blue-400' },
                                            { value: 'awaiting_verification', label: t('diarization.status.awaiting_verification'), color: 'text-emerald-400' },
                                            { value: 'completed', label: t('diarization.status.completed'), color: 'text-emerald-400' },
                                            { value: 'failed', label: t('common.status.failed'), color: 'text-rose-400' }
                                        ].map((opt) => (
                                            <button
                                                key={opt.value}
                                                onClick={() => {
                                                    onStatusFilterChange(opt.value);
                                                    setIsStatusDropdownOpen(false);
                                                }}
                                                className={`w-full text-left px-4 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-between group/opt ${statusFilter === opt.value ? 'bg-emerald-500/10 text-emerald-400' : 'text-zinc-500 hover:bg-white/5 hover:text-white'}`}
                                            >
                                                <span className="flex items-center gap-3">
                                                    <div className={`w-1.5 h-1.5 rounded-full ${opt.color} bg-current opacity-40 group-hover/opt:scale-125 transition-transform`} />
                                                    {opt.label}
                                                </span>
                                                {statusFilter === opt.value && <Check className="w-3.5 h-3.5 stroke-[3px]" />}
                                            </button>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <button 
                        onClick={onRefresh}
                        disabled={isRefreshing || isLoading}
                        className="group flex items-center gap-2 px-3 py-1.5 text-xs font-black uppercase tracking-widest text-zinc-400 bg-zinc-900 border border-white/5 rounded-lg hover:bg-zinc-800 hover:text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 transition-transform duration-500 ${isRefreshing ? 'animate-spin text-emerald-400' : 'group-hover:rotate-180'}`} />
                        {isRefreshing ? t('common.actions.syncing') : t('common.actions.sync')}
                    </button>
                    
                    <button
                        onClick={onNewJob}
                        disabled={isNewJobDisabled}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl font-black uppercase text-[10px] tracking-widest transition-all ${isNewJobDisabled ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed opacity-50' : 'bg-emerald-500 text-black hover:bg-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]'}`}
                        title={isNewJobDisabled ? t('common.hints.select_subject') : ''}
                    >
                        <Plus className="w-4 h-4 stroke-[3px]" />
                        {t('diarization.new_btn')}
                    </button>
                </div>
            </div>

            <div className="flex-1 bg-zinc-900/40 border border-white/5 rounded-2xl backdrop-blur-sm flex flex-col shadow-2xl overflow-hidden">
                <div className="overflow-x-auto overflow-y-auto custom-scrollbar flex-1">
                    <table className="w-full text-left border-separate border-spacing-0 table-fixed min-w-[1000px]">
                        <thead className="sticky top-0 z-10">
                            <tr className="border-b border-white/5 text-[10px] font-black text-zinc-500 uppercase tracking-widest bg-black/20 backdrop-blur-md">
                                <th className="w-14 pl-5 py-4 text-center">Icon</th>
                                <th className="w-[30%] pl-2 pr-4 py-4 text-left">{t('diarization.table.name')}</th>
                                <th className="w-40 px-4 py-4 text-left">{t('diarization.table.date')}</th>
                                <th className="w-24 px-4 py-4 text-center">{t('diarization.table.type')}</th>
                                <th className="w-28 px-4 py-4 text-left">{t('diarization.table.model')}</th>
                                <th className="w-24 px-4 py-4 text-center">{t('diarization.table.duration')}</th>
                                <th className="w-40 px-4 py-4 text-left">{t('diarization.table.status')}</th>
                                <th className="w-36 px-6 py-4 text-right">{t('diarization.table.actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.03]">
                            {isLoading ? (
                                <tr>
                                    <td colSpan={8} className="py-24 text-center">
                                        <div className="flex flex-col items-center justify-center text-zinc-500">
                                            <Loader2 className="w-8 h-8 animate-spin mb-4 text-emerald-500" />
                                            <p className="text-[10px] font-black uppercase tracking-widest opacity-50">{t('diarization.table.loading')}</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : jobs.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="py-24 text-center">
                                        <div className="flex flex-col items-center justify-center text-zinc-500 gap-4">
                                            <Mic className="w-12 h-12 opacity-10" />
                                            <p className="text-[10px] font-black uppercase tracking-widest opacity-30">{t('diarization.table.none')}</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                jobs.map((job, index) => {
                                    const isExpanded = expandedJobId === job.id;
                                    
                                    return (
                                        <React.Fragment key={job.id}>
                                            <motion.tr
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: index * 0.02 }}
                                                onClick={() => onOpenJob(job)}
                                                className={`transition-all group relative border-b border-white/[0.02] hover:bg-white/[0.02] cursor-pointer ${isExpanded ? 'bg-white/[0.03]' : ''}`}
                                            >
                                                <td className="pl-5 pr-2 py-4">
                                                    <div className={`w-10 h-10 rounded-2xl flex items-center justify-center transition-all duration-500 shadow-lg ${job.sourceType === 'youtube' ? 'bg-rose-500/10 text-rose-400 group-hover:bg-rose-500 group-hover:text-white shadow-rose-500/5' : 'bg-blue-500/10 text-blue-400 group-hover:bg-blue-500 group-hover:text-white shadow-blue-500/5'}`}>
                                                        {job.sourceType === 'youtube' ? <Video className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
                                                    </div>
                                                </td>
                                                <td className="pl-2 pr-4 py-4">
                                                    {editingJobId === job.id ? (
                                                        <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                                                            <input
                                                                type="text"
                                                                autoFocus
                                                                value={editingName}
                                                                onChange={e => onEditingNameChange(e.target.value)}
                                                                onKeyDown={e => {
                                                                    if (e.key === 'Enter') onSaveEdit(job.id);
                                                                    if (e.key === 'Escape') onCancelEdit();
                                                                }}
                                                                className="flex-1 bg-zinc-950 border border-emerald-500/50 rounded-xl px-3 py-2 text-sm text-white focus:outline-none font-bold shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                                                            />
                                                            <button onClick={() => onSaveEdit(job.id)} className="p-2 text-emerald-400 hover:bg-emerald-500/20 rounded-xl transition-colors">
                                                                <Check className="w-5 h-5 stroke-[3px]" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="min-w-0">
                                                            <div className="flex items-center gap-2">
                                                                <span className="text-sm font-black text-white tracking-tight group-hover:text-emerald-400 transition-colors truncate">{job.name}</span>
                                                                {job.status === 'completed' && <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />}
                                                            </div>
                                                            <div className="flex items-center gap-2.5 mt-1">
                                                                <span className="text-[9px] font-black uppercase tracking-widest text-zinc-600">#{job.id.slice(0, 8)}</span>
                                                                {(job.sourceMetadata?.uploader || job.sourceMetadata?.filename) && (
                                                                    <>
                                                                        <div className="w-1 h-1 rounded-full bg-zinc-800" />
                                                                        <span className="text-[9px] font-bold text-zinc-500 truncate max-w-[180px] hover:text-zinc-300 transition-colors">
                                                                            {job.sourceMetadata.uploader || job.sourceMetadata.filename}
                                                                        </span>
                                                                    </>
                                                                )}
                                                            </div>
                                                        </div>
                                                    )}
                                                </td>
                                                <td className="px-4 py-4 text-[10px] font-black text-zinc-500 font-mono tracking-tighter uppercase whitespace-nowrap opacity-60">
                                                    {job.date}
                                                </td>
                                                <td className="px-4 py-4 text-center">
                                                    <div className="flex justify-center">
                                                        {job.sourceType === 'youtube' ? (
                                                            <div className="px-2 py-1 rounded-lg bg-rose-500/5 border border-rose-500/10 text-[9px] font-black text-rose-500 uppercase tracking-widest">YT</div>
                                                        ) : (
                                                            <div className="px-2 py-1 rounded-lg bg-blue-500/5 border border-blue-500/10 text-[9px] font-black text-blue-500 uppercase tracking-widest">UP</div>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className="text-[10px] font-black text-zinc-400 uppercase tracking-widest bg-white/5 px-2 py-1 rounded-lg">{job.modelSize || 'standard'}</span>
                                                </td>
                                                <td className="px-4 py-4 text-center">
                                                    <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest font-mono bg-zinc-950/50 px-2.5 py-1 rounded-lg border border-white/[0.02]">{job.duration || '--:--'}</span>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="flex flex-col gap-1.5 items-start">
                                                        <StatusBadge status={job.status} message={job.statusMessage || job.errorMessage} size="sm" />
                                                        {(job.status === 'processing' || job.status === 'pending' || job.status === 'failed') && (job.statusMessage || job.errorMessage) && (
                                                            <p className={`text-[8px] font-black uppercase tracking-tighter truncate max-w-[140px] pl-1 ${job.status === 'failed' ? 'text-rose-500/60' : 'text-emerald-500/60 animate-pulse'}`}>
                                                                {(() => {
                                                                    const msg = job.statusMessage || job.errorMessage || '';
                                                                    const knownSteps = ['starting', 'downloading', 'diarizing', 'exporting', 'recognizing'];
                                                                    return knownSteps.includes(msg) ? t(`diarization.status.steps.${msg}`) : msg;
                                                                })()}
                                                            </p>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center justify-end gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0">
                                                        <button
                                                            onClick={(e) => { 
                                                                e.stopPropagation(); 
                                                                setExpandedJobId(isExpanded ? null : job.id);
                                                            }}
                                                            className={`w-9 h-9 flex items-center justify-center rounded-2xl transition-all ${isExpanded ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' : 'text-zinc-500 hover:text-white hover:bg-white/5 bg-white/[0.03] border border-white/5'}`}
                                                            title={isExpanded ? "Fechar detalhes" : "Ver metadados"}
                                                        >
                                                            <Info className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); onEditJob(job); }}
                                                            className="w-9 h-9 flex items-center justify-center text-zinc-500 hover:text-white hover:bg-white/5 bg-white/[0.03] border border-white/5 rounded-2xl transition-all"
                                                            title="Renomear"
                                                        >
                                                            <Edit2 className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); onReprocessJob(job.id); }}
                                                            className="w-9 h-9 flex items-center justify-center text-zinc-500 hover:text-amber-500 hover:bg-amber-500/10 bg-white/[0.03] border border-white/5 rounded-2xl transition-all"
                                                            title={t('common.actions.reprocess')}
                                                        >
                                                            <RefreshCw className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); onDeleteJob(job.id); }}
                                                            className="w-9 h-9 flex items-center justify-center text-zinc-500 hover:text-rose-500 hover:bg-rose-500/10 bg-white/[0.03] border border-white/5 rounded-2xl transition-all"
                                                            title="Excluir"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                        <div className="w-9 h-9 flex items-center justify-center text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl shadow-inner">
                                                            <ExternalLink className="w-4 h-4" />
                                                        </div>
                                                    </div>
                                                </td>
                                            </motion.tr>
                                            
                                            <AnimatePresence>
                                                {isExpanded && (
                                                    <motion.tr
                                                        initial={{ opacity: 0, height: 0 }}
                                                        animate={{ opacity: 1, height: 'auto' }}
                                                        exit={{ opacity: 0, height: 0 }}
                                                        className="bg-zinc-950/40"
                                                    >
                                                        <td colSpan={8} className="p-0 overflow-hidden border-b border-white/[0.05]">
                                                            <div className="px-8 py-10 flex gap-12">
                                                                <div className="flex-1 grid grid-cols-4 gap-8">
                                                                    <div className="space-y-2">
                                                                        <p className="text-[9px] font-black uppercase tracking-widest text-zinc-600">Fonte Original</p>
                                                                        <p className="text-xs font-bold text-zinc-300 truncate max-w-[200px]" title={job.externalSource}>{job.externalSource || 'N/A'}</p>
                                                                    </div>
                                                                    <div className="space-y-2">
                                                                        <p className="text-[9px] font-black uppercase tracking-widest text-zinc-600">ID Único</p>
                                                                        <p className="text-xs font-mono font-bold text-emerald-500/70">{job.id}</p>
                                                                    </div>
                                                                    <div className="space-y-2">
                                                                        <p className="text-[9px] font-black uppercase tracking-widest text-zinc-600">Idioma Detectado</p>
                                                                        <p className="text-xs font-bold text-zinc-300 uppercase tracking-widest">{job.language || 'Português (Brasil)'}</p>
                                                                    </div>
                                                                    <div className="space-y-2">
                                                                        <p className="text-[9px] font-black uppercase tracking-widest text-zinc-600">Tamanho do Modelo</p>
                                                                        <p className="text-xs font-bold text-zinc-300 uppercase tracking-widest">{job.modelSize || 'Large v3'}</p>
                                                                    </div>
                                                                    
                                                                    {job.sourceMetadata && Object.entries(job.sourceMetadata).filter(([k]) => !['id', 'name', 'status', 'segments'].includes(k)).slice(0, 8).map(([key, value]) => (
                                                                        <div key={key} className="space-y-2">
                                                                            <p className="text-[9px] font-black uppercase tracking-widest text-zinc-600">{key.replaceAll('_', ' ')}</p>
                                                                            <p className="text-xs font-bold text-zinc-300 truncate" title={typeof value === 'string' || typeof value === 'number' ? String(value) : JSON.stringify(value)}>{typeof value === 'string' || typeof value === 'number' ? String(value) : JSON.stringify(value)}</p>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                                
                                                                <div className="w-px bg-white/5" />
                                                                
                                                                <div className="w-64 space-y-4">
                                                                    <div className="p-4 rounded-2xl bg-zinc-900/50 border border-white/5 space-y-3">
                                                                        <p className="text-[9px] font-black uppercase tracking-widest text-zinc-500">Ações Rápidas</p>
                                                                        <div className="grid grid-cols-2 gap-2">
                                                                            <button onClick={() => onOpenJob(job)} className="px-3 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all">Abrir</button>
                                                                            <button onClick={() => onReprocessJob(job.id)} className="px-3 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all">{t('common.actions.reprocess')}</button>
                                                                            <button onClick={() => setExpandedJobId(null)} className="px-3 py-2 bg-white/5 hover:bg-white/10 text-zinc-400 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all">Fechar</button>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </td>
                                                    </motion.tr>
                                                )}
                                            </AnimatePresence>
                                        </React.Fragment>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </motion.div>
    );
};
