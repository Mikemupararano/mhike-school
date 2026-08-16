from __future__ import annotations

import pytest

import app.tasks.assessment_publication as task_module


class _FakeSessionContext:
    def __init__(
        self,
        session,
    ) -> None:
        self.session = session

    async def __aenter__(
        self,
    ):
        return self.session

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        return None


@pytest.mark.asyncio
async def test_publish_due_assessment_results_returns_published_count(
    monkeypatch,
) -> None:
    fake_db = object()
    calls: list[object] = []

    async def fake_publish_due_scheduled_results(
        db,
    ):
        calls.append(
            db,
        )

        return [
            object(),
            object(),
            object(),
        ]

    monkeypatch.setattr(
        task_module,
        "AsyncSessionLocal",
        lambda: _FakeSessionContext(
            fake_db,
        ),
    )

    monkeypatch.setattr(
        task_module,
        "publish_due_scheduled_results",
        fake_publish_due_scheduled_results,
    )

    result = await task_module._publish_due_assessment_results()

    assert result == 3
    assert calls == [
        fake_db,
    ]


@pytest.mark.asyncio
async def test_publish_due_assessment_results_returns_zero_when_none_due(
    monkeypatch,
) -> None:
    fake_db = object()

    async def fake_publish_due_scheduled_results(
        db,
    ):
        assert db is fake_db

        return []

    monkeypatch.setattr(
        task_module,
        "AsyncSessionLocal",
        lambda: _FakeSessionContext(
            fake_db,
        ),
    )

    monkeypatch.setattr(
        task_module,
        "publish_due_scheduled_results",
        fake_publish_due_scheduled_results,
    )

    result = await task_module._publish_due_assessment_results()

    assert result == 0
