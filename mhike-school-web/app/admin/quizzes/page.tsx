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
    const [editingQuestionId, setEditingQuestionId] = useState<number | null>(null);
    const [editingOptionId, setEditingOptionId] = useState<number | null>(null);
    const [deletingQuestionId, setDeletingQuestionId] = useState<number | null>(null);
    const [deletingOptionId, setDeletingOptionId] = useState<number | null>(null);

    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const [questionForm, setQuestionForm] = useState<QuizQuestionCreate>({
        question_text: "",
        order: 1,
    });

    const [optionDrafts, setOptionDrafts] = useState<Record<number, QuizOptionCreate>>({});
    const [questionEdits, setQuestionEdits] = useState<
        Record<number, { question_text: string; order: number }>
    >({});
    const [optionEdits, setOptionEdits] = useState<
        Record<number, { option_text: string; order: number; is_correct: boolean }>
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

            const res = await apiGet<QuizQuestionOut[]>(`/lessons/${lessonId}/quiz/admin`, token);
            setQuestions(res);
            setQuestionForm((prev) => ({
                ...prev,
                order: res.length + 1,
            }));

            const questionEditMap: Record<number, { question_text: string; order: number }> = {};
            const optionEditMap: Record<number, { option_text: string; order: number; is_correct: boolean }> = {};

            res.forEach((question) => {
                questionEditMap[question.id] = {
                    question_text: question.question_text,
                    order: question.order,
                };

                question.options.forEach((option) => {
                    optionEditMap[option.id] = {
                        option_text: option.option_text,
                        order: option.order,
                        is_correct: option.is_correct,
                    };
                });
            });

            setQuestionEdits(questionEditMap);
            setOptionEdits(optionEditMap);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to load quiz";
            if (msg.includes("404")) {
                setQuestions([]);
                setQuestionForm((prev) => ({ ...prev, order: 1 }));
                setQuestionEdits({});
                setOptionEdits({});
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

    async function updateQuestion(questionId: number) {
        const token = authGuard();
        if (!token || !selectedLessonId) return;

        const draft = questionEdits[questionId];
        if (!draft || !draft.question_text.trim()) {
            setError("Question text cannot be empty.");
            return;
        }

        try {
            setEditingQuestionId(questionId);
            setError("");
            setSuccess("");

            await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/quiz/questions/${questionId}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    question_text: draft.question_text.trim(),
                    order: draft.order,
                }),
            }).then(async (res) => {
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(`API error ${res.status}: ${text}`);
                }
            });

            setSuccess("Question updated.");
            await loadQuiz(selectedLessonId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to update question");
        } finally {
            setEditingQuestionId(null);
        }
    }

    async function deleteQuestion(questionId: number) {
        const token = authGuard();
        if (!token || !selectedLessonId) return;

        const confirmed = window.confirm("Delete this question and all its options?");
        if (!confirmed) return;

        try {
            setDeletingQuestionId(questionId);
            setError("");
            setSuccess("");

            await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/quiz/questions/${questionId}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            }).then(async (res) => {
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(`API error ${res.status}: ${text}`);
                }
            });

            setSuccess("Question deleted.");
            await loadQuiz(selectedLessonId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to delete question");
        } finally {
            setDeletingQuestionId(null);
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
        if (!token || !selectedLessonId) return;

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
            await loadQuiz(selectedLessonId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to create option");
        } finally {
            setSavingOptionForQuestionId(null);
        }
    }

    async function updateOption(optionId: number) {
        const token = authGuard();
        if (!token || !selectedLessonId) return;

        const draft = optionEdits[optionId];
        if (!draft || !draft.option_text.trim()) {
            setError("Option text cannot be empty.");
            return;
        }

        try {
            setEditingOptionId(optionId);
            setError("");
            setSuccess("");

            await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/quiz/options/${optionId}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    option_text: draft.option_text.trim(),
                    order: draft.order,
                    is_correct: draft.is_correct,
                }),
            }).then(async (res) => {
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(`API error ${res.status}: ${text}`);
                }
            });

            setSuccess("Option updated.");
            await loadQuiz(selectedLessonId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to update option");
        } finally {
            setEditingOptionId(null);
        }
    }

    async function deleteOption(optionId: number) {
        const token = authGuard();
        if (!token || !selectedLessonId) return;

        const confirmed = window.confirm("Delete this option?");
        if (!confirmed) return;

        try {
            setDeletingOptionId(optionId);
            setError("");
            setSuccess("");

            await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/quiz/options/${optionId}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            }).then(async (res) => {
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(`API error ${res.status}: ${text}`);
                }
            });

            setSuccess("Option deleted.");
            await loadQuiz(selectedLessonId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to delete option");
        } finally {
            setDeletingOptionId(null);
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
                        Manage Multiple Choice Quizzes
                    </h1>
                    <div style={{ opacity: 0.95, fontSize: 17 }}>
                        Create, edit, and delete quiz questions and answer options by lesson.
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

                    <Panel title="3. Edit and Delete Quiz">
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

                                    const questionEdit = questionEdits[question.id] ?? {
                                        question_text: question.question_text,
                                        order: question.order,
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
                                                    display: "grid",
                                                    gap: 10,
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        fontSize: 12,
                                                        fontWeight: 800,
                                                        color: "#6B7280",
                                                    }}
                                                >
                                                    Question {questionIndex + 1}
                                                </div>

                                                <textarea
                                                    value={questionEdit.question_text}
                                                    onChange={(e) =>
                                                        setQuestionEdits((prev) => ({
                                                            ...prev,
                                                            [question.id]: {
                                                                ...questionEdit,
                                                                question_text: e.target.value,
                                                            },
                                                        }))
                                                    }
                                                    rows={3}
                                                    style={{
                                                        width: "100%",
                                                        padding: "12px 14px",
                                                        borderRadius: 12,
                                                        border: "1px solid #E5E7EB",
                                                        background: "white",
                                                        resize: "vertical",
                                                    }}
                                                />

                                                <div
                                                    style={{
                                                        display: "flex",
                                                        gap: 10,
                                                        alignItems: "center",
                                                        flexWrap: "wrap",
                                                    }}
                                                >
                                                    <input
                                                        type="number"
                                                        min={1}
                                                        value={questionEdit.order}
                                                        onChange={(e) =>
                                                            setQuestionEdits((prev) => ({
                                                                ...prev,
                                                                [question.id]: {
                                                                    ...questionEdit,
                                                                    order: Number(e.target.value) || 1,
                                                                },
                                                            }))
                                                        }
                                                        style={{
                                                            width: 120,
                                                            padding: "12px 14px",
                                                            borderRadius: 12,
                                                            border: "1px solid #E5E7EB",
                                                            background: "white",
                                                        }}
                                                    />

                                                    <button
                                                        onClick={() => updateQuestion(question.id)}
                                                        disabled={editingQuestionId === question.id}
                                                        style={{
                                                            padding: "12px 16px",
                                                            borderRadius: 12,
                                                            border: "none",
                                                            background: "#2563EB",
                                                            color: "white",
                                                            fontWeight: 800,
                                                            cursor:
                                                                editingQuestionId === question.id
                                                                    ? "not-allowed"
                                                                    : "pointer",
                                                        }}
                                                    >
                                                        {editingQuestionId === question.id ? "Saving..." : "Save Question"}
                                                    </button>

                                                    <button
                                                        onClick={() => deleteQuestion(question.id)}
                                                        disabled={deletingQuestionId === question.id}
                                                        style={{
                                                            padding: "12px 16px",
                                                            borderRadius: 12,
                                                            border: "1px solid #FCA5A5",
                                                            background: "white",
                                                            color: "#B91C1C",
                                                            fontWeight: 800,
                                                            cursor:
                                                                deletingQuestionId === question.id
                                                                    ? "not-allowed"
                                                                    : "pointer",
                                                        }}
                                                    >
                                                        {deletingQuestionId === question.id ? "Deleting..." : "Delete Question"}
                                                    </button>
                                                </div>
                                            </div>

                                            <div style={{ marginTop: 16, display: "grid", gap: 10 }}>
                                                {question.options.length === 0 && (
                                                    <div style={{ color: "#6B7280" }}>No options added yet.</div>
                                                )}

                                                {question.options
                                                    .slice()
                                                    .sort((a, b) => a.order - b.order)
                                                    .map((option, optionIndex) => {
                                                        const optionEdit = optionEdits[option.id] ?? {
                                                            option_text: option.option_text,
                                                            order: option.order,
                                                            is_correct: option.is_correct,
                                                        };

                                                        return (
                                                            <div
                                                                key={option.id}
                                                                style={{
                                                                    padding: 14,
                                                                    borderRadius: 12,
                                                                    background: optionEdit.is_correct ? "#ECFDF5" : "white",
                                                                    border: "1px solid #E5E7EB",
                                                                    display: "grid",
                                                                    gap: 10,
                                                                }}
                                                            >
                                                                <div
                                                                    style={{
                                                                        fontSize: 12,
                                                                        color: "#6B7280",
                                                                        fontWeight: 700,
                                                                    }}
                                                                >
                                                                    Option {optionIndex + 1}
                                                                </div>

                                                                <input
                                                                    type="text"
                                                                    value={optionEdit.option_text}
                                                                    onChange={(e) =>
                                                                        setOptionEdits((prev) => ({
                                                                            ...prev,
                                                                            [option.id]: {
                                                                                ...optionEdit,
                                                                                option_text: e.target.value,
                                                                            },
                                                                        }))
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
                                                                        display: "flex",
                                                                        gap: 10,
                                                                        alignItems: "center",
                                                                        flexWrap: "wrap",
                                                                    }}
                                                                >
                                                                    <input
                                                                        type="number"
                                                                        min={1}
                                                                        value={optionEdit.order}
                                                                        onChange={(e) =>
                                                                            setOptionEdits((prev) => ({
                                                                                ...prev,
                                                                                [option.id]: {
                                                                                    ...optionEdit,
                                                                                    order: Number(e.target.value) || 1,
                                                                                },
                                                                            }))
                                                                        }
                                                                        style={{
                                                                            width: 120,
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
                                                                            checked={optionEdit.is_correct}
                                                                            onChange={(e) =>
                                                                                setOptionEdits((prev) => ({
                                                                                    ...prev,
                                                                                    [option.id]: {
                                                                                        ...optionEdit,
                                                                                        is_correct: e.target.checked,
                                                                                    },
                                                                                }))
                                                                            }
                                                                        />
                                                                        Correct answer
                                                                    </label>

                                                                    <button
                                                                        onClick={() => updateOption(option.id)}
                                                                        disabled={editingOptionId === option.id}
                                                                        style={{
                                                                            padding: "12px 16px",
                                                                            borderRadius: 12,
                                                                            border: "none",
                                                                            background: "#2563EB",
                                                                            color: "white",
                                                                            fontWeight: 800,
                                                                            cursor:
                                                                                editingOptionId === option.id
                                                                                    ? "not-allowed"
                                                                                    : "pointer",
                                                                        }}
                                                                    >
                                                                        {editingOptionId === option.id ? "Saving..." : "Save Option"}
                                                                    </button>

                                                                    <button
                                                                        onClick={() => deleteOption(option.id)}
                                                                        disabled={deletingOptionId === option.id}
                                                                        style={{
                                                                            padding: "12px 16px",
                                                                            borderRadius: 12,
                                                                            border: "1px solid #FCA5A5",
                                                                            background: "white",
                                                                            color: "#B91C1C",
                                                                            fontWeight: 800,
                                                                            cursor:
                                                                                deletingOptionId === option.id
                                                                                    ? "not-allowed"
                                                                                    : "pointer",
                                                                        }}
                                                                    >
                                                                        {deletingOptionId === option.id ? "Deleting..." : "Delete Option"}
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
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