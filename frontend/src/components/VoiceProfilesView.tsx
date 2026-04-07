import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  User,
  Mic,
  Trash2,
  X,
  Clock,
  AudioLines,
  AlertCircle,
  FolderOpen,
  FileAudio,
  RefreshCw,
  Plus,
  Search,
  Play,
  Square,
  Loader2,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useAppContext } from '../store/AppContext';
import { api } from '../services/api';
import { AddVoiceProfileModal } from './modals/AddVoiceProfileModal';

// --- Types ---
interface AudioFile {
  key: string;
  size: number;
  last_modified: string;
  path: string;
}

type VoiceProfileStatus = 'ready' | 'processing' | 'failed';

interface VoiceProfile {
  id: string;
  name: string;
  audios_path: string;
  samples_count: number;
  created_at: string;
  status?: VoiceProfileStatus;
  status_message?: string | null;
}

const StatusBadge: React.FC<{ status?: VoiceProfileStatus; message?: string | null }> = ({ status, message }) => {
  const { t } = useTranslation();
  const s = status || 'ready';
  const config: Record<VoiceProfileStatus, { icon: React.ReactNode; cls: string; label: string }> = {
    processing: {
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
      cls: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
      label: t('voices.status.processing'),
    },
    ready: {
      icon: <CheckCircle2 className="w-3 h-3" />,
      cls: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
      label: t('voices.status.ready'),
    },
    failed: {
      icon: <XCircle className="w-3 h-3" />,
      cls: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
      label: t('voices.status.failed'),
    },
  };
  const c = config[s];
  return (
    <div
      title={message || undefined}
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg border text-[9px] font-black uppercase tracking-widest ${c.cls}`}
    >
      {c.icon}
      <span>{c.label}</span>
    </div>
  );
};

// --- Sub-components ---

const VoiceCard = ({
  profile,
  onClick,
  onDelete
}: {
  profile: VoiceProfile;
  onClick: (p: VoiceProfile) => void;
  onDelete: (name: string) => void;
}) => {
  const { t } = useTranslation();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -4, backgroundColor: 'rgba(39, 39, 42, 0.8)' }}
      className="bg-zinc-900/40 border border-white/5 rounded-2xl p-5 cursor-pointer group transition-all"
      onClick={() => onClick(profile)}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 rounded-xl bg-zinc-800 border border-white/5 group-hover:border-emerald-500/30 group-hover:bg-emerald-500/5 transition-all">
          <User className="w-6 h-6 text-zinc-500 group-hover:text-emerald-400" />
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(profile.name); }}
          className="p-2 text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
          title={t('common.actions.delete')}
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <h3 className="text-lg font-bold text-white mb-2 truncate group-hover:text-emerald-400 transition-colors">
        {profile.name}
      </h3>

      <StatusBadge status={profile.status} message={profile.status_message} />

      <div className="flex flex-col gap-2.5 mt-4">
        <div className="flex items-center gap-2 text-zinc-500 text-xs font-medium">
          <AudioLines className="w-3.5 h-3.5 text-emerald-500/70" />
          <span>{t('voices.status.samples', { count: profile.samples_count })}</span>
        </div>
        <div className="flex items-center gap-2 text-zinc-500 text-xs font-medium">
          <FolderOpen className="w-3.5 h-3.5 text-zinc-600" />
          <span className="truncate font-mono opacity-80" title={profile.audios_path}>{profile.audios_path}</span>
        </div>
        <div className="flex items-center gap-2 text-zinc-600 text-[10px] uppercase tracking-wider font-bold mt-2">
          <Clock className="w-3 h-3" />
          <span>{new Date(profile.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </motion.div>
  );
};

const VoiceDetailsModal = ({
  profile,
  onClose,
  onDeleteFile,
}: {
  profile: VoiceProfile;
  onClose: () => void;
  onDeleteFile: (key: string) => void;
}) => {
  const { t } = useTranslation();
  const { addToast } = useAppContext();
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [playingKey, setPlayingKey] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let mounted = true;
    api.fetchVoiceAudioFiles(profile.id)
      .then(data => {
        if (mounted) {
          setAudioFiles(data);
          setLoading(false);
        }
      })
      .catch(err => {
        console.error('Failed to fetch audio files:', err);
        if (mounted) setLoading(false);
      });
    return () => { 
      mounted = false; 
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [profile.id]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileName = (key: string) => {
    const parts = key.split('/');
    return parts[parts.length - 1];
  };

  const togglePlay = async (key: string) => {
    if (playingKey === key) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlayingKey(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    try {
      setPlayingKey(key);
      const result = await api.fetchVoiceAudioUrl(key);
      const url = result?.url;
      if (url) {
        const audio = new Audio(url);
        audioRef.current = audio;
        audio.onended = () => {
          setPlayingKey(null);
          audioRef.current = null;
        };
        audio.onerror = () => {
          setPlayingKey(null);
          audioRef.current = null;
          addToast(t('diarization.notifications.playback_error'), 'error');
        };
        await audio.play();
      }
    } catch (err) {
      console.error('Failed to play audio:', err);
      setPlayingKey(null);
      addToast(t('diarization.notifications.audio_fetch_error'), 'error');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/80 backdrop-blur-md"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative bg-zinc-950 border border-white/10 w-full max-w-2xl rounded-3xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]"
      >
        <div className="p-6 border-b border-white/5 flex items-center justify-between bg-zinc-900/30">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20">
              <User className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-xl font-black text-white">{profile.name}</h2>
              <p className="text-zinc-500 text-[10px] font-bold uppercase tracking-[0.2em]">{t('voices.modal.title')}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-zinc-500 hover:text-white hover:bg-white/5 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-3 bg-emerald-500/5 border-b border-white/5">
          <div className="flex items-center gap-3 text-emerald-400/70 text-xs font-medium">
            <FolderOpen className="w-4 h-4" />
            <span className="font-mono truncate">{profile.audios_path}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-zinc-950">
          <div>
            <h3 className="text-[10px] font-black text-zinc-500 mb-4 flex items-center gap-2 uppercase tracking-[0.2em]">
              <FileAudio className="w-3.5 h-3.5" />
              {t('voices.modal.audio_files_title')}
            </h3>
            <div className="space-y-2">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-16 gap-4">
                  <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
                  <p className="text-zinc-500 text-[10px] font-bold uppercase tracking-[0.3em] animate-pulse">
                    {t('voices.modal.loading')}
                  </p>
                </div>
              ) : audioFiles.map((file) => (
                <div
                  key={file.key}
                  className="flex items-center justify-between p-4 bg-zinc-900/30 border border-white/5 rounded-2xl group hover:border-emerald-500/20 hover:bg-zinc-900/60 transition-all"
                >
                  <div className="flex items-center gap-4 overflow-hidden">
                    <button
                      onClick={() => togglePlay(file.key)}
                      className={`p-2.5 rounded-xl transition-all shrink-0 ${playingKey === file.key ? 'bg-emerald-500 text-black' : 'bg-zinc-800 text-zinc-400 group-hover:text-emerald-400 group-hover:bg-emerald-500/10'}`}
                    >
                      {playingKey === file.key ? <Square className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
                    </button>
                    <div className="overflow-hidden">
                      <span className="text-sm font-bold text-zinc-200 block truncate">{getFileName(file.key)}</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">{formatSize(file.size)}</span>
                        <span className="text-zinc-700 text-[10px]">•</span>
                        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">{new Date(file.last_modified).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      onDeleteFile(file.key);
                      setAudioFiles(prev => prev.filter(f => f.key !== file.key));
                    }}
                    className="p-2.5 text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-all opacity-0 group-hover:opacity-100 shrink-0"
                    title={t('voices.modal.delete_file')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
              {!loading && audioFiles.length === 0 && (
                <div className="text-center py-16 border-2 border-dashed border-white/5 rounded-3xl bg-zinc-900/10">
                  <FileAudio className="w-10 h-10 text-zinc-800 mx-auto mb-4" />
                  <p className="text-zinc-500 text-sm font-medium">{t('voices.modal.no_files')}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

// --- Main View ---

export function VoiceProfilesView() {
  const { t } = useTranslation();
  const { addToast, selectedSubjects, lastEvent } = useAppContext();
  const [voices, setVoices] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVoice, setSelectedVoice] = useState<VoiceProfile | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  const fetchVoices = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.fetchVoiceProfiles();
      setVoices(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
      addToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchVoices();
  }, [fetchVoices]);

  // Refetch whenever a voice-scoped SSE event arrives (train_started,
  // train_progress, train, train_failed) so the status badge updates live.
  useEffect(() => {
    if (lastEvent && (lastEvent as any).type === 'voice') {
      fetchVoices();
    }
  }, [lastEvent, fetchVoices]);

  const handleDeleteProfile = useCallback(async (name: string) => {
    try {
      await api.deleteVoiceProfile(name);
      setVoices(prev => prev.filter(v => v.name !== name));
      addToast(t('voices.notifications.delete_success'), 'success');
    } catch (err: any) {
      addToast(err.message || t('voices.notifications.delete_error'), 'error');
    }
  }, [t, addToast]);

  const handleDeleteFile = useCallback(async (s3Key: string) => {
    if (!selectedVoice) return;

    try {
      await api.deleteVoiceAudioFile(s3Key);

      setVoices(prev => prev.map(v => v.id === selectedVoice.id ? {
        ...v,
        samples_count: Math.max(0, v.samples_count - 1)
      } : v));

      addToast(t('voices.notifications.delete_file_success'), 'success');
    } catch (err: any) {
      addToast(err.message || t('voices.notifications.delete_file_error'), 'error');
    }
  }, [selectedVoice, t, addToast]);

  const filteredVoices = useMemo(() => {
    if (!searchQuery) return voices;
    const lowerQuery = searchQuery.toLowerCase();
    return voices.filter(v => v.name.toLowerCase().includes(lowerQuery));
  }, [voices, searchQuery]);

  return (
    <div className="p-8 pt-10 max-w-7xl mx-auto h-full flex flex-col">
      <div className="mb-12 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-4">
          <div className="flex items-center gap-5">
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_30px_rgba(16,185,129,0.1)]">
              <Mic className="w-8 h-8 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-4xl font-black text-white tracking-tight leading-none uppercase">{t('voices.title')}</h2>
              <p className="text-zinc-500 text-sm mt-3 font-medium max-w-md leading-relaxed">{t('voices.subtitle')}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 group-focus-within:text-emerald-400 transition-colors" />
            <input
              type="text"
              placeholder={t('common.actions.search')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-11 pr-4 py-3 bg-zinc-900/50 border border-white/5 rounded-2xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500/50 transition-all w-full sm:w-64"
            />
          </div>
          
          <button
            onClick={() => setIsAddModalOpen(true)}
            disabled={selectedSubjects.length === 0}
            className={`flex items-center justify-center gap-2 px-6 py-3 rounded-2xl transition-all shadow-lg active:scale-95 font-black text-xs uppercase tracking-widest ${selectedSubjects.length === 0 ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed opacity-50' : 'bg-emerald-500 hover:bg-emerald-400 text-black shadow-emerald-500/20'}`}
            title={selectedSubjects.length === 0 ? t('common.hints.select_subject') : ''}
          >
            <Plus className="w-4 h-4" />
            <span>{t('voices.new_btn')}</span>
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1 pb-10">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-40 gap-6">
            <div className="relative">
              <RefreshCw className="w-12 h-12 text-emerald-500 animate-spin" />
              <div className="absolute inset-0 blur-xl bg-emerald-500/20 animate-pulse" />
            </div>
            <p className="text-zinc-500 font-black uppercase tracking-[0.4em] animate-pulse text-xs">
              {t('voices.loading')}
            </p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-40 text-center px-6">
            <div className="p-5 rounded-full bg-rose-500/10 mb-6">
              <AlertCircle className="w-12 h-12 text-rose-500" />
            </div>
            <h3 className="text-white font-black text-2xl mb-3">{t('voices.error_title')}</h3>
            <p className="text-zinc-500 max-w-sm leading-relaxed mb-8">{error}</p>
            <button
              onClick={fetchVoices}
              className="px-8 py-3 bg-white text-black rounded-2xl hover:bg-zinc-200 transition-all font-black text-sm uppercase tracking-wider"
            >
              {t('voices.retry')}
            </button>
          </div>
        ) : filteredVoices.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-40 text-center bg-zinc-900/10 border-2 border-dashed border-white/5 rounded-[3rem] px-6">
            <div className="w-24 h-24 rounded-3xl bg-zinc-900 border border-white/5 flex items-center justify-center mb-8 shadow-2xl rotate-3">
              {searchQuery ? <Search className="w-12 h-12 text-zinc-800 -rotate-3" /> : <User className="w-12 h-12 text-zinc-800 -rotate-3" />}
            </div>
            <h3 className="text-zinc-200 font-black text-2xl mb-3">{searchQuery ? t('common.actions.none_found') : t('voices.empty_title')}</h3>
            <p className="text-zinc-500 text-sm max-w-xs mx-auto leading-relaxed font-medium">
              {searchQuery ? t('common.actions.clear_filters') : t('voices.empty_subtitle')}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            <AnimatePresence mode="popLayout">
              {filteredVoices.map((voice) => (
                <VoiceCard
                  key={voice.id}
                  profile={voice}
                  onClick={setSelectedVoice}
                  onDelete={handleDeleteProfile}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <AnimatePresence>
        {selectedVoice && (
          <VoiceDetailsModal
            profile={selectedVoice}
            onClose={() => setSelectedVoice(null)}
            onDeleteFile={handleDeleteFile}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isAddModalOpen && (
          <AddVoiceProfileModal
            onClose={() => setIsAddModalOpen(false)}
            onSuccess={fetchVoices}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
