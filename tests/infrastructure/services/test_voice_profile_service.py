import os
import pytest
from unittest.mock import MagicMock, patch
from src.infrastructure.services.voice_profile_service import VoiceDB

@pytest.mark.VoiceDB
class TestVoiceDB:
    def test_add_voice_local_file(self, sqlite_memory):
        # Mock pyannote inference
        with patch("src.infrastructure.services.voice_profile_service.get_best_device", return_value="cpu"):
            with patch("src.infrastructure.services.voice_profile_service.VoiceDB._get_inference") as mock_inf_getter:
                mock_inf = MagicMock()
                mock_inf_getter.return_value = mock_inf
                mock_inf.return_value = MagicMock(tolist=lambda: [0.1, 0.2])
                
                with patch("src.infrastructure.utils.audio_utils.load_audio_tensor", return_value={}):
                    with patch("os.path.exists", return_value=True):
                        with patch("src.infrastructure.repositories.storage.storage.StorageService.upload_file", return_value="voices/test.wav"):
                            db_service = VoiceDB(sqlite_memory, hf_token="fake")
                            voice_id = db_service.add("Test User", "local.wav")
                            
                            assert voice_id is not None
                            assert db_service.list_voices()["Test User"] == "voices/test.wav"

    def test_remove_voice(self, sqlite_memory):
        # Setup: add a voice first
        from src.infrastructure.repositories.sql.models.diarization import VoiceRecord
        v = VoiceRecord(id="1", name="Test", embedding=[0.1], audio_source="path/to/s3")
        sqlite_memory.add(v)
        sqlite_memory.commit()
        
        db_service = VoiceDB(sqlite_memory, hf_token="fake")
        with patch("src.infrastructure.repositories.storage.storage.StorageService.delete_file"):
            db_service.remove("Test")
            assert db_service.__len__() == 0
