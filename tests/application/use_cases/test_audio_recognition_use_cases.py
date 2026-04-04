import pytest
from unittest.mock import MagicMock, patch

# Module-level patch for boto3 to prevent botocore initialization during class/module loading
patch("boto3.Session").start()
patch("boto3.client").start()
patch("boto3.resource").start()

from src.application.use_cases.generate_speaker_audio_access_url import (  # noqa: E402
    GenerateSpeakerAudioAccessUrlUseCase,
)
from src.application.use_cases.identify_speakers_in_processed_audio import (  # noqa: E402
    IdentifySpeakersInProcessedAudioUseCase,
)
from src.application.use_cases.list_s3_audio_files import ListS3AudioFilesUseCase  # noqa: E402
from src.application.use_cases.manage_voice_profiles import (  # noqa: E402
    RegisterNewVoiceProfileUseCase,
    DeleteVoiceProfileUseCase,
    ListRegisteredVoiceProfilesUseCase,
)
from src.infrastructure.repositories.sql.models.diarization_record import (  # noqa: E402
    DiarizationRecord,
)


@pytest.mark.AudioRecognitionUseCases
class TestAudioRecognitionUseCases:
    @pytest.fixture(autouse=True)
    def mock_infra_and_fs(self):
        # Stub StorageService and FS logic globally for this class
        with (
            patch(
                "src.application.use_cases.identify_speakers_in_processed_audio.StorageService"
            ),
            patch(
                "src.application.use_cases.generate_speaker_audio_access_url.StorageService"
            ),
            patch("src.application.use_cases.list_s3_audio_files.StorageService"),
            patch("src.application.use_cases.manage_voice_profiles.StorageService"),
            patch("src.infrastructure.services.voice_profile_service.StorageService"),
            patch("os.path.exists", return_value=True),
            patch("os.path.isdir", return_value=True),
            patch("os.listdir", return_value=[]),
            patch("os.makedirs"),
        ):
            yield

    def test_retrieve_history(self, sqlite_memory):
        record = DiarizationRecord(id="1", title="Test", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()

        from src.application.use_cases.retrieve_processed_audio_history import (
            RetrieveProcessedAudioHistoryUseCase,
        )

        use_case = RetrieveProcessedAudioHistoryUseCase(sqlite_memory)
        history = use_case.execute(limit=10, offset=0)
        assert len(history) == 1

    def test_generate_speaker_url(self, sqlite_memory):
        record = DiarizationRecord(id="1", title="T", storage_path="p", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()

        use_case = GenerateSpeakerAudioAccessUrlUseCase(sqlite_memory)
        with patch.object(
            use_case.storage, "get_presigned_url", return_value="http://p"
        ):
            result = use_case.execute("1", "S0")
            assert result["url"] == "http://p"

    def test_list_s3_files(self, sqlite_memory):
        record = DiarizationRecord(id="1", title="T", storage_path="p", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()

        use_case = ListS3AudioFilesUseCase(sqlite_memory)
        with patch.object(
            use_case.storage, "list_files", return_value=[{"key": "f1.wav"}]
        ):
            files = use_case.execute("1")
            assert len(files) == 1

    def test_register_voice_profile(self, sqlite_memory):
        with patch(
            "src.application.use_cases.manage_voice_profiles.VoiceDB"
        ) as mock_vdb_cls:
            mock_vdb = mock_vdb_cls.return_value
            mock_vdb.add.return_value = "v-123"

            use_case = RegisterNewVoiceProfileUseCase(sqlite_memory)
            vid = use_case.execute(name="N", audio_path="a")
            assert vid == "v-123"

    @patch("shutil.rmtree")
    def test_identify_speakers(self, mock_rm, sqlite_memory):
        record = DiarizationRecord(id="1", title="T", storage_path="p", segments=[])
        sqlite_memory.add(record)
        sqlite_memory.commit()

        with (
            patch(
                "src.application.use_cases.identify_speakers_in_processed_audio.VoiceDB"
            ) as mock_db_cls,
            patch(
                "src.application.use_cases.identify_speakers_in_processed_audio.VoiceRecognizer"
            ) as mock_rec_cls,
        ):
            mock_db = mock_db_cls.return_value
            mock_db.__len__.return_value = 1
            mock_rec = mock_rec_cls.return_value
            mock_rec.identify_dir.return_value = MagicMock(
                mapping={"S0": "N"}, id_mapping={"S0": "id"}, results={}
            )

            use_case = IdentifySpeakersInProcessedAudioUseCase(sqlite_memory)
            res = use_case.execute("1")
            assert res["mapping"]["S0"] == "N"

    def test_delete_voice_profile(self, sqlite_memory):
        with patch(
            "src.application.use_cases.manage_voice_profiles.VoiceDB"
        ) as mock_vdb_cls:
            mock_vdb = mock_vdb_cls.return_value
            use_case = DeleteVoiceProfileUseCase(sqlite_memory)
            use_case.execute(name="N")
            mock_vdb.remove.assert_called_with("N")

    def test_list_voice_profiles(self, sqlite_memory):
        use_case = ListRegisteredVoiceProfilesUseCase(sqlite_memory)
        with patch.object(sqlite_memory, "query") as mock_query:
            mock_query.return_value.all.return_value = []
            res = use_case.execute()
            assert isinstance(res, list)

    def test_register_voice_profile_no_name(self, sqlite_memory):
        with patch("src.application.use_cases.manage_voice_profiles.VoiceDB"):
            use_case = RegisterNewVoiceProfileUseCase(sqlite_memory)
            with pytest.raises(ValueError, match="Name required"):
                use_case.execute(name="", audio_path="a")
