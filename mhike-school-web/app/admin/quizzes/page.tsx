"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost, getToken } from "@/lib/api";

type CourseOut = {
    id: number;
    title: string;
    published?: boolean;
};

type ModuleOut = {
    id: number;
    title: string;
    order: number;
};

type LessonOut = {
    id: number;
    module_id: number;
    title: string;
    content_type: string;
    content: string | null;
    order: number;
};

type QuizOptionOut = {
    id: number;
    option_text: string;
    is_correct: boolean;
    order: number;
};

type QuizQuestionOut = {
    id: number;
    lesson_id: number;
    question_text: string;
    order: number;
    options: QuizOptionOut[];
};

type QuizQuestionCreate = {
    question_text: string;
    order: number;
};

type QuizOptionCreate = {
    option_text: string;
    is_correct: boolean;
    order: number;
};

function Panel({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <section
            style={{
                background: "white",
                border: "1px solid #E5E7EB",
                borderRadius: 18,
                padding: 20,
                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
            }}
        >
            <h2
                style={{
                    margin: "0 0 16px 0",
                    fontSize: 20,
                    fontWeight: 900,
                    color: "#111827",
                }}
            >
                {title}
            </h2>
            {children}
        </section>
    );
}

export default function AdminQuizzesPage() {
    const router = useRouter();

    const [courses, setCourses] = useState<CourseOut[]>([]);
    const [modules, setModules] = useState<ModuleOut[]>([]);
    const [lessons, setLessons] = useState<LessonOut[]>([]);
    const [questions, setQuestions] = useState<QuizQuestionOut[]>([]);

    const [selectedCourseId, setSelectedCourseId] = useState<number | "">("");
    const [selectedModuleId, setSelectedModuleId] = useState<number | "">("");
    const [selectedLessonId, setSelectedLessonId] = useState<number | "">("");

    const [loadingCourses, setLoadingCourses] = useState(true);
    const [loadingModules, setLoadingModules] = useState(false);
    const [loadingLessons, setLoadingLessons] = useState(false);
    const [loadingQuiz, setLoadingQuiz] = useState(false);
    const [savingQuestion, setSavingQuestion] = useState(false);
    const [savingOptionForQuestionId, setSavingOptionForQuestionId] = useState<number | null>(null);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const [questionForm, setQuestionForm] = useState<QuizQuestionCreate>({
        question_text: "",
        order: 1,
    });

    const [optionDrafts, setOptionDrafts] = useState<
        Record<number, QuizOptionCreate>
    >({});

    const selectedCourse = useMemo(
        () => courses.find((c) => c.id === selectedCourseId) ?? null,
        [courses, selectedCourseId]
    );
    const selectedModule = useMemo(
        () => modules.find((m) => m.id === selectedModuleId) ?? null,
        [modules, selectedModuleId]
    );
    const selectedLesson = useMemo(
        () => lessons.find((l) => l.id === selectedLessonId) ?? null,
        [lessons, selectedLessonId]
    );

    function authGuard() {
        const token = getToken();
        if (!token) {
            router.replace("/login");
            return null;
        }
        return token;
    }

    async function loadCourses() {
        const token = authGuard();
        if (!token) return;

        try {
            setLoadingCourses(true);
            setError("");
            const res = await apiGet<CourseOut[]>("/courses", token);
            setCourses(res);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load courses");
        } finally {
            setLoadingCourses(false);
        }
    }

    async function loadModules(courseId: number) {
        const token = authGuard();
        if (!token) return;

        try {
            setLoadingModules(true);
            setError("");
            setModules([]);
            setLessons([]);
            setQuestions([]);
            setSelectedModuleId("");
            setSelectedLessonId("");

            const res = await apiGet<ModuleOut[]>(`/courses/${courseId}/modules`, token);
            setModules(res);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load modules");
        } finally {
            setLoadingModules(false);
        }
    }

    async function loadLessons(moduleId: number) {
        const token = authGuard();
        if (!token) return;

        try {
            setLoadingLessons(true);
            setError("");
            setLessons([]);
            setQuestions([]);
            setSelectedLessonId("");

            const res = await apiGet<LessonOut[]>(`/modules/${moduleId}/lessons`, token);
            setLessons(res);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load lessons");
        } finally {
            setLoadingLessons(false);
        }
    }

    async function loadQuiz(lessonId: number) {
        const token = authGuard();
        if (!token) return;

        try {
            setLoadingQuiz(true);
            setError("");
            setSuccess("");
            const res = await apiGet<QuizQuestionOut[]>(
                `/lessons/${lessonId}/quiz/admin`,
                token
            );
            setQuestions(res);
            setQuestionForm((prev) => ({
                ...prev,
                order: res.length + 1,
            }));
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to load quiz";
            if (msg.includes("404")) {
                setQuestions([]);
                setQuestionForm((prev) => ({ ...prev, order: 1 }));
            } else {
                setError(msg);
            }
        } finally {
            setLoadingQuiz(false);
        }
    }

    async function createQuestion() {
        const token = authGuard();
        if (!token || !selectedLessonId) return;

        const text = questionForm.question_text.trim();
        if (!text) {
            setError("Enter a question first.");
            return;
        }

        try {
            setSavingQuestion(true);
            setError("");
            setSuccess("");

            await apiPost<QuizQuestionOut>(
                `/lessons/${selectedLessonId}/quiz/questions`,
                {
                    question_text: text,
                    order: questionForm.order,
                },
                token
            );

            setQuestionForm({
                question_text: "",
                order: questions.length + 2,
            });

            setSuccess("Question created.");
            await loadQuiz(selectedLessonId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to create question");
        } finally {
            setSavingQuestion(false);
        }
    }

    function updateOptionDraft(
        questionId: number,
        patch: Partial<QuizOptionCreate>
    ) {
        setOptionDrafts((prev) => ({
            ...prev,
            [questionId]: {
                option_text: prev[questionId]?.option_text ?? "",
                is_correct: prev[questionId]?.is_correct ?? false,
                order:
                    prev[questionId]?.order ??
                    ((questions.find((q) => q.id === questionId)?.options.length ?? 0) + 1),
                ...patch,
            },
        }));
    }

    async function createOption(questionId: number) {
        const token = authGuard();
        if (!token) return;

        const draft = optionDrafts[questionId];
        if (!draft || !draft.option_text.trim()) {
            setError("Enter option text first.");
            return;
        }

        try {
            setSavingOptionForQuestionId(questionId);
            setError("");
            setSuccess("");

            await apiPost<QuizOptionOut>(
                `/quiz/questions/${questionId}/options`,
                {
                    option_text: draft.option_text.trim(),
                    is_correct: draft.is_correct,
                    order: draft.order,
                },
                token
            );

            setOptionDrafts((prev) => ({
                ...prev,
                [questionId]: {
                    option_text: "",
                    is_correct: false,
                    order:
                        (questions.find((q) => q.id === questionId)?.options.length ?? 0) + 2,
                },
            }));

            setSuccess("Option created.");
            if (selectedLessonId) {
                await loadQuiz(selectedLessonId);
            }
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to create option");
        } finally {
            setSavingOptionForQuestionId(null);
        }
    }

    useEffect(() => {
        void loadCourses();
    }, []);

    useEffect(() => {
        if (selectedCourseId) {
            void loadModules(selectedCourseId);
        }
    }, [selectedCourseId]);

    useEffect(() => {
        if (selectedModuleId) {
            void loadLessons(selectedModuleId);
        }
    }, [selectedModuleId]);

    useEffect(() => {
        if (selectedLessonId) {
            void loadQuiz(selectedLessonId);
        }
    }, [selectedLessonId]);

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "#F3F6FB",
                padding: "32px 24px",
            }}
        >
            <div style={{ maxWidth: 1200, margin: "0 auto" }}>
                <button
                    onClick={() => router.push("/dashboard")}
                    style={{
                        marginBottom: 18,
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

                <section
                    style={{
                        background: "linear-gradient(120deg, #1D4ED8, #60A5FA)",
                        borderRadius: 24,
                        color: "white",
                        padding: "28px 30px",
                        boxShadow: "0 18px 40px rgba(37, 99, 235, 0.18)",
                        marginBottom: 22,
                    }}
                >
                    <div style={{ fontSize: 16, opacity: 0.9 }}>Admin quiz manager</div>
                    <h1
                        style={{
                            margin: "10px 0 8px 0",
                            fontSize: 38,
                            fontWeight: 900,
                            lineHeight: 1.1,
                        }}
                    >
                        Create Multiple Choice Quizzes
                    </h1>
                    <div style={{ opacity: 0.95, fontSize: 17 }}>
                        Select a course, module, and lesson, then add quiz questions and answer
                        options.
                    </div>
                </section>

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

                {success && (
                    <div
                        style={{
                            marginBottom: 16,
                            padding: 12,
                            borderRadius: 12,
                            background: "#ECFDF5",
                            color: "#166534",
                            border: "1px solid #A7F3D0",
                        }}
                    >
                        {success}
                    </div>
                )}

                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: "380px 1fr",
                        gap: 20,
                        alignItems: "start",
                    }}
                >
                    <div style={{ display: "grid", gap: 20 }}>
                        <Panel title="1. Select Lesson">
                            <div style={{ display: "grid", gap: 14 }}>
                                <div>
                                    <label
                                        style={{
                                            display: "block",
                                            marginBottom: 6,
                                            fontWeight: 700,
                                            color: "#111827",
                                        }}
                                    >
                                        Course
                                    </label>
                                    <select
                                        value={selectedCourseId}
                                        onChange={(e) =>
                                            setSelectedCourseId(e.target.value ? Number(e.target.value) : "")
                                        }
                                        style={{
                                            width: "100%",
                                            padding: "12px 14px",
                                            borderRadius: 12,
                                            border: "1px solid #E5E7EB",
                                            background: "white",
                                        }}
                                    >
                                        <option value="">
                                            {loadingCourses ? "Loading courses..." : "Select course"}
                                        </option>
                                        {courses.map((course) => (
                                            <option key={course.id} value={course.id}>
                                                {course.title}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label
                                        style={{
                                            display: "block",
                                            marginBottom: 6,
                                            fontWeight: 700,
                                            color: "#111827",
                                        }}
                                    >
                                        Module
                                    </label>
                                    <select
                                        value={selectedModuleId}
                                        onChange={(e) =>
                                            setSelectedModuleId(e.target.value ? Number(e.target.value) : "")
                                        }
                                        disabled={!selectedCourseId || loadingModules}
                                        style={{
                                            width: "100%",
                                            padding: "12px 14px",
                                            borderRadius: 12,
                                            border: "1px solid #E5E7EB",
                                            background: "white",
                                        }}
                                    >
                                        <option value="">
                                            {!selectedCourseId
                                                ? "Select course first"
                                                : loadingModules
                                                    ? "Loading modules..."
                                                    : "Select module"}
                                        </option>
                                        {modules.map((module) => (
                                            <option key={module.id} value={module.id}>
                                                {module.title}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label
                                        style={{
                                            display: "block",
                                            marginBottom: 6,
                                            fontWeight: 700,
                                            color: "#111827",
                                        }}
                                    >
                                        Lesson
                                    </label>
                                    <select
                                        value={selectedLessonId}
                                        onChange={(e) =>
                                            setSelectedLessonId(e.target.value ? Number(e.target.value) : "")
                                        }
                                        disabled={!selectedModuleId || loadingLessons}
                                        style={{
                                            width: "100%",
                                            padding: "12px 14px",
                                            borderRadius: 12,
                                            border: "1px solid #E5E7EB",
                                            background: "white",
                                        }}
                                    >
                                        <option value="">
                                            {!selectedModuleId
                                                ? "Select module first"
                                                : loadingLessons
                                                    ? "Loading lessons..."
                                                    : "Select lesson"}
                                        </option>
                                        {lessons.map((lesson) => (
                                            <option key={lesson.id} value={lesson.id}>
                                                {lesson.title}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div
                                    style={{
                                        padding: 14,
                                        borderRadius: 14,
                                        background: "#F9FAFB",
                                        border: "1px solid #E5E7EB",
                                        color: "#374151",
                                        lineHeight: 1.6,
                                        fontSize: 14,
                                    }}
                                >
                                    <div>
                                        <b>Course:</b> {selectedCourse?.title ?? "—"}
                                    </div>
                                    <div>
                                        <b>Module:</b> {selectedModule?.title ?? "—"}
                                    </div>
                                    <div>
                                        <b>Lesson:</b> {selectedLesson?.title ?? "—"}
                                    </div>
                                </div>
                            </div>
                        </Panel>

                        <Panel title="2. Add Question">
                            <div style={{ display: "grid", gap: 12 }}>
                                <div>
                                    <label
                                        style={{
                                            display: "block",
                                            marginBottom: 6,
                                            fontWeight: 700,
                                            color: "#111827",
                                        }}
                                    >
                                        Question text
                                    </label>
                                    <textarea
                                        value={questionForm.question_text}
                                        onChange={(e) =>
                                            setQuestionForm((prev) => ({
                                                ...prev,
                                                question_text: e.target.value,
                                            }))
                                        }
                                        placeholder="Enter a multiple choice question"
                                        rows={4}
                                        disabled={!selectedLessonId}
                                        style={{
                                            width: "100%",
                                            padding: "12px 14px",
                                            borderRadius: 12,
                                            border: "1px solid #E5E7EB",
                                            background: "white",
                                            resize: "vertical",
                                        }}
                                    />
                                </div>

                                <div>
                                    <label
                                        style={{
                                            display: "block",
                                            marginBottom: 6,
                                            fontWeight: 700,
                                            color: "#111827",
                                        }}
                                    >
                                        Display order
                                    </label>
                                    <input
                                        type="number"
                                        min={1}
                                        value={questionForm.order}
                                        onChange={(e) =>
                                            setQuestionForm((prev) => ({
                                                ...prev,
                                                order: Number(e.target.value) || 1,
                                            }))
                                        }
                                        disabled={!selectedLessonId}
                                        style={{
                                            width: "100%",
                                            padding: "12px 14px",
                                            borderRadius: 12,
                                            border: "1px solid #E5E7EB",
                                            background: "white",
                                        }}
                                    />
                                </div>

                                <button
                                    onClick={createQuestion}
                                    disabled={!selectedLessonId || savingQuestion}
                                    style={{
                                        padding: "12px 16px",
                                        borderRadius: 12,
                                        border: "none",
                                        background: !selectedLessonId ? "#E5E7EB" : "#2563EB",
                                        color: !selectedLessonId ? "#6B7280" : "white",
                                        fontWeight: 800,
                                        cursor: !selectedLessonId || savingQuestion ? "not-allowed" : "pointer",
                                    }}
                                >
                                    {savingQuestion ? "Saving question..." : "Create Question"}
                                </button>
                            </div>
                        </Panel>
                    </div>

                    <Panel title="3. Manage Quiz Questions">
                        {!selectedLessonId && (
                            <div style={{ color: "#6B7280" }}>
                                Select a lesson to manage its quiz.
                            </div>
                        )}

                        {selectedLessonId && loadingQuiz && (
                            <div style={{ color: "#6B7280" }}>Loading quiz...</div>
                        )}

                        {selectedLessonId && !loadingQuiz && questions.length === 0 && (
                            <div style={{ color: "#6B7280" }}>
                                No quiz questions yet for this lesson. Create your first question.
                            </div>
                        )}

                        {selectedLessonId && !loadingQuiz && questions.length > 0 && (
                            <div style={{ display: "grid", gap: 18 }}>
                                {questions.map((question, questionIndex) => {
                                    const draft = optionDrafts[question.id] ?? {
                                        option_text: "",
                                        is_correct: false,
                                        order: question.options.length + 1,
                                    };

                                    return (
                                        <div
                                            key={question.id}
                                            style={{
                                                border: "1px solid #E5E7EB",
                                                borderRadius: 16,
                                                padding: 16,
                                                background: "#F9FAFB",
                                            }}
                                        >
                                            <div
                                                style={{
                                                    display: "flex",
                                                    justifyContent: "space-between",
                                                    gap: 12,
                                                    alignItems: "start",
                                                    flexWrap: "wrap",
                                                }}
                                            >
                                                <div>
                                                    <div
                                                        style={{
                                                            fontSize: 12,
                                                            fontWeight: 800,
                                                            color: "#6B7280",
                                                        }}
                                                    >
                                                        Question {questionIndex + 1} • Order {question.order}
                                                    </div>
                                                    <div
                                                        style={{
                                                            marginTop: 6,
                                                            fontSize: 18,
                                                            fontWeight: 800,
                                                            color: "#111827",
                                                        }}
                                                    >
                                                        {question.question_text}
                                                    </div>
                                                </div>
                                            </div>

                                            <div style={{ marginTop: 14, display: "grid", gap: 10 }}>
                                                {question.options.length === 0 && (
                                                    <div style={{ color: "#6B7280" }}>
                                                        No options added yet.
                                                    </div>
                                                )}

                                                {question.options
                                                    .slice()
                                                    .sort((a, b) => a.order - b.order)
                                                    .map((option, optionIndex) => (
                                                        <div
                                                            key={option.id}
                                                            style={{
                                                                display: "flex",
                                                                justifyContent: "space-between",
                                                                gap: 12,
                                                                alignItems: "center",
                                                                padding: "12px 14px",
                                                                borderRadius: 12,
                                                                background: option.is_correct ? "#ECFDF5" : "white",
                                                                border: "1px solid #E5E7EB",
                                                            }}
                                                        >
                                                            <div>
                                                                <div
                                                                    style={{
                                                                        fontSize: 12,
                                                                        color: "#6B7280",
                                                                        fontWeight: 700,
                                                                    }}
                                                                >
                                                                    Option {optionIndex + 1}
                                                                </div>
                                                                <div style={{ marginTop: 4, color: "#111827" }}>
                                                                    {option.option_text}
                                                                </div>
                                                            </div>

                                                            {option.is_correct && (
                                                                <span
                                                                    style={{
                                                                        fontSize: 12,
                                                                        fontWeight: 800,
                                                                        color: "#166534",
                                                                        background: "#DCFCE7",
                                                                        padding: "6px 10px",
                                                                        borderRadius: 999,
                                                                    }}
                                                                >
                                                                    Correct
                                                                </span>
                                                            )}
                                                        </div>
                                                    ))}
                                            </div>

                                            <div
                                                style={{
                                                    marginTop: 16,
                                                    paddingTop: 16,
                                                    borderTop: "1px solid #E5E7EB",
                                                    display: "grid",
                                                    gap: 10,
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        fontSize: 14,
                                                        fontWeight: 800,
                                                        color: "#111827",
                                                    }}
                                                >
                                                    Add option
                                                </div>

                                                <input
                                                    type="text"
                                                    placeholder="Option text"
                                                    value={draft.option_text}
                                                    onChange={(e) =>
                                                        updateOptionDraft(question.id, {
                                                            option_text: e.target.value,
                                                        })
                                                    }
                                                    style={{
                                                        width: "100%",
                                                        padding: "12px 14px",
                                                        borderRadius: 12,
                                                        border: "1px solid #E5E7EB",
                                                        background: "white",
                                                    }}
                                                />

                                                <div
                                                    style={{
                                                        display: "grid",
                                                        gridTemplateColumns: "140px 1fr auto",
                                                        gap: 10,
                                                        alignItems: "center",
                                                    }}
                                                >
                                                    <input
                                                        type="number"
                                                        min={1}
                                                        value={draft.order}
                                                        onChange={(e) =>
                                                            updateOptionDraft(question.id, {
                                                                order: Number(e.target.value) || 1,
                                                            })
                                                        }
                                                        style={{
                                                            width: "100%",
                                                            padding: "12px 14px",
                                                            borderRadius: 12,
                                                            border: "1px solid #E5E7EB",
                                                            background: "white",
                                                        }}
                                                    />

                                                    <label
                                                        style={{
                                                            display: "flex",
                                                            alignItems: "center",
                                                            gap: 8,
                                                            color: "#111827",
                                                            fontWeight: 700,
                                                        }}
                                                    >
                                                        <input
                                                            type="checkbox"
                                                            checked={draft.is_correct}
                                                            onChange={(e) =>
                                                                updateOptionDraft(question.id, {
                                                                    is_correct: e.target.checked,
                                                                })
                                                            }
                                                        />
                                                        Mark as correct answer
                                                    </label>

                                                    <button
                                                        onClick={() => createOption(question.id)}
                                                        disabled={savingOptionForQuestionId === question.id}
                                                        style={{
                                                            padding: "12px 16px",
                                                            borderRadius: 12,
                                                            border: "none",
                                                            background: "#2563EB",
                                                            color: "white",
                                                            fontWeight: 800,
                                                            cursor:
                                                                savingOptionForQuestionId === question.id
                                                                    ? "not-allowed"
                                                                    : "pointer",
                                                        }}
                                                    >
                                                        {savingOptionForQuestionId === question.id
                                                            ? "Saving..."
                                                            : "Add Option"}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </Panel>
                </div>
            </div>
        </main>
    );
}