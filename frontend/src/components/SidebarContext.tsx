import React, { useCallback, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Database, Plus, Eraser, Check, MousePointer2, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useAppContext } from '../store/AppContext';
import { Subject } from '../types';

export function SidebarContext() {
  const { 
    subjects, 
    selectedSubjects, 
    setSelectedSubjects, 
    setIsAddSubjectModalOpen 
  } = useAppContext();
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSubjects = useMemo(() => {
    return subjects.filter(s => 
      s.name.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [subjects, searchQuery]);

  const handleSelectAll = useCallback(() => {
    setSelectedSubjects([]); // Empty means "All"
  }, [setSelectedSubjects]);

  const handleToggleSubject = useCallback((subject: Subject) => {
    // Simplified UX: Always toggle selection on click
    const isSelected = selectedSubjects.some(s => s.id === subject.id);
    
    if (isSelected) {
      // If it's the last one being unselected, revert to "All" (empty list)
      if (selectedSubjects.length === 5) {
        // Wait, empty list means "All" in this app.
      }
      setSelectedSubjects(selectedSubjects.filter(s => s.id !== subject.id));
    } else {
      setSelectedSubjects([...selectedSubjects, subject]);
    }
  }, [selectedSubjects, setSelectedSubjects]);

  const isAllSelected = selectedSubjects.length === 0;

  return (
    <div className="w-80 border-l border-white/5 bg-black/20 backdrop-blur-xl flex flex-col h-full shrink-0 relative z-20">
      <div className="p-6 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-black text-white uppercase tracking-widest">{t('sidebarContext.title')}</h3>
        </div>
        <div className="flex items-center gap-2">
           <AnimatePresence>
            {!isAllSelected && (
              <motion.button
                initial={{ opacity: 0, scale: 0.9, x: 10 }}
                animate={{ opacity: 1, scale: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.9, x: 10 }}
                onClick={handleSelectAll}
                className="flex items-center justify-center w-8 h-8 rounded-lg bg-white/5 border border-white/10 text-zinc-400 hover:text-white hover:bg-white/10 transition-all"
                title={t('sidebarContext.clear_filter')}
              >
                <Eraser className="w-3.5 h-3.5" />
              </motion.button>
            )}
           </AnimatePresence>
          <button
            onClick={() => setIsAddSubjectModalOpen(true)}
            className="w-8 h-8 rounded-xl bg-zinc-900 border border-white/5 flex items-center justify-center text-zinc-500 hover:text-white hover:bg-emerald-500/20 hover:border-emerald-500/30 transition-all shadow-sm shadow-black"
            title={t('sidebarContext.new_base')}
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="p-6 border-b border-white/5 bg-emerald-500/5 group relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/0 via-emerald-500/5 to-emerald-500/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
        <p className="text-[10px] text-emerald-400/70 font-black uppercase tracking-widest leading-relaxed relative z-10 flex items-center gap-2">
           <MousePointer2 className="w-3 h-3 opacity-50" />
           {t('sidebarContext.description')}
        </p>
      </div>

      <div className="px-4 pt-4 pb-2">
        <div className="relative group/search">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within/search:text-emerald-500 transition-colors" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('common.actions.search') + '...'}
            className="w-full pl-9 pr-3 py-2 bg-white/[0.03] border border-white/5 rounded-xl text-xs text-zinc-300 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/30 transition-all font-medium"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
        {/* ALL / TODOS Button */}
        <button
          onClick={handleSelectAll}
          className={`w-full group flex items-center gap-3 p-3 rounded-2xl transition-all border relative overflow-hidden ${isAllSelected ? 'bg-emerald-500/10 border-emerald-500/30 text-white shadow-[0_0_20px_rgba(16,185,129,0.1)]' : 'bg-transparent border-transparent text-zinc-500 hover:bg-white/5 hover:text-zinc-300'}`}
        >
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${isAllSelected ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' : 'bg-zinc-900 text-zinc-600'}`}>
            <Database className="w-4 h-4" />
          </div>
          <div className="text-left flex-1 min-w-0">
            <div className={`text-xs font-bold truncate ${isAllSelected ? 'text-white' : 'text-zinc-400 group-hover:text-zinc-200'}`}>
              {t('sidebarContext.all_bases')}
            </div>
            <div className="text-[9px] font-black uppercase tracking-widest opacity-40">
               {isAllSelected ? t('common.active') : t('common.select')}
            </div>
          </div>
          {isAllSelected && (
            <motion.div 
               className="w-5 h-5 rounded-lg bg-emerald-500 flex items-center justify-center shadow-[0_0_8px_rgba(16,185,129,0.5)]"
            >
               <Check className="w-3 h-3 text-black stroke-[3px]" />
            </motion.div>
          )}
        </button>

        <div className="h-px bg-white/5 my-4 mx-2" />

        <AnimatePresence mode="popLayout">
          {filteredSubjects.map((ctx) => {
            const isSelected = selectedSubjects.some(s => s.id === ctx.id);
            return (
              <motion.button
                layout
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                key={ctx.id}
                onClick={() => handleToggleSubject(ctx)}
                className={`w-full group flex items-center gap-3 p-3 rounded-2xl transition-all border ${isSelected ? 'bg-emerald-500/10 border-emerald-500/30 text-white shadow-[0_0_20px_rgba(16,185,129,0.1)]' : 'bg-transparent border-transparent text-zinc-500 hover:bg-white/5 hover:text-zinc-300'}`}
              >
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center transition-all ${isSelected ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' : 'bg-zinc-900 text-zinc-600 group-hover:bg-zinc-800'}`}>
                  <Database className="w-4 h-4" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <div className={`text-xs font-bold truncate ${isSelected ? 'text-white' : 'text-zinc-400 group-hover:text-zinc-200'}`}>
                    {ctx.name}
                  </div>
                  <div className="text-[9px] font-black uppercase tracking-widest opacity-50 mt-0.5">
                    {ctx.sourceCount || 0} {t('sidebarContext.sources_count')}
                  </div>
                </div>
                {isSelected && (
                  <motion.div 
                    className="w-5 h-5 rounded-lg bg-emerald-500 flex items-center justify-center shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                  >
                     <Check className="w-3 h-3 text-black stroke-[3px]" />
                  </motion.div>
                )}
              </motion.button>
            );
          })}
        </AnimatePresence>

        {subjects.length === 0 && (
           <div className="py-20 text-center opacity-20">
              <Database className="w-8 h-8 mx-auto mb-3 text-zinc-500" />
              <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500">{t('sidebarContext.no_base')}</span>
           </div>
        )}
      </div>

      <div className="p-6 border-t border-white/5 mt-auto bg-black/40">
         <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${isAllSelected ? 'bg-emerald-500 animate-pulse' : 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.5)]'}`} />
            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest leading-none mt-0.5 truncate flex-1">
              {isAllSelected ? t('sidebarContext.all_bases') : selectedSubjects.map(s => s.name).join(', ')}
            </span>
         </div>
      </div>
    </div>
  );
}
