import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, Loader2, UserPlus, User, Mic, ChevronDown, Check, Plus, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
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

const isGenericSpeaker = (label: string) => {
    return /^SPEAKER_?\d+$/i.test(label);
};

const SpeakerDropdown: React.FC<{
    speaker: Speaker;
    availableVoices: any[];
    onSpeakerChange: (id: string, name: string) => void;
    onToggleDropdown?: (isOpen: boolean) => void;
}> = ({ speaker, availableVoices, onSpeakerChange, onToggleDropdown }) => {
    const { t } = useTranslation();
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        onToggleDropdown?.(isOpen);
    }, [isOpen, onToggleDropdown]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const filteredVoices = availableVoices.filter(v => 
        v.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleSelect = (value: string) => {
        onSpeakerChange(speaker.id, value);
        setIsOpen(false);
        setSearchQuery('');
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all duration-300 group ${
                    isOpen 
                        ? 'bg-zinc-800/80 border-emerald-500/30 ring-1 ring-emerald-500/10' 
                        : 'bg-black/40 border-white/5 hover:border-white/10'
                }`}
            >
                <div className="flex items-center gap-3 overflow-hidden">
                    <User className={`w-4 h-4 transition-colors ${isOpen ? 'text-emerald-400' : 'text-zinc-500 group-hover:text-zinc-400'}`} />
                    <span className={`text-[13px] font-bold truncate ${ (speaker.assigned === speaker.label && isGenericSpeaker(speaker.label)) ? 'text-zinc-500' : 'text-zinc-100'}`}>
                        {(speaker.assigned === speaker.label && isGenericSpeaker(speaker.label)) ? t('diarization.identification.use_label', { label: speaker.label }) : speaker.assigned}
                    </span>
                </div>
                <ChevronDown className={`w-4 h-4 text-zinc-500 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 8, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 8, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="absolute top-full left-0 mt-3 w-full bg-[#121212]/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-50 overflow-hidden flex flex-col"
                    >
                        <div className="p-3 border-b border-white/5">
                            <div className="relative group/search">
                                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within/search:text-emerald-500 transition-colors" />
                                <input
                                    type="text"
                                    autoFocus
                                    placeholder={t('sidebar.contexts.placeholder')}
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full bg-black/40 border border-white/5 rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-emerald-500/30 transition-all"
                                />
                            </div>
                        </div>

                        <div className="max-h-[240px] overflow-y-auto p-2 custom-scrollbar space-y-1">
                            {/* Option: Default Label */}
                            <button
                                onClick={() => handleSelect(speaker.label)}
                                className={`w-full flex items-center justify-between p-2.5 rounded-xl transition-all group/item ${
                                    speaker.assigned === speaker.label 
                                        ? 'bg-emerald-500/10 text-emerald-400' 
                                        : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-100'
                                }`}
                            >
                                <span className="text-xs font-bold">
                                    {isGenericSpeaker(speaker.label) 
                                        ? t('diarization.identification.use_label', { label: speaker.label }) 
                                        : speaker.label
                                    }
                                </span>
                                {speaker.assigned === speaker.label && <Check className="w-3.5 h-3.5" />}
                            </button>

                            {/* Group: Known Profiles */}
                            {filteredVoices.length > 0 && (
                                <div className="pt-2">
                                    <div className="px-3 mb-1 text-[9px] font-black uppercase tracking-widest text-zinc-600">{t('diarization.identification.known_profiles')}</div>
                                    {filteredVoices.map(v => (
                                        <button
                                            key={v.id}
                                            onClick={() => handleSelect(v.name)}
                                            className={`w-full flex items-center justify-between p-2.5 rounded-xl transition-all group/item ${
                                                speaker.assigned === v.name 
                                                    ? 'bg-emerald-500/10 text-emerald-400' 
                                                    : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-100'
                                            }`}
                                        >
                                            <span className="text-xs font-bold">{v.name}</span>
                                            {speaker.assigned === v.name && <Check className="w-3.5 h-3.5" />}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* Action: New Name */}
                            <div className="pt-2 border-t border-white/5 mx-1">
                                <button
                                    onClick={() => handleSelect("NEW_PROMPT")}
                                    className="w-full flex items-center gap-3 p-3 rounded-xl text-emerald-400 hover:bg-emerald-500/10 transition-all font-black uppercase tracking-widest text-[10px]"
                                >
                                    <Plus className="w-4 h-4" />
                                    <span>{t('diarization.identification.new_name')}</span>
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const SpeakerCard: React.FC<{
    speaker: Speaker;
    index: number;
    availableVoices: any[];
    onTogglePlay: (id: string) => void;
    onSpeakerChange: (id: string, name: string) => void;
    onTrainVoice: (speaker: Speaker) => void;
}> = ({ speaker, index, availableVoices, onTogglePlay, onSpeakerChange, onTrainVoice }) => {
    const { t } = useTranslation();
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    return (
        <motion.div 
            layout
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            key={speaker.id} 
            style={{ zIndex: isDropdownOpen ? 50 : 0 }}
            className="glass-card p-5 rounded-3xl relative group/card"
        >
            {/* Subtle Background Accent */}
            <div className={`absolute -right-4 -top-4 w-24 h-24 blur-3xl rounded-full opacity-0 group-hover/card:opacity-20 transition-opacity duration-1000 pointer-events-none ${speaker.isPlaying ? 'bg-emerald-500 opacity-20' : 'bg-blue-500'}`} />

            <div className="flex items-start justify-between mb-5 relative z-10">
                <div className="flex items-center gap-3.5">
                    <div className={`flex items-center justify-center w-11 h-11 rounded-2xl transition-all duration-500 ${
                        speaker.isPlaying 
                            ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/30' 
                            : 'bg-white/5 text-zinc-500 group-hover/card:bg-white/10 group-hover/card:text-zinc-200'
                    }`}>
                        <User className={`w-5 h-5 ${speaker.isPlaying ? 'animate-pulse' : ''}`} />
                    </div>
                    <div>
                        <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-1">{speaker.label}</div>
                        <div className="text-[15px] font-black text-zinc-100 tracking-tight leading-none truncate max-w-[140px]">
                            {(speaker.assigned === speaker.label && isGenericSpeaker(speaker.label)) ? t('diarization.identification.unknown') : speaker.assigned}
                        </div>
                    </div>
                </div>
                <button
                    onClick={() => onTogglePlay(speaker.id)}
                    className={`w-11 h-11 rounded-2xl flex items-center justify-center transition-all duration-300 ${
                        speaker.isPlaying 
                            ? 'bg-zinc-800 text-emerald-400 ring-2 ring-emerald-500/20' 
                            : 'bg-white/5 text-zinc-500 hover:bg-emerald-500 hover:text-black hover:shadow-lg hover:shadow-emerald-500/40'
                    }`}
                >
                    {speaker.isPlaying ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5 fill-current" />}
                </button>
            </div>

            <div className="space-y-4 relative z-10">
                <SpeakerDropdown 
                    speaker={speaker} 
                    availableVoices={availableVoices} 
                    onSpeakerChange={onSpeakerChange}
                    onToggleDropdown={setIsDropdownOpen}
                />

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => onTrainVoice(speaker)}
                        className={`flex-1 flex items-center justify-center gap-2.5 py-3.5 rounded-2xl border text-[10px] font-black uppercase tracking-widest transition-all duration-300 shadow-sm hover:shadow-md ${
                            (speaker.assigned.toUpperCase().startsWith('SPEAKER_') || speaker.assigned.toUpperCase() === 'UNKNOWN')
                                ? 'bg-emerald-500/10 hover:bg-emerald-500 border-emerald-500/20 hover:border-emerald-500 text-emerald-400 hover:text-black shadow-emerald-500/10'
                                : 'bg-blue-500/10 hover:bg-blue-500 border-blue-500/20 hover:border-blue-500 text-blue-400 hover:text-white shadow-blue-500/10'
                        }`}
                    >
                        <Mic className="w-4 h-4" />
                        <span>
                            {(speaker.assigned.toUpperCase().startsWith('SPEAKER_') || speaker.assigned.toUpperCase() === 'UNKNOWN') 
                                ? t('diarization.identification.train_voice') 
                                : t('diarization.identification.reinforce_voice')
                            }
                        </span>
                    </button>
                    
                    {speaker.confidence > 0 && (
                        <div className="flex flex-col items-center justify-center px-4 border-l border-white/5 text-center min-w-[60px]">
                            <span className="text-[13px] font-black text-emerald-400 leading-none">{speaker.confidence}%</span>
                            <span className="text-[7px] font-black text-zinc-600 uppercase tracking-tighter mt-1 whitespace-nowrap">Conf.</span>
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
};

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
        <div className="flex flex-col h-full bg-[#0a0a0c] border-r border-white/5 flex-shrink-0 w-85 shadow-2xl overflow-visible">
            <div className="p-6 border-b border-white/5 flex items-center justify-between shrink-0">
                <div>
                    <h3 className="text-xs font-black text-white uppercase tracking-widest leading-none mb-1.5">{t('diarization.identification.title')}</h3>
                    <p className="text-[10px] text-zinc-500 font-bold tracking-tight">{t('diarization.identification.subtitle')}</p>
                </div>
                {canRecognize && (
                    <button
                        onClick={onRecognize}
                        disabled={isRecognizing}
                        className="group flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500/10 to-indigo-500/10 hover:from-blue-500 hover:to-indigo-500 text-blue-400 hover:text-white border border-blue-500/20 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all duration-300 disabled:opacity-50 shadow-lg hover:shadow-blue-500/20 active:scale-95 shrink-0"
                    >
                        {isRecognizing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserPlus className="w-3.5 h-3.5 transition-transform group-hover:scale-110" />}
                        <span>{t('diarization.identification.auto_id')}</span>
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6 overflow-x-visible">
                <AnimatePresence mode="popLayout">
                    {speakers.map((speaker, index) => (
                        <SpeakerCard 
                            key={speaker.id}
                            speaker={speaker}
                            index={index}
                            availableVoices={availableVoices}
                            onTogglePlay={onTogglePlay}
                            onSpeakerChange={onSpeakerChange}
                            onTrainVoice={onTrainVoice}
                        />
                    ))}
                </AnimatePresence>
            </div>
        </div>
    );
};
