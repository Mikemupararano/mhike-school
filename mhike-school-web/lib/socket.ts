import { io, Socket } from "socket.io-client";

type SocketAuth = {
    user_id?: number | null;
    school_id?: number | null;
};

let socket: Socket | null = null;

function getSocketUrl() {
    return (
        process.env.NEXT_PUBLIC_SOCKET_URL ??
        "http://localhost:8000"
    );
}

export function getSocket(
    auth?: SocketAuth,
): Socket {
    if (!socket) {
        socket = io(
            getSocketUrl(),
            {
                path: "/socket.io",
                transports: ["websocket"],
                autoConnect: true,
                auth: auth ?? {},
            },
        );

        socket.on(
            "connect",
            () => {
                console.log(
                    "[socket] connected",
                    socket?.id,
                );
            },
        );

        socket.on(
            "disconnect",
            (reason) => {
                console.log(
                    "[socket] disconnected",
                    reason,
                );
            },
        );

        socket.on(
            "connect_error",
            (error) => {
                console.error(
                    "[socket] connection error",
                    error,
                );
            },
        );
    } else if (auth) {
        socket.auth = {
            user_id: auth.user_id,
            school_id: auth.school_id,
        };
    }

    return socket;
}

export function isSocketConnected(): boolean {
    return Boolean(
        socket?.connected,
    );
}

export function reconnectSocket(
    auth?: SocketAuth,
): Socket {
    if (socket) {
        socket.disconnect();
        socket = null;
    }

    return getSocket(auth);
}

export function disconnectSocket() {
    if (!socket) {
        return;
    }

    socket.removeAllListeners();
    socket.disconnect();
    socket = null;
}

export function joinConversation(
    conversationId: number | string,
) {
    const instance = getSocket();

    instance.emit(
        "join_conversation",
        {
            conversation_id:
                conversationId,
        },
    );
}

export function leaveConversation(
    conversationId: number | string,
) {
    const instance = getSocket();

    instance.emit(
        "leave_conversation",
        {
            conversation_id:
                conversationId,
        },
    );
}

export const SocketEvents = {
    MESSAGE_NEW:
        "message:new",

    MESSAGE_DELIVERED:
        "message:delivered",

    MESSAGE_READ:
        "message:read",

    MESSAGES_REFRESH:
        "messages:refresh",

    NOTIFICATION_NEW:
        "notification:new",

    TYPING_START:
        "typing:start",

    TYPING_STOP:
        "typing:stop",
} as const;