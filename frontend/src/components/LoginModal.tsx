import React from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'motion/react';
import { LogIn, Github, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../store/AuthContext';

export function LoginModal({ isOpen }: { isOpen: boolean }) {
  const { t } = useTranslation();
  const { getLoginUrl } = useAuth();

  const handleGoogleLogin = async () => {
    try {
      const url = await getLoginUrl();
      window.location.href = url;
    } catch (err) {
      console.error('Failed to get login URL:', err);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/80 backdrop-blur-md"
          />
          
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="relative w-full max-w-md overflow-hidden rounded-3xl border border-white/10 bg-zinc-900/50 p-8 shadow-2xl backdrop-blur-2xl"
          >
            {/* Background Glow */}
            <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-emerald-500/10 blur-[100px]" />
            <div className="absolute -right-20 -bottom-20 h-64 w-64 rounded-full bg-teal-500/10 blur-[100px]" />

            <div className="relative flex flex-col items-center text-center">
              <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_30px_rgba(16,185,129,0.1)]">
                <ShieldCheck className="h-10 w-10 text-emerald-400" />
              </div>

              <h2 className="mb-2 text-3xl font-black tracking-tight text-white font-sans">
                WhatYouSaid
              </h2>
              <p className="mb-8 text-zinc-400 text-sm font-medium leading-relaxed max-w-[280px]">
                {t('auth.login_description', 'Please sign in to access your vectorized knowledge hub.')}
              </p>

              <button
                onClick={handleGoogleLogin}
                className="group relative flex w-full items-center justify-center gap-3 rounded-2xl bg-white px-6 py-4 text-sm font-bold text-black transition-all hover:bg-zinc-100 active:scale-[0.98] shadow-xl shadow-white/5"
              >
                <div className="flex items-center justify-center bg-white p-1 rounded-full">
                  <svg width="20" height="20" viewBox="0 0 24 24">
                   <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                   <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                   <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l3.66-2.84z"/>
                   <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                </div>
                {t('auth.login_with_google', 'Continue with Google')}
              </button>

              <div className="mt-8 flex items-center justify-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-zinc-600">
                <div className="h-px w-8 bg-zinc-800" />
                SECURE ACCESS
                <div className="h-px w-8 bg-zinc-800" />
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
