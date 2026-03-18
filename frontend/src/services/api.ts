import { Subject, IngestionTask, ContentSource, ChatMessage } from '../types';

const API_BASE_URL = '/rest';

export const api = {
  async fetchSubjects(): Promise<Subject[]> {
    const response = await fetch(`${API_BASE_URL}/subjects`);
    if (!response.ok) throw new Error('Failed to fetch subjects');
    return response.json();
  },

  async createSubject(name: string, description?: string, icon?: string): Promise<Subject> {
    const response = await fetch(`${API_BASE_URL}/subjects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, icon })
    });
    if (!response.ok) throw new Error('Failed to create subject');
    return response.json();
  },

  async fetchSources(): Promise<ContentSource[]> {
    const response = await fetch(`${API_BASE_URL}/sources`);
    if (!response.ok) throw new Error('Failed to fetch sources');
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
      origin: s.external_source,
      processingStatus: s.processing_status || 'unknown'
    }));
  },

  async fetchJobs(): Promise<IngestionTask[]> {
    const response = await fetch(`${API_BASE_URL}/jobs`);
    if (!response.ok) throw new Error('Failed to fetch jobs');
    const data = await response.json();
    return data.map((j: any) => ({
      id: j.id,
      title: j.status_message || `Job ${j.id}`,
      status: j.status.toLowerCase() as any, // backend uses uppercase
      progress: j.total_steps ? Math.round((j.current_step / j.total_steps) * 100) : 0,
      subjectId: '', // Backend doesn't return subject_id directly in the job response model yet
      createdAt: j.created_at,
      ingestionType: j.ingestion_type || undefined,
      errorMessage: j.error_message || undefined,
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
    if (!response.ok) throw new Error('Search failed');
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
  }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/ingest/youtube`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (response.status === 409) {
      throw new Error('DUPLICATE_SOURCE');
    }
    if (!response.ok) throw new Error('Ingestion request failed');
    return response.json();
  },

  async fetchChunks(sourceId?: string, limit: number = 100, offset: number = 0, query?: string): Promise<any[]> {
    const url = new URL(`${API_BASE_URL}/chunks`, window.location.origin);
    if (sourceId) url.searchParams.append('source_id', sourceId);
    if (query) url.searchParams.append('q', query);
    url.searchParams.append('limit', limit.toString());
    url.searchParams.append('offset', offset.toString());

    const response = await fetch(url.toString());
    if (!response.ok) throw new Error('Failed to fetch chunks');
    return response.json();
  },

  async updateChunk(id: string, content: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/chunks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });
    if (!response.ok) throw new Error('Failed to update chunk');
    return response.json();
  },

  async deleteChunk(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/chunks/${id}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete chunk');
  },

  async fetchModelInfo(): Promise<{ name: string; dimensions: number; max_seq_length: number }> {
    const response = await fetch(`${API_BASE_URL}/sources/model`);
    if (!response.ok) throw new Error('Failed to fetch model info');
    return response.json();
  },
  
  async fetchSettings(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/settings`);
    if (!response.ok) throw new Error('Failed to fetch settings');
    return response.json();
  },
  
  async checkHealth(component: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/settings/check/${component}`);
    if (!response.ok) throw new Error(`Health check failed for ${component}`);
    return response.json();
  }
};
