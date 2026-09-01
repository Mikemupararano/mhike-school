"""add question source page provenance

Revision ID: f3a9b7c21d44
Revises: e17c2d42c51b
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a9b7c21d44"
down_revision = "e17c2d42c51b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_questions",
        sa.Column(
            "source_page_number",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "assessment_question_snapshots",
        sa.Column(
            "source_page_number",
            sa.Integer(),
            nullable=True,
        ),
    )


    op.execute(
        sa.text(
            """
            WITH provenance_candidates AS (
                SELECT
                    ad.assessment_id,
                    q.item ->> 'question_number'
                        AS question_number,
                    (
                        q.item
                        -> 'source'
                        ->> 'page_number'
                    )::integer AS source_page_number,
                    aqe.imported_at,
                    aqe.id AS extraction_id
                FROM assessment_question_extractions AS aqe
                JOIN assessment_documents AS ad
                    ON ad.id = aqe.assessment_document_id
                CROSS JOIN LATERAL
                    jsonb_array_elements(
                        CASE
                            WHEN jsonb_typeof(
                                aqe.proposal_data::jsonb
                                -> 'questions'
                            ) = 'array'
                            THEN
                                aqe.proposal_data::jsonb
                                -> 'questions'
                            ELSE
                                '[]'::jsonb
                        END
                    ) AS q(item)
                WHERE aqe.status = 'imported'
                  AND q.item ->> 'included' = 'true'
                  AND (
                        q.item
                        -> 'source'
                        ->> 'page_number'
                      ) ~ '^[1-9][0-9]*$'
            ),
            provenance AS (
                SELECT DISTINCT ON (
                    assessment_id,
                    question_number
                )
                    assessment_id,
                    question_number,
                    source_page_number
                FROM provenance_candidates
                ORDER BY
                    assessment_id,
                    question_number,
                    imported_at DESC NULLS LAST,
                    extraction_id DESC
            )
            UPDATE assessment_questions AS aq
            SET source_page_number =
                provenance.source_page_number
            FROM provenance
            WHERE
                provenance.assessment_id =
                    aq.assessment_id
                AND provenance.question_number =
                    aq.question_number
                AND aq.source_page_number IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE assessment_question_snapshots AS aqs
            SET source_page_number =
                aq.source_page_number
            FROM assessment_questions AS aq
            WHERE
                aq.id = aqs.question_id
                AND aq.source_page_number IS NOT NULL
                AND aqs.source_page_number IS NULL
            """
        )
    )

def downgrade() -> None:
    op.drop_column(
        "assessment_question_snapshots",
        "source_page_number",
    )

    op.drop_column(
        "assessment_questions",
        "source_page_number",
    )
