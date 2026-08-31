from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.user import UserRole
from app.services import assessment_script_upload_service
from tests.conftest import create_test_user


@pytest.mark.asyncio
async def test_upload_removes_pdf_when_script_creation_fails(
    db_session,
    monkeypatch,
    tmp_path: Path,
):
    teacher = await create_test_user(
        db_session,
        email="script.upload.cleanup.teacher@example.com",
        roles=[UserRole.TEACHER],
        school_id=1,
    )

    assessment = SimpleNamespace(
        id=1,
        school_id=1,
    )

    candidate = SimpleNamespace(
        id=1,
        assessment=assessment,
    )

    async def fake_get_candidate(
        **kwargs,
    ):
        return candidate

    async def failing_create_script_version(
        **kwargs,
    ):
        raise RuntimeError(
            "forced script creation failure",
        )

    monkeypatch.setattr(
        assessment_script_upload_service,
        "ASSESSMENT_SCRIPT_UPLOAD_ROOT",
        tmp_path / "assessment-scripts",
    )

    monkeypatch.setattr(
        assessment_script_upload_service,
        "get_candidate",
        fake_get_candidate,
    )

    monkeypatch.setattr(
        assessment_script_upload_service,
        "create_script_version",
        failing_create_script_version,
    )

    with pytest.raises(
        RuntimeError,
        match="forced script creation failure",
    ):
        await assessment_script_upload_service.upload_scanned_script(
            db=db_session,
            current_user=teacher,
            candidate_id=1,
            filename="cleanup-test.pdf",
            mime_type="application/pdf",
            contents=b"%PDF-1.4\ncleanup test\n%%EOF\n",
        )

    assert not list(
        (
            tmp_path
            / "assessment-scripts"
        ).rglob(
            "*.pdf",
        )
    )

