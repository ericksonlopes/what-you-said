import React from 'react';
import { useTranslation } from 'react-i18next';
import { FileUp, Globe, Scan, UploadCloud, CheckCircle2, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface FileSourceFormProps {
  readonly fileInputMode: 'upload' | 'url';
  readonly setFileInputMode: (val: 'upload' | 'url') => void;
  readonly doOcr: boolean;
  readonly setDoOcr: (val: boolean) => void;
  readonly inputValue: string;
  readonly setInputValue: (val: string) => void;
  readonly selectedFile: File | null;
  readonly setSelectedFile: (val: File | null) => void;
  readonly isDragging: boolean;
  readonly handleDragOver: (e: React.DragEvent) => void;
  readonly handleDragLeave: (e: React.DragEvent) => void;
  readonly handleDrop: (e: React.DragEvent) => void;
  readonly handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  readonly uploadStatus: 'idle' | 'chunking' | 'vectorizing' | 'done';
  readonly progress: number;
}

export function FileSourceForm({
  fileInputMode,
  setFileInputMode,
  doOcr,
  setDoOcr,
  inputValue,
  setInputValue,
  selectedFile,
  setSelectedFile,
  isDragging,
  handleDragOver,
  handleDragLeave,
  handleDrop,
  handleFileChange,
  uploadStatus,
  progress
}: FileSourceFormProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="flex p-0.5 bg-black/40 rounded-xl border border-zinc-800/50 w-full mb-4">
        <button
          type="button"
          onClick={() => setFileInputMode('upload')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-lg transition-all ${
            fileInputMode === 'upload' ? 'bg-zinc-800 text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          <FileUp className="w-3.5 h-3.5" />
          {t('common.actions.upload')}
        </button>
        <button
          type="button"
          onClick={() => setFileInputMode('url')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-lg transition-all ${
            fileInputMode === 'url' ? 'bg-zinc-800 text-emerald-400 shadow-sm' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          <Globe className="w-3.5 h-3.5" />
          URL
        </button>
      </div>

      <div className="bg-black/40 rounded-xl border border-zinc-800/50 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg transition-colors ${doOcr ? 'bg-emerald-500/10 text-emerald-400' : 'bg-zinc-800/80 text-zinc-500'}`}>
              <Scan className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">{t('ingestion.options.ocr.label')}</h4>
              <p className="text-xs text-zinc-400 font-medium">{t('ingestion.options.ocr.description')}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setDoOcr(!doOcr)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none ${
              doOcr ? 'bg-emerald-500' : 'bg-zinc-700'
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${doOcr ? 'translate-x-6' : 'translate-x-1'}`} />
          </button>
        </div>
      </div>

      {fileInputMode === 'upload' ? (
        <label
          htmlFor="file-upload"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`relative group h-64 rounded-2xl border-2 border-dashed transition-all duration-300 flex flex-col items-center justify-center p-8 bg-black/20 overflow-hidden cursor-pointer ${
            isDragging ? 'border-emerald-500 bg-emerald-500/5' : 'border-zinc-800 hover:border-zinc-700 hover:bg-black/30'
          }`}
        >
          <input id="file-upload" type="file" className="hidden" onChange={handleFileChange} />
          
          {selectedFile ? (
            <div className="relative z-10 flex flex-col items-center text-center animate-in zoom-in-95 duration-200 w-full">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4 border border-emerald-500/20 shadow-lg">
                <CheckCircle2 className="w-8 h-8 text-emerald-400" />
              </div>
              <h4 className="text-sm font-bold text-zinc-200 mb-1 truncate max-w-full px-4">{selectedFile.name}</h4>
              <p className="text-[11px] text-zinc-500 font-medium mb-4">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
              <button
                type="button"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); setSelectedFile(null); }}
                className="pointer-events-auto px-4 py-1.5 text-[11px] font-black text-rose-400 border border-rose-500/20 bg-rose-500/5 rounded-lg hover:bg-rose-500/10 transition-colors uppercase tracking-widest"
              >
                {t('common.actions.remove')}
              </button>
            </div>
          ) : (
            <div className="relative z-10 flex flex-col items-center pointer-events-none">
              <div className="w-16 h-16 rounded-3xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-5 group-hover:scale-110 group-hover:border-emerald-500/30 transition-all duration-500">
                <UploadCloud className="w-8 h-8 text-zinc-600 group-hover:text-emerald-500 transition-colors" />
              </div>
              <div className="text-center space-y-1">
                <p className="text-sm font-bold text-zinc-200">{t('ingestion.options.types.file_upload')}</p>
                <p className="text-[11px] text-zinc-500 font-medium">{t('ingestion.options.types.file_upload_desc')}</p>
              </div>
            </div>
          )}
        </label>
      ) : (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <label className="text-sm font-medium text-zinc-300" htmlFor="file-url">
            {t('ingestion.options.types.file_url')}
          </label>
          <input
            id="file-url"
            type="url"
            required
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="https://example.com/document.pdf"
            className="w-full bg-black/40 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-zinc-200 focus:outline-none focus:border-emerald-500/50 transition-all placeholder:text-zinc-600 shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)]"
          />
        </div>
      )}

      {/* Progress View */}
      <AnimatePresence>
        {uploadStatus !== 'idle' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute inset-x-0 bottom-0 top-0 z-20 bg-[#121212]/95 backdrop-blur-md flex flex-col items-center justify-center p-8 text-center"
          >
            <div className="relative mb-8">
              <svg className="w-32 h-32 transform -rotate-90">
                <circle cx="64" cy="64" r="58" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-zinc-900" />
                <circle
                  cx="64"
                  cy="64"
                  r="58"
                  stroke="currentColor"
                  strokeWidth="8"
                  fill="transparent"
                  strokeDasharray={364.42}
                  strokeDashoffset={364.42 * (1 - progress / 100)}
                  strokeLinecap="round"
                  className="text-emerald-500 transition-all duration-700 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center bg-black/20 rounded-full blur-xl animate-pulse" />
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-3xl font-black text-white font-mono">{progress}%</span>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-black text-white tracking-tight uppercase">
                {uploadStatus === 'chunking' ? t('ingestion.status.processing') : t('ingestion.status.indexing')}
              </h3>
              <p className="text-zinc-500 text-sm max-w-xs leading-relaxed font-medium">
                {uploadStatus === 'chunking' ? t('ingestion.status.processing_desc') : t('ingestion.status.indexing_desc')}
              </p>
            </div>

            <div className="mt-8 flex items-center gap-3 px-6 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
              <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
              <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">{t('common.actions.syncing')}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
