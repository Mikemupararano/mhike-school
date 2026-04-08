import React from "react";

export default function EmptyState({
    title = "Nothing here yet",
    description,
}: {
    title?: string;
    description?: string;
}) {
    return (
        <div
            style={{
                padding: 24,
                borderRadius: 16,
                border: "1px solid #E5E7EB",
                background: "#F8FAFC",
            }}
        >
            <div style={{ fontSize: 18, fontWeight: 800, color: "#0F172A" }}>
                {title}
            </div>
            {description ? (
                <p style={{ marginTop: 8, color: "#64748B", fontSize: 14 }}>
                    {description}
                </p>
            ) : null}
        </div>
    );
}