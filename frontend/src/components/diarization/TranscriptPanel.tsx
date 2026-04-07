import React from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Loader2, Save, FileText } from 'lucide-react';
import { motion } from 'motion/react';

interface TranscriptPanelProps {
    readonly finalSegments: any[];
    readonly speakerColorMap: Record<string, number>;
    readonly searchQuery: string;
    readonly onSearchChange: (q: string) => void;
    readonly onSave: () => void;
    readonly isSaving: boolean;
    readonly step: string;
    readonly hasContextSelected: boolean;
}

const colors = [
    'emerald', 'blue', 'amber', 'rose', 'purple', 
    'cyan', 'orange', 'indigo', 'pink', 'teal'
];

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
    finalSegments,
    speakerColorMap,
    searchQuery,
    onSearchChange,
    onSave,
    isSaving,
    step,
    hasContextSelected
}) => {
    const { t } = useTranslation();

    const filteredSegments = React.useMemo(() => {
        if (!searchQuery.trim()) return finalSegments;
        const q = searchQuery.toLowerCase();
        return finalSegments.filter(s => 
            s.text.toLowerCase().includes(q) || 
            s.speakerName.toLowerCase().includes(q)
        );
    }, [finalSegments, searchQuery]);

    return (
        <div className="flex-1 flex flex-col h-full bg-black/40 overflow-hidden">
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/40">
                <div className="flex items-center gap-6">
                    <div>
                        <h3 className="text-sm font-black text-white uppercase tracking-widest">{t('diarization.transcript.title')}</h3>
                        <p className="text-[10px] text-zinc-500 font-medium mt-1">{t('diarization.transcript.subtitle')}</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="relative group/search">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within/search:text-emerald-500 transition-colors" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => onSearchChange(e.target.value)}
                            placeholder={t('diarization.transcript.search_placeholder')}
                            className="w-64 pl-9 pr-3 py-1.5 bg-zinc-900 border border-white/5 rounded-lg text-sm text-zinc-300 focus:outline-none focus:border-emerald-500/30 transition-all font-medium"
                        />
                    </div>
                    
                    <button
                        onClick={onSave}
                        disabled={isSaving || !hasContextSelected}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${(!hasContextSelected || isSaving) ? 'bg-zinc-800 text-zinc-500 opacity-50 cursor-not-allowed' : 'bg-emerald-500 text-black hover:bg-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]'}`}
                        title={!hasContextSelected ? t('diarization.transcript.select_context_hint') : ''}
                    >
                        {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4 stroke-[3px]" />}
                        {t('diarization.identification.save_btn')}
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                <div className="max-w-3xl mx-auto space-y-8">
                    {filteredSegments.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 text-zinc-600 gap-4">
                            <FileText className="w-12 h-12 opacity-10" />
                            <p className="text-[10px] font-black uppercase tracking-widest opacity-30">{t('diarization.transcript.no_transcript')}</p>
                        </div>
                    ) : (
                        filteredSegments.map((seg, idx) => {
                            const colorIndex = speakerColorMap[seg.speakerName] || 0;
                            const color = colors[colorIndex % colors.length];
                            
                            return (
                                <motion.div
                                    key={idx}
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    className="flex gap-6 group/seg"
                                >
                                    <div className="flex-shrink-0 w-24 text-right pt-2">
                                        <div className="text-[10px] font-mono text-zinc-600 group-hover/seg:text-zinc-400 transition-colors bg-white/5 px-2 py-1 rounded-md inline-block">
                                            {seg.startTime}
                                        </div>
                                    </div>
                                    <div className="flex-1 space-y-2">
                                        <div className={`text-[10px] font-black uppercase tracking-widest text-${color}-400 flex items-center gap-2`}>
                                            <span className={`w-1.5 h-1.5 rounded-full bg-${color}-400 shadow-[0_0_8px_rgba(var(--${color}-rgb),0.5)]`} />
                                            {seg.speakerName}
                                        </div>
                                        <p className="text-sm text-zinc-300 leading-relaxed font-medium group-hover/seg:text-white transition-colors">
                                            {seg.text}
                                        </p>
                                    </div>
                                </motion.div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
};
