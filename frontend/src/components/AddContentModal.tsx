import React, {useEffect, useState} from 'react';
import {
    Activity,
    ArrowRight,
    BookOpen,
    Check,
    ChevronDown,
    Database,
    FileText,
    FileUp,
    Globe,
    Layers,
    ListVideo,
    Lock,
    Scissors,
    Search,
    Settings2,
    UploadCloud,
    X,
    Youtube,
    Zap
} from 'lucide-react';
import {useAppContext} from '../store/AppContext';
import { useTranslation } from 'react-i18next';
import {useIngestion} from '../hooks/useIngestion';

interface AddContentModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type ContentType = 'youtube' | 'wikipedia' | 'web' | 'notion' | 'file';

interface SourceOption {
    id: ContentType;
    name: string;
    description: string;
    icon: React.ElementType;
    enabled: boolean;
}

interface Strategy {
    id: string;
    name: string;
    description: string;
    tokens: number;
    overlap: number;
    icon: React.ElementType;
}

interface ProcessingStrategyProps {
    tokensPerChunk: number;
    setTokensPerChunk: (val: number) => void;
    tokensOverlap: number;
    setTokensOverlap: (val: number) => void;
    activeStrategy: string;
    setActiveStrategy: (val: string) => void;
    modelInfo: { name: string; dimensions: number; max_seq_length: number } | null;
}

function ProcessingStrategy({
                                tokensPerChunk,
                                setTokensPerChunk,
                                tokensOverlap,
                                setTokensOverlap,
                                activeStrategy,
                                setActiveStrategy,
                                modelInfo
                            }: ProcessingStrategyProps) {
    const { t } = useTranslation();
    
    const STRATEGIES: Strategy[] = [
        { id: 'balanced', name: t('ingestion.options.strategies.balanced.name'), description: t('ingestion.options.strategies.balanced.description'), tokens: 512, overlap: 50, icon: Zap },
        { id: 'granular', name: t('ingestion.options.strategies.granular.name'), description: t('ingestion.options.strategies.granular.description'), tokens: 300, overlap: 30, icon: Scissors },
        { id: 'context', name: t('ingestion.options.strategies.context.name'), description: t('ingestion.options.strategies.context.description'), tokens: 800, overlap: 100, icon: Layers },
    ];

    return (
        <div className="space-y-5">
            <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                    <Settings2 className="w-3.5 h-3.5 text-emerald-400"/>
                    <h4 className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">{t('ingestion.options.strategy')}</h4>
                </div>
                <span
                    className="text-[9px] bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded-full font-medium border border-emerald-500/20">
          {t('ingestion.options.optimized')}
        </span>
            </div>

            <div className="grid grid-cols-3 gap-3">
                {STRATEGIES.map((strategy) => {
                    const Icon = strategy.icon;
                    const isSelected = activeStrategy === strategy.id;
                    return (
                        <button
                            key={strategy.id}
                            type="button"
                            onClick={() => {
                                setActiveStrategy(strategy.id);
                                setTokensPerChunk(strategy.tokens);
                                setTokensOverlap(strategy.overlap);
                            }}
                            className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition-all duration-300 ${
                                isSelected
                                    ? 'bg-emerald-500/5 border-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.05)]'
                                    : 'bg-black/20 border-zinc-800 hover:border-zinc-700'
                            }`}
                        >
                            <div
                                className={`p-1.5 rounded-lg ${isSelected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-800/50 text-zinc-500'}`}>
                                <Icon className="w-3.5 h-3.5"/>
                            </div>
                            <div className="text-center">
                                <div
                                    className={`text-[10px] font-bold ${isSelected ? 'text-zinc-100' : 'text-zinc-400'}`}>{strategy.name}</div>
                                <div
                                    className="text-[8px] text-zinc-500 font-medium truncate w-full max-w-[80px] mt-0.5">{strategy.description}</div>
                            </div>
                        </button>
                    );
                })}
            </div>

            <div className="space-y-4 bg-black/40 rounded-xl p-4 border border-zinc-800/50">
                {/* Chunk Size Slider */}
                <div className="space-y-3">
                    <div className="flex justify-between items-end">
                        <div className="space-y-1">
                            <label className="text-[11px] font-bold text-zinc-300 flex items-center gap-1.5">
                                <Scissors className="w-3 h-3 text-emerald-500"/>
                                {t('ingestion.options.max_tokens')}
                                {modelInfo?.max_seq_length && (
                                    <span
                                        className="text-[9px] px-1.5 py-0.5 bg-zinc-800 text-zinc-500 rounded border border-zinc-700/50 ml-auto font-mono">
                    {t('ingestion.options.model_limit')}: {modelInfo.max_seq_length}
                  </span>
                                )}
                            </label>
                            <p className="text-[10px] text-zinc-500 leading-tight">{t('ingestion.options.tokens_fragment')}</p>
                        </div>
                        <div className="flex items-baseline gap-1">
                            <span
                                className="text-base font-mono font-bold text-emerald-400 leading-none">{tokensPerChunk}</span>
                            <span
                                className="text-[9px] text-zinc-600 font-bold uppercase tracking-tighter">{t('ingestion.options.tokens_label')}</span>
                        </div>
                    </div>
                    <input
                        type="range"
                        min="64"
                        max={modelInfo?.max_seq_length || 2000}
                        step={tokensPerChunk > 1000 ? 100 : 50}
                        value={tokensPerChunk}
                        onChange={(e) => {
                            setTokensPerChunk(parseInt(e.target.value));
                            setActiveStrategy('custom');
                        }}
                        className="w-full h-1 bg-zinc-800 rounded-full appearance-none cursor-pointer accent-emerald-500 hover:accent-emerald-400 transition-all"
                    />
                </div>

                {/* Overlap Slider */}
                <div className="space-y-3">
                    <div className="flex justify-between items-end">
                        <div className="space-y-1">
                            <label className="text-[11px] font-bold text-zinc-300 flex items-center gap-1.5">
                                <Layers className="w-3 h-3 text-emerald-500"/>
                                {t('ingestion.options.context_overlap')}
                            </label>
                            <p className="text-[10px] text-zinc-500 leading-tight">{t('ingestion.options.shared_context')}</p>
                        </div>
                        <div className="flex items-baseline gap-1">
                            <span
                                className="text-base font-mono font-bold text-emerald-400 leading-none">{tokensOverlap}</span>
                            <span
                                className="text-[9px] text-zinc-600 font-bold uppercase tracking-tighter">{t('ingestion.options.tokens_label')}</span>
                        </div>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="300"
                        step="10"
                        value={tokensOverlap}
                        onChange={(e) => {
                            setTokensOverlap(parseInt(e.target.value));
                            setActiveStrategy('custom');
                        }}
                        className="w-full h-1 bg-zinc-800 rounded-full appearance-none cursor-pointer accent-emerald-500 hover:accent-emerald-400 transition-all"
                    />
                </div>
            </div>

            <div
                className="flex items-center gap-3 px-3 py-2 bg-emerald-500/5 rounded-lg border border-emerald-500/10 transition-colors duration-500">
                <Activity className="w-3.5 h-3.5 text-emerald-500/50 flex-shrink-0 animate-pulse"/>
                <div className="flex-1">
                    <p className="text-[9px] text-zinc-500 italic leading-tight">
                        {t('ingestion.options.optimized')} for <span
                        className="text-emerald-500/80 font-bold">{activeStrategy === 'custom' ? t('ingestion.options.strategies.custom.name') : activeStrategy}</span> retrieval.
                        <span className="block mt-0.5 opacity-60">
               {activeStrategy === 'balanced' && t('ingestion.options.strategies.balanced.long_description')}
                            {activeStrategy === 'granular' && t('ingestion.options.strategies.granular.long_description')}
                            {activeStrategy === 'context' && t('ingestion.options.strategies.context.long_description')}
                            {activeStrategy === 'custom' && t('ingestion.options.strategies.custom.long_description')}
             </span>
                    </p>
                </div>
            </div>
        </div>
    );
}

export function AddContentModal({isOpen, onClose}: AddContentModalProps) {
    const { t } = useTranslation();
    const {subjects, selectedSubjects, modelInfo} = useAppContext();
    const {startIngestion} = useIngestion();
    
    const SOURCES: SourceOption[] = [
        {id: 'youtube', name: 'YouTube', description: 'Video & Audio', icon: Youtube, enabled: true},
        {id: 'wikipedia', name: 'Wikipedia', description: t('ingestion.sources.wikipedia'), icon: BookOpen, enabled: false},
        {id: 'web', name: 'Web Article', description: t('ingestion.sources.web'), icon: Globe, enabled: false},
        {id: 'notion', name: 'Notion', description: 'Workspace Sync', icon: Database, enabled: false},
        {id: 'file', name: 'Local Files', description: 'PDF, TXT, CSV', icon: FileUp, enabled: true},
    ];

    const [contentType, setContentType] = useState<ContentType>('youtube');
    const [inputValue, setInputValue] = useState('');
    const [targetSubjectId, setTargetSubjectId] = useState(selectedSubjects[0]?.id || subjects[0]?.id);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const [subjectSearch, setSubjectSearch] = useState('');

    // File Upload State
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'chunking' | 'vectorizing' | 'done'>('idle');
    const [progress, setProgress] = useState(0);

    // Ingestion Parameters
    const [tokensPerChunk, setTokensPerChunk] = useState(512);
    const [tokensOverlap, setTokensOverlap] = useState(50);
    const [activeStrategy, setActiveStrategy] = useState<string>('balanced');
    const [activeTab, setActiveTab] = useState<'source' | 'settings'>('source');
    const [youtubeDataType, setYoutubeDataType] = useState<'video' | 'playlist'>('video');

    const strategyProps = {
        tokensPerChunk,
        setTokensPerChunk,
        tokensOverlap,
        setTokensOverlap,
        activeStrategy,
        setActiveStrategy,
        modelInfo
    };

    // Update target subject if selection changes and modal is opened
    useEffect(() => {
        if (isOpen) {
            if (selectedSubjects.length > 0) {
                setTargetSubjectId(selectedSubjects[0].id);
            }
        }
    }, [isOpen, selectedSubjects]);

    if (!isOpen) return null;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (contentType !== 'youtube' && contentType !== 'file') return;

        const targetSubject = subjects.find(s => s.id === targetSubjectId);
        if (!targetSubject) return;

        if (contentType === 'youtube') {
            startIngestion(inputValue, contentType, targetSubject, tokensPerChunk, tokensOverlap, youtubeDataType);
            setInputValue('');
            onClose();
        } else if (contentType === 'file' && selectedFile) {
            // Simulate file processing
            setUploadStatus('chunking');
            setProgress(0);

            const interval = setInterval(() => {
                setProgress(p => {
                    if (p >= 100) {
                        clearInterval(interval);
                        return 100;
                    }
                    if (p === 40) setUploadStatus('vectorizing');
                    if (p === 90) setUploadStatus('done');
                    return p + 10;
                });
            }, 300);

            setTimeout(() => {
                clearInterval(interval);
                startIngestion(selectedFile.name, contentType, targetSubject, tokensPerChunk, tokensOverlap);
                setSelectedFile(null);
                setUploadStatus('idle');
                setProgress(0);
                onClose();
            }, 3500);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            setSelectedFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setSelectedFile(e.target.files[0]);
        }
    };

    const selectedSource = SOURCES.find(s => s.id === contentType);
    const selectedTarget = subjects.find(s => s.id === targetSubjectId);
    const filteredSubjects = subjects.filter(s => s.name.toLowerCase().includes(subjectSearch.toLowerCase()));

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            {/* Modal Container */}
            <div
                className="w-full max-w-4xl h-[680px] max-h-[90vh] bg-[#18181b] border border-border-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-5 border-b border-border-subtle bg-black/20">
                    <div>
                        <h2 className="text-lg font-semibold text-zinc-100">{t('ingestion.title')}</h2>
                        <div className="text-xs text-zinc-500 mt-1 flex items-center gap-2 relative">
                            {t('ingestion.subject.label')}:
                            <button
                                type="button"
                                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                className="flex items-center gap-2 bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700/50 hover:border-zinc-600 rounded-lg px-2.5 py-1.5 text-emerald-400 font-medium transition-colors"
                            >
                                <span
                                    className="truncate max-w-[180px]">{selectedTarget?.name || t('ingestion.subject.placeholder')}</span>
                                <ChevronDown className="w-3.5 h-3.5 opacity-70"/>
                            </button>

                            {isDropdownOpen && (
                                <>
                                    <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)}/>
                                    <div
                                        className="absolute top-full left-[90px] mt-1 w-64 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col animate-in fade-in slide-in-from-top-2 duration-200">
                                        <div className="p-2 border-b border-zinc-800">
                                            <div className="relative">
                                                <Search
                                                    className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500"/>
                                                <input
                                                    type="text"
                                                    autoFocus
                                                    placeholder={t('sidebar.contexts.placeholder')}
                                                    value={subjectSearch}
                                                    onChange={e => setSubjectSearch(e.target.value)}
                                                    className="w-full bg-black/40 border border-zinc-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-colors"
                                                />
                                            </div>
                                        </div>
                                        <div className="max-h-[200px] overflow-y-auto p-1 custom-scrollbar">
                                            {filteredSubjects.length === 0 ? (
                                                <div className="p-3 text-xs text-zinc-500 text-center">{t('sidebar.contexts.none')}</div>
                                            ) : (
                                                filteredSubjects.map(s => (
                                                    <button
                                                        key={s.id}
                                                        type="button"
                                                        onClick={() => {
                                                            setTargetSubjectId(s.id);
                                                            setIsDropdownOpen(false);
                                                            setSubjectSearch('');
                                                        }}
                                                        className={`w-full flex items-center justify-between px-3 py-2 text-sm rounded-lg transition-colors ${
                                                            targetSubjectId === s.id ? 'bg-emerald-500/10 text-emerald-400' : 'text-zinc-300 hover:bg-zinc-800'
                                                        }`}
                                                    >
                                                        <span className="truncate">{s.name}</span>
                                                        {targetSubjectId === s.id && <Check className="w-4 h-4"/>}
                                                    </button>
                                                ))
                                            )}
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
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
                    <div
                        className="w-full md:w-1/3 border-b md:border-b-0 md:border-r border-border-subtle bg-black/20 p-4 flex flex-col gap-2 overflow-y-auto">
                        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 px-1">{t('sidebar.operations.sources')}</h3>
                        {SOURCES.map((source) => {
                            const Icon = source.icon;
                            const isSelected = contentType === source.id;

                            return (
                                <button
                                    key={source.id}
                                    onClick={() => setContentType(source.id)}
                                    className={`group flex items-start gap-3 p-3 rounded-xl text-left transition-all ${
                                        isSelected
                                            ? 'bg-zinc-800 border border-zinc-700 shadow-sm'
                                            : 'hover:bg-panel-hover border border-transparent'
                                    } ${!source.enabled && !isSelected ? 'opacity-60' : ''}`}
                                >
                                    <div
                                        className={`p-2 rounded-lg transition-colors ${isSelected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-zinc-800 text-zinc-400 group-hover:text-zinc-200'}`}>
                                        <Icon
                                            className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isSelected ? 'scale-110' : ''}`}/>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-2">
                      <span
                          className={`text-sm font-medium truncate ${isSelected ? 'text-zinc-100' : 'text-zinc-300'}`}>
                        {source.name}
                      </span>
                                            {!source.enabled && (
                                                <Lock className="w-3 h-3 text-zinc-500 flex-shrink-0"/>
                                            )}
                                        </div>
                                        <span
                                            className="text-xs text-zinc-500 block truncate">{source.description}</span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    {/* Right Content: Dynamic Input Area */}
                    <div className="w-full md:w-2/3 flex flex-col bg-[#121212] relative">
                        <form onSubmit={handleSubmit} className="flex flex-col h-full overflow-hidden">

                            {/* Fixed Tab Buttons */}
                            <div className="flex border-b border-zinc-800/50">
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('source')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-3 text-xs font-semibold tracking-wide uppercase transition-all border-b-2 ${
                                        activeTab === 'source'
                                            ? 'text-emerald-400 border-emerald-500 bg-emerald-500/5'
                                            : 'text-zinc-500 border-transparent hover:text-zinc-300 hover:bg-white/[0.02]'
                                    }`}
                                >
                                    <Zap className="w-3.5 h-3.5"/>
                                    {t('search.results.source')}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('settings')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-3 text-xs font-semibold tracking-wide uppercase transition-all border-b-2 ${
                                        activeTab === 'settings'
                                            ? 'text-emerald-400 border-emerald-500 bg-emerald-500/5'
                                            : 'text-zinc-500 border-transparent hover:text-zinc-300 hover:bg-white/[0.02]'
                                    }`}
                                >
                                    <Settings2 className="w-3.5 h-3.5"/>
                                    {t('settings.tabs.processing')}
                                </button>
                            </div>

                            {/* Tab Identification (Source tab only) */}
                            {activeTab === 'source' && selectedSource && (
                                <div className="flex items-center gap-3 px-6 py-3 border-b border-zinc-800/30 bg-black/20">
                                    <div className="p-2 rounded-lg bg-zinc-800/80 text-zinc-300">
                                        <selectedSource.icon className="w-4 h-4"/>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-medium text-zinc-200">
                                            {t('common.actions.addData')} {selectedSource.name}
                                        </h3>
                                        <p className="text-[11px] text-zinc-500">
                                            {selectedSource.description}
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Scrollable Content Area */}
                            <div
                                className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-zinc-800 custom-scrollbar">
                                <div className="min-h-full">
                                    {activeTab === 'source' ? (
                                        selectedSource?.enabled ? (
                                            contentType === 'youtube' ? (
                                                <div
                                                    className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                                    {/* Video / Playlist Toggle */}
                                                    <div
                                                        className="flex p-0.5 bg-black/40 rounded-xl border border-zinc-800/50 w-full">
                                                        <button
                                                            type="button"
                                                            onClick={() => setYoutubeDataType('video')}
                                                            className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-lg transition-all ${
                                                                youtubeDataType === 'video' ? 'bg-zinc-800 text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
                                                            }`}
                                                        >
                                                            <Youtube className="w-3.5 h-3.5"/>
                                                            {t('ingestion.options.types.video')}
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => setYoutubeDataType('playlist')}
                                                            className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-lg transition-all ${
                                                                youtubeDataType === 'playlist' ? 'bg-zinc-800 text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
                                                            }`}
                                                        >
                                                            <ListVideo className="w-3.5 h-3.5"/>
                                                            {t('ingestion.options.types.playlist')}
                                                        </button>
                                                    </div>

                                                    <label className="text-sm font-medium text-zinc-300">
                                                        {youtubeDataType === 'playlist' ? t('ingestion.options.types.playlist_url') : t('ingestion.url.label')}
                                                    </label>
                                                    <input
                                                        type="url"
                                                        required
                                                        value={inputValue}
                                                        onChange={(e) => setInputValue(e.target.value)}
                                                        placeholder={youtubeDataType === 'playlist' ? t('ingestion.options.types.playlist_url') : t('ingestion.url.placeholder')}
                                                        className="w-full bg-black/40 border border-border-subtle rounded-xl px-4 py-3 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all placeholder:text-zinc-600 shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)]"
                                                    />
                                                    <div
                                                        className="flex items-start gap-2 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                                                        <ArrowRight
                                                            className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0"/>
                                                        <p className="text-xs text-zinc-400 leading-relaxed">
                                                            {youtubeDataType === 'playlist'
                                                                ? t('ingestion.options.types.playlist_desc')
                                                                : t('ingestion.coming_soon.description', { name: 'YouTube' })}
                                                        </p>
                                                    </div>
                                                </div>
                                            ) : contentType === 'file' ? (
                                                <div
                                                    className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                                                    {!selectedFile ? (
                                                        <div
                                                            onDragOver={handleDragOver}
                                                            onDragLeave={handleDragLeave}
                                                            onDrop={handleDrop}
                                                            className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center transition-colors ${
                                                                isDragging ? 'border-emerald-500 bg-emerald-500/5' : 'border-zinc-700 hover:border-zinc-500 bg-black/20'
                                                            }`}
                                                        >
                                                            <UploadCloud
                                                                className={`w-10 h-10 mb-3 ${isDragging ? 'text-emerald-400' : 'text-zinc-500'}`}/>
                                                            <p className="text-sm font-medium text-zinc-300 mb-1">{t('ingestion.coming_soon.title')}</p>
                                                            <p className="text-xs text-zinc-500 mb-4">Supports PDF, TXT,
                                                                CSV up to 50MB</p>
                                                            <label
                                                                className="cursor-pointer px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm font-medium rounded-lg transition-colors border border-zinc-700">
                                                                {t('common.actions.addData')}
                                                                <input type="file" className="hidden"
                                                                       accept=".pdf,.txt,.csv"
                                                                       onChange={handleFileChange}/>
                                                            </label>
                                                        </div>
                                                    ) : (
                                                        <div
                                                            className="bg-black/40 border border-zinc-800 rounded-xl p-4 animate-in fade-in zoom-in-95 duration-200">
                                                            <div className="flex items-center justify-between mb-4">
                                                                <div className="flex items-center gap-3">
                                                                    <div className="p-2 bg-emerald-500/10 rounded-lg">
                                                                        <FileText className="w-5 h-5 text-emerald-400"/>
                                                                    </div>
                                                                    <div>
                                                                        <p className="text-sm font-medium text-zinc-200">{selectedFile.name}</p>
                                                                        <p className="text-xs text-zinc-500">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                                                                    </div>
                                                                </div>
                                                                {uploadStatus === 'idle' && (
                                                                    <button type="button"
                                                                            onClick={() => setSelectedFile(null)}
                                                                            className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors">
                                                                        <X className="w-4 h-4"/>
                                                                    </button>
                                                                )}
                                                            </div>

                                                            {uploadStatus !== 'idle' && (
                                                                <div className="space-y-2">
                                                                    <div
                                                                        className="flex justify-between text-xs font-medium">
                                  <span className={uploadStatus === 'chunking' ? 'text-emerald-400' : 'text-zinc-400'}>
                                    {uploadStatus === 'chunking' ? t('common.actions.syncing') : uploadStatus === 'vectorizing' ? t('common.actions.syncing') : t('common.status.done')}
                                  </span>
                                                                        <span
                                                                            className="text-zinc-400">{progress}%</span>
                                                                    </div>
                                                                    <div
                                                                        className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                                                        <div
                                                                            className="h-full bg-emerald-500 transition-all duration-300 ease-out"
                                                                            style={{width: `${progress}%`}}
                                                                        />
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            ) : null
                                        ) : (
                                            <div
                                                className="flex flex-col items-center justify-center text-center p-6 border border-dashed border-zinc-800 rounded-xl bg-black/20 animate-in fade-in duration-300">
                                                <Lock className="w-8 h-8 text-zinc-600 mb-3"/>
                                                <h4 className="text-sm font-medium text-zinc-300">{t('ingestion.coming_soon.title')}</h4>
                                                <p className="text-xs text-zinc-500 mt-2 max-w-[250px]">
                                                    {t('ingestion.coming_soon.description', { name: selectedSource?.name })}
                                                </p>
                                            </div>
                                        )
                                    ) : (
                                        <div className="animate-in fade-in slide-in-from-right-2 duration-300">
                                            <ProcessingStrategy {...strategyProps} />
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Fixed Footer Actions */}
                            <div
                                className="flex items-center justify-end gap-3 p-6 border-t border-border-subtle bg-black/20">
                                <button
                                    type="button"
                                    onClick={onClose}
                                    className="px-4 py-2.5 text-sm font-medium text-zinc-400 hover:text-zinc-100 transition-colors"
                                >
                                    {t('common.actions.cancel')}
                                </button>
                                <button
                                    type="submit"
                                    disabled={!selectedSource?.enabled || (contentType === 'youtube' && !inputValue.trim()) || (contentType === 'file' && !selectedFile) || uploadStatus !== 'idle'}
                                    className="px-6 py-2.5 text-sm font-medium text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.15)] disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
                                >
                                    {t('common.actions.addData')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}
