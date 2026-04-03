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
  XCircle
} from 'lucide-react';
import {motion} from 'motion/react';
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
import {KnowledgeAdminView} from './components/KnowledgeAdminView';
import {ErrorBoundary} from './components/ErrorBoundary';
import {ContentSource} from './types';

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
    setJobPageSize: setPageSize,
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

  // With server-side pagination, enrichedJobs is already filtered and paginated
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

  const statConfig: {
    label: string,
    value: number,
    color: string,
    icon: any,
    bg: string,
    pulse?: boolean,
    status: string
  }[] = [
    { label: t('activity.stats.total'), value: stats.total, color: 'text-zinc-400', icon: Database, bg: 'bg-zinc-400/5', status: 'all' },
    { label: t('activity.stats.active'), value: stats.processing, color: 'text-amber-400', icon: Loader2, bg: 'bg-amber-400/5', pulse: stats.processing > 0, status: 'processing' },
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
      {/* Header & Bento Stats */}
      <div className="mb-10 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
              <ActivityIcon className="w-7 h-7 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-3xl font-black text-white tracking-tight leading-none">{t('activity.title')}</h2>
              <p className="text-zinc-500 text-sm mt-2 font-medium">{t('activity.subtitle')}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="relative group/search">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-zinc-500 group-focus-within/search:text-emerald-500 transition-colors" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                placeholder={t('activity.search_placeholder') || 'Search tasks...'}
                className="block w-full md:w-64 pl-9 pr-3 py-1.5 bg-zinc-900 border border-white/5 rounded-lg text-sm text-zinc-300 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500/30 transition-all"
              />
            </div>
             <button 
                onClick={handleRefresh}
                disabled={isSyncing}
                className="group flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-zinc-300 bg-zinc-900 border border-white/5 rounded-lg hover:bg-zinc-800 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <RefreshCw className={`w-4 h-4 transition-transform duration-500 ${isSyncing ? 'animate-spin text-emerald-400' : 'group-hover:rotate-180'}`} />
                {isSyncing ? t('common.actions.syncing') : t('common.actions.sync')}
              </button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {statConfig.map((stat, i) => {
            const isActive = statusFilter === stat.status;
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
                className={`relative text-left overflow-hidden flex flex-col p-5 rounded-2xl border transition-all duration-300 backdrop-blur-sm ${
                  isActive 
                    ? 'bg-zinc-800 border-white/20 shadow-[0_0_30px_rgba(255,255,255,0.05)] scale-[1.02] z-10' 
                    : `bg-zinc-900/40 border-white/5 border hover:border-white/10 hover:bg-zinc-900/60 ${stat.bg}`
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <stat.icon className={`w-4 h-4 ${stat.color} ${stat.pulse ? 'animate-spin' : ''}`} />
                  <span className={`text-[10px] font-black uppercase tracking-[0.2em] ${isActive ? 'text-zinc-300' : 'text-zinc-600'}`}>{t('activity.stats.metric')}</span>
                </div>
                <span className="text-3xl font-mono font-black text-white mb-1 leading-none">{stat.value}</span>
                <span className={`text-[10px] font-bold uppercase tracking-wider ${stat.color} ${isActive ? 'opacity-100' : 'opacity-80'}`}>{stat.label}</span>
                {stat.pulse && <div className="absolute top-0 right-0 w-1 h-full bg-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.5)]" />}
                {isActive && <div className="absolute bottom-0 left-0 w-full h-1 bg-emerald-500 shadow-[0_0_15px_rgba(16,185,129,0.5)]" />}
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
                <RefreshCw className="w-10 h-10 text-emerald-500 animate-spin opacity-20" />
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
                <h3 className="text-zinc-200 font-bold text-xl mb-2">{t('activity.no_results')}</h3>
                <p className="text-zinc-500 text-sm max-w-sm mx-auto leading-relaxed">{t('activity.no_results_desc')}</p>
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

      {/* Pagination Footer */}
      {isJobsLoaded && enrichedJobs.length > 0 && (
        <div className="mt-auto pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] text-zinc-500 font-black uppercase tracking-widest">
                {t('activity.status.live')}
              </span>
            </div>

            <div className="hidden lg:flex items-center gap-3 border-l border-white/5 pl-6">
              <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest whitespace-nowrap">Rows per page</span>
              <div className="flex items-center gap-1 bg-zinc-950 rounded-xl p-0.5 border border-white/5">
                {[12, 24, 48, 96].map((size) => (
                  <button
                    key={size}
                    onClick={() => {
                      setPageSize(size);
                      setPage(1);
                    }}
                    className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-all duration-300 ${
                      pageSize === size 
                        ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' 
                        : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <span className="text-[11px] text-zinc-500 font-medium">
              {t('activity.pagination', { 
                start: (page - 1) * pageSize + 1,
                end: Math.min(page * pageSize, totalJobs),
                total: totalJobs 
              })}
            </span>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-2 py-1 bg-zinc-950 rounded-xl border border-white/5">
                <span
                    className="text-[10px] uppercase tracking-wider font-bold text-zinc-600 pl-1">{t('common.pagination.page_size') || 'Size'}:</span>
                <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setPage(1);
                    }}
                    className="bg-transparent text-[11px] font-black text-emerald-500 focus:outline-none cursor-pointer pr-1"
                >
                  {[12, 24, 48, 96].map(size => (
                      <option key={size} value={size} className="bg-zinc-900 text-white font-sans">{size}</option>
                  ))}
                </select>
              </div>

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
  const { setCurrentView, setSelectedSourceIdForDb, sources = [], isSourcesLoaded, refreshSources, selectedSubjects, addToast } = useAppContext();
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [appliedSearchQuery, setAppliedSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [isSyncing, setIsSyncing] = useState(false);
  const [pageSize, setPageSize] = useState(10);

  const filteredSources = React.useMemo(() => {
    // 0. Base filter: Only show 'done' status
     let result = sources;

    // 1. Filter by subject context
    if (selectedSubjects.length > 0) {
      const selectedIds = new Set(selectedSubjects.map(s => s.id));
      result = result.filter(src => selectedIds.has(src.subjectId));
    }
    
    // 2. Filter by source type
    if (typeFilter !== 'all') {
      result = result.filter(src => src.type === typeFilter);
    }
    
    // 3. Filter by search query (only when applied)
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
    setPage(1); // Reset to first page on new search
  };

  const handleTypeChange = (newType: string) => {
    setTypeFilter(newType);
    setPage(1);
  };

  const handleRowClick = (source: ContentSource) => {
    setSelectedSourceIdForDb?.(source.id);
    setCurrentView?.('database');
  };

  const handleRefresh = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    try {
      await refreshSources?.();
      addToast(t('notifications.sync.success'), 'success');
    } catch (err) {
      console.error('[ContentSources] Sync failed:', err);
      addToast(t('notifications.sync.error'), 'error');
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="p-8 max-w-6xl mx-auto h-full flex flex-col"
    >
      <div className="mb-8 flex justify-between items-center">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
        >
        <div className="flex items-center gap-3">
          <Database className="w-10 h-10 text-emerald-500" />
          <h2 className="text-2xl font-bold text-white tracking-tight">{t('sources.title')}</h2>
        </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-zinc-400">
              {selectedSubjects.length > 0 
                ? t('sources.subtitle.multiple', { count: selectedSubjects.length })
                : t('sources.subtitle.all')}
            </span>
            {selectedSubjects.length > 0 && (
              <div className="flex gap-1 overflow-hidden max-w-md">
                {selectedSubjects.map(s => (
                  <span key={s.id} className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded truncate">
                    {s.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        </motion.div>

        <motion.button 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          onClick={handleRefresh}
          disabled={isSyncing}
          className="group flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-zinc-300 bg-panel-bg border border-border-subtle rounded-lg hover:bg-panel-hover hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 transition-transform duration-500 ${isSyncing ? 'animate-spin text-emerald-400' : 'group-hover:rotate-180'}`} />
          {isSyncing ? t('common.actions.syncing') : t('common.actions.sync')}
        </motion.button>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="flex-1 min-h-0 flex flex-col"
      >
        {!isSourcesLoaded && sources.length === 0 ? (
          <div className="flex items-center gap-3 text-zinc-500 text-sm">
            <RefreshCw className="w-4 h-4 animate-spin text-emerald-500" />
            {t('activity.loading')}
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
            onSearchChange={setSearchQuery}
            onSearchSubmit={handleSearchSubmit}
            typeFilter={typeFilter}
            onTypeFilterChange={handleTypeChange}
            onPageSizeChange={setPageSize}
            emptyMessage={appliedSearchQuery || typeFilter !== 'all' ? undefined : t('chat.locked.description')}
          />
        )}
      </motion.div>
    </motion.div>
  );
}

// --- Main Layout ---
function MainContent() {
  const { currentView, selectedSubjects, isAddModalOpen, setIsAddModalOpen, isAddSubjectModalOpen, setIsAddSubjectModalOpen, addToast } = useAppContext();
  const { isAuthEnabled, isAuthenticated, isLoading, login } = useAuth();
  const { t } = useTranslation();

  const loginAttempted = React.useRef(false);

  // Handle OAuth Callback
  useEffect(() => {
    const urlParams = new URLSearchParams(globalThis.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && !isAuthenticated && !loginAttempted.current) {
      loginAttempted.current = true;
      
      // Prevent infinite loops on failure by clearing the URL immediately
      globalThis.history.replaceState({}, document.title, globalThis.location.pathname);
      
      login(code, state || undefined).then(() => {
        addToast(t('auth.login_success', 'Login successful!'), 'success');
      }).catch((err) => {
        console.error('Login error:', err);
        // Do not reset loginAttempted.current. If they want to retry, they must click "Login" again.
        addToast(t('auth.login_error', 'Login failed. Please try again.'), 'error');
      });
    }
  }, [isAuthenticated, login, addToast, t]);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-bg-dark">
        <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
      </div>
    );
  }

  const showLogin = isAuthEnabled && !isAuthenticated;

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-bg-dark relative">
      <LoginModal isOpen={showLogin} />
      {/* Topbar Context Indicator & Global Actions */}
      <header className="h-14 border-b border-border-subtle flex items-center justify-between px-6 bg-black/20 backdrop-blur-sm">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-zinc-500">{t('sidebar.contexts.title')}:</span>
          <span className="text-emerald-400 font-medium px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
            {(() => {
              if (selectedSubjects.length === 1) return selectedSubjects[0].name;
              if (selectedSubjects.length > 1) return `${selectedSubjects.length} ${t('sidebar.contexts.title')}`;
              return t('sidebar.contexts.none');
            })()}
          </span>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsAddModalOpen(true)}
            className="group flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-black bg-emerald-500 rounded-lg hover:bg-emerald-400 transition-colors shadow-[0_0_15px_rgba(16,185,129,0.2)]"
          >
            <Plus className="w-4 h-4 transition-transform duration-300 group-hover:rotate-90" />
            {t('common.actions.addData')}
          </button>
        </div>
      </header>

      {/* View Router */}
      <main className="flex-1 overflow-auto relative">
        <ErrorBoundary>
          {currentView === 'activity' && <ActivityMonitorView />}
          {currentView === 'sources' && <ContentSourcesView />}
          {currentView === 'chat' && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-2xl mx-auto h-full">
              <div className="w-20 h-20 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(16,185,129,0.1)]">
                <span className="text-3xl">🚀</span>
              </div>
              <h2 className="text-2xl font-bold mb-3 bg-gradient-to-r from-emerald-400 to-teal-500 bg-clip-text text-transparent">
                {t('chat.locked.title')}
              </h2>
              <p className="text-zinc-400 text-lg mb-8 leading-relaxed">
                {t('chat.locked.description')}
              </p>
              <button 
                onClick={() => setIsAddModalOpen(true)}
                className="group flex items-center gap-3 px-8 py-3.5 text-base font-bold text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_25px_rgba(16,185,129,0.3)] active:scale-95 border border-emerald-400/20"
              >
                <Plus className="w-5 h-5 transition-transform duration-300 group-hover:rotate-90" />
                {t('common.actions.addData')}
              </button>
            </div>
          )}
          {currentView === 'search' && <SearchView />}
          {currentView === 'database' && <ChunksViewer />}
          {currentView === 'knowledge_contexts' && <KnowledgeAdminView />}
        </ErrorBoundary>
      </main>

      {/* Modals & Overlays */}
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
          <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
          <p className="text-zinc-500 font-medium text-sm animate-pulse tracking-widest uppercase">Initializing Secure Session...</p>
        </div>
      </div>
    );
  }

  return (
    <AppProvider>
      <div className="flex h-screen w-full bg-bg-dark text-zinc-200 font-sans selection:bg-emerald-500/30">
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
