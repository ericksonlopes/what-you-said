import React, {useEffect, useState, type SyntheticEvent} from 'react';
import {
    Plus,
    Settings2,
    X,
    SquarePlay,
    Zap,
    Globe,
    FileUp,
} from 'lucide-react';
import {useAppContext} from '../store/AppContext';
import { useTranslation } from 'react-i18next';
import { useIngestion } from '../hooks/useIngestion';
import { motion, AnimatePresence } from 'motion/react';

// Sub-components
import { StrategySelector } from './modals/add-content/StrategySelector';
import { SubjectSelector } from './modals/add-content/SubjectSelector';
import { YoutubeSourceForm } from './modals/add-content/YoutubeSourceForm';
import { WebSourceForm } from './modals/add-content/WebSourceForm';
import { FileSourceForm } from './modals/add-content/FileSourceForm';

interface AddContentModalProps {
    readonly isOpen: boolean;
    readonly onClose: () => void;
}

type ContentType = 'youtube' | 'wikipedia' | 'web' | 'notion' | 'pdf' | 'article' | 'docx' | 'pptx' | 'xlsx' | 'markdown' | 'html' | 'asciidoc' | 'latex' | 'csv' | 'image' | 'txt' | 'other' | 'audio';

interface SourceOption {
    id: ContentType;
    name: string;
    description: string;
    icon: React.ElementType;
    enabled: boolean;
}

export function AddContentModal({isOpen, onClose}: AddContentModalProps) {
    const { t } = useTranslation();
    const {subjects, selectedSubjects, selectOnlySubject, modelInfo, addToast, setCurrentView} = useAppContext();
    const {startIngestion} = useIngestion();
    
    const SOURCES: SourceOption[] = [
        {id: 'youtube', name: t('ingestion.sources.youtube'), description: t('ingestion.descriptions.youtube'), icon: SquarePlay, enabled: true},
        {id: 'pdf', name: t('ingestion.sources.file'), description: t('ingestion.descriptions.file'), icon: FileUp, enabled: true},
        {id: 'web', name: t('ingestion.sources.web'), description: t('ingestion.descriptions.web'), icon: Globe, enabled: true},
    ];

    const [contentType, setContentType] = useState<ContentType>('youtube');
    const [inputValue, setInputValue] = useState('');
    const [targetSubjectId, setTargetSubjectId] = useState<string | undefined>(selectedSubjects[0]?.id || subjects[0]?.id);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [subjectSearch, setSubjectSearch] = useState('');

    // File Upload / Ingestion State
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'chunking' | 'vectorizing' | 'done'>('idle');
    const [progress, setProgress] = useState(0);

    // Ingestion Parameters
    const [tokensPerChunk, setTokensPerChunk] = useState(512);
    const [tokensOverlap, setTokensOverlap] = useState(50);
    const [activeStrategy, setActiveStrategy] = useState<string>('balanced');
    const [activeTab, setActiveTab] = useState<'source' | 'settings'>('source');
    const [youtubeDataType, setYoutubeDataType] = useState<'video' | 'playlist' | 'channel'>('video');

    // Channel state
    interface ChannelVideo {
      video_id: string;
      title: string;
      url: string;
      duration: number | null;
      thumbnail: string | null;
      already_ingested: boolean;
    }
    const [channelVideos, setChannelVideos] = useState<ChannelVideo[]>([]);
    const [selectedVideoIds, setSelectedVideoIds] = useState<Set<string>>(new Set());
    const [fileInputMode, setFileInputMode] = useState<'upload' | 'url'>('upload');
    const [doOcr, setDoOcr] = useState(false);
    const [webDepth, setWebDepth] = useState(1);
    const [cssSelector, setCssSelector] = useState('');
    const [excludeLinks, setExcludeLinks] = useState(true);

    // Update target subject if selection changes and modal is opened
    useEffect(() => {
        if (isOpen) {
            if (selectedSubjects.length > 0) {
                setTargetSubjectId(selectedSubjects[0].id);
            }
        }
    }, [isOpen, selectedSubjects]);

    // Sync local targetSubjectId back to global selectedSubjects
    useEffect(() => {
        if (isOpen && targetSubjectId) {
            const subject = subjects.find(s => s.id === targetSubjectId);
            if (subject && (selectedSubjects.length !== 1 || selectedSubjects[0].id !== targetSubjectId)) {
                selectOnlySubject(subject);
            }
            // Clear channel preview when subject changes to avoid stale 'already ingested' status
            setChannelVideos([]);
            setSelectedVideoIds(new Set());
        }
    }, [targetSubjectId, isOpen, subjects, selectedSubjects, selectOnlySubject]);

    const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
        e.preventDefault();
        
        const targetSubject = subjects.find(s => s.id === targetSubjectId);
        if (!targetSubject) {
            addToast(t('ingestion.messages.error_subject'), 'error');
            return;
        }

        try {
            if (contentType === 'youtube') {
                if (youtubeDataType === 'channel') {
                    // Channel mode: send selected video URLs
                    const selectedUrls = channelVideos
                        .filter(v => selectedVideoIds.has(v.video_id))
                        .map(v => v.url);
                    if (selectedUrls.length === 0) {
                        addToast(t('ingestion.channel.no_selection'), 'error');
                        return;
                    }
                    startIngestion('youtube', {
                        videoUrls: selectedUrls,
                        subject: targetSubject,
                        tokensPerChunk,
                        tokensOverlap,
                        youtubeDataType: 'video', // Send as individual videos
                    });
                } else {
                    startIngestion('youtube', {
                        url: inputValue,
                        subject: targetSubject,
                        tokensPerChunk,
                        tokensOverlap,
                        youtubeDataType
                    });
                }
            } else if (contentType === 'web') {
                setUploadStatus('chunking');
                setProgress(30);
                await startIngestion('web', {
                    url: inputValue,
                    subject: targetSubject,
                    tokensPerChunk,
                    tokensOverlap,
                    cssSelector,
                    excludeLinks
                });
            } else if (contentType === 'pdf' && fileInputMode === 'url' && inputValue.trim()) {
                setUploadStatus('chunking');
                setProgress(30);
                await startIngestion('file_url', {
                    url: inputValue,
                    subject: targetSubject,
                    tokensPerChunk,
                    tokensOverlap,
                    doOcr
                });
            } else if (selectedFile) {
                setUploadStatus('chunking');
                setProgress(30);
                await startIngestion('file', {
                    file: selectedFile,
                    subject: targetSubject,
                    tokensPerChunk,
                    tokensOverlap,
                    doOcr
                });
            }

            setCurrentView('activity');
            onClose();
            
            // Reset local state
            setInputValue('');
            setCssSelector('');
            setSelectedFile(null);
            setUploadStatus('idle');
            setProgress(0);
            setChannelVideos([]);
            setSelectedVideoIds(new Set());
        } catch (err) {
            console.error('Ingestion failed:', err);
            setUploadStatus('idle');
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setSelectedFile(e.target.files[0]);
        }
    };

    const selectedSource = SOURCES.find(s => s.id === contentType);

    const isSubmitDisabled = !selectedSource?.enabled || 
        !targetSubjectId ||
        (contentType === 'youtube' && youtubeDataType !== 'channel' && !inputValue.trim()) || 
        (contentType === 'youtube' && youtubeDataType === 'channel' && selectedVideoIds.size === 0) ||
        (contentType === 'web' && !inputValue.trim()) ||
        (contentType === 'pdf' && fileInputMode === 'upload' && !selectedFile) || 
        (contentType === 'pdf' && fileInputMode === 'url' && !inputValue.trim()) ||
        (contentType !== 'youtube' && contentType !== 'pdf' && contentType !== 'web' && !selectedFile) ||
        uploadStatus !== 'idle';

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        transition={{ duration: 0.2 }}
                        className="w-full max-w-4xl h-[680px] max-h-[90vh] bg-[#18181b] border border-border-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col relative z-10"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-5 border-b border-border-subtle bg-black/20">
                            <div>
                                <h2 className="text-lg font-semibold text-zinc-100">{t('ingestion.title')}</h2>
                                <SubjectSelector 
                                    subjects={subjects}
                                    targetSubjectId={targetSubjectId}
                                    setTargetSubjectId={setTargetSubjectId}
                                    isDropdownOpen={isDropdownOpen}
                                    setIsDropdownOpen={setIsDropdownOpen}
                                    subjectSearch={subjectSearch}
                                    setSubjectSearch={setSubjectSearch}
                                />
                            </div>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-panel-hover transition-colors"
                            >
                                <X className="w-5 h-5"/>
                            </button>
                        </div>

                        <div className="flex flex-col md:flex-row flex-1 min-h-0">
                            {/* Left Sidebar: Source Selection */}
                            <div className="w-full md:w-[280px] border-b md:border-b-0 md:border-r border-border-subtle bg-black/20 p-3.5 flex flex-col gap-1.5 overflow-y-auto">
                                <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.1em] mb-2 px-1.5">{t('sidebar.operations.sources')}</h3>
                                {SOURCES.map((source) => {
                                    const Icon = source.icon;
                                    const isSelected = contentType === source.id;

                                    return (
                                        <button
                                            key={source.id}
                                            onClick={() => setContentType(source.id)}
                                            className={`group flex items-center gap-3 p-2.5 rounded-xl text-left transition-all ${
                                                isSelected
                                                    ? 'bg-zinc-800 border-zinc-700 shadow-sm'
                                                    : 'hover:bg-panel-hover border border-transparent'
                                            } ${!source.enabled && !isSelected ? 'opacity-60' : ''}`}
                                        >
                                            <div className={`p-2 rounded-lg transition-colors flex-shrink-0 ${isSelected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-zinc-800 text-zinc-400 group-hover:text-zinc-200'}`}>
                                                <Icon className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isSelected ? 'scale-110' : ''}`}/>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className={`text-[13px] font-semibold truncate ${isSelected ? 'text-zinc-100' : 'text-zinc-400 group-hover:text-zinc-300'}`}>
                                                        {source.name}
                                                    </span>
                                                </div>
                                                <span className="text-[10px] text-zinc-500 block truncate font-medium">
                                                    {source.description}
                                                </span>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Right Content Area */}
                            <div className="flex-1 flex flex-col bg-[#121212] relative">
                                <form onSubmit={handleSubmit} className="flex flex-col h-full overflow-hidden">
                                    {/* Tabs */}
                                    <div className="flex border-b border-zinc-800/50">
                                        <button
                                            type="button"
                                            onClick={() => setActiveTab('source')}
                                            className={`flex-1 flex items-center justify-center gap-2 py-3 text-xs font-semibold tracking-wide uppercase transition-all border-b-2 ${
                                                activeTab === 'source' ? 'text-emerald-400 border-emerald-500 bg-emerald-500/5' : 'text-zinc-500 border-transparent hover:text-zinc-300 hover:bg-white/[0.02]'
                                            }`}
                                        >
                                            <Zap className="w-3.5 h-3.5"/>
                                            {t('search.results.source')}
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setActiveTab('settings')}
                                            className={`flex-1 flex items-center justify-center gap-2 py-3 text-xs font-semibold tracking-wide uppercase transition-all border-b-2 ${
                                                activeTab === 'settings' ? 'text-emerald-400 border-emerald-500 bg-emerald-500/5' : 'text-zinc-500 border-transparent hover:text-zinc-300 hover:bg-white/[0.02]'
                                            }`}
                                        >
                                            <Settings2 className="w-3.5 h-3.5"/>
                                            {t('settings.tabs.processing')}
                                        </button>
                                    </div>

                                    {/* Content area */}
                                    <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">
                                        <div className="min-h-full">
                                            {activeTab === 'source' ? (
                                                selectedSource?.enabled && (
                                                    <>
                                                        {contentType === 'youtube' && (
                                                            <YoutubeSourceForm 
                                                                youtubeDataType={youtubeDataType}
                                                                setYoutubeDataType={setYoutubeDataType}
                                                                inputValue={inputValue}
                                                                setInputValue={setInputValue}
                                                                targetSubjectId={targetSubjectId}
                                                                channelVideos={channelVideos}
                                                                setChannelVideos={setChannelVideos}
                                                                selectedVideoIds={selectedVideoIds}
                                                                setSelectedVideoIds={setSelectedVideoIds}
                                                            />
                                                        )}
                                                        {contentType === 'web' && (
                                                            <WebSourceForm 
                                                                inputValue={inputValue}
                                                                setInputValue={setInputValue}
                                                                webDepth={webDepth}
                                                                setWebDepth={setWebDepth}
                                                                cssSelector={cssSelector}
                                                                setCssSelector={setCssSelector}
                                                                excludeLinks={excludeLinks}
                                                                setExcludeLinks={setExcludeLinks}
                                                            />
                                                        )}
                                                        {contentType === 'pdf' && (
                                                            <FileSourceForm 
                                                                fileInputMode={fileInputMode}
                                                                setFileInputMode={setFileInputMode}
                                                                doOcr={doOcr}
                                                                setDoOcr={setDoOcr}
                                                                inputValue={inputValue}
                                                                setInputValue={setInputValue}
                                                                selectedFile={selectedFile}
                                                                setSelectedFile={setSelectedFile}
                                                                isDragging={isDragging}
                                                                handleDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                                                                handleDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
                                                                handleDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.[0]) setSelectedFile(e.dataTransfer.files[0]); }}
                                                                handleFileChange={handleFileChange}
                                                                uploadStatus={uploadStatus}
                                                                progress={progress}
                                                            />
                                                        )}
                                                    </>
                                                )
                                            ) : (
                                                <StrategySelector 
                                                    tokensPerChunk={tokensPerChunk}
                                                    setTokensPerChunk={setTokensPerChunk}
                                                    tokensOverlap={tokensOverlap}
                                                    setTokensOverlap={setTokensOverlap}
                                                    activeStrategy={activeStrategy}
                                                    setActiveStrategy={setActiveStrategy}
                                                    modelInfo={modelInfo}
                                                />
                                            )}
                                        </div>
                                    </div>

                                    {/* Footer */}
                                    <div className="p-5 border-t border-zinc-800/50 bg-black/20 flex flex-col gap-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex flex-col">
                                                <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest leading-none mb-1">
                                                    {t('common.actions.addData')}
                                                </span>
                                                <span className="text-zinc-200 font-bold text-sm">
                                                    {selectedSource?.name}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <button
                                                    type="button"
                                                    onClick={onClose}
                                                    className="px-5 py-2 text-sm font-bold text-zinc-400 hover:text-zinc-200 transition-colors uppercase tracking-wider"
                                                >
                                                    {t('common.actions.cancel')}
                                                </button>
                                                <button
                                                    type="submit"
                                                    disabled={isSubmitDisabled}
                                                    className="group flex items-center gap-3 px-8 py-3 text-sm font-black text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none uppercase tracking-widest whitespace-nowrap"
                                                >
                                                    {uploadStatus === 'idle' ? (
                                                        <>
                                                            <Plus className="w-4 h-4 transition-transform duration-300 group-hover:rotate-90" />
                                                            {t('common.actions.save')}
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Settings2 className="w-4 h-4 animate-spin" />
                                                            {t('common.actions.syncing')}
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                </form>
                            </div>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    );
}
