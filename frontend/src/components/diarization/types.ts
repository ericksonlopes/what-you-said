export type Step = 'idle' | 'processing' | 'identification' | 'result' | 'error';

export interface Speaker {
    id: string;
    label: string;
    original: string;
    assigned: string;
    isPlaying: boolean;
    confidence: number;
    audioUrl?: string;
}

export interface DiarizationJob {
    id: string;
    name: string;
    date: string;
    status: 'completed' | 'pending' | 'processing' | 'failed' | 'awaiting_verification';
    duration: string;
    durationSeconds: number;
    sourceType: string;
    externalSource: string;
    language: string;
    modelSize: string;
    segments: any[];
    recognitionResults: any;
    storagePath: string;
    sourceMetadata: any;
    statusMessage?: string;
    errorMessage?: string;
}
