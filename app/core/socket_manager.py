from __future__ import annotations

import socketio

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)

socket_app = socketio.ASGIApp(
    sio,
    socketio_path="socket.io",
)


@sio.event
async def connect(
    sid: str,
    environ,
    auth,
) -> None:
    user_id = None
    school_id = None

    if isinstance(auth, dict):
        user_id = auth.get("user_id")
        school_id = auth.get("school_id")

    if user_id is not None:
        await sio.enter_room(
            sid,
            f"user:{user_id}",
        )

    if school_id is not None:
        await sio.enter_room(
            sid,
            f"school:{school_id}",
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
    data: dict,
) -> None:
    conversation_id = data.get("conversation_id")

    if conversation_id is None:
        return

    await sio.enter_room(
        sid,
        f"conversation:{conversation_id}",
    )

    print(
        "Socket joined conversation:",
        sid,
        conversation_id,
    )


@sio.event
async def leave_conversation(
    sid: str,
    data: dict,
) -> None:
    conversation_id = data.get("conversation_id")

    if conversation_id is None:
        return

    await sio.leave_room(
        sid,
        f"conversation:{conversation_id}",
    )

    print(
        "Socket left conversation:",
        sid,
        conversation_id,
    )


async def emit_conversation_message(
    *,
    conversation_id: int,
    payload: dict,
) -> None:
    await sio.emit(
        "message:new",
        payload,
        room=f"conversation:{conversation_id}",
    )


async def emit_user_notification(
    *,
    user_id: int,
    payload: dict,
) -> None:
    await sio.emit(
        "notification:new",
        payload,
        room=f"user:{user_id}",
    )


async def emit_school_notification(
    *,
    school_id: int,
    payload: dict,
) -> None:
    await sio.emit(
        "notification:new",
        payload,
        room=f"school:{school_id}",
    )
