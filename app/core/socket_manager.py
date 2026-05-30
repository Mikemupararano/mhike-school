from __future__ import annotations

import os
from typing import Any

import socketio

ALLOWED_SOCKET_ORIGINS = os.getenv(
    "SOCKET_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=ALLOWED_SOCKET_ORIGINS,
)

socket_app = socketio.ASGIApp(
    sio,
    socketio_path="socket.io",
)


def _room_user(user_id: int | str) -> str:
    return f"user:{user_id}"


def _room_school(school_id: int | str) -> str:
    return f"school:{school_id}"


def _room_conversation(conversation_id: int | str) -> str:
    return f"conversation:{conversation_id}"


@sio.event
async def connect(
    sid: str,
    environ: dict[str, Any],
    auth: dict[str, Any] | None,
) -> None:
    user_id = None
    school_id = None

    if isinstance(auth, dict):
        user_id = auth.get("user_id")
        school_id = auth.get("school_id")

    if user_id is not None:
        await sio.enter_room(
            sid,
            _room_user(user_id),
        )

    if school_id is not None:
        await sio.enter_room(
            sid,
            _room_school(school_id),
        )

    print(
        "Socket connected:",
        sid,
        {
            "user_id": user_id,
            "school_id": school_id,
        },
    )


@sio.event
async def disconnect(sid: str) -> None:
    print("Socket disconnected:", sid)


@sio.event
async def join_conversation(
    sid: str,
    data: dict[str, Any],
) -> None:
    conversation_id = data.get("conversation_id")

    if conversation_id is None:
        return

    await sio.enter_room(
        sid,
        _room_conversation(conversation_id),
    )

    print(
        "Socket joined conversation:",
        sid,
        conversation_id,
    )


@sio.event
async def leave_conversation(
    sid: str,
    data: dict[str, Any],
) -> None:
    conversation_id = data.get("conversation_id")

    if conversation_id is None:
        return

    await sio.leave_room(
        sid,
        _room_conversation(conversation_id),
    )

    print(
        "Socket left conversation:",
        sid,
        conversation_id,
    )


@sio.event
async def send_message(
    sid: str,
    data: dict[str, Any],
) -> None:
    conversation_id = data.get("conversation_id")

    if conversation_id is None:
        return

    await sio.emit(
        "message:new",
        data,
        room=_room_conversation(conversation_id),
    )

    await sio.emit(
        "messages:refresh",
        {
            "conversation_id": conversation_id,
            "message_id": data.get("id"),
        },
        room=_room_conversation(conversation_id),
    )

    print(
        "Socket message emitted:",
        {
            "sid": sid,
            "conversation_id": conversation_id,
            "message_id": data.get("id"),
        },
    )


@sio.event
async def typing_start(
    sid: str,
    data: dict[str, Any],
) -> None:
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")
    full_name = data.get("full_name")

    if conversation_id is None or user_id is None:
        return

    await sio.emit(
        "typing:start",
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "full_name": full_name,
        },
        room=_room_conversation(conversation_id),
        skip_sid=sid,
    )


@sio.event
async def typing_stop(
    sid: str,
    data: dict[str, Any],
) -> None:
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")
    full_name = data.get("full_name")

    if conversation_id is None or user_id is None:
        return

    await sio.emit(
        "typing:stop",
        {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "full_name": full_name,
        },
        room=_room_conversation(conversation_id),
        skip_sid=sid,
    )


async def emit_conversation_message(
    *,
    conversation_id: int,
    payload: dict[str, Any],
) -> None:
    await sio.emit(
        "message:new",
        payload,
        room=_room_conversation(conversation_id),
    )

    await sio.emit(
        "messages:refresh",
        {
            "conversation_id": conversation_id,
            "message_id": payload.get("id"),
        },
        room=_room_conversation(conversation_id),
    )


async def emit_message_delivered(
    *,
    conversation_id: int,
    payload: dict[str, Any],
) -> None:
    await sio.emit(
        "message:delivered",
        payload,
        room=_room_conversation(conversation_id),
    )

    await sio.emit(
        "messages:refresh",
        {
            "conversation_id": conversation_id,
            "message_id": payload.get("message_id"),
        },
        room=_room_conversation(conversation_id),
    )


async def emit_message_read(
    *,
    conversation_id: int,
    payload: dict[str, Any],
) -> None:
    await sio.emit(
        "message:read",
        payload,
        room=_room_conversation(conversation_id),
    )

    await sio.emit(
        "messages:refresh",
        {
            "conversation_id": conversation_id,
            "message_id": payload.get("message_id"),
        },
        room=_room_conversation(conversation_id),
    )


async def emit_user_messages_refresh(
    *,
    user_id: int,
    payload: dict[str, Any] | None = None,
) -> None:
    await sio.emit(
        "messages:refresh",
        payload or {},
        room=_room_user(user_id),
    )


async def emit_school_messages_refresh(
    *,
    school_id: int,
    payload: dict[str, Any] | None = None,
) -> None:
    await sio.emit(
        "messages:refresh",
        payload or {},
        room=_room_school(school_id),
    )


async def emit_user_notification(
    *,
    user_id: int,
    payload: dict[str, Any],
) -> None:
    await sio.emit(
        "notification:new",
        payload,
        room=_room_user(user_id),
    )


async def emit_school_notification(
    *,
    school_id: int,
    payload: dict[str, Any],
) -> None:
    await sio.emit(
        "notification:new",
        payload,
        room=_room_school(school_id),
    )
