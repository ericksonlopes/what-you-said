import React from 'react';
import { useAppContext } from '../store/AppContext';
import { CheckCircle2, Info, XCircle, X } from 'lucide-react';

export function ToastContainer() {
  const { toasts, removeToast } = useAppContext();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none">
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const isError = toast.type === 'error';
        
        const Icon = isSuccess ? CheckCircle2 : isError ? XCircle : Info;
        const iconColor = isSuccess ? 'text-emerald-400' : isError ? 'text-rose-400' : 'text-blue-400';
        const bgColor = isSuccess ? 'bg-emerald-500/10' : isError ? 'bg-rose-500/10' : 'bg-blue-500/10';
        const borderColor = isSuccess ? 'border-emerald-500/20' : isError ? 'border-rose-500/20' : 'border-blue-500/20';

        return (
          <div
            key={toast.id}
            className="pointer-events-auto flex items-center gap-3 p-4 rounded-xl border border-border-subtle bg-[#18181b] shadow-2xl animate-in slide-in-from-bottom-5 fade-in duration-300 max-w-sm w-full"
          >            <div className={`p-1.5 rounded-lg ${bgColor} ${borderColor} border flex-shrink-0 mt-0.5`}>
              <Icon className={`w-4 h-4 ${iconColor}`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-zinc-200 leading-relaxed">
                {toast.message}
              </p>
            </div>
            <button 
              onClick={() => removeToast(toast.id)}
              className="p-1 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
