import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Brain, Briefcase, ChefHat, Cpu, Landmark, Lightbulb, Activity, Hash } from 'lucide-react';
import { useAppContext } from '../store/AppContext';

interface AddSubjectModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ICONS = [
  { name: 'Brain', icon: Brain },
  { name: 'Briefcase', icon: Briefcase },
  { name: 'ChefHat', icon: ChefHat },
  { name: 'Cpu', icon: Cpu },
  { name: 'Landmark', icon: Landmark },
  { name: 'Lightbulb', icon: Lightbulb },
  { name: 'Activity', icon: Activity },
  { name: 'Hash', icon: Hash },
];

export function AddSubjectModal({ isOpen, onClose }: AddSubjectModalProps) {
  const { t } = useTranslation();
  const { addSubject } = useAppContext();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedIcon, setSelectedIcon] = useState('Hash');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div 
        className="w-full max-w-md bg-[#18181b] border border-border-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border-subtle bg-black/20">
          <div>
            <h2 className="text-lg font-semibold text-zinc-100">{t('contexts.new')}</h2>
            <p className="text-xs text-zinc-500 mt-1">Create a new context to organize your data</p>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-panel-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Name <span className="text-emerald-500">*</span>
            </label>
            <input 
              type="text" 
              required
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Personal Finance, Huberman Lab..." 
              className="w-full bg-black/40 border border-border-subtle rounded-xl px-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all placeholder:text-zinc-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Description <span className="text-zinc-500 font-normal">(Optional)</span>
            </label>
            <textarea 
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What kind of knowledge will live here?" 
              rows={2}
              className="w-full bg-black/40 border border-border-subtle rounded-xl px-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/50 transition-all placeholder:text-zinc-600 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-3">
              Icon
            </label>
            <div className="grid grid-cols-4 gap-2">
              {ICONS.map(({ name: iconName, icon: Icon }) => (
                <button
                  key={iconName}
                  type="button"
                  onClick={() => setSelectedIcon(iconName)}
                  className={`group flex items-center justify-center p-3 rounded-xl border transition-all ${
                    selectedIcon === iconName
                      ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
                      : 'bg-black/40 border-border-subtle text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
                  }`}
                >
                  <Icon className={`w-5 h-5 transition-transform duration-200 group-hover:scale-110 group-hover:-rotate-6 ${selectedIcon === iconName ? 'scale-110 -rotate-6' : ''}`} />
                </button>
              ))}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 mt-2 border-t border-border-subtle">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-100 transition-colors"
            >
              {t('common.actions.cancel')}
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="px-5 py-2 text-sm font-medium text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_15px_rgba(16,185,129,0.15)] disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            >
              Create Context
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
