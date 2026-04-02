import React from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, Search, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface Subject {
  id: string;
  name: string;
}

interface SubjectSelectorProps {
  readonly subjects: Subject[];
  readonly targetSubjectId: string | undefined;
  readonly setTargetSubjectId: (id: string) => void;
  readonly isDropdownOpen: boolean;
  readonly setIsDropdownOpen: (open: boolean) => void;
  readonly subjectSearch: string;
  readonly setSubjectSearch: (search: string) => void;
}

export function SubjectSelector({
  subjects,
  targetSubjectId,
  setTargetSubjectId,
  isDropdownOpen,
  setIsDropdownOpen,
  subjectSearch,
  setSubjectSearch
}: SubjectSelectorProps) {
  const { t } = useTranslation();
  
  const selectedTarget = subjects.find(s => s.id === targetSubjectId);
  const filteredSubjects = subjects.filter(s => s.name.toLowerCase().includes(subjectSearch.toLowerCase()));

  return (
    <div className="text-xs text-zinc-500 mt-1 flex items-center gap-2 relative">
      {t('ingestion.subject.label')}:
      <button
        type="button"
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        className="flex items-center gap-2 bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700/50 hover:border-zinc-600 rounded-lg px-2.5 py-1.5 text-emerald-400 font-medium transition-colors"
      >
        <span className="truncate max-w-[180px]">{selectedTarget?.name || t('ingestion.subject.placeholder')}</span>
        <ChevronDown className="w-3.5 h-3.5 opacity-70" />
      </button>

      <AnimatePresence>
        {isDropdownOpen && (
          <>
            <button 
              type="button"
              className="fixed inset-0 z-40 w-full h-full cursor-default bg-transparent border-none p-0 m-0" 
              onClick={() => setIsDropdownOpen(false)} 
              aria-label={t('common.actions.close')}
            />
            <motion.div
              initial={{ opacity: 0, y: -10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute top-full left-[90px] mt-1 w-64 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl z-50 overflow-hidden flex flex-col"
            >
              <div className="p-2 border-b border-zinc-800">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
                  <input
                    type="text"
                    autoFocus
                    placeholder={t('sidebar.contexts.placeholder')}
                    value={subjectSearch}
                    onChange={(e) => setSubjectSearch(e.target.value)}
                    className="w-full bg-black/40 border border-zinc-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-colors"
                  />
                </div>
              </div>
              <div className="max-h-[200px] overflow-y-auto p-1 custom-scrollbar">
                {filteredSubjects.length === 0 ? (
                  <div className="p-3 text-xs text-zinc-500 text-center">{t('sidebar.contexts.none')}</div>
                ) : (
                  filteredSubjects.map((s) => (
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
                      {targetSubjectId === s.id && <Check className="w-4 h-4" />}
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
