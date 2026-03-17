import React, { useState, useEffect } from 'react';
import { 
  X, Settings, Activity, Database, 
  Box, Server, Terminal, Key, Shield, 
  CheckCircle2, XCircle, Loader2, Eye, EyeOff
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { api } from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
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

  if (!isOpen) return null;

  return (
    <AnimatePresence>
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
          className="relative w-full max-w-3xl bg-zinc-950/90 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[650px] max-h-[90vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-white/5 bg-white/[0.02]">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/5 rounded-lg border border-white/10">
                <Settings className="w-5 h-5 text-zinc-300" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white tracking-tight">Settings</h2>
                <p className="text-xs text-zinc-500">Manage your local environment configurations</p>
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
            {loading && !settingsData ? (
              <div className="flex items-center justify-center h-full gap-3 text-zinc-500">
                <Loader2 className="w-5 h-5 animate-spin" />
                Loading settings...
              </div>
            ) : (
              <UnifiedSettings settings={settingsData} />
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

function UnifiedSettings({ settings }: { settings: any }) {
  return (
    <div className="space-y-10 pb-4">
      {/* Bento Grid Info */}
      <div>
        <h3 className="text-lg font-medium text-white mb-4">Environment Details</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <DetailedEnvCard 
            title="Backend API" 
            value={settings?.app?.env || "UNKNOWN"} 
            description="Core API server connection"
            details={[
              { label: "Endpoint", value: window.location.origin },
              { label: "Environment", value: settings?.app?.env || 'n/a' }
            ]}
            icon={Terminal} 
            color="text-purple-400" 
            bg="bg-purple-500/10" 
            checkLabel="Ping API"
            componentId="api"
          />
          <DetailedEnvCard 
            title="Embedding Model" 
            value={settings?.model?.name?.split('/').pop() || "n/a"} 
            description="Text vectorization model"
            details={[
              { label: "Model Path", value: settings?.model?.name || 'n/a' },
              { label: "Status", value: "Loaded" }
            ]}
            icon={Box} 
            color="text-emerald-400" 
            bg="bg-emerald-500/10" 
            checkLabel="Test Model"
            componentId="model"
          />
          <DetailedEnvCard 
            title="Vector Store" 
            value={settings?.vector?.store_type?.toUpperCase() || "n/a"} 
            description="Semantic search database"
            details={[
              { label: "Host", value: settings?.vector?.weaviate_host || 'n/a' },
              { label: "Port", value: settings?.vector?.weaviate_port?.toString() || 'n/a' },
              { label: "Collection", value: settings?.vector?.weaviate_collection || 'n/a' }
            ]}
            icon={Database} 
            color="text-blue-400" 
            bg="bg-blue-500/10" 
            checkLabel="Test Store"
            componentId="vector"
          />
          <DetailedEnvCard 
            title="SQL Driver" 
            value={settings?.sql?.type || "n/a"} 
            description="Relational database"
            details={[
              { label: "Database", value: settings?.sql?.database || 'n/a' },
              { label: "Type", value: settings?.sql?.type || 'n/a' }
            ]}
            icon={Server} 
            color="text-amber-400" 
            bg="bg-amber-500/10" 
            checkLabel="Test DB"
            componentId="sql"
          />
        </div>
      </div>

      {/* Real-time Metrics (Mock for now but could be connected) */}
      <div>
        <h3 className="text-lg font-medium text-white mb-4">Instance Statistics</h3>
        <div className="grid grid-cols-3 gap-4">
          <MetricCard title="System Environment" value={settings?.app?.env?.toUpperCase() || "N/A"} trend="Stable" />
          <MetricCard title="Log Levels" value={settings?.app?.log_levels?.split(',')[0] || "INFO"} trend="Active" />
          <MetricCard title="Store Type" value={settings?.vector?.store_type || "N/A"} trend="Production ready" />
        </div>
      </div>

      {/* API Keys */}
      <div>
        <h3 className="text-lg font-medium text-white mb-4">Internal Identifiers</h3>
        <div className="space-y-3">
          <InfoRow label="Collection Name" value={settings?.vector?.weaviate_collection || "n/a"} />
          <InfoRow label="Embedding Model" value={settings?.model?.name || "n/a"} />
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, trend }: { title: string, value: string, trend: string }) {
  return (
    <div className="p-4 rounded-xl border border-white/5 bg-[#0d0d0d] shadow-sm">
      <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider block mb-1">{title}</span>
      <span className="text-xl font-semibold text-zinc-100 block mb-1 truncate" title={value}>{value}</span>
      <span className="text-[10px] text-zinc-500">{trend}</span>
    </div>
  );
}

function InfoRow({ label, value }: { label: string, value: string }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-xl border border-white/5 bg-[#0d0d0d] shadow-sm">
      <span className="text-sm font-medium text-zinc-400">{label}</span>
      <span className="text-xs font-mono text-zinc-500">{value}</span>
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
  title: string, 
  value: string, 
  description: string,
  details?: { label: string, value: string }[],
  icon: any, 
  color: string, 
  bg: string, 
  checkLabel?: string,
  componentId: string
}) {
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

  return (
    <div className="flex flex-col p-5 rounded-xl border border-white/5 bg-[#0d0d0d] shadow-sm hover:border-white/10 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${bg}`}>
            <Icon className={`w-5 h-5 ${color}`} />
          </div>
          <div>
            <h4 className="text-sm font-medium text-zinc-200">{title}</h4>
            <span className="text-xs text-zinc-500">{description}</span>
          </div>
        </div>
        <span className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider rounded-md bg-white/5 text-zinc-300 border border-white/10">
          {value}
        </span>
      </div>
      
      {details && details.length > 0 && (
        <div className="mb-4 p-3 rounded-lg bg-white/[0.02] border border-white/5 text-xs text-zinc-400 space-y-2">
          {details.map((detail, idx) => (
            <div key={idx} className="flex justify-between items-center">
              <span className="text-zinc-500">{detail.label}:</span>
              <span className="font-mono text-zinc-300">{detail.value}</span>
            </div>
          ))}
        </div>
      )}
      
      <div className="mt-auto pt-4 border-t border-white/5 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {status === 'unknown' && (
              <>
                <div className="w-1.5 h-1.5 rounded-full bg-zinc-500"></div>
                <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">Status Unknown</span>
              </>
            )}
            {status === 'loading' && (
              <>
                <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                <span className="text-[10px] text-blue-400 uppercase tracking-wider font-medium">Checking...</span>
              </>
            )}
            {status === 'success' && (
              <>
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span className="text-[10px] text-emerald-400 uppercase tracking-wider font-medium">Online {latency && `(${latency}ms)`}</span>
              </>
            )}
            {status === 'error' && (
              <>
                <XCircle className="w-3 h-3 text-red-400" />
                <span className="text-[10px] text-red-400 uppercase tracking-wider font-medium">Offline</span>
              </>
            )}
          </div>
          <button 
            onClick={handleCheck}
            disabled={status === 'loading'}
            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-medium text-zinc-300 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            title={checkLabel}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>{checkLabel}</span>
          </button>
        </div>
        
        {status === 'error' && errorMsg && (
          <p className="text-[10px] text-red-400/70 italic break-words">
            {errorMsg}
          </p>
        )}
      </div>
    </div>
  );
}
