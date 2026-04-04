import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  X, Settings, Activity, Database, 
  Box, Server, Terminal, 
  CheckCircle2, XCircle, Loader2,
  Languages
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';

interface SettingsModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { t, i18n } = useTranslation();
  const [settingsData, setSettingsData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const fetchSettings = async () => {
        setLoading(true);
        try {
          const data = await api.fetchSettings();
          setSettingsData(data);
        } catch (err) {
          console.error('Failed to fetch settings:', err);
        } finally {
          setLoading(false);
        }
      };
      fetchSettings();
    }
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="relative w-full max-w-3xl bg-zinc-950/90 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[650px] max-h-[90vh] z-10"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/5 bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                  <Settings className="w-5 h-5 text-zinc-300" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white tracking-tight">{t('settings.title')}</h2>
                  <p className="text-xs text-zinc-500">{t('settings.subtitle')}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-full text-zinc-500 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
              {/* Language Selection */}
              <div className="mb-10">
                <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4 px-1 flex items-center gap-2">
                  <Languages className="w-4 h-4" />
                  {t('settings.language.title')}
                </h3>
                <div className="flex gap-3">
                  <button
                    onClick={() => i18n.changeLanguage('en')}
                    className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border transition-all ${
                      i18n.language.startsWith('en')
                        ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
                        : 'bg-zinc-900/50 border-zinc-800 text-zinc-500 hover:border-zinc-700'
                    }`}
                  >
                    <span className="text-xs font-bold uppercase tracking-widest">{t('settings.language.en')}</span>
                  </button>
                  <button
                    onClick={() => i18n.changeLanguage('pt-BR')}
                    className={`flex-1 flex items-center justify-center gap-2 p-3 rounded-xl border transition-all ${
                      i18n.language === 'pt-BR'
                        ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400'
                        : 'bg-zinc-900/50 border-zinc-800 text-zinc-500 hover:border-zinc-700'
                    }`}
                  >
                    <span className="text-xs font-bold uppercase tracking-widest">{t('settings.language.pt-BR')}</span>
                  </button>
                </div>
              </div>

              {loading && !settingsData ? (
                <div className="flex items-center justify-center h-full gap-3 text-zinc-500 py-20">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {t('activity.loading')}
                </div>
              ) : (
                <UnifiedSettings settings={settingsData} />
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

function UnifiedSettings({ settings }: { readonly settings: any }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-10 pb-4">
      {/* Bento Grid Info */}
      <div>
        <h3 className="text-lg font-medium text-white mb-4">{t('settings.sections.environment')}</h3>
        <div className="grid grid-cols-1 gap-4">
          <DetailedEnvCard 
            title={t('settings.tabs.api')} 
            value={settings?.app?.env || "UNKNOWN"} 
            description={t('settings.labels.api_desc')}
            details={[
              { label: t('settings.labels.endpoint'), value: globalThis.location.origin },
              { label: t('settings.labels.environment'), value: settings?.app?.env || 'n/a' }
            ]}
            icon={Terminal} 
            color="text-purple-400" 
            bg="bg-purple-500/10" 
            checkLabel={t('settings.checks.ping_api')}
            componentId="api"
          />
          <DetailedEnvCard 
            title={t('settings.labels.embedding_model')} 
            value={settings?.model?.name?.split('/').pop() || t('common.status.na')} 
            description={t('settings.labels.model_desc')}
            details={[
              { label: t('settings.labels.model_path'), value: settings?.model?.name || t('common.status.na') },
              { label: t('sources.table.status'), value: t('common.status.loaded') }
            ]}
            icon={Box} 
            color="text-emerald-400" 
            bg="bg-emerald-500/10" 
            checkLabel={t('settings.checks.test_model')}
            componentId="model"
          />
          <DetailedEnvCard 
            title={t('settings.labels.store_type')} 
            value={settings?.vector?.store_type?.toUpperCase() || t('common.status.na')} 
            description={t('settings.labels.production_ready')}
            details={
              settings?.vector?.store_type === 'qdrant' ? [
                { label: t('settings.labels.host'), value: settings?.vector?.qdrant_host || t('common.status.na') },
                { label: t('settings.labels.port'), value: settings?.vector?.qdrant_port?.toString() || t('common.status.na') },
                { label: t('settings.labels.collection'), value: settings?.vector?.qdrant_collection || t('common.status.na') }
              ] : [
                { label: t('settings.labels.host'), value: settings?.vector?.weaviate_host || t('common.status.na') },
                { label: t('settings.labels.port'), value: settings?.vector?.weaviate_port?.toString() || t('common.status.na') },
                { label: t('settings.labels.collection'), value: settings?.vector?.weaviate_collection || t('common.status.na') }
              ]
            }
            icon={Database} 
            color="text-blue-400" 
            bg="bg-blue-500/10" 
            checkLabel={t('settings.checks.test_store')}
            componentId="vector"
          />
          <DetailedEnvCard 
            title={t('settings.labels.sql_desc')} 
            value={settings?.sql?.type || t('common.status.na')} 
            description={t('settings.labels.sql_desc')}
            details={[
              { label: t('settings.labels.database'), value: settings?.sql?.database || t('common.status.na') },
              { label: t('settings.labels.type'), value: settings?.sql?.type || t('common.status.na') }
            ]}
            icon={Server} 
            color="text-amber-400" 
            bg="bg-amber-500/10" 
            checkLabel={t('settings.checks.test_db')}
            componentId="sql"
          />
          <DetailedEnvCard 
            title="Redis" 
            value={settings?.redis?.host || t('common.status.na')} 
            description={t('settings.labels.redis_desc')}
            details={[
              { label: t('settings.labels.host'), value: settings?.redis?.host || t('common.status.na') },
              { label: t('settings.labels.port'), value: settings?.redis?.port?.toString() || t('common.status.na') },
              { label: "DB", value: settings?.redis?.db?.toString() || '0' }
            ]}
            icon={Activity} 
            color="text-red-400" 
            bg="bg-red-500/10" 
            checkLabel={t('settings.checks.test_redis')}
            componentId="redis"
          />
        </div>
      </div>
    </div>
  );
}

function DetailedEnvCard({ 
  title, 
  value, 
  description,
  details,
  icon: Icon, 
  color, 
  bg, 
  checkLabel = "Check",
  componentId
}: { 
  readonly title: string, 
  readonly value: string, 
  readonly description: string,
  readonly details?: { readonly label: string, readonly value: string }[],
  readonly icon: any, 
  readonly color: string, 
  readonly bg: string, 
  readonly checkLabel?: string,
  readonly componentId: string
}) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<'unknown' | 'loading' | 'success' | 'error'>('unknown');
  const [latency, setLatency] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCheck = async () => {
    if (status === 'loading') return;
    setStatus('loading');
    setLatency(null);
    setErrorMsg(null);
    
    try {
      const result = await api.checkHealth(componentId);
      if (result.status === 'success') {
        setStatus('success');
        setLatency(result.latency_ms);
      } else {
        setStatus('error');
        setErrorMsg(result.message);
      }
    } catch (err: any) {
      setStatus('error');
      setErrorMsg(err.message);
    }
  };

  useEffect(() => {
    handleCheck();
  }, []);

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-4 p-4 rounded-xl border border-white/5 bg-[#0d0d0d] shadow-sm hover:border-white/10 transition-colors">
      {/* Icon & Title Group */}
      <div className="flex items-center gap-3 min-w-[200px]">
        <div className={`p-2 rounded-lg shrink-0 ${bg}`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
        <div>
          <h4 className="text-sm font-medium text-zinc-200">{title}</h4>
          <span className="text-[10px] text-zinc-500 uppercase tracking-wider">{value}</span>
        </div>
      </div>

      {/* Details - Horizontal List */}
      <div className="flex-1 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-400">
        {details?.map((detail) => (
          <div key={detail.label} className="flex gap-1.5 items-center">
            <span className="text-zinc-600">{detail.label}:</span>
            <span className="font-mono text-zinc-300">{detail.value}</span>
          </div>
        ))}
      </div>
      
      {/* Status & Action */}
      <div className="flex items-center gap-4 shrink-0">
            <div className="flex items-center gap-2 min-w-[100px] justify-end">
              {status === 'unknown' && (
                <>
                  <div className="w-1.5 h-1.5 rounded-full bg-zinc-500"></div>
                  <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">{t('common.status.unknown')}</span>
                </>
              )}
              {status === 'loading' && (
                <>
                  <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                  <span className="text-[10px] text-blue-400 uppercase tracking-wider font-medium">{t('common.actions.syncing')}</span>
                </>
              )}
              {status === 'success' && (
                <>
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span className="text-[10px] text-emerald-400 uppercase tracking-wider font-medium">{t('common.status.online')} {latency !== null && `(${latency}ms)`}</span>
                </>
              )}
              {status === 'error' && (
                <>
                  <span title={errorMsg || ''}>
                    <XCircle className="w-3 h-3 text-red-400" />
                  </span>
                  <span className="text-[10px] text-red-400 uppercase tracking-wider font-medium">{t('common.status.offline')}</span>
                </>
              )}
            </div>

        <button 
          onClick={handleCheck}
          disabled={status === 'loading'}
          className="p-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-zinc-300 transition-colors disabled:opacity-50"
          title={checkLabel}
        >
          <Activity className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
