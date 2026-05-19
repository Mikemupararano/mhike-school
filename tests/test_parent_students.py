from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent_student import ParentStudent


@pytest.mark.asyncio
async def test_school_admin_can_create_parent_student_link(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    parent_user,
    student_user,
    auth_headers,
):
    response = await client.post(
        "/api/v1/parent-students/links",
        json={
            "parent_id": parent_user.id,
            "student_id": student_user.id,
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["parent_id"] == parent_user.id
    assert data["student_id"] == student_user.id

    created_link = await db_session.get(
        ParentStudent,
        data["id"],
    )

    assert created_link is not None


@pytest.mark.asyncio
async def test_cannot_create_duplicate_parent_student_link(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    parent_user,
    student_user,
    auth_headers,
):
    existing_link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    db_session.add(existing_link)

    await db_session.commit()

    response = await client.post(
        "/api/v1/parent-students/links",
        json={
            "parent_id": parent_user.id,
            "student_id": student_user.id,
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_children_for_parent(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    parent_user,
    student_user,
    auth_headers,
):
    link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    db_session.add(link)

    await db_session.commit()

    response = await client.get(
        f"/api/v1/parent-students/parents/{parent_user.id}/children",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["student_id"] == student_user.id


@pytest.mark.asyncio
async def test_list_parents_for_student(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    parent_user,
    student_user,
    auth_headers,
):
    link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    db_session.add(link)

    await db_session.commit()

    response = await client.get(
        f"/api/v1/parent-students/students/{student_user.id}/parents",
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["parent_id"] == parent_user.id


@pytest.mark.asyncio
async def test_school_admin_can_delete_parent_student_link(
    client: AsyncClient,
    db_session: AsyncSession,
    school_admin_user,
    parent_user,
    student_user,
    auth_headers,
):
    link = ParentStudent(
        parent_id=parent_user.id,
        student_id=student_user.id,
    )

    db_session.add(link)

    await db_session.commit()
    await db_session.refresh(link)

    response = await client.delete(
        "/api/v1/parent-students/links",
        params={
            "parent_id": parent_user.id,
            "student_id": student_user.id,
        },
        headers=auth_headers(school_admin_user),
    )

    assert response.status_code == 204

    deleted_link = await db_session.get(
        ParentStudent,
        link.id,
    )

    assert deleted_link is None
