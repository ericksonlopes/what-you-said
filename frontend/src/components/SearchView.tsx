import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Search, Sparkles, FileText,
  SlidersHorizontal, Database, TextSearch, Network, ListOrdered, 
  ChevronDown, X, Copy, Check, Languages, Cpu, Hash, Calendar, 
  Clock, ArrowUpDown, SquarePlay, BookOpen, Globe, Filter, Newspaper, Loader2,
  Layers
} from 'lucide-react';
import { useAppContext } from '../store/AppContext';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';
import { SubjectIcon } from './SubjectIcon';

// --- Types ---
interface SearchResult {
  id: string;
  source: string;
  text: string;
  score: number;
  index?: number;
  timestamp?: string;
  type: string;
  context: string;
  tokensCount?: number;
  language?: string;
  embeddingModel?: string;
  createdAt?: string;
  sourceType?: string;
}

const getIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case 'youtube': 
    case 'video': return SquarePlay;
    case 'article': return Newspaper;
    case 'pdf': return FileText;
    case 'wikipedia': return BookOpen;
    case 'web': return Globe;
    default: return Filter;
  }
};
const getModeStyles = (mode: string) => {
  if (mode === 'bm25') return { bgClass: 'bg-sky-400', textClass: 'text-sky-400' };
  if (mode === 'hybrid') return { bgClass: 'bg-violet-400', textClass: 'text-violet-400' };
  return { bgClass: 'bg-emerald-500', textClass: 'text-emerald-400' };
};

const getModeLabelForScore = (mode: string, score: number, t: any) => {
  if (mode === 'bm25') return `BM25: ${score.toFixed(2)}`;
  if (mode === 'hybrid') return `${(score * 100).toFixed(1)}% ${t('search.results.hybrid_label')}`;
  return `${(score * 100).toFixed(1)}% ${t('search.results.match')}`;
};

const getModalModeLabelForScore = (mode: string, score: number) => {
  if (mode === 'bm25') return `BM25: ${score.toFixed(2)}`;
  if (mode === 'hybrid') return `${(score * 100).toFixed(1)}% HYBRID`;
  return `${(score * 100).toFixed(1)}% MATCH`;
};

export function SearchView() {
  const { subjects, selectedSubjects, sources } = useAppContext();
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [topK, setTopK] = useState(5);
  const [isTopKOpen, setIsTopKOpen] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [searchMode, setSearchMode] = useState<'semantic' | 'bm25' | 'hybrid'>('semantic');
  const [useRerank, setUseRerank] = useState(true);
  // Local context selection (independent from sidebar). Empty array + searchAll=true => search across all contexts.
  const [searchSubjectIds, setSearchSubjectIds] = useState<string[]>(() => selectedSubjects.map(s => s.id));
  const [searchAll, setSearchAll] = useState<boolean>(true);
  const [isContextsOpen, setIsContextsOpen] = useState(false);
  const [contextsFilter, setContextsFilter] = useState('');
  const contextsRef = React.useRef<HTMLDivElement>(null);

  const filteredSubjects = React.useMemo(
    () => subjects.filter(s => s.name.toLowerCase().includes(contextsFilter.toLowerCase())),
    [subjects, contextsFilter]
  );

  // Close contexts popover on click outside
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (contextsRef.current && !contextsRef.current.contains(e.target as Node)) {
        setIsContextsOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const contextsLabel = searchAll
    ? t('sidebar.contexts.title_all')
    : searchSubjectIds.length === 0
      ? t('sidebar.contexts.none')
      : searchSubjectIds.length === 1
        ? subjects.find(s => s.id === searchSubjectIds[0])?.name || t('common.selected_one')
        : t('common.selected', { count: searchSubjectIds.length });

  const sourceMap = React.useMemo(() => {
    const map = new Map<string, string>();
    // Map by origin (external_source / video ID) to title
    sources.forEach(s => {
      if (s.origin) map.set(s.origin, s.title);
    });
    return map;
  }, [sources]);

  const runSearch = useCallback(async (currentQuery: string, currentMode: string, currentUseRerank: boolean) => {
    if (!currentQuery.trim()) return;
    if (!searchAll && searchSubjectIds.length === 0) return;

    setIsSearching(true);
    setHasSearched(true);
    setResults([]);

    try {
      const subjectIds = searchAll ? undefined : searchSubjectIds;
      const data = await api.search(currentQuery, topK, subjectIds, currentMode, currentUseRerank);

      const mappedResults: SearchResult[] = data.results.map((res: any) => {
        // Resolve subject name from local subjects list if extra.subject_name is missing
        const subject = subjects.find(s => s.id === res.subject_id);
        const subjectName = res.extra?.subject_name || subject?.name || t('sidebar.contexts.none');

        return {
          id: res.id,
          source: sourceMap.get(res.external_source) || res.external_source || t('common.status.unknown'),
          text: res.content || '',
          score: res.score || 0,
          index: res.index,
          timestamp: res.extra?.timestamp || '',
          type: res.source_type?.toLowerCase() === 'youtube' ? 'video' : 'article',
          context: subjectName,
          tokensCount: res.tokens_count,
          language: res.language,
          embeddingModel: res.embedding_model,
          createdAt: res.created_at,
          sourceType: res.source_type
        };
      });

      setResults(mappedResults);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setIsSearching(false);
    }
  }, [searchAll, searchSubjectIds, topK, sourceMap, subjects, t]);

  // Re-run search automatically when the mode or useRerank changes (only if a search was already performed)
  useEffect(() => {
    if (hasSearched && query.trim()) {
      runSearch(query, searchMode, useRerank);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchMode, useRerank]);

  const handleSearch = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    runSearch(query, searchMode, useRerank);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="h-full flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="px-8 pt-10 pb-6 max-w-4xl mx-auto w-full flex-shrink-0">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-6"
        >
          <h2 className="text-2xl font-semibold text-white tracking-tight">{t('search.title')}</h2>
          <p className="text-sm text-zinc-500 mt-1">{t('search.subtitle')}</p>
        </motion.div>

        {/* Search Input — pill */}
        <motion.form
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          onSubmit={handleSearch}
          className="relative"
        >
          <div className="group relative flex items-center h-14 bg-zinc-900/60 backdrop-blur-xl border border-white/10 hover:border-white/15 focus-within:border-emerald-500/40 focus-within:ring-4 focus-within:ring-emerald-500/5 rounded-full transition-all pl-5 pr-2">
            <Search className="w-5 h-5 text-zinc-500 flex-shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('search.placeholder')}
              className="w-full bg-transparent text-base text-zinc-100 placeholder:text-zinc-600 px-4 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!query.trim() || isSearching || (!searchAll && searchSubjectIds.length === 0)}
              className="h-10 px-5 bg-emerald-500 text-black text-sm font-semibold rounded-full hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-[0.97] flex items-center gap-2 flex-shrink-0"
            >
              {isSearching ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
              <span>{isSearching ? t('common.actions.syncing') : t('common.actions.search')}</span>
            </button>
          </div>
        </motion.form>

        {/* Toolbar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          className="mt-4 flex items-center gap-2 min-w-0"
        >
          {/* Contexts chip — opens its own popover */}
          <div ref={contextsRef} className="relative">
            <button
              type="button"
              onClick={() => setIsContextsOpen(v => !v)}
              className={`h-9 inline-flex items-center gap-2 px-3 rounded-full text-xs font-medium transition-all ring-1 ${
                searchAll
                  ? 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30 hover:bg-emerald-500/15'
                  : 'bg-white/[0.04] text-zinc-200 ring-white/10 hover:bg-white/[0.07]'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span className="max-w-[200px] truncate">{contextsLabel}</span>
              <ChevronDown className={`w-3.5 h-3.5 opacity-60 transition-transform ${isContextsOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {isContextsOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.96 }}
                  transition={{ duration: 0.12 }}
                  className="absolute top-full left-0 mt-2 w-72 bg-zinc-900/95 backdrop-blur-xl ring-1 ring-white/10 rounded-2xl shadow-2xl overflow-hidden z-30"
                >
                  {/* Search input */}
                  <div className="p-2 border-b border-white/5">
                    <div className="relative">
                      <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                      <input
                        autoFocus
                        type="text"
                        value={contextsFilter}
                        onChange={(e) => setContextsFilter(e.target.value)}
                        placeholder={t('common.actions.search') + '...'}
                        className="w-full h-8 pl-8 pr-2 bg-white/[0.04] ring-1 ring-white/10 rounded-lg text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:ring-emerald-500/30"
                      />
                    </div>
                  </div>
                  <div className="p-1.5">
                    <button
                      onClick={() => { setSearchAll(true); setIsContextsOpen(false); }}
                      className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl text-xs transition-colors ${
                        searchAll ? 'bg-emerald-500/10 text-emerald-300' : 'text-zinc-200 hover:bg-white/5'
                      }`}
                    >
                      <span className="flex items-center gap-2 font-medium">
                        <Database className="w-3.5 h-3.5" />
                        {t('sidebar.contexts.title')} • All
                      </span>
                      {searchAll && <Check className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <div className="h-px bg-white/5" />
                  <div className="max-h-64 overflow-y-auto custom-scrollbar p-1.5">
                    {filteredSubjects.length === 0 ? (
                      <div className="px-3 py-6 text-center text-xs text-zinc-500">{t('sidebar.contexts.none')}</div>
                    ) : (
                      filteredSubjects.map(s => {
                        const checked = !searchAll && searchSubjectIds.includes(s.id);
                        return (
                          <button
                            key={s.id}
                            onClick={() => {
                              setSearchAll(false);
                              setSearchSubjectIds(ids =>
                                ids.includes(s.id) ? ids.filter(i => i !== s.id) : [...ids, s.id]
                              );
                            }}
                            className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl text-xs transition-colors ${
                              checked ? 'bg-white/[0.06] text-zinc-100' : 'text-zinc-300 hover:bg-white/5'
                            }`}
                          >
                            <span className="flex items-center gap-2 min-w-0">
                              <SubjectIcon iconName={s.icon} className="w-3.5 h-3.5" />
                              <span className="truncate">{s.name}</span>
                            </span>
                            <span className={`w-4 h-4 rounded-md flex items-center justify-center flex-shrink-0 ${
                              checked ? 'bg-emerald-500 text-black' : 'ring-1 ring-white/15'
                            }`}>
                              {checked && <Check className="w-3 h-3" strokeWidth={3} />}
                            </span>
                          </button>
                        );
                      })
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* spacer pushes options to the right */}
          <div className="flex-1 min-w-0" />

          {/* Options group */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Top K */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsTopKOpen(!isTopKOpen)}
                onBlur={() => setTimeout(() => setIsTopKOpen(false), 150)}
                className="h-9 inline-flex items-center gap-1.5 px-3 rounded-full text-xs text-zinc-300 bg-white/[0.04] ring-1 ring-white/10 hover:bg-white/[0.07] transition-all"
                title={t('search.options.topKn')}
              >
                <ListOrdered className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
                <span className="font-medium tabular-nums">{topK}</span>
                <ChevronDown className={`w-3 h-3 text-zinc-500 flex-shrink-0 transition-transform ${isTopKOpen ? 'rotate-180' : ''}`} />
              </button>
              <AnimatePresence>
                {isTopKOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -6, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -6, scale: 0.96 }}
                    transition={{ duration: 0.12 }}
                    className="absolute top-full right-0 mt-2 w-28 bg-zinc-900/95 backdrop-blur-xl ring-1 ring-white/10 rounded-xl shadow-2xl overflow-hidden z-20 p-1"
                  >
                    {[3, 5, 10, 20, 50].map((val) => (
                      <button
                        key={val}
                        onClick={() => { setTopK(val); setIsTopKOpen(false); }}
                        className={`w-full text-left px-3 py-1.5 text-xs rounded-lg transition-colors ${
                          topK === val
                            ? 'bg-emerald-500/10 text-emerald-300'
                            : 'text-zinc-300 hover:bg-white/5'
                        }`}
                      >
                        {val} results
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Re-rank — icon toggle */}
            <button
              type="button"
              onClick={() => setUseRerank(!useRerank)}
              title={t('search.options.rerank')}
              aria-pressed={useRerank}
              className={`h-9 w-9 inline-flex items-center justify-center rounded-full transition-all ring-1 ${
                useRerank
                  ? 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30'
                  : 'bg-white/[0.03] text-zinc-500 ring-white/10 hover:bg-white/[0.06] hover:text-zinc-300'
              }`}
            >
              <ArrowUpDown className="w-4 h-4" />
            </button>

            {/* Mode — icon-only segmented control */}
            <div className="h-9 inline-flex items-center p-1 rounded-full bg-white/[0.04] ring-1 ring-white/10">
              {[
                { key: 'semantic', icon: Sparkles, label: t('search.modes.semantic'), color: 'text-emerald-300' },
                { key: 'bm25', icon: TextSearch, label: t('search.modes.bm25'), color: 'text-sky-300' },
                { key: 'hybrid', icon: SlidersHorizontal, label: t('search.modes.hybrid'), color: 'text-violet-300' },
              ].map(({ key, icon: Icon, label, color }) => {
                const active = searchMode === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSearchMode(key as any)}
                    title={label}
                    className={`h-7 inline-flex items-center gap-1.5 px-2.5 rounded-full text-xs font-medium transition-all whitespace-nowrap ${
                      active ? `bg-zinc-800 ${color} shadow-sm` : 'text-zinc-500 hover:text-zinc-300'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                    {label}
                  </button>
                );
              })}
              <button
                type="button"
                disabled
                title={`${t('ingestion.coming_soon.title')} (MMR)`}
                className="h-7 inline-flex items-center gap-1.5 px-2.5 rounded-full text-xs font-medium text-zinc-600 cursor-not-allowed whitespace-nowrap"
              >
                <Network className="w-3.5 h-3.5" />
                MMR
              </button>
            </div>
          </div>
        </motion.div>
      </div>
      {/* Results Area */}
      <div className="flex-1 overflow-y-auto p-8 pt-0 custom-scrollbar">
        <div className="max-w-3xl mx-auto">
          {!hasSearched && !isSearching && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="mt-24 flex flex-col items-center justify-center text-center"
            >
              <div className="w-20 h-20 rounded-full bg-zinc-900/50 border border-white/5 flex items-center justify-center mb-6 shadow-2xl relative overflow-hidden">
                <div className="absolute inset-0 bg-emerald-500/10 blur-xl"></div>
                <Sparkles className="w-8 h-8 text-zinc-500 relative z-10" />
              </div>
              <h3 className="text-xl font-medium text-zinc-200 mb-2 tracking-tight">{t('common.actions.addData')}</h3>
              <p className="text-zinc-500 max-w-sm text-sm leading-relaxed">
                {t('search.subtitle')}
              </p>
            </motion.div>
          )}

          {isSearching && (
            <div className="space-y-6 animate-in fade-in duration-300 mt-6">
              {[1, 2, 3].map(i => (
                <div key={i} className="p-6 rounded-2xl bg-zinc-900/30 border border-white/5 animate-pulse">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-20 h-6 bg-zinc-800/50 rounded-md"></div>
                    <div className="w-32 h-4 bg-zinc-800/50 rounded"></div>
                  </div>
                  <div className="w-3/4 h-6 bg-zinc-800/50 rounded mb-4"></div>
                  <div className="space-y-3">
                    <div className="w-full h-4 bg-zinc-800/50 rounded"></div>
                    <div className="w-5/6 h-4 bg-zinc-800/50 rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!isSearching && hasSearched && results.length > 0 && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6 mt-6"
            >
              <div className="text-xs font-mono text-zinc-500 uppercase tracking-wider mb-6 pb-3 border-b border-white/5 flex justify-between items-center">
                <span>{results.length} {t('search.results.total')}</span>
                <span>{t('search.options.topKn')} {topK}</span>
              </div>
              
              {results.map((result, index) => (
                <motion.div 
                  key={result.id} 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(index * 0.05, 0.3), duration: 0.4, ease: "easeOut" }}
                  onClick={() => setSelectedResult(result)}
                  className="group relative p-6 rounded-2xl bg-zinc-900/40 border border-white/5 hover:border-emerald-500/30 hover:bg-zinc-900/80 transition-all cursor-pointer overflow-hidden shadow-sm hover:shadow-xl"
                >
                  {/* Subtle gradient background on hover */}
                  <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                  
                  <div className="relative z-10">
                    <div className="flex items-start justify-between gap-4 mb-4">
                      <div className="flex items-center gap-3 flex-wrap">
                        <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-950 border border-white/10 shadow-inner">
                          <div className={`w-1.5 h-1.5 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.8)] ${getModeStyles(searchMode).bgClass}`} />
                          <span className={`text-[11px] font-mono font-medium tracking-tight ${getModeStyles(searchMode).textClass}`}>
                            {getModeLabelForScore(searchMode, result.score, t)}
                          </span>
                        </div>
                        {result.language && (
                          <span className="text-[10px] text-zinc-400 bg-zinc-800/50 px-2 py-0.5 rounded border border-zinc-700/50 uppercase font-mono">
                            {result.language}
                          </span>
                        )}
                        {/* Knowledge Context Badge */}
                        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-800/80 border border-zinc-700/50">
                          <Layers className="w-3 h-3 text-emerald-500/70" />
                          <span className="text-[10px] font-bold text-zinc-300 uppercase tracking-widest">{result.context}</span>
                        </div>
                        {result.tokensCount !== undefined && (
                          <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                            <Hash className="w-3 h-3" />
                            {result.tokensCount} tokens
                          </span>
                        )}
                      </div>
                    </div>

                    <h3 className="text-lg font-medium text-zinc-100 mb-3 flex items-center gap-2.5">
                      {React.createElement(getIcon(result.sourceType || ''), { className: "w-5 h-5 text-zinc-500 shrink-0" })}
                      <div className="flex items-center gap-2 min-w-0">
                        {result.index !== undefined && (
                          <span className="text-[10px] bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded border border-emerald-500/20 font-bold font-mono shrink-0">
                            #{result.index + 1}
                          </span>
                        )}
                        <span className="truncate">{result.source}</span>
                      </div>
                      {result.timestamp && (
                        <span className="text-xs font-mono text-zinc-400 bg-white/5 px-2 py-1 rounded-md border border-white/5 ml-2 shrink-0">
                          {result.timestamp}
                        </span>
                      )}
                    </h3>

                    <p className="text-base text-zinc-400 leading-relaxed font-serif italic">
                      "{result.text}"
                    </p>
                    
                    {result.embeddingModel && (
                      <div className="mt-4 pt-4 border-t border-white/5 flex items-center gap-4 text-[10px] text-zinc-600">
                        <span className="flex items-center gap-1.5">
                          <Cpu className="w-3 h-3" />
                          {result.embeddingModel}
                        </span>
                        {result.createdAt && (
                          <span className="flex items-center gap-1.5">
                            <Calendar className="w-3 h-3" />
                            {new Date(result.createdAt).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}

          {!isSearching && hasSearched && results.length === 0 && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="mt-24 flex flex-col items-center justify-center text-center"
            >
              <div className="w-20 h-20 rounded-full bg-zinc-900/50 border border-white/5 flex items-center justify-center mb-6 shadow-2xl">
                <Search className="w-8 h-8 text-zinc-600" />
              </div>
              <h3 className="text-xl font-medium text-zinc-200 mb-2 tracking-tight">{t('search.results.none')}</h3>
              <p className="text-zinc-500 max-w-sm text-sm leading-relaxed">
                {t('search.results.none')}
              </p>
            </motion.div>
          )}
        </div>
      </div>

      {/* Chunk Detail Modal */}
      <AnimatePresence>
        {selectedResult && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedResult(null)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2 }}
              onClick={(e) => e.stopPropagation()}
              className="relative bg-zinc-900 border border-zinc-700/50 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col overflow-hidden"
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between p-5 border-b border-zinc-800">
                <div className="flex items-center gap-3 min-w-0">
                  {React.createElement(getIcon(selectedResult.sourceType || ''), { className: "w-5 h-5 text-emerald-400 flex-shrink-0" })}
                  <div className="flex items-center gap-2 min-w-0">
                    {selectedResult.index !== undefined && (
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-500 px-1.5 py-0.5 rounded border border-emerald-500/20 font-bold font-mono shrink-0">
                        #{selectedResult.index + 1}
                      </span>
                    )}
                    <h3 className="text-lg font-semibold text-white truncate">{selectedResult.source}</h3>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(selectedResult.text);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
                    title={t('common.actions.copy')}
                  >
                    {copied ? <Check className="w-5 h-5 text-emerald-400" /> : <Copy className="w-5 h-5" />}
                  </button>
                  <button 
                    onClick={() => setSelectedResult(null)}
                    className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors flex-shrink-0"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Modal Metadata Sub-header */}
              <div className="flex flex-wrap items-center gap-4 px-5 py-3 border-b border-zinc-800/50 bg-black/20">
                <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-zinc-950 border border-white/10 flex-shrink-0">
                  <div className={`w-1.5 h-1.5 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.8)] ${getModeStyles(searchMode).bgClass}`} />
                  <span className={`text-[11px] font-mono font-medium ${getModeStyles(searchMode).textClass}`}>
                    {getModalModeLabelForScore(searchMode, selectedResult.score)}
                  </span>
                </div>

                {/* Knowledge Context Badge in Modal */}
                <div className="flex items-center gap-2 flex-shrink-0 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-lg">
                  <Layers className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-[11px] font-black text-emerald-400 uppercase tracking-widest">{selectedResult.context}</span>
                </div>
                
                {selectedResult.timestamp && (
                  <div className="flex items-center gap-1.5 text-xs text-zinc-400 font-mono bg-zinc-800/50 px-2.5 py-1 rounded-md flex-shrink-0 border border-zinc-700/50">
                    <Clock className="w-3.5 h-3.5" />
                    {selectedResult.timestamp}
                  </div>
                )}
                {selectedResult.language && (
                  <div className="flex items-center gap-1.5 text-xs text-zinc-400 flex-shrink-0">
                    <Languages className="w-3.5 h-3.5" />
                    {selectedResult.language.toUpperCase()}
                  </div>
                )}
              </div>

              {/* Modal Content */}
              <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-gradient-to-b from-zinc-900 to-zinc-950">
                <div className="max-w-2xl mx-auto">
                  <p className="text-lg text-zinc-200 leading-relaxed whitespace-pre-wrap font-serif italic">
                    "{selectedResult.text}"
                  </p>
                </div>
              </div>

              {/* Detailed Metadata Grid */}
              <div className="p-5 border-t border-zinc-800 bg-zinc-950">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <span className="w-1 h-3 bg-emerald-500 rounded-full" />
                  {t('search.results.metadata')}
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-zinc-600">{t('search.results.type')}</span>
                    <span className="text-xs text-zinc-300 flex items-center gap-1.5 capitalize">
                      {React.createElement(getIcon(selectedResult.sourceType || ''), { className: "w-3.5 h-3.5 text-zinc-500" })}
                      {selectedResult.sourceType?.toLowerCase() || 'Unknown'}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-zinc-600">{t('search.results.knowledge_context')}</span>
                    <span className="text-xs text-zinc-300 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-emerald-500/70" />
                      {selectedResult.context}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-zinc-600">{t('search.results.model')}</span>
                    <span className="text-xs text-zinc-300 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-zinc-500" />
                      {selectedResult.embeddingModel || 'Unknown'}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-zinc-600">{t('search.results.tokens')}</span>
                    <span className="text-xs text-zinc-300 flex items-center gap-1.5">
                      <Hash className="w-3.5 h-3.5 text-zinc-500" />
                      {selectedResult.tokensCount || 'N/A'}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-zinc-600">{t('search.results.date')}</span>
                    <span className="text-xs text-zinc-300 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                      {selectedResult.createdAt ? new Date(selectedResult.createdAt).toLocaleDateString() : 'N/A'}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-zinc-600">{t('search.results.chunk_id')}</span>
                    <span className="text-xs text-zinc-400 font-mono truncate" title={selectedResult.id}>
                      {selectedResult.id.substring(0, 8)}...
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
