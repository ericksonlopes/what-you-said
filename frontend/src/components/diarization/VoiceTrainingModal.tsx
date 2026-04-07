import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Mic, Loader2, Play } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../../services/api';
import { useAppContext } from '../../store/AppContext';
import { Speaker } from './types';

interface VoiceTrainingModalProps {
    readonly isOpen: boolean;
    readonly speaker: Speaker | null;
    readonly diarizationId: string;
    readonly onClose: () => void;
    readonly onTrained: () => void;
}

export const VoiceTrainingModal: React.FC<VoiceTrainingModalProps> = ({ isOpen, speaker, diarizationId, onClose, onTrained }) => {
    const { t } = useTranslation();
    const { addToast } = useAppContext();
    const [voiceProfileName, setVoiceProfileName] = useState('');
    const [isTraining, setIsTraining] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const audioRef = React.useRef<HTMLAudioElement | null>(null);

    const isReinforce = !!(speaker?.assigned && !speaker.assigned.toUpperCase().startsWith('SPEAKER_') && speaker.assigned.toUpperCase() !== 'UNKNOWN');

    React.useEffect(() => {
        if (isOpen && speaker) {
            if (isReinforce) {
                setVoiceProfileName(speaker.assigned);
            } else {
                setVoiceProfileName('');
            }
        }
    }, [isOpen, speaker, isReinforce]);

    const togglePlay = async () => {
        if (!speaker || !diarizationId) return;

        if (isPlaying) {
            audioRef.current?.pause();
            setIsPlaying(false);
            return;
        }

        try {
            const result = await api.getSpeakerAudioUrl(diarizationId, speaker.label);
            const url = result?.url || result?.presigned_url;
            if (url) {
                const audio = new Audio(url);
                audioRef.current = audio;
                audio.onended = () => setIsPlaying(false);
                setIsPlaying(true);
                await audio.play();
            }
        } catch (err) {
            console.error('Failed to play speaker audio:', err);
            addToast(t('diarization.notifications.audio_fetch_error'), 'error');
        }
    };

    const handleTrainVoice = async () => {
        if (!speaker || !voiceProfileName.trim() || !diarizationId) return;
        setIsTraining(true);
        try {
            const name = voiceProfileName.trim();
            await api.trainVoiceFromSpeaker({
                diarization_id: diarizationId,
                speaker_label: speaker.label,
                name: name,
            });
            
            const successMsg = isReinforce 
                ? t('diarization.notifications.reinforce_success', { name })
                : t('diarization.notifications.train_success', { name });

            addToast(successMsg, 'success');
            onTrained();
            onClose();
        } catch (err: any) {
            console.error('Failed to train voice:', err);
            addToast(err.message || t('diarization.notifications.train_error'), 'error');
        } finally {
            setIsTraining(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="relative w-full max-w-md bg-zinc-900 border border-white/10 rounded-3xl overflow-hidden shadow-2xl"
                    >
                        <div className="p-6 border-b border-white/5 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-xl ${isReinforce ? 'bg-blue-500/10 text-blue-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                                    <Mic className="w-5 h-5" />
                                </div>
                                <h3 className="text-xl font-black text-white uppercase tracking-tight">
                                    {isReinforce ? t('diarization.voice_training.reinforce_title') : t('diarization.voice_training.title')}
                                </h3>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-xl transition-colors">
                                <X className="w-5 h-5 text-zinc-500" />
                            </button>
                        </div>
                        
                        <div className="p-6 space-y-6">
                            <div className="p-4 bg-black/40 rounded-2xl border border-white/5 space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">{t('diarization.voice_training.sample_label')}</span>
                                    <span className="text-xs font-bold text-white">{speaker?.label}</span>
                                </div>
                                <button
                                    onClick={togglePlay}
                                    className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${isPlaying ? 'bg-blue-500 text-black shadow-xl ring-2 ring-blue-500/20' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'}`}
                                >
                                    {isPlaying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                                    {isPlaying ? t('diarization.voice_training.playing') : t('diarization.voice_training.listen_sample')}
                                </button>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">{t('diarization.voice_training.profile_name_label')}</label>
                                <input
                                    type="text"
                                    autoFocus={!isReinforce}
                                    disabled={isReinforce}
                                    value={voiceProfileName}
                                    onChange={(e) => setVoiceProfileName(e.target.value)}
                                    placeholder={t('diarization.voice_training.profile_name_placeholder')}
                                    className={`w-full px-4 py-3 bg-black/40 border border-white/5 rounded-xl text-sm text-white focus:outline-none focus:border-blue-500/30 transition-all font-medium ${isReinforce ? 'opacity-50 cursor-not-allowed' : ''}`}
                                />
                                <p className="text-[9px] text-zinc-500 font-medium ml-1">
                                    {isReinforce ? t('diarization.voice_training.reinforce_description') : t('diarization.voice_training.description')}
                                </p>
                            </div>
                        </div>

                        <div className="p-6 bg-black/20 border-t border-white/5 flex gap-3">
                            <button
                                onClick={onClose}
                                className="flex-1 py-3 px-4 rounded-xl text-[10px] font-black uppercase tracking-widest border border-white/10 text-zinc-400 hover:bg-white/5 transition-all font-bold"
                            >
                                {t('common.actions.cancel')}
                            </button>
                            <button
                                onClick={handleTrainVoice}
                                disabled={isTraining || !voiceProfileName.trim()}
                                className={`flex-1 py-3 px-4 font-black uppercase text-[10px] tracking-widest rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${isReinforce ? 'bg-blue-500 text-black shadow-[0_0_20px_rgba(59,130,246,0.2)] hover:bg-blue-400' : 'bg-emerald-500 text-black shadow-[0_0_20px_rgba(16,185,129,0.2)] hover:bg-emerald-400'}`}
                            >
                                {isTraining ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
                                {isReinforce ? t('diarization.voice_training.reinforce_submit_btn') : t('diarization.voice_training.submit_btn')}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};
