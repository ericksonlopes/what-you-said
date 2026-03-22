import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAppContext } from '../store/AppContext';
import { Subject } from '../types';
import { api } from '../services/api';

export function useIngestion() {
  const { t } = useTranslation();
  const { addToast, addOptimisticJob, removeOptimisticJob, refreshJobs } = useAppContext();

  /**
   * Universal ingestion function that handles optimistic updates and refreshes
   */
  const startIngestion = useCallback(async (
    inputType: 'youtube' | 'web' | 'file' | 'file_url',
    params: {
      url?: string;
      subject: Subject;
      tokensPerChunk?: number;
      tokensOverlap?: number;
      youtubeDataType?: 'video' | 'playlist';
      file?: File;
      doOcr?: boolean;
      cssSelector?: string;
    }
  ) => {
    const { subject, tokensPerChunk, tokensOverlap, url, youtubeDataType, file, doOcr, cssSelector } = params;
    if (!subject) return;

    // 1. Immediate feedback
    const displayType = inputType.includes('file') ? 'file' : inputType;
    addToast(t('notifications.ingestion.started', { type: displayType, name: subject.name }), 'info');
    
    // 2. Add optimistic job card
    const title = file ? file.name : (url || `Ingesting ${displayType}...`);
    const optJobId = addOptimisticJob(title, file ? file.name : url);

    try {
      let response;
      if (inputType === 'youtube') {
        response = await api.ingestYoutube({
          video_url: url!,
          subject_id: subject.id,
          tokens_per_chunk: tokensPerChunk,
          tokens_overlap: tokensOverlap,
          data_type: youtubeDataType,
        });
      } else if (inputType === 'web') {
        response = await api.ingestWeb({
          url: url!,
          subject_id: subject.id,
          tokens_per_chunk: tokensPerChunk,
          tokens_overlap: tokensOverlap,
          css_selector: cssSelector,
          language: 'pt'
        });
      } else if (inputType === 'file_url') {
        response = await (api as any).ingestFileByUrl({
          file_url: url!,
          subject_id: subject.id,
          tokens_per_chunk: tokensPerChunk,
          tokens_overlap: tokensOverlap,
          do_ocr: doOcr,
          language: 'pt'
        });
      } else if (inputType === 'file' && file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('subject_id', subject.id);
        formData.append('tokens_per_chunk', (tokensPerChunk || 512).toString());
        formData.append('tokens_overlap', (tokensOverlap || 50).toString());
        formData.append('do_ocr', (doOcr || false).toString());
        formData.append('language', 'pt');
        response = await api.ingestFile(formData);
      }

      addToast(t('notifications.ingestion.complete', { name: subject.name }), 'success');
      return response;
    } catch (error: any) {
      console.error(`${inputType} ingestion error:`, error);
      
      // Remove optimistic job on error
      removeOptimisticJob(optJobId);

      const errorMsg = error?.message === 'DUPLICATE_SOURCE' 
        ? t('notifications.ingestion.duplicate') 
        : t('notifications.ingestion.error');
      addToast(errorMsg, 'error');
      throw error;
    } finally {
      // 3. Refresh jobs to replace optimistic card (if it hasn't been removed yet)
      await refreshJobs();
    }
  }, [addToast, addOptimisticJob, removeOptimisticJob, refreshJobs, t]);

  return { startIngestion };
}
