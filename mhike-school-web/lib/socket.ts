import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export function getSocket(auth: {
    user_id?: number | null;
    school_id?: number | null;
}) {
    if (!socket) {
        socket = io(
            process.env.NEXT_PUBLIC_SOCKET_URL ??
            "http://localhost:8000",
            {
                path: "/socket.io",
                auth,
                transports: ["websocket"],
            },
        );
    }

    return socket;
}

export function disconnectSocket() {
    socket?.disconnect();

    socket = null;
}