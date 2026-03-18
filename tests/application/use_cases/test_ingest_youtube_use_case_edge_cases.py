import pytest
import uuid
from unittest.mock import MagicMock, patch
from src.application.use_cases.ingest_youtube_use_case import IngestYoutubeUseCase
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.enums.youtube_data_type import YoutubeDataType


@pytest.mark.IngestYouTubeUseCase
class TestIngestYoutubeUseCaseEdgeCases:
    @pytest.fixture
    def mock_services(self):
        return {
            "ks_service": MagicMock(),
            "cs_service": MagicMock(),
            "ingestion_service": MagicMock(),
            "model_loader_service": MagicMock(),
            "embedding_service": MagicMock(),
            "chunk_service": MagicMock(),
            "vector_service": MagicMock(),
            "vector_store_type": "FAISS",
        }

    @pytest.fixture
    def use_case(self, mock_services):
        return IngestYoutubeUseCase(**mock_services)

    def test_execute_job_recovery_fail(self, use_case, mock_services):
        cmd = IngestYoutubeCommand(
            video_url="https://www.youtube.com/watch?v=12345678901",
            subject_id=str(uuid.uuid4()),
            ingestion_job_id="invalid-uuid",
        )
        # This should trigger the except block in execute for job recovery
        # But we need it to continue, so we don't mock it to fail completely
        use_case.execute(cmd)
        # No assertion needed, just checking coverage of the try-except block

    def test_execute_playlist_no_url(self, use_case):
        cmd = IngestYoutubeCommand(
            video_url="",
            video_urls=[],
            subject_id=str(uuid.uuid4()),
            data_type=YoutubeDataType.PLAYLIST,
        )
        with pytest.raises(
            ValueError, match="No video_url provided for playlist ingestion"
        ):
            use_case.execute(cmd)

    def test_execute_no_video_urls(self, use_case):
        cmd = IngestYoutubeCommand(
            video_url="",
            video_urls=[],
            subject_id=str(uuid.uuid4()),
            data_type=YoutubeDataType.VIDEO,
        )
        with pytest.raises(ValueError, match=r"No video_url\(s\) provided in command"):
            use_case.execute(cmd)

    def test_execute_any_failed_with_ingestion(self, use_case, mock_services):
        cmd = IngestYoutubeCommand(
            video_url="https://www.youtube.com/watch?v=12345678901",
            subject_id=str(uuid.uuid4()),
            ingestion_job_id=str(uuid.uuid4()),
        )
        mock_services["ingestion_service"].get_by_id.return_value = MagicMock(
            id=uuid.uuid4()
        )
        mock_services["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid.uuid4()
        )

        with (
            patch.object(
                use_case, "_extract_video_id_from_url", return_value="12345678901"
            ),
            patch.object(
                use_case, "_process_single_video", return_value={"error": "some error"}
            ),
        ):
            use_case.execute(cmd)
            mock_services["ingestion_service"].update_job.assert_called()

    def test_process_single_video_duplicate_fail_job_creation(
        self, use_case, mock_services
    ):
        video_id = "12345678901"
        mock_services["cs_service"].get_by_source_info.return_value = MagicMock(
            processing_status="done"
        )
        mock_services["ingestion_service"].create_job.side_effect = Exception(
            "Failed to create job"
        )

        cmd = IngestYoutubeCommand(video_url="...", subject_id=str(uuid.uuid4()))
        subject = MagicMock()

        result = use_case._process_single_video("url", video_id, subject, cmd)
        assert result["skipped"] is True

    def test_process_single_video_job_reuse_not_found(self, use_case, mock_services):
        video_id = "12345678901"
        mock_services["cs_service"].get_by_source_info.return_value = None
        mock_services[
            "ingestion_service"
        ].get_by_id.return_value = None  # Job not found

        cmd = IngestYoutubeCommand(
            video_url="...",
            subject_id=str(uuid.uuid4()),
            ingestion_job_id=str(uuid.uuid4()),
        )
        subject = MagicMock()

        with patch.object(use_case, "_create_ingestion_job") as mock_create:
            with patch(
                "src.application.use_cases.ingest_youtube_use_case.YoutubeExtractor"
            ):
                with pytest.raises(
                    Exception
                ):  # it will fail later but we check _create_ingestion_job call
                    use_case._process_single_video("url", video_id, subject, cmd)
            mock_create.assert_called()

    def test_resolve_subject_invalid_uuid(self, use_case):
        cmd = IngestYoutubeCommand(video_url="...", subject_id="not-a-uuid")
        with pytest.raises(ValueError, match="Invalid subject_id provided"):
            use_case._resolve_subject(cmd)

    def test_resolve_subject_not_found_by_name(self, use_case, mock_services):
        cmd = IngestYoutubeCommand(video_url="...", subject_name="NonExistent")
        mock_services["ks_service"].get_by_name.return_value = None
        with pytest.raises(
            ValueError, match="KnowledgeSubject with name 'NonExistent' not found"
        ):
            use_case._resolve_subject(cmd)

    def test_resolve_subject_no_identifier(self, use_case):
        cmd = IngestYoutubeCommand(video_url="...")
        cmd.subject_id = None
        cmd.subject_name = None
        with pytest.raises(
            ValueError, match="Either subject_id or subject_name must be provided"
        ):
            use_case._resolve_subject(cmd)

    def test_fail_ingestion_and_job_exception_handling(self, use_case, mock_services):
        # Trigger the catch-all Exception in execute
        cmd = IngestYoutubeCommand(video_url="...", subject_id=str(uuid.uuid4()))
        mock_services["ks_service"].get_subject_by_id.side_effect = Exception(
            "General Failure"
        )

        # Mocking to reach the error handlers at the end of execute
        with patch.object(
            use_case, "_resolve_subject", side_effect=Exception("Failure")
        ):
            with pytest.raises(Exception):
                use_case.execute(cmd)

    def test_process_single_video_no_transcript_chunks(self, use_case, mock_services):
        video_id = "12345678901"
        mock_services["cs_service"].get_by_source_info.return_value = None
        subject = MagicMock()
        cmd = IngestYoutubeCommand(video_url="...", subject_id=str(uuid.uuid4()))

        with (
            patch("src.application.use_cases.ingest_youtube_use_case.YoutubeExtractor"),
            patch.object(use_case, "_extract_and_split", return_value=[]),
        ):
            with pytest.raises(
                ValueError, match="No transcript chunks generated for video"
            ):
                use_case._process_single_video("url", video_id, subject, cmd)

    def test_process_single_video_fail_handlers_internal(self, use_case, mock_services):
        video_id = "12345678901"
        mock_services["cs_service"].get_by_source_info.return_value = None
        subject = MagicMock()
        cmd = IngestYoutubeCommand(video_url="...", subject_id=str(uuid.uuid4()))

        # Original error should bubble up if fail handlers also fail
        # But here we just want to see it reaches those lines.
        mock_services["cs_service"].update_processing_status.side_effect = Exception(
            "Failed status update"
        )
        mock_services["ingestion_service"].update_job.side_effect = Exception(
            "Failed job update"
        )

        with (
            patch("src.application.use_cases.ingest_youtube_use_case.YoutubeExtractor"),
            patch.object(
                use_case, "_extract_and_split", side_effect=Exception("Main Error")
            ),
        ):
            with pytest.raises(Exception) as excinfo:
                use_case._process_single_video("url", video_id, subject, cmd)
            # The last exception raised in the finally/except block might be the one seen
            assert "Failed job update" in str(excinfo.value)

    def test_build_chunk_entities_coverage(self, use_case, mock_services):
        from langchain_core.documents import Document

        docs = [
            Document(page_content="content1", metadata={"token_count": 10}),
            Document(page_content="content2", metadata={"token_count": 20}),
        ]
        source = MagicMock()
        source.id = uuid.uuid4()
        source.source_type = "youtube"
        source.external_source = "vid1"
        subject = MagicMock()
        subject.id = uuid.uuid4()
        cmd = IngestYoutubeCommand(
            video_url="...", subject_id=str(subject.id), language="en"
        )
        job_id = uuid.uuid4()

        mock_services["model_loader_service"].model_name = "test-model"

        chunks = use_case._build_chunk_entities(docs, source, subject, cmd, job_id)
        assert len(chunks) == 2
        assert chunks[0].content == "content1"
        assert chunks[0].tokens_count == 10
        assert chunks[0].embedding_model == "test-model"
