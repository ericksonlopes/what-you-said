import pytest
from unittest.mock import MagicMock, patch
from src.application.use_cases.generate_speaker_audio_access_url import GenerateSpeakerAudioAccessUrlUseCase
from src.application.use_cases.identify_speakers_in_processed_audio import IdentifySpeakersInProcessedAudioUseCase
from src.application.use_cases.list_s3_audio_files import ListS3AudioFilesUseCase
from src.application.use_cases.manage_voice_profiles import RegisterNewVoiceProfileUseCase
from src.application.use_cases.retrieve_processed_audio_history import RetrieveProcessedAudioHistoryUseCase
from src.infrastructure.repositories.sql.models.diarization import DiarizationRecord

@pytest.mark.AudioRecognitionUseCases
class TestAudioRecognitionUseCases:
    def test_retrieve_history(self, sqlite_memory):
        # Setup: add a record
        record = DiarizationRecord(id="1", title="Test", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()
        
        use_case = RetrieveProcessedAudioHistoryUseCase(sqlite_memory)
        history = use_case.execute(limit=10, offset=0)
        
        assert len(history) == 1
        assert history[0]["title"] == "Test"

    @patch("src.infrastructure.repositories.storage.storage.StorageService.get_presigned_url")
    def test_generate_speaker_url(self, mock_url, sqlite_memory):
        # Setup: add a record with storage path
        record = DiarizationRecord(id="1", title="Test", storage_path="path/to/dir", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()
        
        mock_url.return_value = "http://presigned"
        
        use_case = GenerateSpeakerAudioAccessUrlUseCase(sqlite_memory)
        result = use_case.execute("1", "SPEAKER_00")
        
        assert result["url"] == "http://presigned"
        assert result["speaker"] == "SPEAKER_00"

    @patch("src.infrastructure.repositories.storage.storage.StorageService.list_files")
    def test_list_s3_files(self, mock_list, sqlite_memory):
        # Setup: add a record
        record = DiarizationRecord(id="1", title="Test", storage_path="path/to/dir", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()
        
        mock_list.return_value = [{"key": "file1.wav"}]
        
        use_case = ListS3AudioFilesUseCase(sqlite_memory)
        files = use_case.execute("1")
        
        assert len(files) == 1
        assert files[0]["key"] == "file1.wav"

    @patch("src.infrastructure.services.voice_profile_service.VoiceDB.add")
    def test_register_voice_profile(self, mock_add, sqlite_memory):
        mock_add.return_value = "voice-uuid"
        
        use_case = RegisterNewVoiceProfileUseCase(sqlite_memory)
        voice_id = use_case.execute(name="Renato", audio_path="path/to/audio")
        
        assert voice_id == "voice-uuid"
        mock_add.assert_called_with(name="Renato", audio_path="path/to/audio", force=False)

    @patch("src.application.use_cases.identify_speakers_in_processed_audio.StorageService")
    @patch("src.application.use_cases.identify_speakers_in_processed_audio.VoiceDB")
    @patch("src.application.use_cases.identify_speakers_in_processed_audio.VoiceRecognizer")
    @patch("os.makedirs")
    @patch("shutil.rmtree")
    def test_identify_speakers(self, mock_rm, mock_make, mock_rec_cls, mock_db_cls, mock_storage_cls, sqlite_memory):
        # Setup: add record
        record = DiarizationRecord(id="1", title="Test", storage_path="path/to/dir", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()
        
        mock_db = mock_db_cls.return_value
        mock_db.__len__.return_value = 1
        
        mock_rec = mock_rec_cls.return_value
        mock_rec.identify_dir.return_value = MagicMock(mapping={"SPEAKER_00": "Renato"}, results={})
        
        use_case = IdentifySpeakersInProcessedAudioUseCase(sqlite_memory)
        result = use_case.execute("1")
        
        assert result["mapping"]["SPEAKER_00"] == "Renato"
        assert record.recognition_results is not None
