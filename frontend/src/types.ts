export type Subject = {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  sourceCount?: number;
};

export type TaskStatus = 'pending' | 'processing' | 'done' | 'error' | 'started' | 'finished' | 'failed' | 'cancelled' | 'reprocessed';

export type IngestionTask = {
  id: string;
  title: string;
  status: TaskStatus;
  progress: number; // 0 to 100
  currentStep?: number;
  totalSteps?: number;
  statusMessage?: string;
  contentSourceId?: string;
  chunksCount?: number;
  subjectId: string;
  subjectName?: string;
  createdAt: string;
  finishedAt?: string;
  ingestionType?: string;
  errorMessage?: string;
  externalSource?: string;
};

export type ContentSource = {
  id: string;
  title: string;
  type: string;
  date: string;
  subjectId: string;
  duration?: string;
  chunkCount: number;
  model?: string;
  dimensions?: number;
  totalTokens?: number;
  maxTokensPerChunk?: number;
  origin?: string;
  processingStatus: string;
  statusMessage?: string;
  errorMessage?: string;
  sourceMetadata?: Record<string, any>;
};

export interface RawQueueTask {
  func_name: string;
  args: any[];
  kwargs: Record<string, any>;
  task_title?: string;
  metadata?: Record<string, any>;
  enqueued_at: number;
}

export type ViewState = 'chat' | 'search' | 'sources' | 'activity' | 'database' | 'knowledge_contexts' | 'diarization' | 'voice_profiles' | 'queue' | 'duplicates';

export type ChunkDuplicate = {
  id: string;
  chunk_ids: string[];
  chunks?: {
    id: string;
    content: string;
    source_title?: string;
    source_id?: string;
  }[];
  similarity: number;
  status: string;
  created_at: string;
  updated_at: string;
};


export type ToastType = 'success' | 'info' | 'error';

export type Toast = {
  id: string;
  message: string;
  type: ToastType;
};

export type Citation = {
  id: string;
  sourceId: string;
  title: string;
  index?: number;
  timestamp?: string;
  textSnippet: string;
  relevanceScore: number;
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp: string;
};

export type ModelInfo = {
  name: string;
  dimensions: number;
  max_seq_length: number;
};

export type Chunk = {
  id: string;
  content_source_id: string;
  chunk_id?: string;
  index?: number;
  content: string;
  tokens_count?: number;
  created_at: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  stats?: Record<string, number>;
};
