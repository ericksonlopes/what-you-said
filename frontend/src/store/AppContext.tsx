import React, { createContext, useContext, useState, ReactNode, useCallback, useEffect } from 'react';
import { Subject, ViewState, Toast, ToastType, ContentSource, IngestionTask, ModelInfo } from '../types';
import { api } from '../services/api';

// 1. Estrutura de classes/objetos para gerenciar o estado da aplicação.
// Utilizamos a Context API do React para simular o st.session_state de forma reativa e tipada.

interface AppState {
  selectedSubjects: Subject[];
  toggleSubjectSelection: (subject: Subject) => void;
  selectOnlySubject: (subject: Subject) => void;
  currentView: ViewState;
  setCurrentView: (view: ViewState) => void;
  selectedSourceIdForDb: string | null;
  setSelectedSourceIdForDb: (id: string | null) => void;
  subjects: Subject[];
  refreshSubjects: () => Promise<void>;
  addSubject: (subject: Omit<Subject, 'id' | 'sourceCount'>) => void;
  isSourcesLoaded: boolean;
  refreshSources: () => Promise<void>;
  sources: ContentSource[];
  jobs: IngestionTask[];
  refreshJobs: () => Promise<void>;
  addOptimisticJob: (title: string) => void;
  toasts: Toast[];
  addToast: (message: string, type?: ToastType) => void;
  removeToast: (id: string) => void;
  modelInfo: ModelInfo | null;
  refreshModelInfo: () => Promise<void>;
}

const AppContext = createContext<AppState | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjects, setSelectedSubjects] = useState<Subject[]>([]);
  const [sources, setSources] = useState<ContentSource[]>([]);
  const [isSourcesLoaded, setIsSourcesLoaded] = useState(false);
  const [jobs, setJobs] = useState<IngestionTask[]>([]);
  const [isJobsLoaded, setIsJobsLoaded] = useState(false);
  const [currentView, setCurrentView] = useState<ViewState>(() => {
    const saved = localStorage.getItem('currentView') as ViewState;
    const validViews: ViewState[] = ['chat', 'search', 'sources', 'activity', 'database'];
    const initial = validViews.includes(saved) ? saved : 'search';
    return initial;
  });
  const [selectedSourceIdForDb, setSelectedSourceIdForDb] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);

  const refreshSubjects = useCallback(async () => {
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

      if (data.length > 0 && selectedSubjects.length === 0) {
        setSelectedSubjects([data[0]]);
      }
    } catch (err) {
      console.error('Error fetching subjects:', err);
    }
  }, [selectedSubjects.length]);

  const refreshSources = useCallback(async () => {
    try {
      const data = await api.fetchSources();
      setSources(data);
    } catch (err) {
      console.error('Error fetching sources:', err);
    } finally {
      setIsSourcesLoaded(true);
    }
  }, []);

  const refreshJobs = useCallback(async () => {
    try {
      const data = await api.fetchJobs();
      setJobs(data);
    } catch (err) {
      console.error('Error fetching jobs:', err);
    } finally {
      setIsJobsLoaded(true);
    }
  }, []);

  const addOptimisticJob = useCallback((title: string) => {
    const optimisticJob: IngestionTask = {
      id: `optimistic-${Date.now()}`,
      title,
      status: 'processing',
      progress: 0,
      subjectId: '',
      createdAt: new Date().toISOString(),
    };
    setJobs((prev) => [optimisticJob, ...prev]);
  }, []);

  const refreshModelInfo = useCallback(async () => {
    try {
      const data = await api.fetchModelInfo();
      setModelInfo(data);
    } catch (err) {
      console.error('Error fetching model info:', err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    refreshSubjects();
    refreshSources();
    refreshJobs();
    refreshModelInfo();
  }, [refreshSubjects, refreshSources, refreshJobs, refreshModelInfo]);

  // Periodic refresh for jobs (Activity Monitor)
  useEffect(() => {
    const interval = setInterval(refreshJobs, 3000);
    return () => clearInterval(interval);
  }, [refreshJobs]);

  useEffect(() => {
    const interval = setInterval(() => {
      refreshSources();
      refreshSubjects();
    }, 5000);
    return () => clearInterval(interval);
  }, [refreshSources, refreshSubjects]);

  // Persist currentView
  useEffect(() => {
    localStorage.setItem('currentView', currentView);
  }, [currentView]);

  // Persist selectedSubjects
  useEffect(() => {
    if (selectedSubjects.length > 0) {
      const ids = selectedSubjects.map(s => s.id);
      localStorage.setItem('selectedSubjectIds', JSON.stringify(ids));
    }
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

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);

    // Auto remove after 4 seconds
    setTimeout(() => {
      removeToast(id);
    }, 4000);
  }, [removeToast]);

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
  }, [addToast]);

  return (
    <AppContext.Provider
      value={{
        selectedSubjects,
        toggleSubjectSelection,
        selectOnlySubject,
        currentView,
        setCurrentView,
        selectedSourceIdForDb,
        setSelectedSourceIdForDb,
        subjects,
        refreshSubjects,
        addSubject,
        sources,
        isSourcesLoaded,
        refreshSources,
        jobs,
        isJobsLoaded,
        refreshJobs,
        addOptimisticJob,
        toasts,
        addToast,
        removeToast,
        modelInfo,
        refreshModelInfo,
      }}
    >
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
