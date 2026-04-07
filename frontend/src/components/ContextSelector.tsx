import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Database, ChevronDown, Search, Check, 
  CheckSquare, Square, Plus, Layers, 
  MessageSquare, TextSearch, LayoutGrid,
  Info
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useAppContext } from '../store/AppContext';
import { SubjectIcon } from './SubjectIcon';

export function ContextSelector() {
  const { t } = useTranslation();
  const { 
    subjects, 
    selectedSubjects, 
    toggleSubjectSelection, 
    selectOnlySubject, 
    currentView,
    setIsAddSubjectModalOpen
  } = useAppContext();

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Determine selection mode based on current view
  const isMultiSelect = ['chat', 'search'].includes(currentView);
  
  const filteredSubjects = useMemo(() => 
    subjects.filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase())),
    [subjects, searchQuery]
  );

  const handleToggle = (subject: any) => {
    if (isMultiSelect) {
      toggleSubjectSelection(subject);
    } else {
      selectOnlySubject(subject);
      setIsOpen(false);
    }
  };

  const getActiveViewIcon = () => {
    switch (currentView) {
      case 'chat': return <MessageSquare className="w-3.5 h-3.5" />;
      case 'search': return <TextSearch className="w-3.5 h-3.5" />;
      case 'sources': return <Database className="w-3.5 h-3.5" />;
      default: return <LayoutGrid className="w-3.5 h-3.5" />;
    }
  };

  const selectedLabel = useMemo(() => {
    if (selectedSubjects.length === 1) return selectedSubjects[0].name;
    if (selectedSubjects.length > 1) return `${selectedSubjects.length} ${t('sidebar.contexts.title')}`;
    return t('sidebar.contexts.none');
  }, [selectedSubjects, t]);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="group flex items-center gap-3 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-emerald-500/30 transition-all duration-300 shadow-sm hover:shadow-emerald-500/5 backdrop-blur-md"
      >
        <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 group-hover:scale-110 transition-transform">
          {getActiveViewIcon()}
        </div>
        
        <div className="flex flex-col items-start translate-y-[1px]">
          <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500 leading-none mb-1 group-hover:text-zinc-400 transition-colors">
            {isMultiSelect ? t('sidebar.contexts.title') : t('ingestion.subject.label')}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-zinc-100 truncate max-w-[150px]">
              {selectedLabel}
            </span>
            <ChevronDown className={`w-3.5 h-3.5 text-zinc-500 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
          </div>
        </div>

        {/* Mode indicator badge */}
        <div className="ml-2 px-2 py-0.5 rounded-full bg-zinc-900/50 border border-white/5 text-[9px] font-black uppercase tracking-tighter text-zinc-500">
          {isMultiSelect ? 'Multi' : 'Single'}
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop for closing */}
            <div 
              className="fixed inset-0 z-40" 
              onClick={() => setIsOpen(false)}
              role="none"
            />
            
            <motion.div
              initial={{ opacity: 0, y: 12, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.95 }}
              transition={{ duration: 0.2, ease: [0.23, 1, 0.32, 1] }}
              className="absolute top-full left-0 mt-3 w-80 bg-[#121212]/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-50 overflow-hidden flex flex-col"
            >
              {/* Header Info */}
              <div className="px-4 py-3 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Info className="w-3.5 h-3.5 text-emerald-500/70" />
                  <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                    {isMultiSelect ? 'Modo Multi-seleção' : 'Modo Seleção Única'}
                  </span>
                </div>
                <button
                  onClick={() => {
                    setIsAddSubjectModalOpen(true);
                    setIsOpen(false);
                  }}
                  className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500 hover:text-black transition-all border border-emerald-500/20"
                  title={t('sidebar.contexts.create')}
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Search */}
              <div className="p-3">
                <div className="relative group">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 transition-colors group-focus-within:text-emerald-500" />
                  <input
                    type="text"
                    autoFocus
                    placeholder={t('sidebar.contexts.placeholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-black/40 border border-white/5 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/30 focus:ring-1 focus:ring-emerald-500/10 transition-all placeholder:text-zinc-600"
                  />
                </div>
              </div>

              {/* List */}
              <div className="max-h-[320px] overflow-y-auto p-2 custom-scrollbar">
                {filteredSubjects.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-10 opacity-40">
                    <Layers className="w-8 h-8 mb-2" />
                    <span className="text-xs">{t('sidebar.contexts.none')}</span>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {filteredSubjects.map((subject) => {
                      const isSelected = selectedSubjects.some(s => s.id === subject.id);
                      
                      const SelectionIcon = () => {
                        if (isMultiSelect) {
                          return isSelected ? <CheckSquare className="w-5 h-5" /> : <Square className="w-5 h-5" />;
                        }
                        return isSelected ? <Check className="w-5 h-5" /> : <div className="w-5 h-5 border-2 border-current rounded-full" />;
                      };

                      return (
                        <button
                          key={subject.id}
                          onClick={() => handleToggle(subject)}
                          className={`w-full flex items-center justify-between p-3.5 rounded-2xl transition-all duration-300 group/item relative overflow-hidden ${
                            isSelected 
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]' 
                              : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-200 border border-transparent'
                          }`}
                        >
                          {/* Inner glow for selected state */}
                          {isSelected && (
                            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-transparent pointer-events-none" />
                          )}

                          <div className="flex items-center gap-4 truncate relative z-10">
                            <div className={`flex-shrink-0 transition-all duration-500 ${isSelected ? 'text-emerald-400 scale-110 drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'text-zinc-600 group-hover/item:text-zinc-400'}`}>
                              <SelectionIcon />
                            </div>
                            <div className="flex flex-col items-start min-w-0">
                                <div className="flex items-center gap-2">
                                  <SubjectIcon iconName={subject.icon} className={`w-3.5 h-3.5 ${isSelected ? 'text-emerald-400' : 'text-zinc-500'}`} />
                                  <span className={`text-[15px] font-bold tracking-tight truncate ${isSelected ? 'text-white' : 'text-zinc-300'}`}>
                                      {subject.name}
                                  </span>
                                </div>
                                {subject.sourceCount !== undefined && (
                                    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">
                                        {subject.sourceCount} {t('sidebar.operations.sources')}
                                    </span>
                                )}
                            </div>
                          </div>
                          
                          <AnimatePresence>
                            {isMultiSelect && !isSelected && (
                              <motion.button
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 10 }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  selectOnlySubject(subject);
                                  setIsOpen(false);
                                }}
                                className="px-3 py-1.5 text-[9px] font-black uppercase tracking-widest bg-zinc-800 text-zinc-500 rounded-lg opacity-0 group-hover/item:opacity-100 hover:bg-emerald-500 hover:text-black transition-all shadow-lg active:scale-95 z-20"
                              >
                                {t('sidebar.contexts.only')}
                              </motion.button>
                            )}
                          </AnimatePresence>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
              
              {/* Footer selection summary */}
              {isMultiSelect && selectedSubjects.length > 0 && (
                <div className="p-3 bg-white/[0.02] border-t border-white/5 flex items-center justify-between">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
                        {selectedSubjects.length} selecionados
                    </span>
                </div>
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
