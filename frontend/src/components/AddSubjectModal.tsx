import React, { useState, type SyntheticEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { useAppContext } from '../store/AppContext';
import { motion, AnimatePresence } from 'motion/react';
import { SubjectIcon, ICONS_LIST as ICONS } from './SubjectIcon';

interface AddSubjectModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
}

export function AddSubjectModal({ isOpen, onClose }: AddSubjectModalProps) {
  const { t } = useTranslation();
  const { addSubject } = useAppContext();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedIcon, setSelectedIcon] = useState('Hash');

  const handleSubmit = (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!name.trim()) return;

    addSubject({
      name: name.trim(),
      description: description.trim(),
      icon: selectedIcon,
    });

    // Reset and close
    setName('');
    setDescription('');
    setSelectedIcon('Hash');
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0"
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2 }}
            className="w-full max-w-sm bg-[#18181b] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col relative z-10"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-white/5 bg-black/20">
              <div>
                <h2 className="text-lg font-semibold text-zinc-100">{t('sidebar.contexts.new')}</h2>
                <p className="text-[10px] text-zinc-500 mt-1 uppercase tracking-widest font-bold">Create a new context to organize your data</p>
              </div>
              <button 
                onClick={onClose}
                className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-white/5 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-zinc-600 mb-2">
                  {t('knowledge_contexts.name_label')} <span className="text-emerald-500">*</span>
                </label>
                <input 
                  type="text" 
                  required
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t('knowledge_contexts.placeholder_name')} 
                  className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-zinc-700 font-bold"
                />
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-zinc-600 mb-2">
                  {t('knowledge_contexts.description_label')} <span className="text-zinc-700 font-normal">(Optional)</span>
                </label>
                <textarea 
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t('knowledge_contexts.placeholder_description')} 
                  rows={2}
                  className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-zinc-700 resize-none"
                />
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-zinc-600 mb-3">
                  {t('knowledge_contexts.icon_label')}
                </label>
                <div className="grid grid-cols-6 gap-2 max-h-[160px] overflow-y-auto custom-scrollbar p-1">
                  {ICONS.map(({ name: iconName, icon: Icon }) => (
                    <button
                      key={iconName}
                      type="button"
                      onClick={() => setSelectedIcon(iconName)}
                      className={`group flex items-center justify-center p-2.5 rounded-xl border transition-all ${
                        selectedIcon === iconName
                          ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
                          : 'bg-black/40 border-white/5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200'
                      }`}
                    >
                      <SubjectIcon iconName={iconName} className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${selectedIcon === iconName ? 'scale-110' : ''}`} />
                    </button>
                  ))}
                </div>
              </div>

              {/* Footer Actions */}
              <div className="flex items-center justify-end gap-3 pt-4 mt-2 border-t border-white/5">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-bold text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  {t('common.actions.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={!name.trim()}
                  className="px-6 py-2 text-sm font-black text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none uppercase tracking-wider"
                >
                  {t('common.actions.save')}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
