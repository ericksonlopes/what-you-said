from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord
from src.infrastructure.services.voice_profile_service import VoiceDB


@pytest.mark.VoiceDB
class TestVoiceDB:
    @pytest.fixture(autouse=True)
    def mock_infra(self):
        # Stub StorageService and Os logic globally for this class to prevent ANY footprint
        with (
            patch("src.infrastructure.services.voice_profile_service.StorageService") as mock_cls,
            patch("os.path.exists", return_value=True),
            patch("os.path.isdir", return_value=True),
            patch("os.makedirs"),
            patch("os.remove"),
        ):
            self.mock_storage_cls = mock_cls
            self.mock_storage = mock_cls.return_value
            yield

    def test_add_voice_local_file(self, sqlite_memory):
        # Mock pyannote inference
        with patch(
            "src.infrastructure.services.voice_profile_service.get_best_device",
            return_value="cpu",
        ):
            with patch("src.infrastructure.services.voice_profile_service.VoiceDB._get_inference") as mock_inf_getter:
                mock_inf = MagicMock()
                mock_inf_getter.return_value = mock_inf
                mock_inf.return_value = MagicMock(tolist=lambda: [0.1, 0.2])

                with patch(
                    "src.infrastructure.utils.audio_utils.load_audio_tensor",
                    return_value={},
                ):
                    self.mock_storage.upload_file.return_value = "voices/test.wav"

                    db_service = VoiceDB(sqlite_memory, hf_token="fake")
                    voice_id, _ = db_service.add("Test User", "local.wav")

                    assert voice_id is not None
                    
                    # Verify status was updated to ready
                    record = sqlite_memory.get(VoiceRecord, voice_id)
                    assert record.status == "ready"
                    assert record.status_message is None
                    
                    voices = db_service.voices
                    assert "Test User" in voices

    def test_remove_voice(self, sqlite_memory):
        from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord

        v = VoiceRecord(
            id="1",
            name="Test",
            embedding=[0.1],
            audios_path="voices/1/",
        )
        sqlite_memory.add(v)
        sqlite_memory.commit()

        self.mock_storage.list_files.return_value = [{"key": "voices/1/reference_1.wav"}]

        db_service = VoiceDB(sqlite_memory, hf_token="fake")
        db_service.remove("Test")
        assert db_service.__len__() == 0
        assert self.mock_storage.delete_file.called

    def test_add_voice_s3_source(self, sqlite_memory):
        with patch(
            "src.infrastructure.services.voice_profile_service.get_best_device",
            return_value="cpu",
        ):
            with patch("src.infrastructure.services.voice_profile_service.VoiceDB._get_inference") as mock_inf_getter:
                mock_inf = MagicMock()
                mock_inf_getter.return_value = mock_inf
                mock_inf.return_value = MagicMock(tolist=lambda: [0.1, 0.2])

                with patch(
                    "src.infrastructure.utils.audio_utils.load_audio_tensor",
                    return_value={},
                ):
                    self.mock_storage.download_file.return_value = "local_tmp.wav"
                    self.mock_storage.upload_file.return_value = "voices/test.wav"

                    db_service = VoiceDB(sqlite_memory, hf_token="fake")
                    voice_id, _ = db_service.add("S3 User", "s3://bucket/voice.wav")

                    assert voice_id is not None
                    assert self.mock_storage.download_file.called

    def test_add_voice_already_exists_reinforces(self, sqlite_memory):
        from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord

        v = VoiceRecord(
            id="exists-123",
            name="Exists",
            embedding=[0.1, 0.9],
            audios_path="voices/exists-123/",
        )
        sqlite_memory.add(v)
        sqlite_memory.commit()

        db_service = VoiceDB(sqlite_memory, hf_token="fake")

        with patch.object(db_service, "_extract_embedding", return_value=[0.9, 0.1]):
            voice_id, s3_path = db_service.add("Exists", "local.wav")

            assert voice_id == "exists-123"
            assert s3_path.startswith("voices/exists-123/sample_")
            assert s3_path.endswith(".wav")
            updated = sqlite_memory.get(VoiceRecord, "exists-123")
            assert np.allclose(updated.embedding, [0.5, 0.5])

    def test_add_voice_skips_reinforcement_when_too_similar(self, sqlite_memory):
        from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord

        v = VoiceRecord(
            id="exists-456",
            name="Similar",
            embedding=[0.1, 0.2],
            audios_path="voices/exists-456/",
        )
        sqlite_memory.add(v)
        sqlite_memory.commit()

        db_service = VoiceDB(sqlite_memory, hf_token="fake")

        # Same direction embedding → cosine similarity ≈ 1.0 → should skip
        with patch.object(db_service, "_extract_embedding", return_value=[0.3, 0.6]):
            voice_id, s3_path = db_service.add("Similar", "local.wav")

            assert voice_id == "exists-456"
            assert s3_path == ""
            # Embedding should NOT be updated
            updated = sqlite_memory.get(VoiceRecord, "exists-456")
            assert np.allclose(updated.embedding, [0.1, 0.2])
            # No file should be uploaded
            assert not self.mock_storage.upload_file.called

    def test_remove_by_invalid_name(self, sqlite_memory):
        db_service = VoiceDB(sqlite_memory, hf_token="fake")
        with pytest.raises(KeyError, match="not found"):
            db_service.remove("NonExistent")

    def test_add_voice_s3_download_failure(self, sqlite_memory):
        self.mock_storage.download_file.side_effect = Exception("S3 Error")
        db_service = VoiceDB(sqlite_memory, hf_token="fake")

        with pytest.raises(ValueError, match="Failed to download from S3"):
            db_service.add("S3 User", "s3://bucket/voice.wav")

        # After failure, it should NOT have created a successful record
        # but let's check if it created a fixed "failed" record if we implement it that way.
        # Currently, if it fails at download, it doesn't even create the record yet in the DB.
        # Wait, the record is created AFTER the S3 check block. 
        # So no record should exist in DB yet.
        assert sqlite_memory.query(VoiceRecord).count() == 0

    def test_add_voice_embedding_extraction_failure(self, sqlite_memory):
        db_service = VoiceDB(sqlite_memory, hf_token="fake")
        
        # Fail during embedding extraction
        with patch.object(db_service, "_extract_embedding", side_effect=Exception("Model Error")):
            with pytest.raises(Exception, match="Model Error"):
                db_service.add("Failed User", "local.wav")

            # Verify it marked as failed
            record = sqlite_memory.query(VoiceRecord).filter(VoiceRecord.name == "Failed User").first()
            assert record is not None
            assert record.status == "failed"
            assert "Model Error" in record.status_message

    def test_list_audio_files(self, sqlite_memory):
        v = VoiceRecord(id="v1", name="V1", embedding=[0.1], audios_path="voices/v1/", status="ready")
        sqlite_memory.add(v)
        sqlite_memory.commit()

        self.mock_storage.list_files.return_value = [{"key": "f1.wav"}, {"key": "f2.wav"}]
        
        db_service = VoiceDB(sqlite_memory, hf_token="fake")
        files = db_service.list_audio_files("v1")
        
        assert len(files) == 2
        self.mock_storage.list_files.assert_called_once_with(prefix="voices/v1/", extension=".wav")

    def test_delete_audio_file(self, sqlite_memory):
        db_service = VoiceDB(sqlite_memory, hf_token="fake")
        db_service.delete_audio_file("some/key.wav")
        self.mock_storage.delete_file.assert_called_once_with("some/key.wav")

    def test_list_voices_and_len(self, sqlite_memory):
        v1 = VoiceRecord(id="v1", name="Ready", embedding=[0.1], status="ready")
        v2 = VoiceRecord(id="v2", name="Processing", embedding=[], status="processing")
        sqlite_memory.add_all([v1, v2])
        sqlite_memory.commit()

        db_service = VoiceDB(sqlite_memory, hf_token="fake")
        
        # list_voices should only show ready ones
        voice_list = db_service.list_voices()
        assert "Ready" in voice_list
        assert "Processing" not in voice_list
        
        # len should only show ready ones
        assert len(db_service) == 1
        
        # .voices property should only show ready ones
        assert "Ready" in db_service.voices
        assert "Processing" not in db_service.voices
