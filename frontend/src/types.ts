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
  subjectId: string;
  createdAt: string;
  ingestionType?: string;
  errorMessage?: string;
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
  origin?: string;
};

export type ViewState = 'chat' | 'search' | 'sources' | 'activity' | 'database';

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
