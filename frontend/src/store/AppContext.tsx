import React, {createContext, ReactNode, useCallback, useContext, useEffect, useState} from 'react';
import {ContentSource, IngestionTask, ModelInfo, RawQueueTask, Subject, Toast, ToastType, ViewState} from '../types';

import {api} from '../services/api';
import {useTranslation} from 'react-i18next';
import {useAuth} from './AuthContext';

// 1. Estrutura de classes/objetos para gerenciar o estado da aplicação.
// Utilizamos a Context API do React para simular o st.session_state de forma reativa e tipada.

interface AppState {
  selectedSubjects: Subject[];
  setSelectedSubjects: (subjects: Subject[]) => void;
  toggleSubjectSelection: (subject: Subject) => void;
  selectOnlySubject: (subject: Subject) => void;
  currentView: ViewState;
  previousView: ViewState | null;
  setCurrentView: (view: ViewState) => void;
  goBack: () => void;
  selectedSourceIdForDb: string | null;
  setSelectedSourceIdForDb: (id: string | null) => void;
  subjects: Subject[];
  refreshSubjects: () => Promise<void>;
  addSubject: (subject: Omit<Subject, 'id' | 'sourceCount'>) => void;
  updateSubject: (id: string, subject: Partial<Subject>) => Promise<void>;
  deleteSubject: (id: string) => Promise<void>;
  isSourcesLoaded: boolean;
  refreshSources: () => Promise<void>;
  sources: ContentSource[];
  sourceTypes: string[];
  jobs: IngestionTask[];
  totalJobs: number;
  jobStats: Record<string, number>;
  isJobsLoaded: boolean;
  refreshJobs: (params?: { page?: number; pageSize?: number; status?: string; search?: string }) => Promise<void>;
  jobPage: number;
  setJobPage: (page: number) => void;
  jobPageSize: number;
  setJobPageSize: (size: number) => void;
  jobStatusFilter: string;
  setJobStatusFilter: (status: any) => void;
  jobSearchQuery: string;
  setJobSearchQuery: (query: string) => void;
  addOptimisticJob: (title: string, externalSource?: string) => string;
  removeOptimisticJob: (id: string) => void;
  toasts: Toast[];
  addToast: (message: string, type?: ToastType) => void;
  removeToast: (id: string) => void;
  deleteSource: (id: string) => Promise<void>;
  updateSourceTitle: (id: string, title: string) => Promise<void>;
  modelInfo: ModelInfo | null;
  refreshModelInfo: () => Promise<void>;
  voices: any[];
  refreshVoices: () => Promise<void>;
  isAddModalOpen: boolean;
  setIsAddModalOpen: (isOpen: boolean) => void;
  isAddSubjectModalOpen: boolean;
  setIsAddSubjectModalOpen: (isOpen: boolean) => void;
  lastEvent: Record<string, any> | null;
  queueTasks: RawQueueTask[];
  isQueueLoaded: boolean;
  refreshQueue: (limit?: number) => Promise<void>;
}


const AppContext = createContext<AppState | undefined>(undefined);

export function AppProvider({ children }: { readonly children: ReactNode }) {
  const { t } = useTranslation();
  const { isAuthEnabled, isAuthenticated } = useAuth();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjects, setSelectedSubjects] = useState<Subject[]>([]);
  const [sources, setSources] = useState<ContentSource[]>([]);
  const [sourceTypes, setSourceTypes] = useState<string[]>([]);
  const [isSourcesLoaded, setIsSourcesLoaded] = useState(false);
  const [jobs, setJobs] = useState<IngestionTask[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [jobStats, setJobStats] = useState<Record<string, number>>({ total: 0, processing: 0, completed: 0, failed: 0 });
  const [isJobsLoaded, setIsJobsLoaded] = useState(false);
  const [currentView, setCurrentView] = useState<ViewState>(() => {
    const saved = localStorage.getItem('currentView') as ViewState;
    const validViews: ViewState[] = ['chat', 'search', 'sources', 'activity', 'database', 'knowledge_contexts', 'diarization', 'voice_profiles', 'duplicates'];
    const initial = validViews.includes(saved) ? saved : 'search';
    return initial;
  });
  const [previousView, setPreviousView] = useState<ViewState | null>(null);
  const [selectedSourceIdForDb, setSelectedSourceIdForDb] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [voices, setVoices] = useState<any[]>([]);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState(false);
  const [lastEvent, setLastEvent] = useState<Record<string, unknown> | null>(null);
  const [queueTasks, setQueueTasks] = useState<RawQueueTask[]>([]);
  const [isQueueLoaded, setIsQueueLoaded] = useState(false);

  
  // Activity Monitor state
  const [jobPage, setJobPage] = useState(1);
  const [jobPageSize, setJobPageSize] = useState(12);
  const [jobStatusFilter, setJobStatusFilter] = useState<string>('all');
  const [jobSearchQuery, setJobSearchQuery] = useState('');


  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);

    // Auto remove after 8 seconds
    setTimeout(() => {
      removeToast(id);
    }, 8000);
  }, [removeToast]);

  const handleSetCurrentView = useCallback((view: ViewState) => {
    if (currentView !== view) {
      setPreviousView(currentView);
      setCurrentView(view);
    }
  }, [currentView]);

  const goBack = useCallback(() => {
    if (previousView) {
      setCurrentView(previousView);
      setPreviousView(null);
    } else {
      setCurrentView('sources');
    }
  }, [previousView]);

  const refreshSubjects = useCallback(async () => {
    if (isAuthEnabled && !isAuthenticated) return;
    try {
      const data = await api.fetchSubjects();
      setSubjects(data);

      // If we have persisted selection, restore it
      const savedIdsStr = localStorage.getItem('selectedSubjectIds');
      if (savedIdsStr) {
        try {
          const savedIds = JSON.parse(savedIdsStr) as string[];
          const restored = data.filter(s => savedIds.includes(s.id));
          if (restored.length > 0) {
            setSelectedSubjects(restored);
            return;
          }
        } catch (e) {
          console.error("Failed to parse saved subject IDs", e);
        }
      }

      // No auto-selecting anymore, empty selection means "All"
    } catch (err) {
      console.error('Error fetching subjects:', err);
    }
  }, [selectedSubjects.length, isAuthEnabled, isAuthenticated]);

  const refreshSources = useCallback(async () => {
    if (isAuthEnabled && !isAuthenticated) return;
    try {
      const [sourcesData, typesData] = await Promise.all([
        api.fetchSources(),
        api.fetchSourceTypes()
      ]);
      setSources(sourcesData);
      setSourceTypes(typesData);
    } catch (err) {
      console.error('Error fetching sources or types:', err);
    } finally {
      setIsSourcesLoaded(true);
    }
  }, [isAuthEnabled, isAuthenticated]);

  const normalizeYoutubeId = useCallback((s: string | undefined): string => {
    if (!s) return '';
    if (s.includes('youtube.com') || s.includes('youtu.be')) {
      const regex = /(?:v=|v\/|embed\/|watch\?v=|&v=|youtu\.be\/|\/v\/|watch\?feature=player_embedded&v=)([a-zA-Z0-9_-]{11})/;
      const match = regex.exec(s);
      return match ? match[1] : s;
    }
    return s;
  }, []);

  const isOptimisticJobInResults = useCallback((oj: IngestionTask, items: IngestionTask[]): boolean => {
    const ojNorm = normalizeYoutubeId(oj.externalSource || oj.title);
    return items.some(rj => {
      if (rj.title === oj.title) return true;
      return !!rj.externalSource && normalizeYoutubeId(rj.externalSource) === ojNorm;
    });
  }, [normalizeYoutubeId]);

  const refreshJobs = useCallback(async (params?: { page?: number; pageSize?: number; status?: string; search?: string }) => {
    if (isAuthEnabled && !isAuthenticated) return;
    try {
      const fetchParams = params || { 
        page: jobPage, 
        pageSize: jobPageSize, 
        status: jobStatusFilter, 
        search: jobSearchQuery 
      };
      const data = await api.fetchJobs(fetchParams);
      
      setJobs((prev) => {
        const optimisticJobs = prev.filter(job => job.id.startsWith('optimistic-'));
        const now = Date.now();
        
        const recentOptimisticJobs = optimisticJobs.filter(job => {
          const createdAt = new Date(job.createdAt).getTime();
          return now - createdAt < 120000;
        });
        
        const deduplicated = recentOptimisticJobs.filter(oj => !isOptimisticJobInResults(oj, data.items));
        
        return [...data.items, ...deduplicated];
      });
      
      setTotalJobs(data.total);
      if (data.stats) setJobStats(data.stats);
    } catch (err) {
      console.error('Error fetching jobs:', err);
    } finally {
      setIsJobsLoaded(true);
    }
  }, [jobPage, jobPageSize, jobStatusFilter, jobSearchQuery, isAuthEnabled, isAuthenticated, isOptimisticJobInResults]);

  const addOptimisticJob = useCallback((title: string, externalSource?: string) => {
    const id = `optimistic-${Date.now()}`;
    const optimisticJob: IngestionTask = {
      id,
      title,
      status: 'processing',
      progress: 0,
      subjectId: '',
      createdAt: new Date().toISOString(),
      externalSource,
    };
    setJobs((prev) => [optimisticJob, ...prev]);
    return id;
  }, []);

  const removeOptimisticJob = useCallback((id: string) => {
    setJobs((prev) => prev.filter(job => job.id !== id));
  }, []);

  const refreshModelInfo = useCallback(async () => {
    if (isAuthEnabled && !isAuthenticated) return;
    try {
      const data = await api.fetchModelInfo();
      setModelInfo(data);
    } catch (err) {
      console.error('Error fetching model info:', err);
    }
  }, [isAuthEnabled, isAuthenticated]);

  const refreshVoices = useCallback(async () => {
    if (isAuthEnabled && !isAuthenticated) return;
    try {
      const data = await api.fetchVoiceProfiles();
      setVoices(data);
    } catch (err) {
      console.error('Error fetching voice profiles:', err);
    }
  }, [isAuthEnabled, isAuthenticated]);

  const refreshQueue = useCallback(async (limit: number = 50) => {
    if (isAuthEnabled && !isAuthenticated) return;
    try {
      const data = await api.fetchRawQueue(limit);
      setQueueTasks(data);
    } catch (err) {
      console.error('Error fetching raw queue:', err);
    } finally {
      setIsQueueLoaded(true);
    }
  }, [isAuthEnabled, isAuthenticated]);

  // Initial load

  useEffect(() => {
    refreshSubjects();
    refreshSources();
    refreshModelInfo();
    refreshVoices();
    refreshQueue();
  }, [refreshSubjects, refreshSources, refreshJobs, refreshModelInfo, refreshVoices, refreshQueue, isAuthEnabled, isAuthenticated]);


  // Ref to store current filters for use in polling intervals without triggering re-renders
  const jobFiltersRef = React.useRef({ 
    page: jobPage, 
    pageSize: jobPageSize, 
    status: jobStatusFilter, 
    search: jobSearchQuery 
  });

  useEffect(() => {
    jobFiltersRef.current = { 
      page: jobPage, 
      pageSize: jobPageSize, 
      status: jobStatusFilter, 
      search: jobSearchQuery 
    };
  }, [jobPage, jobPageSize, jobStatusFilter, jobSearchQuery]);



  // Periodic refresh for state (Global SSE Listener)
  useEffect(() => {
    if (isAuthEnabled && !isAuthenticated) return;

    let eventSource: EventSource | null = null;
    let retryCount = 0;
    const maxRetries = 5;

    const connectSSE = () => {
        if (eventSource) eventSource.close();
        
        eventSource = new EventSource('/rest/notifications/events');

        eventSource.onopen = () => {
            retryCount = 0;
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setLastEvent(data);
                
                // Dispatch refreshes based on event type
                if (data.type === 'ingestion' || data.type === 'diarization') {
                    refreshJobs(jobFiltersRef.current);
                    if (['done', 'ingested', 'completed', 'awaiting_verification', 'failed', 'cancelled'].includes(data.status)) {
                        refreshSources();
                    }
                } else if (data.type === 'source') {
                    refreshSources();
                } else if (data.type === 'subject') {
                    refreshSubjects();
                } else if (data.type === 'voice') {
                    refreshVoices();
                }
            } catch (err) {
                console.error('[SSE] Error parsing event data:', err);
            }
        };

        eventSource.onerror = (err) => {
            console.error('[SSE] EventSource failed:', err);
            eventSource?.close();
            
            if (retryCount < maxRetries) {
                const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
                setTimeout(connectSSE, delay);
                retryCount++;
            } else {
                console.warn('[SSE] Max retries reached. Polling fallback or manual refresh needed.');
            }
        };
    };

    connectSSE();

    // Still keep a VERY slow safety polling (e.g. 60s) just in case SSE dies silently
    const safetyInterval = setInterval(() => {
      refreshJobs(jobFiltersRef.current);
      refreshSources();
      refreshSubjects();
    }, 60000);

    return () => {
        if (eventSource) eventSource.close();
        clearInterval(safetyInterval);
    };
  }, [refreshJobs, refreshSources, refreshSubjects, isAuthEnabled, isAuthenticated]);

  // Polling for raw queue when in queue view
  useEffect(() => {
    if (currentView !== 'queue' || (isAuthEnabled && !isAuthenticated)) return;

    const interval = setInterval(() => {
      refreshQueue();
    }, 10000); // 10s polling for technical view

    return () => clearInterval(interval);
  }, [currentView, refreshQueue, isAuthEnabled, isAuthenticated]);


  // Persist currentView
  useEffect(() => {
    localStorage.setItem('currentView', currentView);
  }, [currentView]);

  // Persist selectedSubjects
  useEffect(() => {
      const ids = selectedSubjects.map(s => s.id);
      localStorage.setItem('selectedSubjectIds', JSON.stringify(ids));
  }, [selectedSubjects]);

  const toggleSubjectSelection = useCallback((subject: Subject) => {
    setSelectedSubjects((prev) => {
      const isSelected = prev.some((s) => s.id === subject.id);
      if (isSelected) {
        const next = prev.filter((s) => s.id !== subject.id);
        return next.length > 0 ? next : prev; // Prevent empty selection
      } else {
        return [...prev, subject];
      }
    });
  }, []);

  const selectOnlySubject = useCallback((subject: Subject) => {
    setSelectedSubjects([subject]);
  }, []);

  const deleteSource = useCallback(async (id: string) => {
    try {
      await api.deleteSource(id);
      setSources((prev) => prev.filter((s) => s.id !== id));
      addToast(t('sources.notifications.delete_success'), 'success');
    } catch (err) {
      console.error('Error deleting source:', err);
      addToast(t('sources.notifications.delete_error'), 'error');
      throw err;
    }
  }, [addToast, t]);

  const updateSourceTitle = useCallback(async (id: string, title: string) => {
    try {
      await api.updateSource(id, title);
      setSources((prev) => prev.map((s) => s.id === id ? { ...s, title } : s));
      addToast(t('notifications.source.updated', { name: title }), 'success');
    } catch (err) {
      console.error('Error updating source title:', err);
      addToast(t('notifications.source.error_update'), 'error');
      throw err;
    }
  }, [addToast, t]);

  const addSubject = useCallback(async (subjectData: Omit<Subject, 'id' | 'sourceCount'>) => {
    try {
      const newSubject = await api.createSubject(subjectData.name, subjectData.description, subjectData.icon);
      setSubjects((prev) => [...prev, newSubject]);
      setSelectedSubjects([newSubject]); // Auto-select the newly created subject
      addToast(t('notifications.subject.created', { name: newSubject.name }), 'success');
    } catch (err) {
      console.error('Error creating subject:', err);
      addToast(t('notifications.subject.error'), 'error');
    }
  }, [addToast, t]);

  const updateSubject = useCallback(async (id: string, subjectData: Partial<Subject>) => {
    try {
      await api.updateSubject(id, subjectData.name, subjectData.description, subjectData.icon);
      setSubjects((prev) => prev.map(s => s.id === id ? { ...s, ...subjectData } : s));
      addToast(t('notifications.subject.updated', { name: subjectData.name }), 'success');
    } catch (err) {
      console.error('Error updating subject:', err);
      addToast(t('notifications.subject.error_update'), 'error');
    }
  }, [addToast, t]);

  const deleteSubject = useCallback(async (id: string) => {
    try {
      await api.deleteSubject(id);
      setSubjects((prev) => prev.filter(s => s.id !== id));
      setSelectedSubjects((prev) => {
        const next = prev.filter(s => s.id !== id);
        if (next.length === 0 && subjects.length > 1) {
           const other = subjects.find(s => s.id !== id);
           return other ? [other] : [];
        }
        return next;
      });
      addToast(t('notifications.subject.deleted'), 'success');
    } catch (err) {
      console.error('Error deleting subject:', err);
      addToast(t('notifications.subject.error_delete'), 'error');
    }
  }, [addToast, t, subjects]);

  const contextValue = React.useMemo(() => ({
    selectedSubjects,
    setSelectedSubjects,
    toggleSubjectSelection,
    selectOnlySubject,
    currentView,
    previousView,
    setCurrentView: handleSetCurrentView,
    goBack,
    selectedSourceIdForDb,
    setSelectedSourceIdForDb,
    subjects,
    refreshSubjects,
    addSubject,
    updateSubject,
    deleteSubject,
    sources,
    isSourcesLoaded,
    refreshSources,
    sourceTypes,
    jobs,
    totalJobs,
    jobStats,
    isJobsLoaded,
    refreshJobs,
    jobPage,
    setJobPage,
    jobPageSize,
    setJobPageSize,
    jobStatusFilter,
    setJobStatusFilter,
    jobSearchQuery,
    setJobSearchQuery,
    addOptimisticJob,
    removeOptimisticJob,
    toasts,
    addToast,
    removeToast,
    deleteSource,
    updateSourceTitle,
    modelInfo,
    refreshModelInfo,
    voices,
    refreshVoices,
    isAddModalOpen,
    setIsAddModalOpen,
    isAddSubjectModalOpen,
    setIsAddSubjectModalOpen,
    lastEvent,
    queueTasks,
    isQueueLoaded,
    refreshQueue,
  }), [

    selectedSubjects,
    setSelectedSubjects,
    toggleSubjectSelection,
    selectOnlySubject,
    currentView,
    previousView,
    handleSetCurrentView,
    goBack,
    selectedSourceIdForDb,
    subjects,
    refreshSubjects,
    addSubject,
    updateSubject,
    deleteSubject,
    sources,
    isSourcesLoaded,
    refreshSources,
    sourceTypes,
    jobs,
    totalJobs,
    jobStats,
    isJobsLoaded,
    refreshJobs,
    jobPage,
    jobPageSize,
    jobStatusFilter,
    jobSearchQuery,
    addOptimisticJob,
    removeOptimisticJob,
    toasts,
    addToast,
    removeToast,
    deleteSource,
    updateSourceTitle,
    modelInfo,
    refreshModelInfo,
    voices,
    refreshVoices,
    isAddModalOpen,
    setIsAddModalOpen,
    isAddSubjectModalOpen,
    setIsAddSubjectModalOpen,
    lastEvent,
    queueTasks,
    isQueueLoaded,
    refreshQueue,
  ]);


  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}
