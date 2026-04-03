import { Subject, IngestionTask, ContentSource, Chunk, PaginatedResponse } from '../types';

const API_BASE_URL = '/rest';

async function handleResponseError(response: Response, defaultMessage: string) {
  if (response.status === 401) {
    // Standard handling for unauthorized: clear token and reload
    localStorage.removeItem('auth_token');
    if (!globalThis.location.pathname.includes('/auth/google/callback')) {
      // Avoid redirect loops during callback
    }
  }

  if (response.ok) return;
  
  let errorMessage = defaultMessage;
  try {
    const data = await response.json();
    if (data?.detail) {
      errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
  } catch (e) {
    console.error('Failed to parse error response:', e);
    // Ignore JSON parse errors and use default message
  }
  
  throw new Error(errorMessage);
}

function getHeaders(contentType: string | null = 'application/json') {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {};
  if (contentType) headers['Content-Type'] = contentType;
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export const api = {
  async ingestFileByUrl(data: {
    file_url: string;
    subject_id?: string;
    subject_name?: string;
    title?: string;
    language?: string;
    tokens_per_chunk?: number;
    tokens_overlap?: number;
    do_ocr?: boolean;
  }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/ingest/file-url`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data)
    });
    await handleResponseError(response, 'File URL ingestion failed');
    return response.json();
  },

  async fetchSubjects(): Promise<Subject[]> {
    const response = await fetch(`${API_BASE_URL}/subjects`, {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch subjects');
    return response.json();
  },

  async createSubject(name: string, description?: string, icon?: string): Promise<Subject> {
    const response = await fetch(`${API_BASE_URL}/subjects`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ name, description, icon })
    });
    await handleResponseError(response, 'Failed to create subject');
    return response.json();
  },

  async updateSubject(id: string, name?: string, description?: string, icon?: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/subjects/${id}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({ name, description, icon })
    });
    await handleResponseError(response, 'Failed to update subject');
  },

  async deleteSubject(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/subjects/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to delete subject');
  },

  async fetchSources(): Promise<ContentSource[]> {
    const response = await fetch(`${API_BASE_URL}/sources`, {
      headers: getHeaders()
    });
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
      processingStatus: s.processing_status || 'unknown',
      sourceMetadata: s.source_metadata
    }));
  },

  async deleteSource(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/sources/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to delete source');
  },

  async updateSource(id: string, title: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/sources/${id}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify({ title })
    });
    await handleResponseError(response, 'Failed to update source title');
  },

  async fetchSourceTypes(): Promise<string[]> {
    const response = await fetch(`${API_BASE_URL}/sources/types`, {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch source types');
    return response.json();
  },

  async fetchJobs(params?: { page?: number; pageSize?: number; status?: string; search?: string }): Promise<PaginatedResponse<IngestionTask>> {
    const url = new URL(`${API_BASE_URL}/jobs`, globalThis.location.origin);
    if (params?.page) url.searchParams.append('page', params.page.toString());
    if (params?.pageSize) url.searchParams.append('page_size', params.pageSize.toString());
    if (params?.status && params.status !== 'all') url.searchParams.append('status', params.status);
    if (params?.search) url.searchParams.append('search', params.search);

    const response = await fetch(url.toString(), {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch jobs');
    const data = await response.json();
    return {
      items: data.items.map((j: any) => ({
        id: j.id,
        title: j.source_title || j.status_message || `Job ${j.id.substring(0, 8)}`,
        status: j.status.toLowerCase(), // backend uses uppercase
        progress: j.total_steps ? Math.round((j.current_step / j.total_steps) * 100) : 0,
        currentStep: j.current_step,
        totalSteps: j.total_steps,
        statusMessage: j.status_message,
        contentSourceId: j.content_source_id || undefined,
        chunksCount: j.chunks_count || undefined,
        subjectId: j.subject_id || '',
        createdAt: j.created_at,
        finishedAt: j.finished_at,
        ingestionType: j.ingestion_type || undefined,
        errorMessage: j.error_message || undefined,
        externalSource: j.external_source || undefined,
      })),
      total: data.total,
      page: data.page,
      page_size: data.page_size,
      stats: data.stats
    };
  },

  async search(query: string, topK: number, subjectId?: string, searchMode?: string, reRank: boolean = true): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: getHeaders(),
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
      headers: getHeaders(),
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
      headers: getHeaders(null), // FormData uses null for Content-Type
      body: formData
    });
    await handleResponseError(response, 'File ingestion failed');
    return response.json();
  },


  async fetchChunks(sourceId?: string, limit: number = 100, offset: number = 0, query?: string): Promise<Chunk[]> {
    const url = new URL(`${API_BASE_URL}/chunks`, globalThis.location.origin);
    if (sourceId) url.searchParams.append('source_id', sourceId);
    if (query) url.searchParams.append('q', query);
    url.searchParams.append('limit', limit.toString());
    url.searchParams.append('offset', offset.toString());

    const response = await fetch(url.toString(), {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch chunks');
    return response.json();
  },

  async updateChunk(id: string, content: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/chunks/${id}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify({ content })
    });
    await handleResponseError(response, 'Failed to update chunk');
    return response.json();
  },

  async deleteChunk(id: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/chunks/${id}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to delete chunk');
  },

  async fetchModelInfo(): Promise<{ name: string; dimensions: number; max_seq_length: number }> {
    const response = await fetch(`${API_BASE_URL}/sources/model`, {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch model info');
    return response.json();
  },
  
  async fetchSettings(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/settings`, {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch settings');
    return response.json();
  },
  
  async checkHealth(component: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/settings/check/${component}`, {
      headers: getHeaders()
    });
    await handleResponseError(response, `Health check failed for ${component}`);
    return response.json();
  },

  async ingestWeb(data: {
    url: string;
    subject_id?: string;
    subject_name?: string;
    title?: string;
    language?: string;
    tokens_per_chunk?: number;
    tokens_overlap?: number;
    css_selector?: string;
    depth?: number;
    exclude_links?: boolean;
    ingestion_job_id?: string;
    reprocess?: boolean;
  }): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/ingest/web`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data)
    });
    if (response.status === 409) {
      throw new Error('DUPLICATE_SOURCE');
    }
    await handleResponseError(response, 'Web ingestion request failed');
    return response.json();
  },

  // Auth Methods
  async fetchAuthConfig(): Promise<{ enable_google: boolean; redirect_uri: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/config`, {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch auth config');
    return response.json();
  },

  async getGoogleLoginUrl(): Promise<{ url: string; state: string }> {
    const response = await fetch(`${API_BASE_URL}/auth/google/login`, {
      headers: getHeaders(),
    });
    await handleResponseError(response, 'Failed to get login URL');
    return response.json();
  },

  async googleCallback(code: string, state?: string, expectedState?: string): Promise<{ access_token: string; user: any }> {
    const params = new URLSearchParams({ code });
    if (state) params.append('state', state);
    if (expectedState) params.append('expected_state', expectedState);
    const response = await fetch(`${API_BASE_URL}/auth/google/callback?${params.toString()}`, {
      headers: getHeaders(),
    });
    await handleResponseError(response, 'Auth callback failed');
    return response.json();
  },

  async fetchMe(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: getHeaders()
    });
    await handleResponseError(response, 'Failed to fetch user profile');
    return response.json();
  }
};
