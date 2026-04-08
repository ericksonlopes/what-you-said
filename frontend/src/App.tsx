import React, {useCallback, useEffect, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {
  Activity as ActivityIcon,
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  XCircle,
  LayoutGrid,
  Filter
} from 'lucide-react';
import { motion } from 'framer-motion';
import {AppProvider, useAppContext} from './store/AppContext';
import {AuthProvider, useAuth} from './store/AuthContext';
import {Sidebar} from './components/Sidebar';
import {LoginModal} from './components/LoginModal';
import {TaskCard} from './components/TaskCard';
import {SourcesTable} from './components/SourcesTable';
import {AddContentModal} from './components/AddContentModal';
import {ToastContainer} from './components/ToastContainer';
import {SearchView} from './components/SearchView';
import {ChunksViewer} from './components/ChunksViewer';
import {AddSubjectModal} from './components/AddSubjectModal';
import {DiarizationView} from './components/DiarizationView';
import {VoiceProfilesView} from './components/VoiceProfilesView';
import {ErrorBoundary} from './components/ErrorBoundary';
import {ContentSource} from './types';
import {ChatView} from './components/ChatView';
import {KnowledgeAdminView} from './components/KnowledgeAdminView';
import {QueueMonitorView} from './components/QueueMonitorView';
import {DuplicatesView} from './components/DuplicatesView';
import {SidebarContext} from './components/SidebarContext';


function ActivityMonitorView() {
  const {
    jobs = [],
    totalJobs = 0,
    jobStats = {total: 0, processing: 0, completed: 0, failed: 0},
    refreshJobs,
    isJobsLoaded,
    sources = [],
    subjects = [],
    addToast,
    jobPage: page,
    setJobPage: setPage,
    jobPageSize: pageSize,
    jobStatusFilter: statusFilter,
    setJobStatusFilter: setStatusFilter,
    jobSearchQuery: searchQuery,
    setJobSearchQuery: setSearchQuery
  } = useAppContext();
  const { t } = useTranslation();
  const [isSyncing, setIsSyncing] = useState(false);

  const handleRefresh = useCallback(async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    try {
      await refreshJobs?.({page, pageSize, status: statusFilter, search: searchQuery});
      addToast(t('notifications.sync.success'), 'success');
    } catch (err) {
      console.error('[ActivityMonitor] Sync failed:', err);
      addToast(t('notifications.sync.error'), 'error');
    } finally {
      setIsSyncing(false);
    }
  }, [isSyncing, refreshJobs, page, pageSize, statusFilter, searchQuery, addToast, t]);

  // Trigger refresh on page, pageSize, status, or search changes
  useEffect(() => {
    refreshJobs?.({page, pageSize, status: statusFilter, search: searchQuery});
  }, [page, pageSize, statusFilter, searchQuery, refreshJobs]);

  const enrichedJobs = React.useMemo(() => {
    return jobs.map(job => {
      const subject = subjects.find(s => s.id === job.subjectId);
      const subjectName = subject?.name || '';
      
      if (job.contentSourceId) {
        const source = sources.find(s => s.id === job.contentSourceId);
        if (source) {
          return { 
            ...job, 
            title: (job.title === job.statusMessage || job.title.includes('Job')) ? source.title : job.title,
            chunksCount: source.chunkCount || job.chunksCount,
            subjectName
          };
        }
      }
      return { ...job, subjectName };
    });
  }, [jobs, sources, subjects]);

  const totalPages = Math.ceil(totalJobs / pageSize);

  const stats = React.useMemo(() => ({
    total: jobStats.total,
    processing: jobStats.processing,
    completed: jobStats.completed,
    failed: jobStats.failed,
    cancelled: jobStats.cancelled || 0,
  }), [jobStats]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  const statConfig = [
    { label: t('activity.stats.total'), value: stats.total, color: 'text-zinc-400', icon: Database, bg: 'bg-zinc-400/5', status: 'all' },
    { label: t('activity.stats.active'), value: stats.processing, color: 'text-primary-400', icon: Loader2, bg: 'bg-primary-400/5', pulse: stats.processing > 0, status: 'processing' },
    { label: t('activity.stats.completed'), value: stats.completed, color: 'text-emerald-400', icon: CheckCircle2, bg: 'bg-emerald-400/5', status: 'completed' },
    {
      label: t('activity.stats.failed'),
      value: stats.failed,
      color: 'text-rose-400',
      icon: AlertCircle,
      bg: 'bg-rose-400/5',
      status: 'failed'
    },
    {
      label: t('activity.stats.cancelled'),
      value: stats.cancelled,
      color: 'text-zinc-500',
      icon: XCircle,
      bg: 'bg-zinc-500/5',
      status: 'cancelled'
    }
  ];

  return (
    <div className="p-8 pt-10 max-w-7xl mx-auto h-full flex flex-col">
      <div className="mb-10 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-2xl bg-primary-500/10 border border-primary-500/20 shadow-[0_0_20px_rgba(var(--primary-color),0.1)]">
              <ActivityIcon className="w-7 h-7 text-primary-400" />
            </div>
            <div>
              <h2 className="text-3xl font-black text-white tracking-tight leading-none">{t('activity.title')}</h2>
              <p className="text-zinc-500 text-sm mt-2 font-medium">{t('activity.subtitle')}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="relative group/search">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-zinc-500 group-focus-within/search:text-primary-500 transition-colors" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                placeholder="Filtrar tarefas..."
                className="block w-full md:w-64 pl-9 pr-3 py-1.5 bg-zinc-900 border border-white/5 rounded-lg text-sm text-zinc-300 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:border-primary-500/30 transition-all"
              />
            </div>
             <button 
                onClick={handleRefresh}
                disabled={isSyncing}
                className="group flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-zinc-300 bg-zinc-900 border border-white/5 rounded-lg hover:bg-zinc-800 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 transition-transform duration-500 ${isSyncing ? 'animate-spin text-primary-400' : 'group-hover:rotate-180'}`} />
                {isSyncing ? t('common.actions.syncing') : t('common.actions.sync')}
              </button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {statConfig.map((stat, i) => {
            const isActive = statusFilter === stat.status;
            let containerBgClass = `bg-zinc-900/40 border-white/5 border hover:border-white/10 hover:bg-zinc-900/60 ${stat.bg}`;
            if (isActive) {
              containerBgClass = 'bg-zinc-800 border-white/20 shadow-[0_0_30px_rgba(255,255,255,0.05)] scale-[1.02] z-10';
            }

            return (
              <motion.button 
                key={stat.status} 
                onClick={() => {
                  setStatusFilter(stat.status);
                  setPage(1);
                }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className={`relative text-left overflow-hidden flex flex-col p-5 rounded-2xl border transition-all duration-300 backdrop-blur-sm ${containerBgClass}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <stat.icon className={`w-4 h-4 ${stat.color} ${stat.pulse ? 'animate-spin' : ''}`} />
                  <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${isActive ? 'text-zinc-300' : 'text-zinc-600'}`}>Status</span>
                </div>
                <span className="text-3xl font-mono font-black text-white mb-1 leading-none">{stat.value}</span>
                <span className={`text-[10px] font-bold uppercase tracking-wider ${stat.color} ${isActive ? 'opacity-100' : 'opacity-80'}`}>{stat.label}</span>
                {stat.pulse && <div className="absolute top-0 right-0 w-1 h-full bg-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.5)]" />}
                {isActive && <div className="absolute bottom-0 left-0 w-full h-1 bg-primary-500 shadow-[0_0_15px_rgba(var(--primary-color),0.5)]" />}
              </motion.button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1">
        {(() => {
          if (!isJobsLoaded && jobs.length === 0) {
            return (
              <div className="flex items-center justify-center py-20">
                <RefreshCw className="w-10 h-10 text-primary-500 animate-spin opacity-20" />
              </div>
            );
          }
          if (enrichedJobs.length === 0) {
            return (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-32 text-center bg-zinc-900/20 border border-dashed border-white/5 rounded-3xl"
              >
                <div className="w-20 h-20 rounded-full bg-zinc-900 border border-white/5 flex items-center justify-center mb-6 shadow-2xl">
                  <Search className="w-10 h-10 text-zinc-800" />
                </div>
                <h3 className="text-zinc-200 font-bold text-xl mb-2">Nenhuma tarefa encontrada</h3>
                <p className="text-zinc-500 text-sm max-w-sm mx-auto leading-relaxed">Tente ajustar seus filtros para encontrar o que procura.</p>
              </motion.div>
            );
          }
          return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 pb-10 mt-6">
              {enrichedJobs.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          );
        })()}
      </div>

      {isJobsLoaded && enrichedJobs.length > 0 && (
        <div className="mt-auto pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
              <span className="text-[10px] text-zinc-500 font-black uppercase tracking-widest">Live Updates Ativos</span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 p-1 bg-zinc-950 rounded-xl border border-white/5">
                <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page === 1}
                    className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-white disabled:opacity-20 transition-all"
                >
                  <ChevronLeft className="w-4 h-4"/>
                </button>
                <div className="text-[11px] font-black px-3 text-zinc-400">
                  {page} <span className="mx-1 text-zinc-700">/</span> {totalPages}
                </div>
                <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page === totalPages}
                    className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-500 hover:text-white disabled:opacity-20 transition-all"
                >
                  <ChevronRight className="w-4 h-4"/>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ContentSourcesView() {
  const { 
    setCurrentView, 
    setSelectedSourceIdForDb, 
    sources = [], 
    isSourcesLoaded, 
    selectedSubjects, 
    setSelectedSubjects,
    subjects,
    setIsAddModalOpen,
    sourceTypes,
    refreshSources,
    addToast
  } = useAppContext();
  
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [appliedSearchQuery, setAppliedSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isSyncing, setIsSyncing] = useState(false);

  const filteredSources = React.useMemo(() => {
    let result = sources;

    // Filter by subject context (Multi select)
    if (selectedSubjects.length > 0) {
      const selectedIds = selectedSubjects.map(s => s.id);
      result = result.filter(src => src.subjectId && selectedIds.includes(src.subjectId));
    }
    
    if (typeFilter !== 'all') {
      result = result.filter(src => src.type === typeFilter);
    }
    
    if (appliedSearchQuery.trim()) {
      const query = appliedSearchQuery.toLowerCase().trim();
      result = result.filter(src => 
        src.title.toLowerCase().includes(query) || 
        src.origin?.toLowerCase().includes(query)
      );
    }
    
    return result;
  }, [sources, selectedSubjects, typeFilter, appliedSearchQuery]);

  const handleSearchSubmit = () => {
    setAppliedSearchQuery(searchQuery);
    setPage(1);
  };

  const handleTypeChange = (newType: string) => {
    setTypeFilter(newType);
    setPage(1);
  };

  const handleRowClick = (source: ContentSource) => {
    setSelectedSourceIdForDb?.(source.id);
    setCurrentView?.('database');
  };

  const selectSubject = (subject: any) => {
    setSelectedSubjects([subject]);
  };

  return (
    <div className="h-full flex overflow-hidden">
      {/* 🟢 MAIN LIST AREA */}
      <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col">
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-8 h-full flex flex-col"
        >
          {/* Header — same pattern as DiarizationList */}
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                <Database className="w-7 h-7 text-emerald-400" />
              </div>
              <div>
                <h2 className="text-3xl font-black text-white tracking-tight leading-none">{t('sources.title')}</h2>
                <p className="text-zinc-500 text-sm mt-2 font-medium">{t('sources.subtitle.view')}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative group/search">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within/search:text-emerald-500 transition-colors" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setAppliedSearchQuery(e.target.value);
                    setPage(1);
                  }}
                  placeholder={`${t('common.actions.search')}...`}
                  className="w-48 pl-9 pr-3 py-1.5 bg-zinc-900 border border-white/5 rounded-lg text-sm text-zinc-300 focus:outline-none focus:border-emerald-500/30 transition-all font-medium"
                />
              </div>

              <div className="relative">
                <Filter className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                <select
                  value={typeFilter}
                  onChange={(e) => handleTypeChange(e.target.value)}
                  className="appearance-none pl-8 pr-8 py-1.5 bg-zinc-900 border border-white/5 rounded-lg text-sm text-zinc-300 focus:outline-none focus:border-emerald-500/30 transition-all font-medium cursor-pointer"
                >
                  <option value="all">{t('sources.table.types.all')}</option>
                  {(sourceTypes || []).map(type => (
                    <option key={type} value={type}>
                      {t(`ingestion.sources.${type.toLowerCase()}`, { defaultValue: type })}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={async () => {
                   if (isSyncing) return;
                   setIsSyncing(true);
                   try {
                     await refreshSources?.();
                     addToast(t('notifications.sync.success'), 'success');
                   } catch (err) {
                     console.error('[ContentSourcesView] Sync failed:', err);
                     addToast(t('notifications.sync.error'), 'error');
                   } finally {
                     setIsSyncing(false);
                   }
                }}
                disabled={isSyncing}
                className="group flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-zinc-300 bg-zinc-900 border border-white/5 rounded-lg hover:bg-zinc-800 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title={t('common.actions.sync')}
              >
                <RefreshCw className={`w-4 h-4 transition-transform duration-500 ${isSyncing ? 'animate-spin text-emerald-400' : 'group-hover:rotate-180'}`} />
              </button>

              <button
                onClick={() => setIsAddModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl font-black uppercase text-[10px] tracking-widest transition-all bg-emerald-500 text-black hover:bg-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]"
              >
                <Plus className="w-4 h-4 stroke-[3px]" />
                {t('sources.add_btn')}
              </button>
            </div>
          </div>

          {/* Table Card */}
          {!isSourcesLoaded && sources.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-zinc-500">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em]">{t('sources.loading')}</span>
            </div>
          ) : (
            <SourcesTable 
              sources={filteredSources.slice((page - 1) * pageSize, page * pageSize)} 
              totalCount={filteredSources.length}
              page={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onRowClick={handleRowClick}
              searchQuery={searchQuery}
              onSearchChange={(q) => {
                setSearchQuery(q);
                setAppliedSearchQuery(q);
                setPage(1);
              }}
              onSearchSubmit={handleSearchSubmit}
              typeFilter={typeFilter}
              onTypeFilterChange={handleTypeChange}
              emptyMessage="Nenhuma fonte encontrada nesta base ou com esses filtros."
            />
          )}
        </motion.div>
      </div>
    </div>
  );
}

// --- Main Layout ---
function MainContent() {
  const { currentView, isAddModalOpen, setIsAddModalOpen, isAddSubjectModalOpen, setIsAddSubjectModalOpen, addToast, selectedSubjects } = useAppContext();
  const { isAuthEnabled, isAuthenticated, isLoading, login } = useAuth();
  const { t } = useTranslation();

  const loginAttempted = React.useRef(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && !isAuthenticated && !loginAttempted.current) {
      loginAttempted.current = true;
      globalThis.history.replaceState({}, document.title, globalThis.location.pathname);
      login(code, state || undefined).then(() => {
        addToast(t('auth.login_success', 'Login successful!'), 'success');
      }).catch((err) => {
        console.error('Login error:', err);
        addToast(t('auth.login_error', 'Login failed. Please try again.'), 'error');
      });
    }
  }, [isAuthenticated, login, addToast, t]);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-bg-dark">
        <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
      </div>
    );
  }

  const showLogin = isAuthEnabled && !isAuthenticated;

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-bg-dark relative">
      <LoginModal isOpen={showLogin} />
      
      {/* Header (Minimalist) */}
      <header className="h-20 border-b border-border-subtle flex items-center justify-between px-8 bg-[#121212]/30 backdrop-blur-xl z-30 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-primary-600 to-primary-400 rotate-12 flex items-center justify-center shadow-lg shadow-primary-500/20 group hover:rotate-0 transition-transform duration-500">
             <LayoutGrid size={16} className="text-black" />
          </div>
          <span className="text-[10px] font-black uppercase tracking-[0.3em] text-zinc-500">
            {t('sidebar.brand.title')} / {t(`sidebar.operations.${currentView}`, { defaultValue: currentView })}
          </span>
        </div>
        
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setIsAddModalOpen(true)}
            disabled={selectedSubjects.length === 0}
            className={`group flex items-center gap-3 px-5 py-2 text-xs font-black uppercase tracking-widest transition-all border rounded-xl ${selectedSubjects.length === 0 ? 'bg-zinc-900 text-zinc-600 border-white/5 cursor-not-allowed opacity-50' : 'text-white bg-zinc-900 border-white/10 hover:bg-primary-500 hover:text-black hover:border-primary-400'}`}
            title={selectedSubjects.length === 0 ? t('common.hints.select_subject') : ''}
          >
            <Plus className="w-4 h-4 transition-transform duration-300 group-hover:rotate-90" />
            {t('common.actions.addData')}
          </button>
        </div>
      </header>

      {/* View Router */}
      <main className="flex-1 overflow-hidden relative flex">
        <div className="flex-1 h-full min-w-0 overflow-y-auto">
          <ErrorBoundary>
            {currentView === 'activity' && <ActivityMonitorView />}
            {currentView === 'queue' && <QueueMonitorView />}
            {currentView === 'sources' && <ContentSourcesView />}

            {currentView === 'chat' && <ChatView />}
            {currentView === 'search' && <SearchView />}
            {currentView === 'database' && <ChunksViewer />}
            {currentView === 'knowledge_contexts' && <KnowledgeAdminView />}
            {currentView === 'diarization' && <DiarizationView/>}
            {currentView === 'voice_profiles' && <VoiceProfilesView />}
            {currentView === 'duplicates' && <DuplicatesView />}
          </ErrorBoundary>
        </div>
        
        {/* Global Ecosystem Sidebar for Data operations */}
        {['sources', 'duplicates', 'diarization'].includes(currentView) && (
          <SidebarContext />
        )}
      </main>

      <AddContentModal 
        isOpen={isAddModalOpen} 
        onClose={() => setIsAddModalOpen(false)} 
      />
      <AddSubjectModal 
        isOpen={isAddSubjectModalOpen} 
        onClose={() => setIsAddSubjectModalOpen(false)} 
      />
      <ToastContainer />
    </div>
  );
}

function AppShell() {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-bg-dark">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
          <p className="text-zinc-500 font-medium text-sm animate-pulse tracking-widest uppercase">Initializing Secure Session...</p>
        </div>
      </div>
    );
  }

  return (
    <AppProvider>
      <div className="flex h-screen w-full bg-bg-dark text-zinc-200 font-sans selection:bg-primary-500/30">
        <Sidebar />
        <MainContent />
      </div>
    </AppProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
