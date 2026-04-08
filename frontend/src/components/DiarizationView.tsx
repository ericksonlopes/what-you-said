import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import { 
    ChevronLeft
} from 'lucide-react';
import { useAppContext } from '../store/AppContext';
import { api } from '../services/api';

// Sub-components
import { DiarizationJob, Speaker, Step } from './diarization/types';
import { 
    mapBackendJob, 
    mergeSpeakerSegments, 
    extractSpeakersFromSegments 
} from './diarization/diarizationUtils';
import { StatusBadge } from './diarization/StatusBadge';
import { NewDiarizationModal } from './diarization/NewDiarizationModal';
import { VoiceTrainingModal } from './diarization/VoiceTrainingModal';
import { SpeakerIdentificationPanel } from './diarization/SpeakerIdentificationPanel';
import { TranscriptPanel } from './diarization/TranscriptPanel';
import { DiarizationList } from './diarization/DiarizationList';

import { DiarizationMetadataPanel } from './diarization/DiarizationMetadataPanel';

export function DiarizationView() {
    const { t } = useTranslation();
    const { 
        selectedSubjects, 
        addToast, 
        refreshJobs, 
        refreshSources,
        voices,
        refreshVoices,
        lastEvent 
    } = useAppContext();

    // -- STATE --
    const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');
    const [jobs, setJobs] = useState<DiarizationJob[]>([]);
    const [isLoadingJobs, setIsLoadingJobs] = useState(true);
    const [activeJob, setActiveJob] = useState<DiarizationJob | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');

    // Modal & Selection State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingJobId, setEditingJobId] = useState<string | null>(null);
    const [editingName, setEditingName] = useState('');
    const [trainingSpeaker, setTrainingSpeaker] = useState<Speaker | null>(null);

    // Detail View State
    const [step, setStep] = useState<Step>('idle');
    const [speakers, setSpeakers] = useState<Speaker[]>([]);
    const [finalSegments, setFinalSegments] = useState<any[]>([]);
    const [isSaving, setIsSaving] = useState(false);
    const [isRecognizing, setIsRecognizing] = useState(false);
    
    // Audio playback
    const audioRef = useRef<HTMLAudioElement | null>(null);

    // -- DATA LOADING --
    const loadJobs = useCallback(async (silent = false) => {
        if (!silent) setIsLoadingJobs(true);
        try {
            const subject_ids = selectedSubjects.map(s => s.id);
            const data = await api.fetchDiarizations(50, 0, subject_ids);
            const mappedJobs = data.map(mapBackendJob);
            setJobs(mappedJobs);
            return mappedJobs;
        } catch (err) {
            console.error('Failed to load diarizations:', err);
            if (!silent) addToast(t('diarization.notifications.load_error'), 'error');
            return [];
        } finally {
            if (!silent) setIsLoadingJobs(false);
        }
    }, [addToast, t, selectedSubjects]);

    useEffect(() => {
        loadJobs();
    }, [loadJobs]);

    // React to global SSE events from AppContext
    useEffect(() => {
        if (!lastEvent) return;

        if (lastEvent.type === 'diarization') {
            loadJobs(true);
            
            // If the updated job is the active one, refresh its details
            if (activeJob && lastEvent.id === activeJob.id) {
                loadJobs(true).then(updatedJobs => {
                    const updated = updatedJobs.find(j => j.id === activeJob.id);
                    if (updated && updated.status !== activeJob.status) {
                         // If user is already in identification/result, don't reset the
                         // local speakers state on transient status changes (e.g. voice
                         // training flipping the job to TRAINING → COMPLETED). Only
                         // open/reset the job when we were still waiting on the initial
                         // diarization run.
                         const inIdentification = step === 'identification' || step === 'result';
                         if (!inIdentification && (updated.status === 'awaiting_verification' || updated.status === 'completed' || updated.status === 'failed')) {
                            handleOpenJob(updated);
                        } else {
                            setActiveJob(updated);
                        }
                    }
                });

                if (lastEvent.status === 'completed') {
                    addToast(lastEvent.message || t('diarization.notifications.identify_success'), 'success');
                } else if (lastEvent.status === 'failed') {
                    addToast(lastEvent.message || t('diarization.notifications.start_error'), 'error');
                }
            }
        }

        // Voice training finished in background → clear per-speaker processing flag
        if (lastEvent.type === 'voice' && lastEvent.action === 'train' && lastEvent.name) {
            const finishedName = lastEvent.name as string;
            setSpeakers(prev => prev.map(s =>
                s.trainingStatus === 'processing' && s.assigned === finishedName
                    ? { ...s, trainingStatus: undefined, confidence: Math.max(s.confidence, 95) }
                    : s
            ));
            refreshVoices();
        }
    }, [lastEvent, loadJobs, activeJob, addToast, t, step, refreshVoices]);


    // -- HANDLERS --
    const handleOpenJob = (job: DiarizationJob) => {
        setActiveJob(job);
        if (job.status === 'completed') {
            setFinalSegments(mergeSpeakerSegments(job.segments, job.recognitionResults));
            setSpeakers(extractSpeakersFromSegments(job.segments, job.recognitionResults));
            setStep('result');
        } else if (job.status === 'awaiting_verification') {
            setSpeakers(extractSpeakersFromSegments(job.segments, job.recognitionResults));
            setStep('identification');
        } else if (job.status === 'failed') {
            setStep('error');
        } else {
            setStep('processing');
        }
        setViewMode('detail');
    };

    const handleBackToList = () => {
        setViewMode('list');
        setActiveJob(null);
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
    };

    const handleDeleteJob = async (id: string) => {
        try {
            await api.deleteDiarization(id);
            setJobs(prev => prev.filter(j => j.id !== id));
            if (activeJob?.id === id) {
                setActiveJob(null);
                setViewMode('list');
            }
            addToast(t('diarization.notifications.delete_success'), 'success');
            refreshSources();
            refreshJobs();
        } catch (err) {
            console.error('Failed to delete diarization:', err);
            addToast(t('diarization.notifications.delete_error'), 'error');
        }
    };

    const handleReprocessJob = async (id: string) => {
        if (!globalThis.confirm(t('diarization.reprocess_confirmation'))) return;
        try {
            await api.reprocessDiarization(id);
            addToast(t('diarization.notifications.reprocess_success'), 'success');
            loadJobs(true);
        } catch (err) {
            console.error('Failed to reprocess diarization:', err);
            addToast(t('diarization.notifications.reprocess_error'), 'error');
        }
    };

    const handleTogglePlay = async (speakerId: string) => {
        const speaker = speakers.find(s => s.id === speakerId);
        if (!speaker || !activeJob) return;

        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }

        if (speaker.isPlaying) {
            setSpeakers(prev => prev.map(s => ({...s, isPlaying: false})));
            return;
        }

        setSpeakers(prev => prev.map(s => ({...s, isPlaying: s.id === speakerId})));

        try {
            const result = await api.getSpeakerAudioUrl(activeJob.id, speaker.label);
            const url = result?.url || result?.presigned_url;
            if (url) {
                const audio = new Audio(url);
                audioRef.current = audio;
                
                const onAudioEnded = () => {
                    setSpeakers(prev => prev.map(s => ({...s, isPlaying: false})));
                    audioRef.current = null;
                };
                
                audio.onended = onAudioEnded;
                await audio.play();
            }
        } catch (err) {
            console.error('Failed to play speaker audio:', err);
            setSpeakers(prev => prev.map(s => ({...s, isPlaying: false})));
            addToast(t('diarization.notifications.audio_fetch_error'), 'error');
        }
    };

    const handleSpeakerChange = (speakerId: string, name: string) => {
        if (name === 'NEW_PROMPT') {
            const speaker = speakers.find(s => s.id === speakerId);
            if (speaker) setTrainingSpeaker(speaker);
            return;
        }
        setSpeakers(prev => prev.map(s => s.id === speakerId ? {...s, assigned: name} : s));
    };

    const handleRecognizeSpeakers = async () => {
        if (!activeJob) return;
        setIsRecognizing(true);
        try {
            const result = await api.recognizeSpeakers(activeJob.id);
            const mapping = result?.mapping;
            if (mapping) {
                setSpeakers(prev => prev.map(s => {
                    const recognizedName = mapping[s.label];
                    return recognizedName ? {...s, assigned: recognizedName, confidence: 95} : s;
                }));
                addToast(t('diarization.notifications.identify_success'), 'success');
            }
        } catch (err) {
            console.error('Failed to recognize speakers:', err);
            addToast(t('diarization.notifications.identify_error'), 'error');
        } finally {
            setIsRecognizing(false);
        }
    };

    const handleSaveToContext = async () => {
        if (!activeJob || finalSegments.length === 0) return;
        if (selectedSubjects.length === 0) {
            addToast('Selecione um Contexto na barra lateral para poder indexar na base', 'error');
            return;
        }

        setIsSaving(true);
        try {
            const speakerMapping = speakers.reduce((acc: any, s) => {
                acc[s.label] = s.assigned;
                return acc;
            }, {});
            
            const mergedSegmentsData = mergeSpeakerSegments(activeJob.segments, speakerMapping);
            
            await api.updateDiarization(activeJob.id, {
                segments: mergedSegmentsData.map(s => ({
                    start: Number(s.start),
                    end: Number(s.end),
                    text: String(s.text),
                    speaker: String(s.speakerName)
                }))
            });

            const subjectId = selectedSubjects[0].id;
            await api.ingestDiarization({
                diarization_id: activeJob.id,
                subject_id: subjectId,
                name: activeJob.name,
                tokens_per_chunk: 512,
                tokens_overlap: 50,
                language: activeJob.language || 'pt',
                reprocess: true
            });

            addToast('Transcrição salva e indexada com sucesso', 'success');
            refreshJobs();
            if (typeof refreshSources === 'function') refreshSources();
            loadJobs(true); // Refresh local diarization list
            handleBackToList();
        } catch (err) {
            console.error('Error saving transcript:', err);
            addToast('Falha ao salvar transcrição', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleSaveEditName = async (id: string) => {
        if (editingName.trim()) {
            setJobs(prev => prev.map(j => j.id === id ? { ...j, name: editingName.trim() } : j));
            if (activeJob?.id === id) setActiveJob({ ...activeJob, name: editingName.trim() });
        }
        setEditingJobId(null);
    };

    // -- DERIVED --
    const speakerColorMap = useMemo(() => {
        const map: Record<string, number> = {};
        speakers.forEach((s, idx) => { map[s.assigned] = idx % 10; });
        return map;
    }, [speakers]);

    // Live update transcript preview
    useEffect(() => {
        if (activeJob && (step === 'identification' || step === 'result')) {
            const speakerMapping = speakers.reduce((acc: any, s) => {
                acc[s.label] = s.assigned;
                return acc;
            }, {});
            setFinalSegments(mergeSpeakerSegments(activeJob.segments, speakerMapping));
        }
    }, [speakers, activeJob, step]);

    const filteredJobs = useMemo(() => {
        let result = jobs;
        
        if (statusFilter !== 'all') {
            result = result.filter(j => j.status === statusFilter);
        }

        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            result = result.filter(j => 
                j.name.toLowerCase().includes(q) || 
                j.date.toLowerCase().includes(q) ||
                j.status.toLowerCase().includes(q)
            );
        }
        return result;
    }, [jobs, searchQuery, statusFilter]);

    return (
        <div className="h-full flex overflow-hidden">
            <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col">
                <AnimatePresence mode="wait">
                    {viewMode === 'list' ? (
                        <DiarizationList
                            key="list"
                            jobs={filteredJobs}
                            isLoading={isLoadingJobs}
                            isRefreshing={isLoadingJobs}
                            onRefresh={() => loadJobs()}
                            searchQuery={searchQuery}
                            onSearchChange={setSearchQuery}
                            statusFilter={statusFilter}
                            onStatusFilterChange={setStatusFilter}
                            onOpenJob={handleOpenJob}
                            onDeleteJob={handleDeleteJob}
                            onReprocessJob={handleReprocessJob}
                            onNewJob={() => setIsModalOpen(true)}
                            onEditJob={(job) => { setEditingJobId(job.id); setEditingName(job.name); }}
                            editingJobId={editingJobId}
                            editingName={editingName}
                            onEditingNameChange={setEditingName}
                            onSaveEdit={handleSaveEditName}
                            onCancelEdit={() => setEditingJobId(null)}
                            isNewJobDisabled={selectedSubjects.length === 0}
                        />
                    ) : (
                        <motion.div
                            key="detail"
                            initial={{opacity: 0, x: 20}}
                            animate={{opacity: 1, x: 0}}
                            exit={{opacity: 0, x: -20}}
                            className="flex flex-col h-full overflow-hidden"
                        >
                            {/* TOP BAR */}
                            <div className="h-20 bg-zinc-900/50 border-b border-white/5 flex items-center justify-between px-8 backdrop-blur-md font-bold">
                                <div className="flex items-center gap-6">
                                    <button 
                                        onClick={handleBackToList}
                                        className="p-3 bg-white/5 hover:bg-white/10 rounded-2xl transition-all group"
                                    >
                                        <ChevronLeft className="w-5 h-5 text-zinc-400 group-hover:text-white group-hover:-translate-x-1 transition-all" />
                                    </button>
                                    <div>
                                        <div className="flex items-center gap-3">
                                            <h2 className="text-xl font-black text-white uppercase tracking-tight">{activeJob?.name}</h2>
                                            {activeJob && (
                                                <StatusBadge 
                                                    status={activeJob.status} 
                                                    message={activeJob.statusMessage || activeJob.errorMessage}
                                                    size="sm" 
                                                />
                                            )}
                                        </div>
                                        <div className="flex items-center gap-4 mt-1">
                                            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">{activeJob?.date}</span>
                                            <span className="w-1 h-1 rounded-full bg-zinc-700" />
                                            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">{activeJob?.duration}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* MAIN DETAIL AREA */}
                            <div className="flex-1 flex overflow-hidden">
                                <div className="w-96 flex-shrink-0">
                                    <SpeakerIdentificationPanel
                                        job={activeJob}
                                        speakers={speakers}
                                        availableVoices={voices}
                                        isRecognizing={isRecognizing}
                                        onTogglePlay={handleTogglePlay}
                                        onSpeakerChange={handleSpeakerChange}
                                        onTrainVoice={setTrainingSpeaker}
                                        onRecognize={handleRecognizeSpeakers}
                                        canRecognize={step === 'identification' || step === 'result'}
                                    />
                                </div>
                                <div className="flex-1">
                                    <TranscriptPanel
                                        finalSegments={finalSegments}
                                        speakerColorMap={speakerColorMap}
                                        searchQuery={searchQuery}
                                        onSearchChange={setSearchQuery}
                                        onSave={handleSaveToContext}
                                        isSaving={isSaving}
                                        step={step}
                                        hasContextSelected={selectedSubjects.length > 0}
                                    />
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* 🔵 RIGHT SIDEBAR (Metadata only, Ecosystem is global) */}
            <AnimatePresence mode="wait">
                {viewMode === 'detail' && activeJob && (
                    <motion.div 
                        key="metadata"
                        initial={{ opacity: 0, x: 20, width: 0 }}
                        animate={{ opacity: 1, x: 0, width: 320 }}
                        exit={{ opacity: 0, x: 20, width: 0 }}
                        className="border-l border-white/5 bg-black/20 backdrop-blur-xl flex flex-col shrink-0 overflow-hidden"
                    >
                        <DiarizationMetadataPanel job={activeJob} onReprocess={handleReprocessJob} />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* MODALS */}
            <NewDiarizationModal 
                isOpen={isModalOpen} 
                onClose={() => setIsModalOpen(false)} 
                onStart={() => loadJobs()} 
            />
            <VoiceTrainingModal
                isOpen={!!trainingSpeaker}
                speaker={trainingSpeaker}
                diarizationId={activeJob?.id || ''}
                onClose={() => setTrainingSpeaker(null)}
                onTrained={(name) => {
                    // Mark this speaker as "processing" and optimistically assign the
                    // new name so the UI reflects the in-flight training job. The
                    // button will switch to "Reinforce" once the backend publishes
                    // the voice/train completion event.
                    const targetId = trainingSpeaker?.id;
                    if (targetId) {
                        setSpeakers(prev => prev.map(s =>
                            s.id === targetId
                                ? { ...s, assigned: name, trainingStatus: 'processing' }
                                : s
                        ));
                    }
                }}
            />
        </div>
    );
}

// Re-export StatusBadge as SmallStatusBadge for backward compatibility.
export { StatusBadge as SmallStatusBadge } from './diarization/StatusBadge';
