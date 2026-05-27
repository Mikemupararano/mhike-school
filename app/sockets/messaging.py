import socketio

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)

socket_app = socketio.ASGIApp(
    socketio_server=sio,
)


@sio.event
async def connect(sid, environ, auth):
    print("Socket connected:", sid)


@sio.event
async def disconnect(sid):
    print("Socket disconnected:", sid)


@sio.event
async def join_conversation(sid, data):
    conversation_id = data["conversation_id"]

    await sio.enter_room(
        sid,
        f"conversation:{conversation_id}",
    )


@sio.event
async def send_message(sid, data):
    await sio.emit(
        "new_message",
        data,
        room=f"conversation:{data['conversation_id']}",
    )
