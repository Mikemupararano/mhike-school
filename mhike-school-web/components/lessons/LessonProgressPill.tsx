"use client";

type LessonProgressPillProps = {
    text: string;
    background: string;
    color: string;
};

export default function LessonProgressPill({
    text,
    background,
    color,
}: LessonProgressPillProps) {
    return (
        <span
            style={{
                fontSize: 12,
                fontWeight: 800,
                color,
                background,
                padding: "6px 10px",
                borderRadius: 999,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                whiteSpace: "nowrap",
            }}
        >
            {text}
        </span>
    );
}