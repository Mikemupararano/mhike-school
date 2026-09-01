from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.models.user import User, UserRole
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

@pytest.mark.asyncio
async def test_upload_rolls_back_when_scaffolding_fails(
    db_session,
    monkeypatch,
    tmp_path: Path,
):
    teacher = await create_test_user(
        db_session,
        email="script.upload.scaffold.rollback@example.com",
        roles=[UserRole.TEACHER],
        school_id=1,
    )

    await db_session.commit()

    teacher_id = teacher.id
    original_email = teacher.email

    assessment = SimpleNamespace(
        id=1,
        school_id=1,
    )

    candidate = SimpleNamespace(
        id=1,
        assessment=assessment,
    )

    script = SimpleNamespace(
        id=1001,
    )

    async def fake_get_candidate(
        **kwargs,
    ):
        return candidate

    async def fake_create_script_version(
        **kwargs,
    ):
        assert kwargs["commit_transaction"] is False

        teacher.email = "transaction-should-rollback@example.com"

        db_session.add(
            teacher,
        )

        await db_session.flush()

        return script

    async def failing_scaffold(
        *args,
        **kwargs,
    ):
        raise RuntimeError(
            "forced scanned scaffolding failure",
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
        fake_create_script_version,
    )

    monkeypatch.setattr(
        assessment_script_upload_service,
        "scaffold_submitted_scanned_script_responses",
        failing_scaffold,
    )

    with pytest.raises(
        RuntimeError,
        match="forced scanned scaffolding failure",
    ):
        await assessment_script_upload_service.upload_scanned_script(
            db=db_session,
            current_user=teacher,
            candidate_id=1,
            filename="scaffold-rollback.pdf",
            mime_type="application/pdf",
            contents=b"%PDF-1.4\nrollback test\n%%EOF\n",
        )

    stored_teacher = await db_session.get(
        User,
        teacher_id,
    )

    assert stored_teacher is not None
    assert stored_teacher.email == original_email

    assert not list(
        (
            tmp_path
            / "assessment-scripts"
        ).rglob(
            "*.pdf",
        )
    )



