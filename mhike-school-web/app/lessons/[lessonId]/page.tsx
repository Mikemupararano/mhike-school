"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiPost, getToken } from "@/lib/api";

type LessonOut = {
    id: number;
    title: string;
    content: string | null;
    content_type: string;
    order: number;
    module_id: number;
};

type LessonListItem = {
    id: number;
    title: string;
    order: number;
    published?: boolean;
};

type ProgressItem = {
    lesson_id: number;
    completed: boolean;
};

type QuizOptionPublicOut = {
    id: number;
    option_text: string;
    order: number;
};

type QuizQuestionPublicOut = {
    id: number;
    question_text: string;
    order: number;
    options: QuizOptionPublicOut[];
};

type QuizSubmitOut = {
    score: number;
    total: number;
    passed: boolean;
};

function ProgressPill({
    text,
    background,
    color,
}: {
    text: string;
    background: string;
    color: string;
}) {
    return (
        <span
            style={{
                fontSize: 12,
                fontWeight: 800,
                color,
                background,
                padding: "6px 10px",
                borderRadius: 999,
            }}
        >
            {text}
        </span>
    );
}

export default function LessonPage() {
    const router = useRouter();
    const params = useParams<{ lessonId: string }>();
    const lessonId = Number(params.lessonId);

    const [lesson, setLesson] = useState<LessonOut | null>(null);
    const [lessons, setLessons] = useState<LessonListItem[]>([]);
    const [completedLessonIds, setCompletedLessonIds] = useState<Set<number>>(new Set());

    const [quizQuestions, setQuizQuestions] = useState<QuizQuestionPublicOut[]>([]);
    const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({});
    const [quizResult, setQuizResult] = useState<QuizSubmitOut | null>(null);
    const [loadingQuiz, setLoadingQuiz] = useState(false);
    const [submittingQuiz, setSubmittingQuiz] = useState(false);

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState("");
    const [error, setError] = useState("");

    async function loadLesson() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        try {
            setLoading(true);
            setLoadingQuiz(true);
            setError("");
            setMessage("");
            setQuizResult(null);
            setQuizAnswers({});

            const lessonRes = await apiGet<LessonOut>(`/lessons/${lessonId}`, token);
            setLesson(lessonRes);

            const [listRes, progressRes, quizRes] = await Promise.all([
                apiGet<LessonListItem[]>(`/modules/${lessonRes.module_id}/lessons`, token),
                apiGet<ProgressItem[]>("/me/progress", token),
                apiGet<QuizQuestionPublicOut[]>(`/lessons/${lessonId}/quiz`, token).catch(() => []),
            ]);

            const sortedLessons = [...listRes].sort((a, b) => a.order - b.order);
            setLessons(sortedLessons);

            const completedIds = new Set(
                progressRes.filter((item) => item.completed).map((item) => item.lesson_id)
            );
            setCompletedLessonIds(completedIds);

            const sortedQuiz = [...quizRes].sort((a, b) => a.order - b.order);
            setQuizQuestions(sortedQuiz);

            if (completedIds.has(lessonId)) {
                setQuizResult({
                    score: sortedQuiz.length,
                    total: sortedQuiz.length,
                    passed: true,
                });
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to load lesson";
            setError(msg);
            setLesson(null);
            setLessons([]);
            setCompletedLessonIds(new Set());
            setQuizQuestions([]);
            setQuizAnswers({});
            setQuizResult(null);

            if (msg.includes("401") || msg.includes("403")) {
                router.replace("/login");
            }
        } finally {
            setLoading(false);
            setLoadingQuiz(false);
        }
    }

    useEffect(() => {
        if (!lessonId || Number.isNaN(lessonId)) return;
        void loadLesson();
    }, [lessonId]);

    const currentIndex = useMemo(
        () => lessons.findIndex((l) => l.id === lesson?.id),
        [lessons, lesson]
    );

    const prevLesson = currentIndex > 0 ? lessons[currentIndex - 1] : null;
    const nextLesson =
        currentIndex >= 0 && currentIndex < lessons.length - 1
            ? lessons[currentIndex + 1]
            : null;

    const currentLessonCompleted = lesson ? completedLessonIds.has(lesson.id) : false;
    const quizExists = quizQuestions.length > 0;
    const allQuestionsAnswered =
        quizQuestions.length > 0 &&
        quizQuestions.every((question) => Boolean(quizAnswers[question.id]));
    const canCompleteLesson =
        currentLessonCompleted || !quizExists || Boolean(quizResult?.passed);

    function selectAnswer(questionId: number, optionId: number) {
        setQuizAnswers((prev) => ({
            ...prev,
            [questionId]: optionId,
        }));
        setQuizResult(null);
        setMessage("");
    }

    async function submitQuiz() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        if (!quizExists) return;

        try {
            setSubmittingQuiz(true);
            setError("");
            setMessage("");

            const result = await apiPost<QuizSubmitOut>(
                `/lessons/${lessonId}/quiz/submit`,
                { answers: quizAnswers },
                token
            );

            setQuizResult(result);

            if (result.passed) {
                setMessage(
                    `Quiz passed! You scored ${result.score}/${result.total}. You can now complete the lesson.`
                );
            } else {
                setMessage(
                    `Quiz not passed yet. You scored ${result.score}/${result.total}. Please review the lesson and try again.`
                );
            }
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to submit quiz");
        } finally {
            setSubmittingQuiz(false);
        }
    }

    async function markComplete() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return;
        }

        if (!canCompleteLesson) {
            setMessage("Please pass the quiz before completing this lesson.");
            return;
        }

        try {
            setSaving(true);
            setMessage("");

            await apiPost(`/lessons/${lessonId}/progress`, {}, token);

            setCompletedLessonIds((prev) => {
                const next = new Set(prev);
                next.add(lessonId);
                return next;
            });

            if (nextLesson) {
                setMessage("Lesson completed. Moving to the next lesson...");
                setTimeout(() => {
                    router.push(`/lessons/${nextLesson.id}`);
                }, 900);
            } else {
                setMessage("Lesson marked as complete. You have finished this module.");
            }
        } catch (err: unknown) {
            setMessage(err instanceof Error ? err.message : "Failed to update progress");
        } finally {
            setSaving(false);
        }
    }

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F3F6FB",
                padding: "32px 24px",
            }}
        >
            <div style={{ maxWidth: 1400, margin: "0 auto" }}>
                <button
                    onClick={() => router.push("/dashboard")}
                    style={{
                        marginBottom: 20,
                        padding: "10px 14px",
                        borderRadius: 10,
                        border: "1px solid #E5E7EB",
                        background: "white",
                        cursor: "pointer",
                        fontWeight: 700,
                    }}
                >
                    ← Back to Dashboard
                </button>

                {loading && <div>Loading lesson...</div>}

                {error && (
                    <div
                        style={{
                            marginBottom: 16,
                            padding: 12,
                            borderRadius: 12,
                            background: "#FEF2F2",
                            color: "#991B1B",
                            border: "1px solid #FECACA",
                        }}
                    >
                        {error}
                    </div>
                )}

                {!loading && lesson && (
                    <div
                        style={{
                            display: "grid",
                            gridTemplateColumns: "360px 1fr",
                            gap: 24,
                            alignItems: "start",
                        }}
                    >
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

                            <div style={{ color: "#6B7280", fontSize: 14, marginBottom: 14 }}>
                                Module {lesson.module_id} • {lessons.length} lessons
                            </div>

                            <div style={{ display: "grid", gap: 10 }}>
                                {lessons.map((item, index) => {
                                    const isCurrent = item.id === lesson.id;
                                    const isCompleted = completedLessonIds.has(item.id);

                                    return (
                                        <button
                                            key={item.id}
                                            onClick={() => router.push(`/lessons/${item.id}`)}
                                            style={{
                                                width: "100%",
                                                padding: "14px 14px",
                                                borderRadius: 14,
                                                border: isCurrent ? "1px solid #2563EB" : "1px solid #E5E7EB",
                                                background: isCurrent ? "#EFF6FF" : isCompleted ? "#ECFDF5" : "white",
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
                                                        color: isCurrent ? "#2563EB" : "#6B7280",
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

                        <section
                            style={{
                                background: "white",
                                border: "1px solid #E5E7EB",
                                borderRadius: 18,
                                padding: 28,
                                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
                            }}
                        >
                            <h1
                                style={{
                                    fontSize: 40,
                                    fontWeight: 900,
                                    margin: "0 0 10px 0",
                                    color: "#111827",
                                    lineHeight: 1.1,
                                }}
                            >
                                {lesson.title}
                            </h1>

                            <div
                                style={{
                                    color: "#6B7280",
                                    marginBottom: 20,
                                    fontSize: 15,
                                    display: "flex",
                                    gap: 10,
                                    flexWrap: "wrap",
                                    alignItems: "center",
                                }}
                            >
                                <span>
                                    Lesson {lesson.order} • Type: {lesson.content_type}
                                </span>

                                {currentLessonCompleted && (
                                    <ProgressPill
                                        text="Completed"
                                        background="#DCFCE7"
                                        color="#166534"
                                    />
                                )}

                                {!currentLessonCompleted && quizExists && (
                                    <ProgressPill
                                        text={quizResult?.passed ? "Quiz passed" : "Quiz required"}
                                        background={quizResult?.passed ? "#DBEAFE" : "#FEF3C7"}
                                        color={quizResult?.passed ? "#1D4ED8" : "#92400E"}
                                    />
                                )}
                            </div>

                            <div
                                style={{
                                    minHeight: 320,
                                    borderRadius: 16,
                                    background: "#EFF6FF",
                                    display: "grid",
                                    placeItems: "center",
                                    padding: 28,
                                }}
                            >
                                {lesson.content_type === "video" ? (
                                    <video
                                        src={lesson.content ?? ""}
                                        controls
                                        style={{ width: "100%", borderRadius: 12 }}
                                    />
                                ) : (
                                    <div
                                        style={{
                                            color: "#374151",
                                            lineHeight: 1.9,
                                            width: "100%",
                                            maxWidth: 900,
                                            margin: "0 auto",
                                            whiteSpace: "pre-wrap",
                                            fontSize: 18,
                                        }}
                                    >
                                        {lesson.content || "No content available for this lesson yet."}
                                    </div>
                                )}
                            </div>

                            <section
                                style={{
                                    marginTop: 24,
                                    border: "1px solid #E5E7EB",
                                    borderRadius: 18,
                                    padding: 20,
                                    background: "#F9FAFB",
                                }}
                            >
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        gap: 12,
                                        alignItems: "center",
                                        flexWrap: "wrap",
                                        marginBottom: 16,
                                    }}
                                >
                                    <div>
                                        <h2
                                            style={{
                                                margin: 0,
                                                fontSize: 24,
                                                fontWeight: 900,
                                                color: "#111827",
                                            }}
                                        >
                                            Lesson Quiz
                                        </h2>
                                        <div style={{ color: "#6B7280", marginTop: 6, fontSize: 14 }}>
                                            {quizExists
                                                ? "Answer the multiple-choice questions and pass the quiz to complete this lesson."
                                                : "No quiz has been added to this lesson yet. You can complete the lesson directly."}
                                        </div>
                                    </div>

                                    {quizExists && quizResult && (
                                        <ProgressPill
                                            text={`${quizResult.score}/${quizResult.total} • ${quizResult.passed ? "Passed" : "Not passed"
                                                }`}
                                            background={quizResult.passed ? "#DCFCE7" : "#FEE2E2"}
                                            color={quizResult.passed ? "#166534" : "#991B1B"}
                                        />
                                    )}
                                </div>

                                {loadingQuiz && <div style={{ color: "#6B7280" }}>Loading quiz...</div>}

                                {!loadingQuiz && quizExists && (
                                    <div style={{ display: "grid", gap: 16 }}>
                                        {quizQuestions.map((question, questionIndex) => {
                                            const selectedOptionId = quizAnswers[question.id];

                                            return (
                                                <div
                                                    key={question.id}
                                                    style={{
                                                        border: "1px solid #E5E7EB",
                                                        borderRadius: 16,
                                                        padding: 16,
                                                        background: "white",
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            fontSize: 12,
                                                            color: "#6B7280",
                                                            fontWeight: 800,
                                                            marginBottom: 8,
                                                        }}
                                                    >
                                                        Question {questionIndex + 1}
                                                    </div>

                                                    <div
                                                        style={{
                                                            fontSize: 18,
                                                            fontWeight: 800,
                                                            color: "#111827",
                                                            marginBottom: 14,
                                                        }}
                                                    >
                                                        {question.question_text}
                                                    </div>

                                                    <div style={{ display: "grid", gap: 10 }}>
                                                        {question.options
                                                            .slice()
                                                            .sort((a, b) => a.order - b.order)
                                                            .map((option) => {
                                                                const isSelected = selectedOptionId === option.id;

                                                                return (
                                                                    <label
                                                                        key={option.id}
                                                                        style={{
                                                                            display: "flex",
                                                                            alignItems: "center",
                                                                            gap: 12,
                                                                            padding: "12px 14px",
                                                                            borderRadius: 12,
                                                                            border: isSelected
                                                                                ? "1px solid #2563EB"
                                                                                : "1px solid #E5E7EB",
                                                                            background: isSelected ? "#EFF6FF" : "white",
                                                                            cursor: "pointer",
                                                                        }}
                                                                    >
                                                                        <input
                                                                            type="radio"
                                                                            name={`question-${question.id}`}
                                                                            checked={isSelected}
                                                                            onChange={() =>
                                                                                selectAnswer(question.id, option.id)
                                                                            }
                                                                        />
                                                                        <span style={{ color: "#111827" }}>
                                                                            {option.option_text}
                                                                        </span>
                                                                    </label>
                                                                );
                                                            })}
                                                    </div>
                                                </div>
                                            );
                                        })}

                                        <div
                                            style={{
                                                display: "flex",
                                                gap: 12,
                                                flexWrap: "wrap",
                                                alignItems: "center",
                                            }}
                                        >
                                            <button
                                                onClick={submitQuiz}
                                                disabled={submittingQuiz || !allQuestionsAnswered}
                                                style={{
                                                    padding: "12px 16px",
                                                    borderRadius: 12,
                                                    border: "none",
                                                    background:
                                                        submittingQuiz || !allQuestionsAnswered ? "#E5E7EB" : "#2563EB",
                                                    color:
                                                        submittingQuiz || !allQuestionsAnswered ? "#6B7280" : "white",
                                                    fontWeight: 800,
                                                    cursor:
                                                        submittingQuiz || !allQuestionsAnswered
                                                            ? "not-allowed"
                                                            : "pointer",
                                                }}
                                            >
                                                {submittingQuiz ? "Submitting quiz..." : "Submit Quiz"}
                                            </button>

                                            {!allQuestionsAnswered && (
                                                <span style={{ color: "#6B7280", fontSize: 14 }}>
                                                    Answer all questions before submitting.
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {!loadingQuiz && !quizExists && (
                                    <div style={{ color: "#6B7280" }}>
                                        This lesson has no quiz yet.
                                    </div>
                                )}
                            </section>

                            <div
                                style={{
                                    marginTop: 20,
                                    display: "flex",
                                    gap: 12,
                                    flexWrap: "wrap",
                                }}
                            >
                                <button
                                    onClick={markComplete}
                                    disabled={saving || currentLessonCompleted || !canCompleteLesson}
                                    style={{
                                        padding: "12px 16px",
                                        borderRadius: 12,
                                        border: "none",
                                        background:
                                            saving || currentLessonCompleted || !canCompleteLesson
                                                ? "#E5E7EB"
                                                : "#2563EB",
                                        color:
                                            saving || currentLessonCompleted || !canCompleteLesson
                                                ? "#6B7280"
                                                : "white",
                                        fontWeight: 800,
                                        cursor:
                                            saving || currentLessonCompleted || !canCompleteLesson
                                                ? "not-allowed"
                                                : "pointer",
                                        opacity: saving ? 0.75 : 1,
                                    }}
                                >
                                    {currentLessonCompleted
                                        ? "Completed"
                                        : saving
                                            ? "Saving..."
                                            : quizExists && !quizResult?.passed
                                                ? "Pass Quiz to Complete Lesson"
                                                : "Mark Lesson Complete"}
                                </button>

                                <button
                                    disabled={!prevLesson}
                                    onClick={() => prevLesson && router.push(`/lessons/${prevLesson.id}`)}
                                    style={{
                                        padding: "12px 16px",
                                        borderRadius: 12,
                                        border: "1px solid #E5E7EB",
                                        background: prevLesson ? "white" : "#F3F4F6",
                                        color: "#111827",
                                        fontWeight: 700,
                                        cursor: prevLesson ? "pointer" : "not-allowed",
                                    }}
                                >
                                    ← Previous
                                </button>

                                <button
                                    disabled={!nextLesson}
                                    onClick={() => nextLesson && router.push(`/lessons/${nextLesson.id}`)}
                                    style={{
                                        padding: "12px 16px",
                                        borderRadius: 12,
                                        border: "none",
                                        background: nextLesson ? "#2563EB" : "#E5E7EB",
                                        color: nextLesson ? "white" : "#6B7280",
                                        fontWeight: 800,
                                        cursor: nextLesson ? "pointer" : "not-allowed",
                                    }}
                                >
                                    Next →
                                </button>
                            </div>

                            {message && (
                                <div
                                    style={{
                                        marginTop: 14,
                                        padding: 12,
                                        borderRadius: 12,
                                        background: "#F9FAFB",
                                        border: "1px solid #E5E7EB",
                                        color: "#111827",
                                    }}
                                >
                                    {message}
                                </div>
                            )}
                        </section>
                    </div>
                )}
            </div>
        </main>
    );
}