from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment_question import AssessmentQuestion
from app.services import assessment_document_service
from tests.test_assessment_question_extractions_api import (
    _build_pdf_bytes,
    _create_assessment_with_question_paper,
)


@pytest.fixture
def assessment_upload_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """
    Keep integration-test assessment documents outside the real uploads folder.

    Fixtures declared in another test module are not automatically available to
    this standalone test file, so the upload-root fixture is intentionally
    defined locally.
    """

    upload_root = tmp_path / "assessment_interaction_palette_uploads"

    monkeypatch.setattr(
        assessment_document_service,
        "ASSESSMENT_UPLOAD_ROOT",
        upload_root,
    )

    return upload_root


@pytest.mark.asyncio
async def test_inferred_equation_interaction_config_survives_review_and_import(
    client: AsyncClient,
    db_session: AsyncSession,
    teacher_user,
    auth_headers,
    assessment_upload_root: Path,
):
    """
    Prove the parser-v8 interaction configuration survives the complete public
    workflow:

        extraction proposal -> teacher review -> explicit import
        -> canonical AssessmentQuestion.interaction_config

    The review payload deliberately omits ``interaction_config``. This verifies
    that an inferred configuration is preserved unless the teacher explicitly
    replaces or removes it.
    """

    pdf_bytes = _build_pdf_bytes(
        [
            [
                (
                    "1 Use the equation for density and rearrange the equation "
                    "to make area the subject. Show your algebra. [3]"
                ),
            ],
        ]
    )

    assessment, document = await _create_assessment_with_question_paper(
        client,
        db_session,
        teacher_user=teacher_user,
        auth_headers=auth_headers,
        pdf_bytes=pdf_bytes,
    )

    create_response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/documents/{document['id']}"
            "/question-extractions"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert create_response.status_code == 201, create_response.text

    created = create_response.json()

    assert created["parser_version"] == "8"

    proposal = created["proposal_data"]
    questions = proposal["questions"]

    assert len(questions) == 1

    proposed_question = questions[0]
    proposed_config = proposed_question.get(
        "interaction_config",
    )

    assert isinstance(
        proposed_config,
        dict,
    )
    assert proposed_config["palette_id"] == "general.equation_editor"
    assert proposed_config["mode"] == "equation"
    assert proposed_config["equation_format"] == "latex"
    assert proposed_config["allow_equation_rearrangement"] is True
    assert proposed_config["allow_equation_steps"] is True

    review_payload = {
        "review_status": "reviewed",
        "review_notes": "Interaction configuration checked.",
        "questions": [
            {
                "candidate_index": 0,
                "question_number": proposed_question["question_number"],
                "text": proposed_question.get(
                    "text",
                    "",
                )
                or "",
                "marks": proposed_question["marks"],
                "parent_question_number": proposed_question.get(
                    "parent_question_number",
                ),
                # interaction_config intentionally omitted
                "included": True,
                "reviewed": True,
            },
        ],
    }

    review_response = await client.patch(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{created['id']}/review"
        ),
        json=review_payload,
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert review_response.status_code == 200, review_response.text

    reviewed = review_response.json()
    reviewed_question = reviewed["proposal_data"]["questions"][0]
    reviewed_config = reviewed_question.get(
        "interaction_config",
    )

    assert isinstance(
        reviewed_config,
        dict,
    )
    assert reviewed_config["palette_id"] == "general.equation_editor"
    assert reviewed_config == proposed_config

    import_response = await client.post(
        (
            f"/api/v1/assessments/{assessment['id']}"
            f"/question-extractions/{created['id']}/import"
        ),
        headers=auth_headers(
            teacher_user,
        ),
    )

    assert import_response.status_code == 200, import_response.text

    imported = import_response.json()

    assert imported["imported_markable_question_count"] == 1

    result = await db_session.execute(
        select(
            AssessmentQuestion,
        ).where(
            AssessmentQuestion.assessment_id == assessment["id"],
            AssessmentQuestion.is_markable.is_(True),
        )
    )

    canonical_question = result.scalar_one()

    assert isinstance(
        canonical_question.interaction_config,
        dict,
    )
    assert (
        canonical_question.interaction_config["palette_id"]
        == "general.equation_editor"
    )
    assert canonical_question.interaction_config["mode"] == "equation"
    assert canonical_question.interaction_config["equation_format"] == "latex"

    canonical_tool_types = {
        tool["tool_type"]
        for tool in canonical_question.interaction_config["tools"]
    }

    assert "equation_editor" in canonical_tool_types
    assert "equation_manipulation" in canonical_tool_types
