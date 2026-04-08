## Description
Implemented a comprehensive test suite for the chunk duplication feature, covering repository, service, and API layers. Additionally, improved the sidebar UX by enabling simple-toggle multi-selection, fixing indicator icon bugs, and adding a search-by-name field for subjects.

## Tasks
- [x] Create SQL repository tests for chunk duplicates `tests/infrastructure/repositories/sql/test_chunk_duplicate_repository.py`
- [x] Create service tests for duplicate detection logic `tests/infrastructure/services/test_chunk_duplicate_service.py`
- [x] Create API router tests for duplicate endpoints `tests/presentation/api/routes/test_duplicate_router.py`
- [x] Update `SidebarContext.tsx` to enable simple toggle selection for multiple bases.
- [x] Fix Check icon bug in multi-selection in `SidebarContext.tsx`.
- [x] Add search filter field in `SidebarContext.tsx`.
- [x] Fix `tests/conftest.py` import path for infrastructure.

## Additional Context
The sidebar changes eliminate the need for Ctrl+Click, making the multi-knowledge selection more discoverable. The search field ensures usability as the number of knowledge bases grows.
