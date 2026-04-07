import { DiarizationJob } from './types';

export function formatDuration(seconds: number): string {
    if (!seconds || seconds <= 0) return '--:--';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function mapBackendJob(r: any): DiarizationJob {
    const backendStatus = r.status || 'pending';
    const hasSegments = r.segments && r.segments.length > 0;

    let status: DiarizationJob['status'] = backendStatus;
    
    if (backendStatus === 'completed' && hasSegments) {
        const allGeneric = r.segments.every((s: any) => 
            !s.speaker || s.speaker.startsWith('SPEAKER_')
        );
        status = allGeneric ? 'awaiting_verification' : 'completed';
    }

    return {
        id: r.id,
        name: r.name || 'Untitled',
        date: r.created_at ? r.created_at.split('T')[0].split(' ')[0] : '',
        status,
        duration: formatDuration(r.duration),
        durationSeconds: r.duration || 0,
        sourceType: r.source_type || '',
        externalSource: r.external_source || '',
        language: r.language || 'pt',
        modelSize: r.model_size || '',
        segments: r.segments || [],
        recognitionResults: r.recognition_results || {},
        storagePath: r.storage_path || '',
        sourceMetadata: r.source_metadata || null,
        statusMessage: r.status_message,
        errorMessage: r.error_message,
    };
}

export function mergeSpeakerSegments(segments: any[], recognition?: any) {
    if (!segments || segments.length === 0) return [];
    
    const merged: any[] = [];
    let current: any = null;
    
    const mapping = recognition?.mapping || recognition || {};

    segments.forEach((seg, idx) => {
        const speakerName = mapping[seg.speaker] || seg.speaker;
        
        if (current && current.speakerName === speakerName) {
            current.end = seg.end;
            current.endTime = formatDuration(seg.end);
            current.text = `${current.text} ${seg.text}`;
        } else {
            current = {
                ...seg,
                id: idx,
                speakerName: speakerName,
                startTime: formatDuration(seg.start),
                endTime: formatDuration(seg.end)
            };
            merged.push(current);
        }
    });
    
    return merged;
}

export function buildTranscriptFromSegments(segments: any[], mapping?: any) {
    if (!segments || segments.length === 0) return '';
    const merged = mergeSpeakerSegments(segments, mapping);
    return merged.map(seg => {
        return `[${seg.startTime} - ${seg.endTime}] ${seg.speakerName}: ${seg.text}`;
    }).join('\n');
}

export function extractSpeakersFromSegments(segments: any[], recognition?: any): any[] {
    const speakerLabels = [
        ...new Set(
            segments
                .map((s: any) => s.speaker)
                .filter((speaker: any) => !!speaker)
                .map((speaker: any) => String(speaker))
        )
    ].sort((a, b) => a.localeCompare(b));
    const mapping = recognition?.mapping || {};
    const details = recognition?.details || {};

    return speakerLabels.map((label, i) => {
        const identifiedName = mapping[label];
        const assigned = identifiedName || label;
        
        let confidence = 0;
        if (details[label]?.score) {
            confidence = Math.round(details[label].score * 100);
        } else if (identifiedName) {
            confidence = 95;
        }

        return {
            id: String(i),
            label,
            original: label,
            assigned,
            isPlaying: false,
            confidence: confidence,
        };
    });
}
