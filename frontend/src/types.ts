export type Subject = {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  sourceCount?: number;
};

export type TaskStatus = 'pending' | 'processing' | 'done' | 'error' | 'started' | 'finished' | 'failed' | 'cancelled';

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
};

export type ViewState = 'chat' | 'search' | 'sources' | 'activity' | 'database' | 'knowledge_contexts';

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
