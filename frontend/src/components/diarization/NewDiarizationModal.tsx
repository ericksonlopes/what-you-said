import React, { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Video, Upload, Plus, Loader2, ListVideo, Radio, PlaySquare } from 'lucide-react';
import { motion, AnimatePresence, LayoutGroup } from 'motion/react';
import { api } from '../../services/api';
import { useAppContext } from '../../store/AppContext';

interface NewDiarizationModalProps {
    isOpen: boolean;
    onClose: () => void;
    onStart: () => void;
}

export const NewDiarizationModal: React.FC<NewDiarizationModalProps> = ({ isOpen, onClose, onStart }) => {
    const { t } = useTranslation();
    const { addToast, selectedSubjects } = useAppContext();
    const [uploadType, setUploadType] = useState<'file' | 'youtube'>('file');
    const [youtubeMode, setYoutubeMode] = useState<'video' | 'playlist' | 'channel'>('video');
    const [youtubeLink, setYoutubeLink] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isPreviewLoading, setIsPreviewLoading] = useState(false);
    const [previewVideos, setPreviewVideos] = useState<any[]>([]);
    const [selectedUrls, setSelectedUrls] = useState<Set<string>>(new Set());
    const [showPreview, setShowPreview] = useState(false);
    const [language, setLanguage] = useState('pt');
    const [modelSize, setModelSize] = useState('base');

    const getYoutubeLabel = () => {
        if (youtubeMode === 'video') return 'URL do YouTube';
        if (youtubeMode === 'playlist') return 'URL da Playlist';
        return 'URL do Canal';
    };

    const getYoutubePlaceholder = () => {
        if (youtubeMode === 'video') return "https://www.youtube.com/watch?v=...";
        if (youtubeMode === 'playlist') return "https://www.youtube.com/playlist?list=...";
        return "https://www.youtube.com/@Canal ou URL do Canal";
    };

    const youtubeLabel = getYoutubeLabel();
    const youtubePlaceholder = getYoutubePlaceholder();

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
        
        // Capturamos os dados necessários antes de fechar/limpar para evitar perda de referência
        const subjectId = selectedSubjects[0]?.id;
        const urlsToProcess = uploadType === 'youtube' 
            ? (youtubeMode === 'channel' && showPreview ? Array.from(selectedUrls) : [youtubeLink])
            : [];
        const currentFile = file;
        const currentLang = language;
        const currentModel = modelSize;
        const currentUploadType = uploadType;

        // Fecha o modal e notifica imediatamente para feedback instantâneo
        onClose();
        addToast(t('diarization.notifications.start_success'), 'success');

        try {
            if (currentUploadType === 'youtube') {
                if (urlsToProcess.length === 0) {
                    setIsSubmitting(false);
                    return;
                }

                await Promise.all(urlsToProcess.map(url => 
                    api.startAudioProcessing({
                        source_type: 'youtube',
                        source: url,
                        language: currentLang,
                        model_size: currentModel,
                        recognize_voices: true,
                        subject_id: subjectId
                    })
                ));
            } else {
                const formData = new FormData();
                formData.append('file', currentFile!);
                if (subjectId) {
                    formData.append('subject_id', subjectId);
                }
                const uploadResult = await api.ingestFile(formData);
                const s3Path = uploadResult?.s3_path || uploadResult?.file_path || '';

                await api.startAudioProcessing({
                    source_type: 'upload',
                    source: s3Path,
                    language: currentLang,
                    model_size: currentModel,
                    recognize_voices: true,
                    subject_id: subjectId
                });
            }

            // Notifica o componente pai para atualizar a lista
            onStart();
            
            // Limpa o estado local
            setFile(null);
            setYoutubeLink('');
            setShowPreview(false);
            setPreviewVideos([]);
            setSelectedUrls(new Set());
        } catch (err) {
            console.error('Failed to start processing:', err);
            addToast(t('diarization.notifications.start_error'), 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
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
                        className="relative w-full max-w-lg bg-zinc-900 border border-white/10 rounded-3xl overflow-hidden shadow-2xl"
                    >
                        <div className="p-6 border-b border-white/5 flex items-center justify-between">
                            <h3 className="text-xl font-black text-white uppercase tracking-tight">{t('diarization.modal.new_title')}</h3>
                            <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-xl transition-colors">
                                <X className="w-5 h-5 text-zinc-500" />
                            </button>
                        </div>
                        
                        <div className="p-6 space-y-6">
                            <div className="flex p-1 bg-black/40 rounded-2xl border border-white/5">
                                <button
                                    onClick={() => setUploadType('file')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${uploadType === 'file' ? 'bg-zinc-800 text-white shadow-xl' : 'text-zinc-500 hover:text-zinc-300'}`}
                                >
                                    <Upload className="w-4 h-4" />
                                    {t('diarization.modal.file_tab')}
                                </button>
                                <button
                                    onClick={() => setUploadType('youtube')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${uploadType === 'youtube' ? 'bg-zinc-800 text-white shadow-xl' : 'text-zinc-500 hover:text-zinc-300'}`}
                                >
                                    <Video className="w-4 h-4" />
                                    YouTube
                                </button>
                            </div>

                            {uploadType === 'youtube' ? (
                                <div className="space-y-4">
                                    <div className="flex p-1.5 bg-black/40 rounded-2xl border border-white/5 relative">
                                        <LayoutGroup id="youtube-modes">
                                            {[
                                                { id: 'video', label: 'Vídeo', icon: PlaySquare },
                                                { id: 'playlist', label: 'Playlist', icon: ListVideo },
                                                { id: 'channel', label: 'Canal', icon: Radio },
                                            ].map((mode) => (
                                                <button
                                                    key={mode.id}
                                                    onClick={() => setYoutubeMode(mode.id as any)}
                                                    className={`flex-1 relative flex items-center justify-center gap-2 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all z-10 ${youtubeMode === mode.id ? 'text-emerald-400' : 'text-zinc-500 hover:text-zinc-300'}`}
                                                >
                                                    {youtubeMode === mode.id && (
                                                        <motion.div
                                                            layoutId="active-youtube-mode"
                                                            className="absolute inset-0 bg-white/5 border border-white/5 rounded-xl shadow-inner"
                                                            transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                                        />
                                                    )}
                                                    <mode.icon className={`w-3.5 h-3.5 ${youtubeMode === mode.id ? 'text-emerald-400' : 'text-zinc-500'}`} />
                                                    {mode.label}
                                                </button>
                                            ))}
                                        </LayoutGroup>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">
                                            {youtubeLabel}
                                        </label>
                                        <input
                                            type="text"
                                            value={youtubeLink}
                                            onChange={(e) => {
                                                setYoutubeLink(e.target.value);
                                                setShowPreview(false);
                                            }}
                                            placeholder={youtubePlaceholder}
                                            className="w-full px-4 py-4 bg-black/40 border border-white/5 rounded-xl text-sm text-white placeholder:text-zinc-700 focus:outline-none focus:border-emerald-500/30 transition-all font-medium"
                                        />
                                    </div>

                                    {youtubeMode === 'channel' && youtubeLink && !showPreview && (
                                        <button
                                            type="button"
                                            onClick={async () => {
                                                setIsPreviewLoading(true);
                                                try {
                                                    const result = await api.previewYoutubeChannel({ 
                                                        channel_url: youtubeLink,
                                                        subject_id: selectedSubjects[0]?.id
                                                    });
                                                    setPreviewVideos(result.videos);
                                                    setSelectedUrls(new Set(result.videos.map(v => v.url)));
                                                    setShowPreview(true);
                                                } catch (err) {
                                                    addToast(t('common.errors.general'), 'error');
                                                } finally {
                                                    setIsPreviewLoading(false);
                                                }
                                            }}
                                            disabled={isPreviewLoading}
                                            className="w-full py-3 bg-zinc-800 hover:bg-zinc-700 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all flex items-center justify-center gap-2"
                                        >
                                            {isPreviewLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ListVideo className="w-4 h-4" />}
                                            {t('diarization.modal.fetchChannelVideos')}
                                        </button>
                                    )}

                                    <AnimatePresence>
                                        {showPreview && previewVideos.length > 0 && (
                                            <motion.div
                                                initial={{ opacity: 0, height: 0 }}
                                                animate={{ opacity: 1, height: 'auto' }}
                                                exit={{ opacity: 0, height: 0 }}
                                                className="space-y-3"
                                            >
                                                <div className="flex items-center justify-between px-1">
                                                    <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">
                                                        {t('diarization.modal.selectVideos')} ({selectedUrls.size}/{previewVideos.length})
                                                    </span>
                                                    <div className="flex gap-2">
                                                        <button 
                                                            type="button"
                                                            onClick={() => setSelectedUrls(new Set(previewVideos.map(v => v.url)))}
                                                            className="text-[9px] font-bold text-emerald-500 hover:text-emerald-400 uppercase tracking-tight"
                                                        >
                                                            {t('common.actions.selectAll')}
                                                        </button>
                                                        <span className="text-zinc-700">|</span>
                                                        <button 
                                                            type="button"
                                                            onClick={() => setSelectedUrls(new Set())}
                                                            className="text-[9px] font-bold text-zinc-500 hover:text-zinc-400 uppercase tracking-tight"
                                                        >
                                                            {t('common.actions.deselectAll')}
                                                        </button>
                                                    </div>
                                                </div>

                                                <div className="max-h-48 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
                                                    {previewVideos.map((video) => (
                                                        <div 
                                                            key={video.video_id}
                                                            role="checkbox"
                                                            aria-checked={selectedUrls.has(video.url)}
                                                            tabIndex={0}
                                                            onClick={() => {
                                                                const newSelected = new Set(selectedUrls);
                                                                if (newSelected.has(video.url)) newSelected.delete(video.url);
                                                                else newSelected.add(video.url);
                                                                setSelectedUrls(newSelected);
                                                            }}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter' || e.key === ' ') {
                                                                    e.preventDefault();
                                                                    const newSelected = new Set(selectedUrls);
                                                                    if (newSelected.has(video.url)) newSelected.delete(video.url);
                                                                    else newSelected.add(video.url);
                                                                    setSelectedUrls(newSelected);
                                                                }
                                                            }}
                                                            className={`group flex items-center gap-3 p-2 rounded-xl border transition-all cursor-pointer ${selectedUrls.has(video.url) ? 'bg-emerald-500/10 border-emerald-500/20' : 'bg-black/20 border-white/5 hover:border-white/10'}`}
                                                        >
                                                            <div className="relative w-16 h-9 rounded-lg overflow-hidden bg-zinc-800 flex-shrink-0">
                                                                {video.thumbnail ? (
                                                                    <img src={video.thumbnail} alt="" className="w-full h-full object-cover" />
                                                                ) : (
                                                                    <Video className="w-4 h-4 text-zinc-600 m-auto mt-2.5" />
                                                                )}
                                                            </div>
                                                            <div className="flex-1 min-w-0">
                                                                <p className="text-[11px] font-bold text-white truncate group-hover:text-emerald-400 transition-colors">
                                                                    {video.title}
                                                                </p>
                                                            </div>
                                                            <div className={`w-4 h-4 rounded border flex items-center justify-center transition-all ${selectedUrls.has(video.url) ? 'bg-emerald-500 border-emerald-500' : 'border-white/20'}`}>
                                                                {selectedUrls.has(video.url) && <X className="w-3 h-3 text-black stroke-[4px]" />}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">{t('diarization.modal.supported_formats')}</label>
                                    <div 
                                        onClick={() => fileInputRef.current?.click()}
                                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
                                        role="button"
                                        tabIndex={0}
                                        className="w-full h-32 border-2 border-dashed border-white/5 rounded-2xl flex flex-col items-center justify-center gap-3 cursor-pointer hover:bg-white/5 hover:border-emerald-500/20 transition-all group focus:outline-none focus:border-emerald-500/30"
                                    >
                                        <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept="audio/*,video/*" />
                                        <div className="p-3 rounded-xl bg-zinc-800 text-zinc-400 group-hover:bg-emerald-500 group-hover:text-black transition-all">
                                            <Upload className="w-5 h-5" />
                                        </div>
                                        <span className="text-xs font-bold text-zinc-500 group-hover:text-zinc-300">
                                            {file ? file.name : t('diarization.modal.drag_drop')}
                                        </span>
                                    </div>
                                </div>
                            )}

                            {selectedSubjects.length === 0 && (
                                <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl flex items-start gap-3">
                                    <X className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                                    <div className="space-y-1">
                                        <p className="text-[10px] font-black text-rose-500 uppercase tracking-widest">{t('diarization.modal.no_context')}</p>
                                        <p className="text-[10px] text-rose-400/70 font-medium leading-relaxed">{t('common.hints.select_subject')}</p>
                                    </div>
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">{t('diarization.modal.language_label')}</label>
                                    <select
                                        value={language}
                                        onChange={(e) => setLanguage(e.target.value)}
                                        className="w-full px-4 py-3 bg-black/40 border border-white/5 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500/30 transition-all appearance-none"
                                    >
                                        <option value="pt">Português</option>
                                        <option value="en">English</option>
                                        <option value="es">Español</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest ml-1">{t('diarization.modal.model_label')}</label>
                                    <select
                                        value={modelSize}
                                        onChange={(e) => setModelSize(e.target.value)}
                                        className="w-full px-4 py-3 bg-black/40 border border-white/5 rounded-xl text-sm text-white focus:outline-none focus:border-emerald-500/30 transition-all appearance-none"
                                    >
                                        <option value="base">{t('diarization.modal.models.base')}</option>
                                        <option value="small">{t('diarization.modal.models.small')}</option>
                                        <option value="medium">{t('diarization.modal.models.medium')}</option>
                                        <option value="large-v2">{t('diarization.modal.models.large')}</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div className="p-6 bg-black/20 border-t border-white/5 flex gap-3">
                            <button
                                onClick={onClose}
                                className="flex-1 py-3 px-4 rounded-xl text-[10px] font-black uppercase tracking-widest border border-white/10 text-zinc-400 hover:bg-white/5 transition-all"
                            >
                                {t('common.actions.cancel')}
                            </button>
                            <button
                                onClick={handleStartProcessing}
                                disabled={isSubmitting || selectedSubjects.length === 0}
                                className="flex-1 py-3 px-4 bg-emerald-500 text-black font-black uppercase text-[10px] tracking-widest rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                title={selectedSubjects.length === 0 ? t('common.hints.select_subject') : ''}
                            >
                                {isSubmitting ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Plus className="w-4 h-4 stroke-[3px]" />
                                )}
                                {t('diarization.modal.start_btn')}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
};
