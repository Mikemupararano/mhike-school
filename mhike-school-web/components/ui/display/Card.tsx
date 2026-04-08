import React from "react";

export default function Card({
    children,
    style,
}: {
    children: React.ReactNode;
    style?: React.CSSProperties;
}) {
    return (
        <div
            style={{
                background: "rgba(255,255,255,0.96)",
                border: "1px solid #E2E8F0",
                borderRadius: 24,
                padding: 22,
                boxShadow: "0 12px 32px rgba(15, 23, 42, 0.06)",
                backdropFilter: "blur(10px)",
                ...style,
            }}
        >
            {children}
        </div>
    );
}