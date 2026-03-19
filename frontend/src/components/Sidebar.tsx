import React, { useState } from 'react';
import { useAppContext } from '../store/AppContext';
import { useTranslation } from 'react-i18next';
import { AddSubjectModal } from './AddSubjectModal';
import { SettingsModal } from './SettingsModal';
import * as LucideIcons from 'lucide-react';
import {
  MessageSquare, Search, Database, Activity as ActivityIcon,
  Hash, Plus, Brain, Briefcase, ChefHat, Cpu, Landmark, Lightbulb,
  CheckSquare, Square, Settings, Layout, Layers, HardDrive,
  Cloud, Lock, User, Users, Target, Award, GraduationCap,
  Music, Video, Image, FileText, Mail, Terminal, Bug
} from 'lucide-react';

const ICONS = [
  { name: 'Brain', icon: Brain },
  { name: 'Briefcase', icon: Briefcase },
  { name: 'ChefHat', icon: ChefHat },
  { name: 'Cpu', icon: Cpu },
  { name: 'Landmark', icon: Landmark },
  { name: 'Lightbulb', icon: Lightbulb },
  { name: 'Activity', icon: ActivityIcon },
  { name: 'Hash', icon: Hash },
  { name: 'Database', icon: Database },
  { name: 'Search', icon: Search },
  { name: 'Code', icon: LucideIcons.Code },
  { name: 'MessageSquare', icon: MessageSquare },
  { name: 'Layout', icon: Layout },
  { name: 'Layers', icon: Layers },
  { name: 'HardDrive', icon: HardDrive },
  { name: 'Cloud', icon: Cloud },
  { name: 'Lock', icon: Lock },
  { name: 'User', icon: User },
  { name: 'Users', icon: Users },
  { name: 'Target', icon: Target },
  { name: 'Award', icon: Award },
  { name: 'GraduationCap', icon: GraduationCap },
  { name: 'Music', icon: Music },
  { name: 'Video', icon: Video },
  { name: 'Image', icon: Image },
  { name: 'FileText', icon: FileText },
  { name: 'Mail', icon: Mail },
  { name: 'Terminal', icon: Terminal },
  { name: 'Bug', icon: Bug },
];

const getSubjectIcon = (iconName?: string) => {
  const item = ICONS.find(i => i.name === iconName);
  return item ? item.icon : Hash;
};

export function Sidebar() {
  const { subjects, selectedSubjects, toggleSubjectSelection, selectOnlySubject, currentView, setCurrentView } = useAppContext();
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);

  const navGroups = [
    {
      id: 'explore',
      label: t('sidebar.groups.search'),
      items: [
        { id: 'chat', label: t('sidebar.operations.chat'), icon: MessageSquare, disabled: true },
        { id: 'search', label: t('sidebar.operations.search'), icon: Search },
      ]
    },
    {
      id: 'data',
      label: t('sidebar.groups.data'),
      items: [
        { id: 'sources', label: t('sidebar.operations.sources'), icon: Database },
        { id: 'knowledge_contexts', label: t('sidebar.operations.knowledge_contexts') || 'Knowledge Contexts', icon: Layers },
      ]
    },
    {
      id: 'monitor',
      label: t('sidebar.groups.monitor'),
      items: [
        { id: 'activity', label: t('sidebar.operations.activity'), icon: ActivityIcon },
      ]
    }
  ] as const;

  const filteredSubjects = subjects.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-64 border-r border-border-subtle bg-[#121212] flex flex-col h-screen">
      {/* Brand */}
      <div className="p-5 border-b border-border-subtle bg-black/20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.2)] flex-shrink-0">
            <span className="text-black text-sm font-black">W</span>
          </div>
          <div className="flex flex-col min-w-0">
            <h1 className="text-base font-bold tracking-tight text-white truncate">{t('sidebar.brand.title')}</h1>
            <p className="text-[10px] text-emerald-500/80 font-mono uppercase tracking-wider truncate">{t('sidebar.brand.subtitle')}</p>
          </div>
        </div>
      </div>

      {/* Context Selector (Subjects) */}
      <div className="flex flex-col flex-1 min-h-0 border-b border-border-subtle">
        <div className="p-4 pb-2 flex items-center justify-between">
          <h2 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest px-2 whitespace-nowrap overflow-hidden text-ellipsis">
            {t('sidebar.contexts.title')}
          </h2>
          <button
            onClick={() => setIsAddSubjectModalOpen(true)}
            className="group p-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
            title={t('sidebar.contexts.create')}
          >
            <Plus className="w-4 h-4 transition-transform duration-300 group-hover:rotate-90" />
          </button>
        </div>

        {/* Search Contexts */}
        <div className="px-4 pb-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              placeholder={t('sidebar.contexts.placeholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/40 border border-border-subtle rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-zinc-600 transition-colors placeholder:text-zinc-600"
            />
          </div>
        </div>

        {/* Scrollable Context List */}
        <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-1 custom-scrollbar">
          {filteredSubjects.length === 0 ? (
            <div className="text-xs text-zinc-500 text-center py-4">{t('sidebar.contexts.none')}</div>
          ) : (
            filteredSubjects.map((subject) => {
              const Icon = getSubjectIcon(subject.icon);
              const isSelected = selectedSubjects.some(s => s.id === subject.id);

              return (
                <div
                  key={subject.id}
                  onClick={() => toggleSubjectSelection(subject)}
                  className={`relative w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all group select-none cursor-pointer ${isSelected
                      ? 'bg-zinc-800 text-white font-medium shadow-sm'
                      : 'text-zinc-400 hover:bg-panel-hover hover:text-zinc-200'
                    }`}
                  title={t('sidebar.contexts.toggle')}
                >
                  <div className="flex items-center gap-3 truncate pr-8">
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-emerald-400 flex-shrink-0 transition-transform duration-200 scale-110" />
                    ) : (
                      <Square className="w-4 h-4 opacity-50 flex-shrink-0 group-hover:opacity-100 transition-transform duration-200 group-hover:scale-110" />
                    )}
                    <span className="truncate">{subject.name}</span>
                  </div>

                  <div className="flex items-center">
                    {subject.sourceCount !== undefined && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 transition-opacity duration-200 group-hover:opacity-0 ${isSelected ? 'bg-zinc-700 text-zinc-300' : 'bg-black/40 text-zinc-500'
                        }`}>
                        {subject.sourceCount}
                      </span>
                    )}

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        selectOnlySubject(subject);
                      }}
                      className="absolute right-3 opacity-0 group-hover:opacity-100 px-2 py-0.5 text-[10px] font-medium bg-zinc-600 text-white rounded hover:bg-emerald-500 hover:text-black transition-all shadow-sm"
                      title={t('sidebar.contexts.only')}
                    >
                      {t('sidebar.contexts.only')}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Navigation Groups */}
      <div className="p-4 pt-2 space-y-6">
        {navGroups.map((group, index) => (
          <div key={group.id} className="space-y-2">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-zinc-600 px-3">
              {group.label}
            </h3>
            <div className="space-y-1">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isSourcesGroup = item.id === 'sources';
                const isActive = currentView === item.id || (isSourcesGroup && currentView === 'database');
                const isDisabled = (item as any).disabled;

                return (
                  <button
                    key={item.id}
                    disabled={isDisabled}
                    onClick={() => setCurrentView(item.id as any)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all relative group ${isActive
                        ? 'bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20'
                        : isDisabled
                          ? 'opacity-30 cursor-not-allowed grayscale'
                          : 'text-zinc-400 hover:bg-white/5 hover:text-zinc-200'
                      }`}
                  >
                    <Icon className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'scale-110 text-emerald-400' : 'text-zinc-500 group-hover:text-zinc-300'}`} />
                    <span className="truncate">
                      {isSourcesGroup && currentView === 'database' ? t('sidebar.operations.chunks') : item.label}
                    </span>
                    {isActive && (
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-emerald-500 rounded-r-full shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    )}
                  </button>
                );
              })}
            </div>
            {index < navGroups.length - 1 && <div className="h-px bg-white/5 mt-6 mx-2" />}
          </div>
        ))}
      </div>

      {/* User Profile / Settings placeholder */}
      <div className="p-4 border-t border-border-subtle">
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center">
              <span className="text-xs font-medium text-zinc-400">US</span>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-zinc-200">{t('sidebar.profile.name')}</span>
              <span className="text-[10px] text-emerald-500 uppercase tracking-wider font-mono">{t('sidebar.profile.plan')}</span>
            </div>
          </div>
          <button
            onClick={() => setIsSettingsModalOpen(true)}
            className="p-2 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      <AddSubjectModal
        isOpen={isAddSubjectModalOpen}
        onClose={() => setIsAddSubjectModalOpen(false)}
      />

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
      />
    </div>
  );
}
