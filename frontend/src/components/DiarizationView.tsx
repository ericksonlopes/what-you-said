import React, {useCallback, useEffect, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {AnimatePresence, motion} from 'motion/react';
import {
    AlertCircle,
    ArrowRight,
    Check,
    CheckCircle2,
    ChevronLeft,
    Clock,
    Database,
    Edit2,
    FileText,
    Link as LinkIcon,
    Loader2,
    Mic,
    Play,
    Plus,
    RefreshCw,
    Save,
    Square,
    Trash2,
    Upload,
    User,
    Video,
    X,
    Youtube
} from 'lucide-react';
import {useAppContext} from '../store/AppContext';
import {api} from '../services/api';

type Step = 'idle' | 'processing' | 'identification' | 'result';

interface Speaker {
    id: string;
    label: string;
    original: string;
    assigned: string;
    isPlaying: boolean;
    confidence: number;
    audioUrl?: string;
}

interface DiarizationJob {
    id: string;
    title: string;
    date: string;
    status: 'completed' | 'pending' | 'processing' | 'failed' | 'ready';
    duration: string;
    durationSeconds: number;
    sourceType: string;
    externalSource: string;
    language: string;
    modelSize: string;
    segments: any[];
    recognitionResults: any;
    storagePath: string;
    sourceMetadata: any;
    statusMessage?: string;
    errorMessage?: string;
}

function formatDuration(seconds: number): string {
    if (!seconds || seconds <= 0) return '--:--';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function mapBackendJob(r: any): DiarizationJob {
    const backendStatus = r.status || 'pending';
    const hasSegments = r.segments && r.segments.length > 0;

    // We want users to ALWAYS go through the identification step first to confirm voices
    // unless they already clicked "Generate Final Transcript" which we can infer
    // if the segments in the DB already have names that aren't SPEAKER_XX.
    let status: DiarizationJob['status'] = backendStatus;
    
    if (backendStatus === 'completed' && hasSegments) {
        // If all speakers in segments are still generic SPEAKER_ labels, stay in 'ready'
        const allGeneric = r.segments.every((s: any) => 
            !s.speaker || s.speaker.startsWith('SPEAKER_')
        );
        
        // If we have recognition but haven't "applied" it to segments yet (generic speakers),
        // we show it as 'ready' so the user can see the automatic labels in the ID step.
        status = allGeneric ? 'ready' : 'completed';
    }

    return {
        id: r.id,
        title: r.title || 'Untitled',
        date: r.created_at ? r.created_at.split('T')[0].split(' ')[0] : '',
        status,
        duration: formatDuration(r.duration),
        durationSeconds: r.duration || 0,
        sourceType: r.source_type || '',
        externalSource: r.external_source || '',
        language: r.language || 'pt',
        modelSize: r.model_size || '',
        segments: r.segments || [],
        recognitionResults: r.recognition_results || {},
        storagePath: r.storage_path || '',
        sourceMetadata: r.source_metadata || null,
        statusMessage: r.status_message,
        errorMessage: r.error_message,
    };
}

export function DiarizationView() {
    const {t} = useTranslation();
    const {selectedSubjects, addToast, refreshJobs} = useAppContext();

    const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');
    const [jobs, setJobs] = useState<DiarizationJob[]>([]);
    const [isLoadingJobs, setIsLoadingJobs] = useState(true);
    const [activeJob, setActiveJob] = useState<DiarizationJob | null>(null);

    // Edit State
    const [editingJobId, setEditingJobId] = useState<string | null>(null);
    const [editingTitle, setEditingTitle] = useState('');

    // Modal State
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [uploadType, setUploadType] = useState<'file' | 'youtube'>('file');
    const [youtubeLink, setYoutubeLink] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Processing options
    const [language, setLanguage] = useState('pt');
    const [modelSize, setModelSize] = useState('base');

    // Detail View State
    const [step, setStep] = useState<Step>('idle');
    const [speakers, setSpeakers] = useState<Speaker[]>([]);
    const [availableVoices, setAvailableVoices] = useState<any[]>([]);
    const [finalSegments, setFinalSegments] = useState<any[]>([]);
    const [rawTranscript, setRawTranscript] = useState<string>('');
    const [transcript, setTranscript] = useState<string>('');
    const [isSaving, setIsSaving] = useState(false);
    const [isRecognizing, setIsRecognizing] = useState(false);

    // Voice Training State
    const [trainingSpeaker, setTrainingSpeaker] = useState<Speaker | null>(null);
    const [voiceProfileName, setVoiceProfileName] = useState('');
    const [isTraining, setIsTraining] = useState(false);

    // Audio playback
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const loadAvailableVoices = useCallback(async () => {
        try {
            const voices = await api.fetchVoiceProfiles();
            setAvailableVoices(voices);
        } catch (err) {
            console.error('Failed to load voice profiles:', err);
        }
    }, []);

    const loadJobs = useCallback(async (silent = false) => {
        if (!silent) setIsLoadingJobs(true);
        try {
            const data = await api.fetchDiarizations(50, 0);
            const mappedJobs = data.map(mapBackendJob);
            setJobs(mappedJobs);
            return mappedJobs; // Return the fresh data
        } catch (err) {
            console.error('Failed to load diarizations:', err);
            if (!silent) addToast(t('diarization.notifications.load_error'), 'error');
            return [];
        } finally {
            if (!silent) setIsLoadingJobs(false);
        }
    }, [addToast, t]);

    // Initial load
    useEffect(() => {
        loadJobs();
        loadAvailableVoices();
    }, [loadJobs, loadAvailableVoices]);

    // Auto-refresh interval (every 5 seconds) as fallback
    useEffect(() => {
        const interval = setInterval(() => {
            if (viewMode === 'list') {
                loadJobs(true);
            }
        }, 30000); // Increased fallback to 30s since we have SSE

        return () => clearInterval(interval);
    }, [loadJobs, viewMode]);

    // SSE Real-time updates
    useEffect(() => {
        const eventSource = new EventSource('/api/notifications/events');

        eventSource.onmessage = async (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'diarization') {
                    console.log('Real-time diarization update:', data);
                    
                    // Refresh the full list to keep everything in sync
                    const freshJobs = await loadJobs(true);
                    
                    // Update the jobs state with the new message if present
                    setJobs(prevJobs => prevJobs.map(j => {
                        if (j.id === data.id) {
                            return {
                                ...j,
                                status: data.status,
                                statusMessage: data.message // Use the real-time message from Redis
                            };
                        }
                        return j;
                    }));
                    
                    // If we are looking at this specific job, update the activeJob state too
                    if (activeJob && activeJob.id === data.id) {
                        const updated = freshJobs.find(j => j.id === data.id);
                        if (updated) {
                            setActiveJob({
                                ...updated,
                                statusMessage: data.message
                            });
                            // If it just finished, transition to the next step automatically
                            if (updated.status === 'ready' || updated.status === 'completed') {
                                handleOpenJob(updated);
                            }
                        }
                    }
                    
                    if (data.status === 'completed') {
                        addToast(data.message || t('diarization.notifications.identify_success'), 'success');
                    } else if (data.status === 'failed') {
                        addToast(data.message || t('diarization.notifications.start_error'), 'error');
                    }
                }
            } catch (err) {
                console.error('Failed to parse SSE message:', err);
            }
        };

        eventSource.onerror = (err) => {
            console.error('SSE Connection error:', err);
            eventSource.close();
        };

        return () => {
            eventSource.close();
        };
    }, [loadJobs, addToast]);

    const buildTranscriptFromSegments = (segments: any[], recognition?: any) => {
        if (!segments || segments.length === 0) return '';
        return segments.map(seg => {
            const speaker = recognition?.[seg.speaker] || seg.speaker;
            return `${speaker}: ${seg.text}`;
        }).join('\n');
    };

    const extractSpeakersFromSegments = (segments: any[], recognition?: any): Speaker[] => {
        const speakerLabels = [...new Set(segments.map((s: any) => s.speaker as string))].sort();
        const mapping = recognition?.mapping || {};
        const details = recognition?.details || {};

        return speakerLabels.map((label, i) => {
            const identifiedName = mapping[label];
            const confidence = details[label]?.score ? Math.round(details[label].score * 100) : (identifiedName ? 95 : 0);
            
            return {
                id: String(i),
                label,
                original: label,
                assigned: identifiedName || label,
                isPlaying: false,
                confidence: confidence,
            };
        });
    };

    const handleOpenJob = (job: DiarizationJob) => {
        console.log('Opening job:', job.id, 'Status:', job.status);
        setActiveJob(job);

        if (job.status === 'completed') {
            console.log('Job is completed, setting up result step');
            const text = buildTranscriptFromSegments(job.segments, job.recognitionResults);
            setTranscript(text);
            
            // Populate finalSegments from segments if it's already completed
            const enriched = job.segments.map((seg, idx) => ({
                ...seg,
                id: idx,
                speakerName: job.recognitionResults?.mapping?.[seg.speaker] || seg.speaker,
                startTime: formatDuration(seg.start),
                endTime: formatDuration(seg.end)
            }));
            setFinalSegments(enriched);
            setStep('result');
        } else if (job.status === 'ready') {
            console.log('Job is ready or needs identification, setting up identification step');
            const rawText = buildTranscriptFromSegments(job.segments);
            setRawTranscript(rawText);
            setSpeakers(extractSpeakersFromSegments(job.segments, job.recognitionResults));
            setStep('identification');
        } else {
            console.log('Job is processing/pending, setting up processing step');
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

    const handleDeleteJob = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        try {
            await api.deleteDiarization(id);
            setJobs(jobs.filter(j => j.id !== id));
            if (activeJob?.id === id) {
                setActiveJob(null);
                setViewMode('list');
            }
            addToast(t('diarization.notifications.delete_success'), 'success');
        } catch (err) {
            console.error('Failed to delete diarization:', err);
            addToast(t('diarization.notifications.delete_error'), 'error');
        }
    };

    const handleStartEdit = (e: React.MouseEvent, job: DiarizationJob) => {
        e.stopPropagation();
        setEditingJobId(job.id);
        setEditingTitle(job.title);
    };

    const handleSaveEdit = (e: React.MouseEvent | React.KeyboardEvent, id: string) => {
        e.stopPropagation();
        if (editingTitle.trim()) {
            setJobs(jobs.map(j => j.id === id ? {...j, title: editingTitle.trim()} : j));
            if (activeJob?.id === id) {
                setActiveJob({...activeJob, title: editingTitle.trim()});
            }
        }
        setEditingJobId(null);
    };

    const handleCancelEdit = (e: React.MouseEvent | React.KeyboardEvent) => {
        e.stopPropagation();
        setEditingJobId(null);
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFile(e.target.files[0]);
        }
    };

    const handleStartProcessing = async () => {
        if (uploadType === 'youtube' && !youtubeLink) {
            addToast(t('diarization.notifications.youtube_link_error'), 'error');
            return;
        }
        if (uploadType === 'file' && !file) {
            addToast(t('diarization.notifications.file_selection_error'), 'error');
            return;
        }

        setIsSubmitting(true);
        try {
            if (uploadType === 'youtube') {
                await api.startAudioProcessing({
                    source_type: 'youtube',
                    source: youtubeLink,
                    language,
                    model_size: modelSize,
                    recognize_voices: true,
                });
            } else {
                // Upload the file first via ingestFile, then use the path
                // For now, use the upload source type
                const formData = new FormData();
                formData.append('file', file!);
                const uploadResult = await api.ingestFile(formData);
                const s3Path = uploadResult?.s3_path || uploadResult?.file_path || '';

                await api.startAudioProcessing({
                    source_type: 'upload',
                    source: s3Path,
                    language,
                    model_size: modelSize,
                    recognize_voices: true,
                });
            }

            setIsModalOpen(false);
            setFile(null);
            setYoutubeLink('');
            addToast(t('diarization.notifications.start_success'), 'success');

            // Refresh list after short delay
            setTimeout(() => loadJobs(), 2000);
        } catch (err) {
            console.error('Failed to start processing:', err);
            addToast(t('diarization.notifications.start_error'), 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    const togglePlay = async (speakerId: string) => {
        const speaker = speakers.find(s => s.id === speakerId);
        if (!speaker || !activeJob) return;

        // Stop current playback
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
                audio.onended = () => {
                    setSpeakers(prev => prev.map(s => ({...s, isPlaying: false})));
                    audioRef.current = null;
                };
                audio.onerror = () => {
                    setSpeakers(prev => prev.map(s => ({...s, isPlaying: false})));
                    audioRef.current = null;
                    addToast(t('diarization.notifications.playback_error'), 'error');
                };
                await audio.play();
            }
        } catch (err) {
            console.error('Failed to play speaker audio:', err);
            setSpeakers(prev => prev.map(s => ({...s, isPlaying: false})));
            addToast(t('diarization.notifications.audio_fetch_error'), 'error');
        }
    };

    const handleRecognizeSpeakers = async () => {
        if (!activeJob) return;
        setIsRecognizing(true);
        try {
            const result = await api.recognizeSpeakers(activeJob.id);
            // Result now has {mapping, id_mapping, details}
            const mapping = result?.mapping;
            
            // Update speakers with recognition results
            if (mapping) {
                setSpeakers(prev => prev.map(s => {
                    const recognizedName = mapping[s.label];
                    if (recognizedName) {
                        return {...s, assigned: recognizedName, confidence: 95};
                    }
                    return s;
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

    const applyIdentification = async () => {
        if (!activeJob) return;

        setIsSaving(true);
        try {
            // Build final segments with assigned names and timestamps
            const enrichedSegments = activeJob.segments.map((seg, idx) => {
                const speaker = speakers.find(s => s.label === seg.speaker);
                const name = speaker?.assigned || seg.speaker;
                return {
                    ...seg,
                    id: idx,
                    speaker: name, // Overwrite original speaker label with name for the DB
                    speakerName: name,
                    startTime: formatDuration(seg.start),
                    endTime: formatDuration(seg.end)
                };
            });

            // Persist to backend
            await api.updateDiarization(activeJob.id, {
                segments: enrichedSegments.map(s => ({
                    start: Number(s.start),
                    end: Number(s.end),
                    text: String(s.text),
                    speaker: String(s.speaker)
                }))
            });

            setFinalSegments(enrichedSegments);
            
            // Build transcript string for legacy purposes if needed
            const finalTranscript = enrichedSegments.map(seg => 
                `[${seg.startTime} - ${seg.endTime}] ${seg.speakerName}: ${seg.text}`
            ).join('\n');

            setTranscript(finalTranscript);
            setStep('result');

            const updatedJob = {
                ...activeJob, 
                status: 'completed' as const, 
                segments: enrichedSegments
            };
            setJobs(jobs.map(j => j.id === activeJob.id ? updatedJob : j));
            setActiveJob(updatedJob);

            addToast('Transcrição finalizada e salva com sucesso!', 'success');
        } catch (err) {
            console.error('Failed to finalize diarization:', err);
            addToast('Falha ao finalizar transcrição', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleSaveToContext = async () => {
        if (finalSegments.length === 0 || selectedSubjects.length === 0) {
            addToast('Nenhuma transcrição ou contexto selecionado', 'error');
            return;
        }

        setIsSaving(true);
        try {
            const subjectId = selectedSubjects[0].id;
            const sourceMeta = activeJob?.sourceMetadata;
            const displayTitle = sourceMeta?.title || activeJob?.title || 'Midia';
            
            // Generate content with timestamps for local UI feedback if needed
            // but we now send the ID to the backend for direct ingestion
            const result = await api.ingestDiarization({
                diarization_id: activeJob!.id,
                subject_id: subjectId,
                title: displayTitle,
                tokens_per_chunk: 512,
                tokens_overlap: 50,
                language: activeJob?.language || 'pt',
                reprocess: true
            });

            addToast('Transcrição indexada na base com sucesso', 'success');
            refreshJobs();
        } catch (err) {
            console.error('Error saving transcript:', err);
            addToast('Falha ao salvar transcrição', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleTrainVoice = async () => {
        if (!trainingSpeaker || !voiceProfileName.trim() || !activeJob) return;
        setIsTraining(true);
        try {
            await api.trainVoiceFromSpeaker({
                diarization_id: activeJob.id,
                speaker_label: trainingSpeaker.label,
                name: voiceProfileName.trim(),
            });
            addToast(`Perfil de voz "${voiceProfileName}" salvo com sucesso!`, 'success');
            setTrainingSpeaker(null);
            setVoiceProfileName('');
        } catch (err) {
            console.error('Failed to train voice:', err);
            addToast('Falha ao treinar perfil de voz', 'error');
        } finally {
            setIsTraining(false);
        }
    };

    const parseTranscript = (text: string) => {
        if (!text) return [];
        const lines = text.split('\n').filter(line => line.trim() !== '');
        return lines.map((line, index) => {
            const match = line.match(/^(.*?):\s*(.*)$/);
            if (match) {
                return {id: index, speaker: match[1], text: match[2]};
            }
            return {id: index, speaker: 'Desconhecido', text: line};
        });
    };

    const parsedTranscript = parseTranscript(transcript);

    return (
        <div className="relative h-full">
            {viewMode === 'list' ? (
                <motion.div
                    initial={{opacity: 0, y: 10}}
                    animate={{opacity: 1, y: 0}}
                    className="p-8 max-w-5xl mx-auto h-full flex flex-col"
                >
                    <div className="mb-8 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div
                                className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                                <Mic className="w-7 h-7 text-emerald-400"/>
                            </div>
                            <div>
                                <h2 className="text-3xl font-black text-white tracking-tight leading-none">{t('diarization.title')}</h2>
                                <p className="text-zinc-500 text-sm mt-2 font-medium">{t('diarization.subtitle')}</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setIsModalOpen(true)}
                            className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500 text-black font-bold rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                        >
                            <Plus className="w-5 h-5"/>
                            {t('diarization.new_btn')}
                        </button>
                    </div>

                    <div
                        className="flex-1 bg-zinc-900/40 border border-white/5 rounded-2xl overflow-hidden backdrop-blur-sm flex flex-col">
                        <div className="overflow-x-auto custom-scrollbar flex-1 flex flex-col">
                            <div className="min-w-[800px] flex-1 flex flex-col">
                                <div
                                    className="grid grid-cols-12 gap-4 p-4 border-b border-white/5 text-xs font-bold text-zinc-500 uppercase tracking-wider bg-black/20">
                                    <div className="col-span-3">{t('diarization.table.name')}</div>
                                    <div className="col-span-2">{t('diarization.table.date')}</div>
                                    <div className="col-span-1">{t('diarization.table.type')}</div>
                                    <div className="col-span-1">{t('diarization.table.model')}</div>
                                    <div className="col-span-1">{t('diarization.table.duration')}</div>
                                    <div className="col-span-2">{t('diarization.table.status')}</div>
                                    <div className="col-span-2 text-right">{t('diarization.table.actions')}</div>
                                </div>
                                <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
                                    {isLoadingJobs ? (
                                        <div
                                            className="h-full flex flex-col items-center justify-center text-zinc-500 py-20">
                                            <Loader2 className="w-8 h-8 animate-spin mb-4 text-emerald-500"/>
                                            <p>{t('diarization.table.loading')}</p>
                                        </div>
                                    ) : jobs.length === 0 ? (
                                        <div
                                            className="h-full flex flex-col items-center justify-center text-zinc-500 py-20">
                                            <Mic className="w-12 h-12 mb-4 opacity-20"/>
                                            <p>{t('diarization.table.none')}</p>
                                        </div>
                                    ) : (
                                        jobs.map((job) => (
                                            <div
                                                key={job.id}
                                                onClick={() => {
                                                    console.log('Clicked row for job:', job.id);
                                                    if (editingJobId !== job.id) {
                                                        const currentJob = jobs.find(j => j.id === job.id);
                                                        if (currentJob) handleOpenJob(currentJob);
                                                    }
                                                }}
                                                className="grid grid-cols-12 gap-4 p-3 rounded-xl hover:bg-white/5 cursor-pointer transition-colors items-center group"
                                            >
                                                <div className="col-span-3 flex items-center gap-3">
                                                    <div
                                                        className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-500/20 transition-colors flex-shrink-0">
                                                        <FileText className="w-4 h-4"/>
                                                    </div>
                                                    {editingJobId === job.id ? (
                                                        <div className="flex items-center gap-1 flex-1 min-w-0"
                                                             onClick={e => e.stopPropagation()}>
                                                            <input
                                                                type="text"
                                                                autoFocus
                                                                value={editingTitle}
                                                                onChange={e => setEditingTitle(e.target.value)}
                                                                onKeyDown={e => {
                                                                    if (e.key === 'Enter') handleSaveEdit(e, job.id);
                                                                    if (e.key === 'Escape') handleCancelEdit(e);
                                                                }}
                                                                className="flex-1 bg-zinc-900 border border-emerald-500/50 rounded-lg px-2 py-1 text-sm text-white focus:outline-none min-w-0"
                                                            />
                                                            <button onClick={(e) => handleSaveEdit(e, job.id)}
                                                                    className="p-1 text-emerald-400 hover:bg-emerald-500/20 rounded-md transition-colors flex-shrink-0">
                                                                <Check className="w-4 h-4"/>
                                                            </button>
                                                            <button onClick={handleCancelEdit}
                                                                    className="p-1 text-zinc-400 hover:bg-zinc-700 rounded-md transition-colors flex-shrink-0">
                                                                <X className="w-4 h-4"/>
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <span
                                                            className="text-sm font-medium text-zinc-200 truncate">{job.title}</span>
                                                    )}
                                                </div>
                                                <div className="col-span-2 text-sm text-zinc-400">{job.date}</div>
                                                <div className="col-span-1">
                                                    {job.sourceType === 'youtube' ? (
                                                        <span className="flex items-center gap-1.5 text-rose-400" title="YouTube">
                                                            <Youtube className="w-4 h-4" />
                                                            <span className="text-[10px] font-bold uppercase tracking-wider">YT</span>
                                                        </span>
                                                    ) : (
                                                        <span className="flex items-center gap-1.5 text-blue-400" title={t('common.actions.upload')}>
                                                            <Upload className="w-4 h-4" />
                                                            <span className="text-[10px] font-bold uppercase tracking-wider">FILE</span>
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="col-span-1">
                                                    {job.modelSize && (
                                                        <span className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 text-[10px] font-bold uppercase border border-white/5">
                                                            {job.modelSize}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="col-span-1 text-sm text-zinc-400 flex items-center gap-1.5">
                                                    <Clock className="w-3.5 h-3.5"/>
                                                    {job.duration}
                                                </div>
                                                <div className="col-span-2">
                                                    {job.status === 'completed' && (
                                                        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20">
                                                            <CheckCircle2 className="w-3.5 h-3.5"/>
                                                            {t('diarization.status.completed')}
                                                        </span>
                                                    )}
                                                    {job.status === 'ready' && (
                                                        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-blue-500/10 text-blue-400 text-xs font-medium border border-blue-500/20 whitespace-nowrap">
                                                            <User className="w-3.5 h-3.5"/>
                                                            {t('diarization.status.waiting')}
                                                        </span>
                                                    )}
                                                    {job.status === 'failed' && (
                                                        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-rose-500/10 text-rose-400 text-xs font-medium border border-rose-500/20" title={job.errorMessage}>
                                                            <AlertCircle className="w-3.5 h-3.5"/>
                                                            {t('diarization.status.failed')}
                                                        </span>
                                                    )}
                                                    {/* Dynamic status for anything else (processing, downloading, etc) */}
                                                    {job.status !== 'completed' && job.status !== 'ready' && job.status !== 'failed' && (
                                                        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-amber-500/10 text-amber-400 text-xs font-medium border border-amber-500/20 whitespace-nowrap overflow-hidden" title={job.statusMessage}>
                                                            <Loader2 className="w-3.5 h-3.5 animate-spin flex-shrink-0"/>
                                                            <span className="truncate max-w-[100px]">
                                                                {job.statusMessage?.split('...')[0] || (job.status === 'pending' ? t('diarization.status.in_queue') : job.status)}...
                                                            </span>
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="col-span-2 flex items-center justify-end gap-1">
                                                    {editingJobId !== job.id && (
                                                        <>
                                                            <button
                                                                onClick={(e) => handleStartEdit(e, job)}
                                                                className="p-1.5 text-zinc-500 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-md transition-colors"
                                                                title={t('diarization.table.edit_name')}
                                                            >
                                                                <Edit2 className="w-4 h-4"/>
                                                            </button>
                                                            <button
                                                                onClick={(e) => handleDeleteJob(e, job.id)}
                                                                className="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition-colors"
                                                                title={t('diarization.table.delete')}
                                                            >
                                                                <Trash2 className="w-4 h-4"/>
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            ) : (
                <motion.div
                    initial={{opacity: 0, y: 10}}
                    animate={{opacity: 1, y: 0}}
                    className="p-8 max-w-5xl mx-auto h-full flex flex-col"
                >
                    <div className="mb-8 flex items-center gap-4">
                        <button
                            onClick={handleBackToList}
                            className="p-3 rounded-2xl bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700 transition-colors border border-white/5"
                        >
                            <ChevronLeft className="w-6 h-6"/>
                        </button>
                        <div
                            className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                            <Mic className="w-7 h-7 text-emerald-400"/>
                        </div>
                        <div>
                            <h2 className="text-3xl font-black text-white tracking-tight leading-none">
                                {activeJob?.title}
                            </h2>
                            <p className="text-zinc-500 text-sm mt-2 font-medium">
                                {activeJob?.status === 'completed' && t('diarization.detail.viewing_completed')}
                                {(activeJob?.status === 'pending' || activeJob?.status === 'processing') && t('diarization.detail.server_processing')}
                                {activeJob?.status === 'failed' && `${t('diarization.status.failed_msg')}: ${activeJob?.errorMessage || t('common.status.unknown')}`}
                                {activeJob?.status === 'ready' && t('diarization.detail.id_speakers_help')}
                            </p>
                        </div>
                    </div>

                    <div
                        className="grid grid-cols-1 lg:grid-cols-12 grid-rows-[auto_1fr] lg:grid-rows-1 gap-6 flex-1 min-h-0">
                        {/* Left Column: Job Details */}
                        <div className="flex flex-col gap-6 lg:col-span-4">
                            {activeJob && (
                                <div className="bg-zinc-900/40 border border-white/5 rounded-2xl p-6 backdrop-blur-sm">
                                    <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                                        <FileText className="w-5 h-5 text-emerald-400"/>
                                        {t('diarization.detail.file_details')}
                                    </h3>
                                    <div className="space-y-5">
                                        <div>
                                            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1.5">{t('diarization.detail.original_name')}</p>
                                            <p className="text-sm text-zinc-200 font-medium">{activeJob.title}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1.5">{t('diarization.detail.process_date')}</p>
                                            <p className="text-sm text-zinc-200 font-medium">{activeJob.date}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1.5">{t('diarization.table.duration')}</p>
                                            <p className="text-sm text-zinc-200 font-medium flex items-center gap-1.5">
                                                <Clock className="w-4 h-4 text-zinc-400"/>
                                                {activeJob.duration}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1.5">{t('diarization.table.type')}</p>
                                            <p className="text-sm text-zinc-200 font-medium">{activeJob.sourceType}</p>
                                        </div>
                                        {activeJob.modelSize && (
                                        <div>
                                            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1.5">{t('diarization.table.model')}</p>
                                            <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-200 text-xs font-bold border border-white/5">
                                                {activeJob.modelSize}
                                            </span>
                                        </div>
                                        )}
                                        <div>
                                            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1.5">{t('diarization.detail.speakers_count')}</p>
                                            <p className="text-sm text-zinc-200 font-medium">{speakers.length || [...new Set((activeJob.segments || []).map(s => s.speaker))].length}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-1.5">{t('diarization.table.status')}</p>
                                            {activeJob.status === 'completed' && (
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-bold border border-emerald-500/20">
                                                    <CheckCircle2 className="w-3.5 h-3.5"/>
                                                    {t('diarization.status.completed')}
                                                </span>
                                            )}
                                            {(activeJob.status === 'pending' || activeJob.status === 'processing') && (
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 text-xs font-bold border border-amber-500/20">
                                                    <Loader2 className="w-3.5 h-3.5 animate-spin"/>
                                                    {activeJob.status === 'pending' ? t('diarization.status.in_queue') : t('common.status.processing')}
                                                </span>
                                            )}
                                            {activeJob.status === 'failed' && (
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-500/10 text-rose-400 text-xs font-bold border border-rose-500/20">
                                                    <AlertCircle className="w-3.5 h-3.5"/>
                                                    {t('diarization.status.failed')}
                                                </span>
                                            )}
                                            {activeJob.status === 'ready' && (
                                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-500/10 text-blue-400 text-xs font-bold border border-blue-500/20">
                                                    <User className="w-3.5 h-3.5"/>
                                                    {t('diarization.status.waiting')}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Right Column: Dynamic Content based on Step */}
                        <div
                            className="bg-zinc-900/40 border border-white/5 rounded-2xl p-6 backdrop-blur-sm flex flex-col h-full min-h-0 lg:col-span-8">
                            {step === 'processing' && (
                                <div className="h-full flex flex-col items-center justify-center text-zinc-500 gap-4">
                                    <div className="relative">
                                        <div
                                            className="w-16 h-16 rounded-full border-2 border-emerald-500/20 border-t-emerald-500 animate-spin"/>
                                        <Mic
                                            className="w-6 h-6 text-emerald-500/50 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"/>
                                    </div>
                                    <p className="animate-pulse font-medium text-emerald-400">
                                        {activeJob?.statusMessage || t('diarization.status.processing_default')}
                                    </p>
                                    <button
                                        onClick={() => loadJobs().then((freshJobs) => {
                                            const updated = freshJobs.find(j => j.id === activeJob?.id);
                                            if (updated && updated.status !== 'pending' && updated.status !== 'processing') {
                                                handleOpenJob(updated);
                                            } else if (updated?.status === 'failed') {
                                                addToast(t('diarization.status.failed_msg'), 'error');
                                            } else {
                                                addToast(t('diarization.status.still_processing'), 'info');
                                            }
                                        })}
                                        className="mt-4 px-4 py-2 text-sm font-bold text-zinc-400 hover:text-white bg-zinc-800 rounded-xl hover:bg-zinc-700 transition-colors border border-white/5"
                                    >
                                        {t('diarization.status.check_status')}
                                    </button>
                                </div>
                            )}

                            {step === 'identification' && (
                                <div className="flex flex-col h-full min-h-0">
                                    <div className="mb-6 flex items-center justify-between">
                                        <div>
                                            <h4 className="text-xl font-bold text-white mb-2">{t('diarization.detail.id_speakers_title')}</h4>
                                            <p className="text-zinc-400 text-sm">{t('diarization.detail.id_speakers_desc', { count: speakers.length })}</p>
                                        </div>
                                        <button
                                            onClick={handleRecognizeSpeakers}
                                            disabled={isRecognizing}
                                            className="flex items-center gap-2 px-4 py-2 text-sm font-bold bg-zinc-800 text-zinc-200 rounded-xl hover:bg-zinc-700 transition-colors border border-white/5 disabled:opacity-50 flex-shrink-0 ml-4"
                                        >
                                            {isRecognizing ? <Loader2 className="w-4 h-4 animate-spin"/> :
                                                <Mic className="w-4 h-4"/>}
                                            {t('diarization.detail.auto_identify')}
                                        </button>
                                    </div>

                                    <div className="space-y-4 flex-1 overflow-y-auto custom-scrollbar pr-2">
                                        {speakers.map((s, i) => (
                                            <motion.div
                                                initial={{opacity: 0, x: 20}}
                                                animate={{opacity: 1, x: 0}}
                                                transition={{delay: i * 0.1}}
                                                key={s.id}
                                                className="bg-black/40 border border-white/5 rounded-2xl p-4 flex flex-col gap-4"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <button
                                                            onClick={() => togglePlay(s.id)}
                                                            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${s.isPlaying ? 'bg-emerald-500 text-black shadow-[0_0_15px_rgba(16,185,129,0.4)]' : 'bg-zinc-800 text-emerald-400 hover:bg-zinc-700'}`}
                                                        >
                                                            {s.isPlaying ? <Square className="w-4 h-4 fill-current"/> :
                                                                <Play className="w-4 h-4 fill-current ml-0.5"/>}
                                                        </button>
                                                        <div>
                                                            <p className="text-sm font-bold text-zinc-200">{t('diarization.detail.voice_label', { index: i + 1 })}
                                                                <span
                                                                    className="text-zinc-500 font-normal text-xs">({s.label})</span>
                                                            </p>
                                                            {s.confidence > 0 &&
                                                                <p className="text-xs text-zinc-500">{t('diarization.detail.confidence')}: {s.confidence}%</p>}
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center gap-1 h-8 px-4">
                                                        {[...Array(16)].map((_, j) => (
                                                            <motion.div
                                                                key={j}
                                                                animate={s.isPlaying ? {height: ['20%', '100%', '40%', '80%', '20%']} : {height: '20%'}}
                                                                transition={s.isPlaying ? {
                                                                    repeat: Infinity,
                                                                    duration: 0.6 + Math.random() * 0.4,
                                                                    ease: "easeInOut"
                                                                } : {duration: 0.3}}
                                                                className="w-1 bg-emerald-500/50 rounded-full"
                                                                style={{height: '20%'}}
                                                            />
                                                        ))}
                                                    </div>
                                                </div>

                                                <div
                                                    className="flex items-center gap-3 bg-zinc-900/50 p-2 rounded-xl border border-white/5 focus-within:border-emerald-500/50 transition-colors">
                                                    <div
                                                        className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center">
                                                        <User className="w-4 h-4 text-zinc-400"/>
                                                    </div>
                                                    <input
                                                        type="text"
                                                        list={`voices-list-${s.id}`}
                                                        value={s.assigned}
                                                        onChange={(e) => {
                                                            setSpeakers(prev => prev.map(sp => sp.id === s.id ? {
                                                                ...sp,
                                                                assigned: e.target.value
                                                            } : sp));
                                                        }}
                                                        placeholder={t('diarization.detail.speaker_placeholder')}
                                                        className="flex-1 bg-transparent border-none text-sm text-white focus:outline-none font-medium"
                                                    />
                                                    <datalist id={`voices-list-${s.id}`}>
                                                        {availableVoices.map((v) => (
                                                            <option key={v.id} value={v.name} />
                                                        ))}
                                                    </datalist>
                                                </div>

                                                <div className="flex justify-end mt-3">
                                                    <button
                                                        onClick={() => {
                                                            setTrainingSpeaker(s);
                                                            setVoiceProfileName(s.assigned !== 'Desconhecido' && !s.assigned.startsWith('SPEAKER_') ? s.assigned : '');
                                                        }}
                                                        className="text-xs font-bold px-3 py-1.5 bg-zinc-800/50 text-zinc-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors flex items-center gap-1.5 border border-white/5"
                                                    >
                                                        {availableVoices.some(v => v.name === s.assigned) ? (
                                                            <>
                                                                <RefreshCw className="w-3.5 h-3.5"/>
                                                                {t('diarization.detail.reinforce_voice')}
                                                            </>
                                                        ) : (
                                                            <>
                                                                <Mic className="w-3.5 h-3.5"/>
                                                                {t('diarization.detail.train_voice')}
                                                            </>
                                                        )}
                                                    </button>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>

                                    <div className="pt-6 mt-4 border-t border-white/5">
                                        <button
                                            onClick={applyIdentification}
                                            className="w-full flex items-center justify-center gap-2 py-3.5 bg-emerald-500 text-black font-bold rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)]"
                                        >
                                            {t('diarization.detail.generate_transcript')}
                                            <ArrowRight className="w-5 h-5"/>
                                        </button>
                                    </div>
                                </div>
                            )}

                            {step === 'result' && (
                                <div className="flex flex-col h-full min-h-0">
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                                                <FileText className="w-5 h-5 text-emerald-400"/>
                                            </div>
                                            <div>
                                                <h3 className="text-lg font-bold text-white leading-tight">{t('diarization.detail.final_transcript')}</h3>
                                                <p className="text-xs text-zinc-500">{t('diarization.detail.segments_count', { count: finalSegments.length })}</p>
                                            </div>
                                        </div>
                                        <button
                                            onClick={handleSaveToContext}
                                            disabled={isSaving || selectedSubjects.length === 0}
                                            className="flex items-center gap-2 px-4 py-2 bg-emerald-500 text-black text-sm font-bold rounded-xl hover:bg-emerald-400 transition-all disabled:opacity-50"
                                        >
                                            {isSaving ? <Loader2 className="w-4 h-4 animate-spin"/> :
                                                <Save className="w-4 h-4"/>}
                                            {t('diarization.detail.index_base')}
                                        </button>
                                    </div>

                                    <div className="flex-1 bg-black/40 border border-white/5 rounded-2xl overflow-hidden backdrop-blur-sm flex flex-col">
                                        <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
                                            <div className="space-y-3 pb-4">
                                                {finalSegments.map((seg, i) => {
                                                    const hash = seg.speakerName.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
                                                    const colorIdx = hash % 5;
                                                    const colors = [
                                                        'border-emerald-500/20 bg-emerald-500/5 text-emerald-400',
                                                        'border-blue-500/20 bg-blue-500/5 text-blue-400',
                                                        'border-purple-500/20 bg-purple-500/5 text-purple-400',
                                                        'border-amber-500/20 bg-amber-500/5 text-amber-400',
                                                        'border-rose-500/20 bg-rose-500/5 text-rose-400'
                                                    ];
                                                    const colorClass = colors[colorIdx];

                                                    return (
                                                        <motion.div
                                                            initial={{opacity: 0, x: -10}}
                                                            animate={{opacity: 1, x: 0}}
                                                            transition={{delay: Math.min(i * 0.03, 1)}}
                                                            key={seg.id}
                                                            className={`group flex flex-col gap-1 p-3 rounded-xl border transition-all hover:bg-white/5 ${colorClass.split(' ').slice(0, 2).join(' ')}`}
                                                        >
                                                            <div className="flex items-center justify-between">
                                                                <div className="flex items-center gap-2">
                                                                    <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${colorClass.split(' ').slice(0, 3).join(' ')}`}>
                                                                        {seg.speakerName.charAt(0).toUpperCase()}
                                                                    </div>
                                                                    <span className={`text-xs font-bold uppercase tracking-wider ${colorClass.split(' ').pop()}`}>
                                                                        {seg.speakerName}
                                                                    </span>
                                                                </div>
                                                                <div className="flex items-center gap-1 text-[10px] font-mono text-zinc-500 group-hover:text-zinc-400 transition-colors">
                                                                    <Clock className="w-3 h-3"/>
                                                                    <span>{seg.startTime}</span>
                                                                    <span className="opacity-30">→</span>
                                                                    <span>{seg.endTime}</span>
                                                                </div>
                                                            </div>
                                                            <p className="text-zinc-300 text-sm leading-relaxed pl-7 font-sans">
                                                                {seg.text}
                                                            </p>
                                                        </motion.div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </motion.div>
            )}

            {/* New Diarization Modal */}
            <AnimatePresence>
                {isModalOpen && (
                    <motion.div
                        initial={{opacity: 0}}
                        animate={{opacity: 1}}
                        exit={{opacity: 0}}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                    >
                        <motion.div
                            initial={{scale: 0.95, opacity: 0}}
                            animate={{scale: 1, opacity: 1}}
                            exit={{scale: 0.95, opacity: 0}}
                            className="bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden"
                        >
                            <div className="flex items-center justify-between p-6 border-b border-white/5">
                                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                    <Mic className="w-5 h-5 text-emerald-400"/>
                                    {t('diarization.modal.new_title')}
                                </h3>
                                <button
                                    onClick={() => setIsModalOpen(false)}
                                    className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                                >
                                    <X className="w-5 h-5"/>
                                </button>
                            </div>

                            <div className="p-6 space-y-6 overflow-y-auto max-h-[70vh] custom-scrollbar">
                                {/* Source Type Tabs */}
                                <div className="flex p-1 bg-black/40 rounded-xl border border-white/5">
                                    <button
                                        onClick={() => setUploadType('file')}
                                        className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold transition-all ${
                                            uploadType === 'file'
                                                ? 'bg-zinc-800 text-white shadow-sm'
                                                : 'text-zinc-500 hover:text-zinc-300'
                                        }`}
                                    >
                                        <Upload className="w-4 h-4"/>
                                        {t('diarization.modal.file_tab')}
                                    </button>
                                    <button
                                        onClick={() => setUploadType('youtube')}
                                        className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold transition-all ${
                                            uploadType === 'youtube'
                                                ? 'bg-zinc-800 text-white shadow-sm'
                                                : 'text-zinc-500 hover:text-zinc-300'
                                        }`}
                                    >
                                        <Youtube className="w-4 h-4"/>
                                        {t('diarization.modal.youtube_tab')}
                                    </button>
                                </div>

                                {/* Source Input */}
                                {uploadType === 'file' ? (
                                    <div
                                        onClick={() => fileInputRef.current?.click()}
                                        className="border-2 border-dashed border-white/10 hover:border-emerald-500/50 rounded-xl p-8 text-center cursor-pointer transition-colors bg-black/20 group"
                                    >
                                        <input
                                            type="file"
                                            ref={fileInputRef}
                                            onChange={handleFileChange}
                                            accept="audio/*,video/*"
                                            className="hidden"
                                        />
                                        <div
                                            className="w-12 h-12 rounded-full bg-zinc-800 group-hover:bg-emerald-500/20 flex items-center justify-center mx-auto mb-4 transition-colors">
                                            <Video className="w-6 h-6 text-zinc-400 group-hover:text-emerald-400"/>
                                        </div>
                                        <p className="text-zinc-300 font-medium mb-1 truncate px-2">
                                            {file ? file.name : t('diarization.modal.drag_drop')}
                                        </p>
                                        <p className="text-zinc-600 text-xs">
                                            {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : t('diarization.modal.supported_formats')}
                                        </p>
                                    </div>
                                ) : (
                                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                                        <label
                                            className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">{t('diarization.modal.video_url_label')}</label>
                                        <div
                                            className="flex items-center gap-3 bg-zinc-900/50 p-3 rounded-lg border border-white/5 focus-within:border-emerald-500/50 transition-colors">
                                            <LinkIcon className="w-5 h-5 text-zinc-400"/>
                                            <input
                                                type="text"
                                                value={youtubeLink}
                                                onChange={(e) => setYoutubeLink(e.target.value)}
                                                placeholder="https://youtube.com/watch?v=..."
                                                className="flex-1 bg-transparent border-none text-sm text-white focus:outline-none placeholder:text-zinc-600 font-medium"
                                            />
                                        </div>
                                    </div>
                                )}

                                {/* Options */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                                        <label
                                            className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">{t('diarization.modal.language_label')}</label>
                                        <select
                                            value={language}
                                            onChange={(e) => setLanguage(e.target.value)}
                                            className="w-full bg-zinc-900/50 border border-white/5 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-emerald-500/50 appearance-none cursor-pointer"
                                        >
                                            <option value="pt" className="bg-zinc-800">{t('diarization.modal.languages.pt')}</option>
                                            <option value="en" className="bg-zinc-800">{t('diarization.modal.languages.en')}</option>
                                            <option value="es" className="bg-zinc-800">{t('diarization.modal.languages.es')}</option>
                                        </select>
                                    </div>
                                    <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                                        <label
                                            className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">{t('diarization.modal.model_label')}</label>
                                        <select
                                            value={modelSize}
                                            onChange={(e) => setModelSize(e.target.value)}
                                            className="w-full bg-zinc-900/50 border border-white/5 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-emerald-500/50 appearance-none cursor-pointer"
                                        >
                                            <option value="base" className="bg-zinc-800">{t('diarization.modal.models.base')}</option>
                                            <option value="small" className="bg-zinc-800">{t('diarization.modal.models.small')}</option>
                                            <option value="medium" className="bg-zinc-800">{t('diarization.modal.models.medium')}</option>
                                            <option value="large-v2" className="bg-zinc-800">{t('diarization.modal.models.large')}</option>
                                        </select>
                                    </div>
                                </div>

                                {/* Context Selection */}
                                <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                                    <label
                                        className="block text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">{t('diarization.modal.target_context')}</label>
                                    {selectedSubjects.length > 0 ? (
                                        <div
                                            className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20 flex items-center gap-3">
                                            <Database className="w-5 h-5 text-emerald-400"/>
                                            <div className="min-w-0">
                                                <p className="text-sm font-bold text-emerald-400 truncate">{selectedSubjects[0].name}</p>
                                            </div>
                                        </div>
                                    ) : (
                                        <div
                                            className="p-3 rounded-lg bg-zinc-800/50 border border-white/5 flex items-center gap-3">
                                            <AlertCircle className="w-5 h-5 text-zinc-500 flex-shrink-0"/>
                                            <div>
                                                <p className="text-sm font-medium text-zinc-400">{t('diarization.modal.no_context')}</p>
                                                <p className="text-xs text-zinc-500">{t('diarization.modal.optional_context')}</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="p-6 border-t border-white/5 bg-black/20 flex justify-end gap-3">
                                <button
                                    onClick={() => setIsModalOpen(false)}
                                    className="px-4 py-2 rounded-xl text-sm font-bold text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                                >
                                    {t('common.actions.cancel')}
                                </button>
                                <button
                                    onClick={handleStartProcessing}
                                    disabled={isSubmitting || (uploadType === 'file' ? !file : !youtubeLink)}
                                    className="flex items-center gap-2 px-6 py-2 bg-emerald-500 text-black font-bold rounded-xl hover:bg-emerald-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                                >
                                    {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin"/> : null}
                                    {t('diarization.modal.start_btn')}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Voice Training Modal */}
            <AnimatePresence>
                {trainingSpeaker && (
                    <motion.div
                        initial={{opacity: 0}}
                        animate={{opacity: 1}}
                        exit={{opacity: 0}}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
                    >
                        <motion.div
                            initial={{scale: 0.95, opacity: 0}}
                            animate={{scale: 1, opacity: 1}}
                            exit={{scale: 0.95, opacity: 0}}
                            className="bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden"
                        >
                            <div className="flex items-center justify-between p-6 border-b border-white/5">
                                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                    <Mic className="w-5 h-5 text-emerald-400"/>
                                    {t('diarization.train_modal.title')}
                                </h3>
                                <button
                                    onClick={() => setTrainingSpeaker(null)}
                                    className="p-2 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white transition-colors"
                                >
                                    <X className="w-5 h-5"/>
                                </button>
                            </div>

                            <div className="p-6 space-y-6">
                                <div
                                    className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-start gap-3">
                                    <AlertCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5"/>
                                    <p className="text-sm text-emerald-100/80 leading-relaxed">
                                        {t('diarization.train_modal.desc')}
                                    </p>
                                </div>

                                <div className="space-y-2">
                                    <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                        {t('diarization.train_modal.profile_name_label')}
                                    </label>
                                    <div
                                        className="flex items-center gap-3 bg-black/40 p-3 rounded-xl border border-white/10 focus-within:border-emerald-500/50 transition-colors">
                                        <User className="w-5 h-5 text-zinc-400"/>
                                        <input
                                            type="text"
                                            value={voiceProfileName}
                                            onChange={(e) => setVoiceProfileName(e.target.value)}
                                            placeholder={t('diarization.train_modal.placeholder')}
                                            className="flex-1 bg-transparent border-none text-sm text-white focus:outline-none placeholder:text-zinc-600 font-medium"
                                            autoFocus
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="p-6 border-t border-white/5 bg-black/20 flex justify-end gap-3">
                                <button
                                    onClick={() => setTrainingSpeaker(null)}
                                    className="px-4 py-2 rounded-xl text-sm font-bold text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                                >
                                    {t('common.actions.cancel')}
                                </button>
                                <button
                                    onClick={handleTrainVoice}
                                    disabled={!voiceProfileName.trim() || isTraining}
                                    className="flex items-center gap-2 px-6 py-2 bg-emerald-500 text-black font-bold rounded-xl hover:bg-emerald-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(16,185,129,0.2)]"
                                >
                                    {isTraining ? <Loader2 className="w-4 h-4 animate-spin"/> :
                                        <Save className="w-4 h-4"/>}
                                    {t('diarization.train_modal.save_btn')}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
