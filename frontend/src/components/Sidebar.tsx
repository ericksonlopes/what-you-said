import React, { useState } from 'react';
import { useAppContext } from '../store/AppContext';
import { useAuth } from '../store/AuthContext';
import { useTranslation } from 'react-i18next';
import {
  Activity as ActivityIcon,
  Database,
  LogOut,
  MessageSquare,
  Mic,
  Search,
  Settings,
  User,
  Layers,
  ChevronDown,
  Copy
} from 'lucide-react';

import { SettingsModal } from './SettingsModal';

export function Sidebar() {
  const { currentView, setCurrentView } = useAppContext();
  const { user, logout, isAuthEnabled } = useAuth();
  const { t } = useTranslation();
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({
    data: true
  });

  const toggleGroup = (id: string) => {
    setExpandedGroups(prev => ({ ...prev, [id]: !prev[id] }));
  };

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
      id: 'contexts',
      label: t('sidebar.groups.contexts'),
      items: [
        { id: 'knowledge_contexts', label: t('sidebar.operations.knowledge_contexts'), icon: Layers },
        { id: 'voice_profiles', label: t('voices.title', 'Vozes Reconhecidas'), icon: User },
      ]
    },
    {
      id: 'data',
      label: t('sidebar.operations.contentSources'),
      icon: Database,
      isExpandable: true,
      items: [
        { id: 'sources', label: t('sidebar.operations.sources'), icon: Database },
        { id: 'duplicates', label: t('sidebar.operations.duplicates'), icon: Copy },
        { id: 'diarization', label: t('sidebar.operations.diarization'), icon: Mic },
      ]
    },
    {
      id: 'monitor',
      label: t('sidebar.groups.monitor'),
      items: [
        { id: 'activity', label: t('sidebar.operations.activity'), icon: ActivityIcon },
        { id: 'queue', label: t('sidebar.operations.queue', 'Task Queue (Redis)'), icon: Layers },
      ]
    }
  ];

  const getItemClass = (isActive: boolean, isDisabled: boolean) => {
    if (isActive) return 'bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20 shadow-[0_4px_12px_rgba(16,185,129,0.05)]';
    if (isDisabled) return 'opacity-30 cursor-not-allowed grayscale';
    return 'text-zinc-400 hover:bg-white/5 hover:text-zinc-200';
  };

  return (
    <div className="w-64 border-r border-border-subtle bg-[#121212] flex flex-col h-screen z-50">
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

      {/* Navigation Groups - Scrollable Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 pt-2 space-y-6">
        {navGroups.map((group, index) => {
          const isExpandable = 'isExpandable' in group ? (group as any).isExpandable : false;
          const isExpanded = expandedGroups[group.id] ?? false;
          const GroupIcon = 'icon' in group ? (group as any).icon : null;

          if (isExpandable) {
            return (
              <div key={group.id} className="space-y-1">
                <button
                  onClick={() => toggleGroup(group.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${isExpanded ? 'text-white' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                  <div className="flex items-center gap-3">
                    {GroupIcon && <GroupIcon className="w-3.5 h-3.5" />}
                    {group.label}
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-300 ${isExpanded ? '' : '-rotate-90'}`} />
                </button>
                
                {isExpanded && (
                  <div className="ml-4 pl-2 border-l border-white/5 space-y-1 mt-1">
                    {group.items.map((item) => {
                      const Icon = item.icon;
                      const isActive = currentView === item.id || (item.id === 'sources' && currentView === 'database');
                      const isDisabled = 'disabled' in item ? item.disabled : false;

                      return (
                        <button
                          key={item.id}
                          disabled={isDisabled}
                          onClick={() => setCurrentView(item.id)}
                          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group ${getItemClass(isActive, isDisabled)}`}
                        >
                          <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-zinc-600 group-hover:text-zinc-400'}`} />
                          <span className="truncate">{item.label}</span>
                          {isActive && (
                            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-3 bg-emerald-500 rounded-r-full shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
                {index < navGroups.length - 1 && <div className="h-px bg-white/5 mt-6 mx-2" />}
              </div>
            );
          }

          return (
            <div key={group.id} className="space-y-2">
              <h3 className="text-[10px] font-black uppercase tracking-widest text-zinc-600 px-3">
                {group.label}
              </h3>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentView === item.id;
                  const isDisabled = 'disabled' in item ? item.disabled : false;

                  return (
                    <button
                      key={item.id}
                      disabled={isDisabled}
                      onClick={() => setCurrentView(item.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all relative group ${getItemClass(isActive, isDisabled)}`}
                    >
                      <Icon className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'scale-110 text-emerald-400' : 'text-zinc-500 group-hover:text-zinc-300'}`} />
                      <span className="truncate">{item.label}</span>
                      {isActive && (
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-emerald-500 rounded-r-full shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                      )}
                    </button>
                  );
                })}
              </div>
              {index < navGroups.length - 1 && <div className="h-px bg-white/5 mt-6 mx-2" />}
            </div>
          );
        })}
      </div>

      {/* User Profile / Settings */}
      <div className="p-4 border-t border-border-subtle bg-black/20">
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-3 min-w-0">
              {user?.picture_url ? (
                <img src={user.picture_url} alt={user.full_name} className="w-8 h-8 rounded-full border border-white/10 flex-shrink-0" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center flex-shrink-0">
                  <User className="w-4 h-4 text-zinc-500" />
                </div>
              )}
              <div className="flex flex-col min-w-0">
                <span className="text-sm font-bold text-zinc-200 truncate pr-1">
                  {user?.full_name || t('sidebar.profile.name')}
                </span>
                <span className="text-[10px] text-zinc-500 truncate font-medium">
                  {user?.email || t('sidebar.profile.plan')}
                </span>
              </div>
            </div>
            
            <button
              onClick={() => setIsSettingsModalOpen(true)}
              className="p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all flex-shrink-0"
              title={t('sidebar.profile.settings')}
            >
              <Settings className="w-4.5 h-4.5" />
            </button>
          </div>

          {isAuthEnabled && user && (
            <button
              onClick={logout}
              className="mx-2 flex items-center justify-center gap-2 group px-4 py-2.5 rounded-xl text-[11px] font-black uppercase tracking-widest text-zinc-500 border border-zinc-800/50 bg-zinc-900/30 hover:bg-red-500/10 hover:border-red-500/20 hover:text-red-400 transition-all duration-300"
            >
              <LogOut className="w-3.5 h-3.5 transition-transform duration-300 group-hover:-translate-x-0.5" />
              {t('auth.logout', 'Logout')}
            </button>
          )}
        </div>
      </div>

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
      />
    </div>
  );
}
