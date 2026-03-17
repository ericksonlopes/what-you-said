import React, { useState } from 'react';
import { useAppContext } from '../store/AppContext';
import { AddSubjectModal } from './AddSubjectModal';
import { SettingsModal } from './SettingsModal';
import { 
  MessageSquare, Search, Database, Activity as ActivityIcon, 
  Hash, Plus, Brain, Briefcase, ChefHat, Cpu, Landmark, Lightbulb,
  CheckSquare, Square, Settings
} from 'lucide-react';

const getSubjectIcon = (iconName?: string) => {
  switch (iconName) {
    case 'Brain': return Brain;
    case 'Briefcase': return Briefcase;
    case 'ChefHat': return ChefHat;
    case 'Cpu': return Cpu;
    case 'Landmark': return Landmark;
    case 'Lightbulb': return Lightbulb;
    case 'Activity': return ActivityIcon;
    default: return Hash;
  }
};

export function Sidebar() {
  const { subjects, selectedSubjects, toggleSubjectSelection, selectOnlySubject, currentView, setCurrentView } = useAppContext();
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddSubjectModalOpen, setIsAddSubjectModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);

  const navItems = [
    { id: 'chat', label: 'RAG Chat', icon: MessageSquare },
    { id: 'search', label: 'Search', icon: Search },
    { id: 'sources', label: 'Content Sources', icon: Database },
    { id: 'activity', label: 'Activity Monitor', icon: ActivityIcon },
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
            <h1 className="text-base font-bold tracking-tight text-white truncate">WhatYouSaid</h1>
            <p className="text-[10px] text-emerald-500/80 font-mono uppercase tracking-wider truncate">Vector Data Hub</p>
          </div>
        </div>
      </div>

      {/* Context Selector (Subjects) */}
      <div className="flex flex-col flex-1 min-h-0 border-b border-border-subtle">
        <div className="p-4 pb-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider px-2">
            Knowledge Contexts
          </h2>
          <button 
            onClick={() => setIsAddSubjectModalOpen(true)}
            className="group p-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
            title="Create new context"
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
              placeholder="Filter contexts..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/40 border border-border-subtle rounded-lg pl-8 pr-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-zinc-600 transition-colors placeholder:text-zinc-600"
            />
          </div>
        </div>

        {/* Scrollable Context List */}
        <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-1 custom-scrollbar">
          {filteredSubjects.length === 0 ? (
            <div className="text-xs text-zinc-500 text-center py-4">No contexts found.</div>
          ) : (
            filteredSubjects.map((subject) => {
              const Icon = getSubjectIcon(subject.icon);
              const isSelected = selectedSubjects.some(s => s.id === subject.id);
              
              return (
                <div
                  key={subject.id}
                  onClick={() => toggleSubjectSelection(subject)}
                  className={`relative w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-all group select-none cursor-pointer ${
                    isSelected
                      ? 'bg-zinc-800 text-white font-medium shadow-sm'
                      : 'text-zinc-400 hover:bg-panel-hover hover:text-zinc-200'
                  }`}
                  title="Click to toggle"
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
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full flex-shrink-0 transition-opacity duration-200 group-hover:opacity-0 ${
                        isSelected ? 'bg-zinc-700 text-zinc-300' : 'bg-black/40 text-zinc-500'
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
                      title="Select only this context"
                    >
                      Only
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Navigation Views */}
      <div className="p-4">
        <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 px-2">
          Operations
        </h2>
        <div className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isSourcesGroup = item.id === 'sources';
            const isActive = currentView === item.id || (isSourcesGroup && currentView === 'database');
            
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id)}
                className={`group w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 font-medium border border-emerald-500/20'
                    : 'text-zinc-400 hover:bg-panel-hover hover:text-zinc-200 border border-transparent'
                }`}
              >
                <Icon className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'scale-110' : ''}`} />
                <span className="truncate">
                  {isSourcesGroup && currentView === 'database' ? 'Sources > Chunks' : item.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* User Profile / Settings placeholder */}
      <div className="p-4 border-t border-border-subtle">
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center">
              <span className="text-xs font-medium text-zinc-400">US</span>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-zinc-200">User</span>
              <span className="text-[10px] text-emerald-500 uppercase tracking-wider font-mono">Pro Plan</span>
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
