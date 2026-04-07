import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Database, 
  Check, 
  ChevronDown, 
  X, 
  Search
} from 'lucide-react';
import { useAppContext } from '../store/AppContext';
import { SubjectIcon } from './SubjectIcon';

interface LocalContextSelectorProps {
  mode: 'single' | 'multi';
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  label?: string;
  placeholder?: string;
  className?: string;
  compact?: boolean;
}

export const LocalContextSelector: React.FC<LocalContextSelectorProps> = ({
  mode,
  selectedIds,
  onChange,
  label,
  placeholder = 'Selecionar base...',
  className = '',
  compact = false
}) => {
  const { subjects } = useAppContext();
  const [isOpen, setIsOpen] = React.useState(false);
  const [searchTerm, setSearchTerm] = React.useState('');
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Close on click outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedSubjects = subjects.filter(s => selectedIds.includes(s.id));
  const filteredSubjects = subjects.filter(s => 
    s.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleSubject = (id: string) => {
    if (mode === 'single') {
      onChange([id]);
      setIsOpen(false);
    } else {
      const newIds = selectedIds.includes(id)
        ? selectedIds.filter(i => i !== id)
        : [...selectedIds, id];
      onChange(newIds);
    }
  };

  const renderTrigger = () => {
    if (selectedIds.length === 0) {
      return (
        <div className="flex items-center gap-2 text-zinc-500">
          <Database className="w-4 h-4" />
          <span>{placeholder}</span>
        </div>
      );
    }
    
    if (mode === 'single') {
      const selected = subjects.find(s => s.id === selectedIds[0]);
      return (
        <div className="flex items-center gap-2 text-primary-400">
          <Database className="w-4 h-4" />
          <span className="truncate max-w-[120px]">{selected?.name || 'Selecionado'}</span>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2">
        <div className="px-2 py-0.5 bg-primary-500 text-black text-[10px] font-black rounded-md">
          {selectedIds.length}
        </div>
        <span className="text-zinc-300">Bases Selected</span>
      </div>
    );
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {label && (
        <label className="block text-xs font-medium text-gray-400 mb-1.5 ml-1 uppercase tracking-wider">
          {label}
        </label>
      )}

      {/* Trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between gap-2 px-3 py-2 
          bg-white/5 border border-white/10 hover:border-white/20 
          rounded-xl transition-all duration-200 group
          ${isOpen ? 'ring-2 ring-primary-500/20 border-primary-500/50' : ''}`}
      >
        <div className="flex items-center gap-2 overflow-hidden">
          <div className={`p-1.5 rounded-lg ${selectedIds.length > 0 ? 'bg-primary-500/20 text-primary-400' : 'bg-white/5 text-gray-500'}`}>
            <Database size={16} />
          </div>
          
          <div className="flex items-center gap-1.5 overflow-hidden">
            {renderTrigger()}
          </div>
        </div>
        
        <ChevronDown 
          size={16} 
          className={`text-gray-500 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 4, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            className="absolute z-50 w-full mt-2 bg-[#1a1c20]/95 backdrop-blur-xl 
              border border-white/10 rounded-2xl shadow-2xl overflow-hidden shadow-black/50"
          >
            {/* Search Box */}
            <div className="p-3 border-b border-white/10">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Buscar base..."
                  className="w-full pl-9 pr-3 py-2 bg-white/5 border border-white/5 rounded-lg 
                    text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-primary-500/50"
                  autoFocus
                />
              </div>
            </div>

            {/* List */}
            <div className="max-h-[240px] overflow-y-auto p-1 custom-scrollbar">
              {filteredSubjects.length === 0 ? (
                <div className="py-8 px-4 text-center">
                  <Database size={24} className="mx-auto text-gray-700 mb-2 opacity-50" />
                  <p className="text-sm text-gray-500 font-medium">Nenhuma base encontrada</p>
                </div>
              ) : (
                filteredSubjects.map((subject) => {
                  const isSelected = selectedIds.includes(subject.id);
                  return (
                    <button
                      key={subject.id}
                      onClick={() => toggleSubject(subject.id)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl transition-all group mb-0.5
                        ${isSelected 
                          ? 'bg-primary-500/10 text-primary-400' 
                          : 'hover:bg-white/5 text-gray-400 hover:text-gray-200'}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-lg
                          ${isSelected ? 'bg-primary-500/20' : 'bg-white/5 border border-white/5 group-hover:bg-white/10'}`}>
                          <SubjectIcon iconName={subject.icon} className="w-4 h-4" />
                        </div>
                        <div className="text-left">
                          <p className="text-sm font-medium">{subject.name}</p>
                          {subject.description && (
                            <p className="text-[10px] opacity-50 line-clamp-1">{subject.description}</p>
                          )}
                        </div>
                      </div>
                      
                      {isSelected ? (
                        <div className="w-5 h-5 bg-primary-500 rounded-full flex items-center justify-center">
                          <Check size={12} className="text-white" />
                        </div>
                      ) : (
                        mode === 'multi' && (
                          <div className="w-5 h-5 border-2 border-white/10 rounded-full group-hover:border-white/20 transition-colors" />
                        )
                      )}
                    </button>
                  );
                })
              )}
            </div>

            {/* Selected Pills */}
            {mode === 'multi' && selectedSubjects.length > 0 && (
              <div className="p-3 border-t border-white/10 bg-white/5 flex flex-wrap gap-1.5">
                {selectedSubjects.map(s => (
                  <div key={s.id} className="flex items-center gap-1 px-2 py-1 bg-primary-500/20 border border-primary-500/30 rounded-lg text-[10px] text-primary-400 font-bold uppercase tracking-tighter">
                    {s.name}
                    <X size={10} className="cursor-pointer hover:text-white" onClick={(e) => {
                      e.stopPropagation();
                      toggleSubject(s.id);
                    }} />
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
