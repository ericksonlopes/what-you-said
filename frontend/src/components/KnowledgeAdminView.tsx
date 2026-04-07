import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Settings, Trash2, Edit2, Check, X, Plus, AlertTriangle, Search, Zap
} from 'lucide-react';
import { useAppContext } from '../store/AppContext';
import { motion, AnimatePresence } from 'motion/react';
import { Subject } from '../types';
import { SubjectIcon, ICONS_LIST as ICONS } from './SubjectIcon';

export function KnowledgeAdminView() {
  const { t } = useTranslation();
  const { subjects, updateSubject, deleteSubject, setIsAddSubjectModalOpen } = useAppContext();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Subject>>({});
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [filterQuery, setFilterQuery] = useState('');

  const handleEdit = (subject: Subject) => {
    setEditingId(subject.id);
    setEditForm({
      name: subject.name,
      description: subject.description,
      icon: subject.icon
    });
  };

  const handleSave = async () => {
    if (!editingId || !editForm.name?.trim()) return;
    await updateSubject(editingId, editForm);
    setEditingId(null);
    setEditForm({});
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditForm({});
  };

  const handleDelete = async (id: string) => {
    if (isDeleting) return;
    setIsDeleting(true);
    try {
      await deleteSubject(id);
      setDeletingId(null);
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredSubjects = subjects.filter(s => 
    s.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
    (s.description || '').toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div className="p-8 pt-10 max-w-5xl mx-auto h-full flex flex-col font-sans">
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
            <Settings className="w-7 h-7 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-3xl font-black text-white tracking-tight leading-none">
              {t('knowledge_contexts.title') || 'Knowledge Contexts'}
            </h2>
            <p className="text-zinc-500 text-sm mt-2 font-medium">
              {t('knowledge_contexts.subtitle') || 'Manage and organize your data contexts'}
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsAddSubjectModalOpen(true)}
          className="group flex items-center gap-2 px-4 py-2 text-sm font-bold text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all shadow-[0_0_20px_rgba(16,185,129,0.2)] active:scale-95"
        >
          <Plus className="w-5 h-5 transition-transform duration-300 group-hover:rotate-90" />
          {t('sidebar.contexts.create') || 'New Context'}
        </button>
      </div>

      {/* Filter Section */}
      <div className="mb-6 relative">
        <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" />
        <input 
          type="text"
          value={filterQuery}
          onChange={(e) => setFilterQuery(e.target.value)}
          placeholder={t('knowledge_contexts.filter_placeholder')}
          className="w-full bg-zinc-900/50 border border-white/5 rounded-2xl pl-12 pr-4 py-3 text-white placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/30 transition-all"
        />
        {filterQuery && (
          <button 
            onClick={() => setFilterQuery('')}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-2 pb-10">
        <div className="grid grid-cols-1 gap-4">
          {filteredSubjects.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="p-4 rounded-full bg-zinc-900 border border-white/5 mb-4">
                <Search className="w-8 h-8 text-zinc-700" />
              </div>
              <h3 className="text-white font-bold mb-1">{t('knowledge_contexts.no_results')}</h3>
              <p className="text-zinc-500 text-sm">{t('knowledge_contexts.no_results_desc')}</p>
            </div>
          ) : (
            filteredSubjects.map((subject) => {
              const isEditing = editingId === subject.id;

              return (
                <motion.div
                  key={subject.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`relative overflow-hidden p-6 rounded-2xl border transition-all ${isEditing
                      ? 'bg-zinc-900 border-emerald-500/30'
                      : 'bg-zinc-900/40 border-white/5 hover:border-white/10'
                    }`}
                >
                  {isEditing ? (
                    <div className="space-y-6">
                      <div className="flex flex-col md:flex-row gap-6">
                        <div className="flex flex-col items-center gap-3">
                          <label className="text-[10px] font-black uppercase tracking-widest text-zinc-600 self-start">{t('knowledge_contexts.icon_label')}</label>
                          <div className="grid grid-cols-6 gap-2 bg-black/20 p-3 rounded-xl border border-white/5 max-h-[160px] overflow-y-auto custom-scrollbar">
                             {ICONS.map(({ name: iconName }) => (
                              <button
                                key={iconName}
                                onClick={() => setEditForm({ ...editForm, icon: iconName })}
                                className={`p-2 rounded-lg transition-all ${editForm.icon === iconName
                                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                                  }`}
                              >
                                <SubjectIcon iconName={iconName} className="w-4 h-4" />
                              </button>
                            ))}
                          </div>
                        </div>

                        <div className="flex-1 space-y-4">
                          <div>
                            <label className="text-[10px] font-black uppercase tracking-widest text-zinc-600">{t('knowledge_contexts.name_label')}</label>
                            <input
                              value={editForm.name || ''}
                              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                              className="w-full mt-1 bg-black/40 border border-white/5 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-emerald-500/50 transition-all font-bold"
                              placeholder={t('knowledge_contexts.placeholder_name')}
                            />
                          </div>
                          <div>
                            <label className="text-[10px] font-black uppercase tracking-widest text-zinc-600">{t('knowledge_contexts.description_label')}</label>
                            <textarea
                              value={editForm.description || ''}
                              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                              className="w-full mt-1 bg-black/40 border border-white/5 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-emerald-500/50 transition-all resize-none"
                              placeholder={t('knowledge_contexts.placeholder_description')}
                              rows={2}
                            />
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/5">
                        <button
                          onClick={handleCancel}
                          className="flex items-center gap-2 px-4 py-2 text-sm font-bold text-zinc-400 hover:text-zinc-200 transition-colors"
                        >
                          <X className="w-4 h-4" />
                          {t('common.actions.cancel')}
                        </button>
                        <button
                          onClick={handleSave}
                          disabled={!editForm.name?.trim()}
                          className="flex items-center gap-2 px-6 py-2 text-sm font-bold text-black bg-emerald-500 rounded-xl hover:bg-emerald-400 transition-all disabled:opacity-50"
                        >
                          <Check className="w-4 h-4" />
                          {t('knowledge_contexts.save_changes')}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between gap-6">
                      <div className="flex items-center gap-5 flex-1 min-w-0">
                        <div className="w-14 h-14 rounded-2xl bg-zinc-800 border border-white/5 flex items-center justify-center shadow-inner group">
                          <SubjectIcon iconName={subject.icon} className="w-7 h-7 text-zinc-400 group-hover:text-emerald-400 transition-colors" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="text-xl font-bold text-white truncate">{subject.name}</h3>
                          <p className="text-zinc-500 text-sm mt-1 line-clamp-1">{subject.description || t('knowledge_contexts.no_description')}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-zinc-800 text-zinc-500 uppercase tracking-widest">
                              {subject.sourceCount || 0} {t('knowledge_contexts.source_count')}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleEdit(subject)}
                          className="p-2.5 rounded-xl bg-white/5 border border-white/5 text-zinc-400 hover:text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/20 transition-all"
                          title={t('knowledge_contexts.edit_tooltip')}
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeletingId(subject.id)}
                          className="p-2.5 rounded-xl bg-white/5 border border-white/5 text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/20 transition-all"
                          title={t('knowledge_contexts.delete_tooltip')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </motion.div>
              );
            })
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deletingId && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-md p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDeletingId(null)}
              className="absolute inset-0"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-sm bg-[#18181b] border border-white/10 rounded-2xl shadow-2xl p-8 relative z-10 text-center"
            >
              <div className="w-20 h-20 bg-rose-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <AlertTriangle className="w-10 h-10 text-rose-500" />
              </div>
              <h4 className="text-xl font-bold text-white mb-3">{t('knowledge_contexts.delete_confirm_title')}</h4>
              <p className="text-zinc-400 text-sm mb-8 leading-relaxed">
                {t('knowledge_contexts.delete_confirm_desc', { name: subjects.find(s => s.id === deletingId)?.name })}
              </p>
              <div className="flex items-center justify-center gap-4">
                <button
                  onClick={() => setDeletingId(null)}
                  disabled={isDeleting}
                  className="flex-1 px-4 py-3 text-sm font-bold text-zinc-400 hover:text-white transition-colors disabled:opacity-50"
                >
                  {t('common.actions.cancel')}
                </button>
                <button
                  onClick={() => handleDelete(deletingId)}
                  disabled={isDeleting}
                  className={`flex-1 px-4 py-3 text-sm font-bold text-white bg-rose-600 rounded-xl hover:bg-rose-500 transition-all shadow-lg shadow-rose-600/20 disabled:opacity-50 inline-flex items-center justify-center gap-2`}
                >
                  {isDeleting ? <Zap className="w-4 h-4 animate-pulse" /> : null}
                  {t('common.actions.delete')}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
