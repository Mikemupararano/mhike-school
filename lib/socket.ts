import { io } from "socket.io-client";

export const socket = io("http://localhost:8000", {
    path: "/socket.io/socket.io",
    transports: ["websocket"],
    autoConnect: true,
});