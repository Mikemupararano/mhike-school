import React from "react";

type BadgeKind = "neutral" | "success" | "warning" | "danger" | "info";

export default function Badge({
    text,
    kind = "neutral",
}: {
    text: string;
    kind?: BadgeKind;
}) {
    const styles: Record<BadgeKind, React.CSSProperties> = {
        neutral: { background: "#F3F4F6", color: "#374151" },
        success: { background: "#DCFCE7", color: "#166534" },
        warning: { background: "#FEF3C7", color: "#92400E" },
        danger: { background: "#FEE2E2", color: "#991B1B" },
        info: { background: "#DBEAFE", color: "#1D4ED8" },
    };

    return (
        <span
            style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "6px 10px",
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 800,
                ...styles[kind],
            }}
        >
            {text}
        </span>
    );
}