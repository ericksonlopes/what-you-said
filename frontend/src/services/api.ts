import { Subject, IngestionTask, ContentSource, ChatMessage, Chunk } from '../types';

const API_BASE_URL = '/rest';

async function handleResponseError(response: Response, defaultMessage: string) {
  if (response.ok) return;
  
  let errorMessage = defaultMessage;
  try {
    const data = await response.json();
    if (data && data.detail) {
      errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
  } catch (e) {
    // Ignore JSON parse errors and use default message
  }
  
  throw new Error(errorMessage);
}

export const api = {
  async fetchSubjects(): Promise<Subject[]> {
    const response = await fetch(`${API_BASE_URL}/subjects`);
    await handleResponseError(response, 'Failed to fetch subjects');
    return response.json();
  },

  async createSubject(name: string, description?: string, icon?: string): Promise<Subject> {
    const response = await fetch(`${API_BASE_URL}/subjects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, icon })
    });
    await handleResponseError(response, 'Failed to create subject');
    return response.json();
  },

  async updateSubject(id: string, name?: string, description?: string, icon?: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/subjects/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, icon })
    });
    await handleResponseError(response, 'Failed to update subject');
  },

  async deleteSubject(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/subjects/${id}`, {
      method: 'DELETE'
    });
    await handleResponseError(response, 'Failed to delete subject');
  },

  async fetchSources(): Promise<ContentSource[]> {
    const response = await fetch(`${API_BASE_URL}/sources`);
    await handleResponseError(response, 'Failed to fetch sources');
    const data = await response.json();
    return data.map((s: any) => ({
      id: s.id,
      title: s.title || `Source ${s.id.substring(0, 8)}`,
      type: s.source_type.toLowerCase(),
      date: s.created_at,
      subjectId: s.subject_id,
      chunkCount: s.chunks || 0,
      model: s.embedding_model,
      dimensions: s.dimensions,
      totalTokens: s.total_tokens,
      maxTokensPerChunk: s.max_tokens_per_chunk,
      origin: s.external_source,
      processingStatus: s.processing_status || 'unknown'
    }));
  },

  async deleteSource(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/sources/${id}`, {
      method: 'DELETE'
    });
    await handleResponseError(response, 'Failed to delete source');
  },

  async fetchSourceTypes(): Promise<string[]> {
    const response = await fetch(`${API_BASE_URL}/sources/types`);
    await handleResponseError(response, 'Failed to fetch source types');
    return response.json();
  },

  async fetchJobs(): Promise<IngestionTask[]> {
    const response = await fetch(`${API_BASE_URL}/jobs`);
    await handleResponseError(response, 'Failed to fetch jobs');
    const data = await response.json();
    return data.map((j: any) => ({
      id: j.id,
      title: j.source_title || j.status_message || `Job ${j.id.substring(0, 8)}`,
      status: j.status.toLowerCase() as any, // backend uses uppercase
      progress: j.total_steps ? Math.round((j.current_step / j.total_steps) * 100) : 0,
      currentStep: j.current_step,
      totalSteps: j.total_steps,
      statusMessage: j.status_message,
      contentSourceId: j.content_source_id || undefined,
      chunksCount: j.chunks_count || undefined,
      subjectId: j.subject_id || '',
      createdAt: j.created_at,
      ingestionType: j.ingestion_type || undefined,
      errorMessage: j.error_message || undefined,
      externalSource: j.external_source || undefined,
    }));
  },

  async search(query: string, topK: number, subjectId?: string, searchMode?: string, reRank: boolean = true): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        top_k: topK,
        subject_id: subjectId,
        search_mode: searchMode ?? 'semantic',
        re_rank: reRank,
      })
    });
    await handleResponseError(response, 'Search failed');
    return response.json();
  },

  async ingestYoutube(data: {
    video_url?: string;
    video_urls?: string[];
    subject_id?: string;
    subject_name?: string;
    language?: string;
    tokens_per_chunk?: number;
    tokens_overlap?: number;
    ingestion_job_id?: string;
    data_type?: string;
    reprocess?: boolean;
  }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/ingest/youtube`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (response.status === 409) {
      throw new Error('DUPLICATE_SOURCE');
    }
    await handleResponseError(response, 'Ingestion request failed');
    return response.json();
  },

  async ingestFile(formData: FormData): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/ingest/file`, {
      method: 'POST',
      body: formData
    });
    await handleResponseError(response, 'File ingestion failed');
    return response.json();
  },

  async fetchChunks(sourceId?: string, limit: number = 100, offset: number = 0, query?: string): Promise<Chunk[]> {
    const url = new URL(`${API_BASE_URL}/chunks`, window.location.origin);
    if (sourceId) url.searchParams.append('source_id', sourceId);
    if (query) url.searchParams.append('q', query);
    url.searchParams.append('limit', limit.toString());
    url.searchParams.append('offset', offset.toString());

    const response = await fetch(url.toString());
    await handleResponseError(response, 'Failed to fetch chunks');
    return response.json();
  },

  async updateChunk(id: string, content: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/chunks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    await handleResponseError(response, 'Failed to update chunk');
    return response.json();
  },

  async deleteChunk(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/chunks/${id}`, {
      method: 'DELETE'
    });
    await handleResponseError(response, 'Failed to delete chunk');
  },

  async fetchModelInfo(): Promise<{ name: string; dimensions: number; max_seq_length: number }> {
    const response = await fetch(`${API_BASE_URL}/sources/model`);
    await handleResponseError(response, 'Failed to fetch model info');
    return response.json();
  },
  
  async fetchSettings(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/settings`);
    await handleResponseError(response, 'Failed to fetch settings');
    return response.json();
  },
  
  async checkHealth(component: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/settings/check/${component}`);
    await handleResponseError(response, `Health check failed for ${component}`);
    return response.json();
  }
};
