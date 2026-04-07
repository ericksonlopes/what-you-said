import React from 'react';
import { useTranslation } from 'react-i18next';
import { Play, Loader2, UserPlus, User, Mic } from 'lucide-react';
import { Speaker, DiarizationJob } from './types';

interface SpeakerIdentificationPanelProps {
    readonly job?: DiarizationJob | null;
    readonly speakers: Speaker[];
    readonly availableVoices: any[];
    readonly isRecognizing: boolean;
    readonly onTogglePlay: (id: string) => void;
    readonly onSpeakerChange: (id: string, name: string) => void;
    readonly onTrainVoice: (speaker: Speaker) => void;
    readonly onRecognize: () => void;
    readonly canRecognize: boolean;
}

export const SpeakerIdentificationPanel: React.FC<SpeakerIdentificationPanelProps> = ({
    job,
    speakers,
    availableVoices,
    isRecognizing,
    onTogglePlay,
    onSpeakerChange,
    onTrainVoice,
    onRecognize,
    canRecognize
}) => {
    const { t } = useTranslation();

    return (
        <div className="flex flex-col h-full bg-black/20 border-r border-white/5">
            <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/40">
                <div>
                    <h3 className="text-sm font-black text-white uppercase tracking-widest">{t('diarization.identification.title')}</h3>
                    <p className="text-[10px] text-zinc-500 font-medium mt-1">{t('diarization.identification.subtitle')}</p>
                </div>
                {canRecognize && (
                    <button
                        onClick={onRecognize}
                        disabled={isRecognizing}
                        className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all disabled:opacity-50"
                    >
                        {isRecognizing ? <Loader2 className="w-3 h-3 animate-spin" /> : <UserPlus className="w-3 h-3" />}
                        {t('diarization.identification.auto_id')}
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-4">
                {speakers.map((speaker) => (
                    <div key={speaker.id} className="p-4 rounded-2xl bg-zinc-900/40 border border-white/5 hover:border-white/10 transition-all group/card">
                        <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-xl bg-zinc-800 text-zinc-500 group-hover/card:bg-emerald-500/20 group-hover/card:text-emerald-400 transition-all">
                                    <User className="w-4 h-4" />
                                </div>
                                <div>
                                    <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest leading-none mb-1">{speaker.label}</div>
                                    <div className="text-xs font-bold text-zinc-300 group-hover/card:text-white transition-colors">{speaker.assigned || t('diarization.identification.unknown')}</div>
                                </div>
                            </div>
                            <button
                                onClick={() => onTogglePlay(speaker.id)}
                                className={`p-2.5 rounded-xl transition-all ${speaker.isPlaying ? 'bg-emerald-500 text-black shadow-[0_0_15px_rgba(16,185,129,0.3)]' : 'bg-black/40 text-zinc-500 hover:bg-emerald-500/20 hover:text-emerald-400'}`}
                            >
                                {speaker.isPlaying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                            </button>
                        </div>

                        <div className="space-y-3">
                            <div className="relative">
                                <select
                                    value={speaker.assigned}
                                    onChange={(e) => onSpeakerChange(speaker.id, e.target.value)}
                                    className="w-full px-3 py-2 bg-black/40 border border-white/5 rounded-xl text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-all appearance-none font-bold"
                                >
                                    <option value={speaker.label}>{t('diarization.identification.use_label', { label: speaker.label })}</option>
                                    <optgroup label={t('diarization.identification.known_profiles')}>
                                        {availableVoices.map(v => (
                                            <option key={v.id} value={v.name}>{v.name}</option>
                                        ))}
                                    </optgroup>
                                    <option value="" disabled>---</option>
                                    <option value="NEW_PROMPT">{t('diarization.identification.new_name')}</option>
                                </select>
                                <UserPlus className="w-3 h-3 absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                            </div>

                            <button
                                onClick={() => onTrainVoice(speaker)}
                                className={`w-full flex items-center justify-center gap-2 py-2 rounded-xl border text-[9px] font-black uppercase tracking-widest transition-all ${
                                    (speaker.assigned.toUpperCase().startsWith('SPEAKER_') || speaker.assigned.toUpperCase() === 'UNKNOWN')
                                        ? 'bg-emerald-500/5 hover:bg-emerald-500/10 border-emerald-500/10 text-emerald-400'
                                        : 'bg-blue-500/5 hover:bg-blue-500/10 border-blue-500/10 text-blue-400'
                                }`}
                            >
                                <Mic className="w-3 h-3" />
                                {(speaker.assigned.toUpperCase().startsWith('SPEAKER_') || speaker.assigned.toUpperCase() === 'UNKNOWN') ? t('diarization.identification.train_voice') : t('diarization.identification.reinforce_voice')}
                                {speaker.confidence > 0 && <span className="ml-auto opacity-50">{t('diarization.identification.match_pct', { count: speaker.confidence })}</span>}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
