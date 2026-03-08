from pprint import pprint

from src.infrastructure.services.transcript_processor import TranscriptProcessor

if __name__ == '__main__':
    tp = TranscriptProcessor()

    v_id = "VQnM8Y3RIyM"
    languages = ["pt"]

    fetch = tp.fetch_transcript(video_id=v_id, languages=languages)

    pprint(fetch)
