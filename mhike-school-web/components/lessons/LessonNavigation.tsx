"use client";

export type LessonNavigationItem = {
    id: number;
    title: string;
    order: number;
    published?: boolean;
};

type LessonNavigationProps = {
    moduleId: number;
    lessons: LessonNavigationItem[];
    currentLessonId: number;
    completedLessonIds: Set<number>;
    onSelectLesson: (lessonId: number) => void;
};

export default function LessonNavigation({
    moduleId,
    lessons,
    currentLessonId,
    completedLessonIds,
    onSelectLesson,
}: LessonNavigationProps) {
    return (
        <aside
            style={{
                background: "white",
                border: "1px solid #E5E7EB",
                borderRadius: 18,
                padding: 18,
                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
                position: "sticky",
                top: 24,
            }}
        >
            <h2
                style={{
                    margin: "0 0 14px 0",
                    fontSize: 20,
                    fontWeight: 900,
                    color: "#111827",
                }}
            >
                Lesson Navigation
            </h2>

            <div
                style={{
                    color: "#6B7280",
                    fontSize: 14,
                    marginBottom: 14,
                }}
            >
                Module {moduleId} • {lessons.length} lessons
            </div>

            <div style={{ display: "grid", gap: 10 }}>
                {lessons.map((item, index) => {
                    const isCurrent = item.id === currentLessonId;
                    const isCompleted = completedLessonIds.has(item.id);

                    return (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => onSelectLesson(item.id)}
                            style={{
                                width: "100%",
                                padding: "14px 14px",
                                borderRadius: 14,
                                border: isCurrent
                                    ? "1px solid #2563EB"
                                    : "1px solid #E5E7EB",
                                background: isCurrent
                                    ? "#EFF6FF"
                                    : isCompleted
                                        ? "#ECFDF5"
                                        : "white",
                                textAlign: "left",
                                cursor: "pointer",
                            }}
                        >
                            <div
                                style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
                                    gap: 8,
                                }}
                            >
                                <div
                                    style={{
                                        fontSize: 12,
                                        color: isCurrent
                                            ? "#2563EB"
                                            : "#6B7280",
                                        fontWeight: 800,
                                    }}
                                >
                                    Lesson {index + 1}
                                </div>

                                {isCompleted && (
                                    <span
                                        style={{
                                            fontSize: 11,
                                            fontWeight: 800,
                                            color: "#166534",
                                            background: "#DCFCE7",
                                            padding: "4px 8px",
                                            borderRadius: 999,
                                        }}
                                    >
                                        Completed
                                    </span>
                                )}
                            </div>

                            <div
                                style={{
                                    marginTop: 4,
                                    fontWeight: isCurrent ? 800 : 700,
                                    color: "#111827",
                                    lineHeight: 1.4,
                                }}
                            >
                                {item.title}
                            </div>
                        </button>
                    );
                })}
            </div>
        </aside>
    );
}