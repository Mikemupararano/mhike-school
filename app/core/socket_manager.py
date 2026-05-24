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


@sio.event
async def disconnect(sid: str) -> None:
    return None


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
