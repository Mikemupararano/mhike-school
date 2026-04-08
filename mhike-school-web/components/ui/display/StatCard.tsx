import React from "react";

export default function StatCard({
    label,
    value,
}: {
    label: string;
    value: string | number;
}) {
    return (
        <div
            style={{
                background: "#FFFFFF",
                border: "1px solid #E2E8F0",
                borderRadius: 20,
                padding: 18,
                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
            }}
        >
            <div style={{ fontSize: 14, color: "#64748B", fontWeight: 600 }}>
                {label}
            </div>
            <div
                style={{
                    marginTop: 8,
                    fontSize: 28,
                    fontWeight: 900,
                    color: "#0F172A",
                }}
            >
                {value}
            </div>
        </div>
    );
}