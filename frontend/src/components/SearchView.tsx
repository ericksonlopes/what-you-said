import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Search, Sparkles, Lock, FileText,
  SlidersHorizontal, Database, TextSearch, Network, ListOrdered, 
  ChevronDown, X, Copy, Check, Languages, Cpu, Hash, Calendar, 
  Clock, ArrowUpDown, SquarePlay, BookOpen, Globe, Filter, Newspaper, Loader2,
  Layers
} from 'lucide-react';
import { useAppContext } from '../store/AppContext';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';

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
    case 'youtube': return SquarePlay;
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

const renderContextBadge = (selectedSubjects: any[], t: any) => {
  if (!selectedSubjects || selectedSubjects.length === 0) {
    return <span className="text-red-400 font-medium whitespace-nowrap">{t('sidebar.contexts.none')}</span>;
  }
  if (selectedSubjects.length <= 2) {
    return selectedSubjects.map(s => (
      <span key={s.id} className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs truncate max-w-[180px]" title={s.name}>
        {s.name}
      </span>
    ));
  }
  return (
    <span className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs whitespace-nowrap">
      {selectedSubjects.length} {t('sidebar.contexts.title')}
    </span>
  );
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
  const [searchMode, setSearchMode] = useState<'semantic' | 'bm25' | 'hybrid'>('hybrid');
  const [useRerank, setUseRerank] = useState(true);

  const sourceMap = React.useMemo(() => {
    const map = new Map<string, string>();
    // Map by origin (external_source / video ID) to title
    sources.forEach(s => {
      if (s.origin) map.set(s.origin, s.title);
    });
    return map;
  }, [sources]);

  const runSearch = useCallback(async (currentQuery: string, currentMode: string, currentUseRerank: boolean) => {
    if (!currentQuery.trim() || selectedSubjects.length === 0) return;

    setIsSearching(true);
    setHasSearched(true);
    setResults([]);

    try {
      const subjectId = selectedSubjects.length > 0 ? selectedSubjects[0].id : undefined;
      const data = await api.search(currentQuery, topK, subjectId, currentMode, currentUseRerank);

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
  }, [selectedSubjects, topK, sourceMap, t]);

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
      {/* Header & Search Bar */}
      <div className="p-8 pb-4 max-w-5xl mx-auto w-full flex-shrink-0">
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="mb-8 text-center"
        >
          <h2 className="text-3xl font-bold text-white tracking-tight mb-3">{t('search.title')}</h2>
          <p className="text-zinc-400">
            {t('search.subtitle')}
          </p>
        </motion.div>

        <motion.form 
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          onSubmit={handleSearch} 
          className="relative max-w-4xl mx-auto"
        >
          <div className="relative flex items-center bg-zinc-900/60 backdrop-blur-xl border border-white/10 hover:border-white/20 focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10 rounded-2xl shadow-2xl transition-all p-2">
            <Search className="w-6 h-6 text-zinc-400 ml-4" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('search.placeholder')}
              className="w-full bg-transparent text-xl text-zinc-100 placeholder:text-zinc-600 px-5 py-4 focus:outline-none font-sans"
            />
            <button
              type="submit"
              disabled={!query.trim() || isSearching || selectedSubjects.length === 0}
              className="group px-8 py-4 bg-emerald-500 text-black font-bold rounded-xl hover:bg-emerald-400 disabled:opacity-50 disabled:hover:bg-emerald-500 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] active:scale-95 flex items-center gap-3 uppercase tracking-wider text-sm"
            >
              {isSearching ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Search className="w-5 h-5 transition-transform group-hover:scale-110" />
              )}
              {isSearching ? t('common.actions.syncing') : t('common.actions.search')}
            </button>
          </div>
        </motion.form>

        {/* Search Controls */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="max-w-4xl mx-auto mt-6 flex flex-wrap items-center justify-between gap-4"
        >
          <div className="flex items-center gap-2 text-sm min-w-0 flex-1">
            <Database className="w-4 h-4 text-zinc-500 flex-shrink-0" />
            <span className="text-zinc-400 whitespace-nowrap flex-shrink-0">{t('search.results.source')}:</span>
            <div className="flex gap-1.5 flex-nowrap overflow-hidden min-w-0">
              {renderContextBadge(selectedSubjects, t)}
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Top K Selector */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsTopKOpen(!isTopKOpen)}
                onBlur={() => setTimeout(() => setIsTopKOpen(false), 150)}
                className="flex items-center gap-2 bg-zinc-900/80 border border-zinc-800 hover:border-zinc-700 rounded-lg p-1.5 px-3 h-[34px] transition-colors"
              >
                <ListOrdered className="w-3.5 h-3.5 text-zinc-500" />
                <span className="text-xs text-zinc-400 font-medium">{t('search.options.topKn')}:</span>
                <span className="text-xs text-zinc-200 font-medium w-4 text-left">{topK}</span>
                <ChevronDown className={`w-3.5 h-3.5 text-zinc-500 transition-transform duration-200 ${isTopKOpen ? 'rotate-180' : ''}`} />
              </button>
              
              <AnimatePresence>
                {isTopKOpen && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    transition={{ duration: 0.1 }}
                    className="absolute top-full right-0 mt-1 w-24 bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl overflow-hidden z-20"
                  >
                    {[3, 5, 10, 20, 50].map((val) => (
                      <button
                        key={val}
                        onClick={() => {
                          setTopK(val);
                          setIsTopKOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2 text-xs transition-colors ${
                          topK === val 
                            ? 'bg-emerald-500/10 text-emerald-400 font-medium' 
                            : 'text-zinc-300 hover:bg-zinc-800/80 hover:text-white'
                        }`}
                      >
                        {val}
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Re-rank Toggle */}
            <button
              type="button"
              onClick={() => setUseRerank(!useRerank)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border flex-shrink-0 ${
                useRerank 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]' 
                  : 'bg-zinc-900/80 text-zinc-500 border-zinc-800 hover:border-zinc-700 hover:text-zinc-300'
              }`}
              title={t('search.options.rerank')}
            >
              <ArrowUpDown className="w-3.5 h-3.5" />
              {t('common.actions.filter')} {useRerank ? 'ON' : 'OFF'}
            </button>

            {/* Search Mode Toggle */}
            <div className="flex flex-nowrap items-center gap-1 bg-zinc-900/80 border border-zinc-800 rounded-lg p-1 flex-shrink-0">
            {/* Semantic */}
            <button
              type="button"
              onClick={() => setSearchMode('semantic')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap ${
                searchMode === 'semantic'
                  ? 'bg-zinc-800 text-emerald-400 shadow-sm border border-zinc-700/50'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              {t('search.modes.semantic')}
            </button>

            {/* Keyword (BM25) */}
            <button
              type="button"
              onClick={() => setSearchMode('bm25')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap ${
                searchMode === 'bm25'
                  ? 'bg-zinc-800 text-sky-400 shadow-sm border border-zinc-700/50'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <TextSearch className="w-3.5 h-3.5" />
              {t('search.modes.bm25')}
            </button>

            {/* Hybrid */}
            <button
              type="button"
              onClick={() => setSearchMode('hybrid')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all whitespace-nowrap ${
                searchMode === 'hybrid'
                  ? 'bg-zinc-800 text-violet-400 shadow-sm border border-zinc-700/50'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              {t('search.modes.hybrid')}
            </button>

            {/* MMR (Disabled — needs dedicated implementation) */}
            <div className="relative group">
              <button 
                disabled
                className="flex items-center gap-2 px-3 py-1.5 rounded-md text-zinc-500 text-xs font-medium cursor-not-allowed opacity-70 whitespace-nowrap"
              >
                <Network className="w-3.5 h-3.5" />
                MMR
                <Lock className="w-3 h-3 ml-1" />
              </button>
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-zinc-800 border border-zinc-700 rounded-lg text-[10px] text-zinc-300 text-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none shadow-xl z-10">
                {t('ingestion.coming_soon.title')} (MMR)
              </div>
            </div>
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
