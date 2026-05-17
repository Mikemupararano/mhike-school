from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response, status
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import PermissionService
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import AttendanceFilter
from app.services.attendance_service import AttendanceService

router = APIRouter(tags=["Attendance PDF Exports"])


@router.get("/registers/export/{session_id}/pdf")
async def export_attendance_register_pdf(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    PermissionService.ensure_active_user(current_user)
    PermissionService.ensure_school_admin_or_platform_admin(current_user)

    service = AttendanceService(db)

    session = await service.get_session_or_404(session_id)

    if session.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot export attendance register from another school.",
        )

    records = await service.list_records(
        AttendanceFilter(
            school_id=current_user.school_id,
            class_group_id=session.class_group_id,
            session_date=session.session_date,
            session_type=session.session_type,
            timetable_entry_id=session.timetable_entry_id,
            timetable_period_id=session.timetable_period_id,
            limit=200,
            offset=0,
        )
    )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
    )

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph(
        f"Attendance Register - Session {session.id}",
        styles["Heading1"],
    )

    elements.append(title)

    metadata = Paragraph(
        (
            f"Date: {session.session_date}<br/>"
            f"Session Type: {session.session_type}<br/>"
            f"Class Group ID: {session.class_group_id}"
        ),
        styles["BodyText"],
    )

    elements.append(metadata)
    elements.append(Spacer(1, 12))

    table_data = [
        [
            "Record ID",
            "Student ID",
            "Status",
            "Notes",
            "Marked By",
        ]
    ]

    for record in records:
        table_data.append(
            [
                str(record.id),
                str(record.student_id),
                str(record.status),
                record.notes or "",
                str(record.marked_by_id or ""),
            ]
        )

    table = Table(table_data, repeatRows=1)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]
        )
    )

    elements.append(table)

    document.build(elements)

    pdf_data = buffer.getvalue()
    buffer.close()

    filename = f"attendance_register_{session.id}_{session.session_date}.pdf"

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (f'attachment; filename="{filename}"'),
        },
    )
