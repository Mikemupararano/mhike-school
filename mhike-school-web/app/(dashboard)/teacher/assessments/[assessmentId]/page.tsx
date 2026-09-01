"use client";

import Link from "next/link";
import {
    useParams,
    useRouter,
} from "next/navigation";
import {
    FormEvent,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import RoleGate from "@/components/auth/RoleGate";
import AssessmentQuestionExtractionPanel from "@/components/assessments/AssessmentQuestionExtractionPanel";
import AssessmentMarkingPanel from "@/components/assessments/AssessmentMarkingPanel";
import AssessmentScannedScriptUploadPanel from "@/components/assessments/AssessmentScannedScriptUploadPanel";
import { apiGet, apiPatch } from "@/lib/api";
import {
    archiveAssessment,
    closeAssessment,
    createAssessmentQuestion,
    createAssessmentSection,
    deleteAssessment,
    deleteAssessmentQuestion,
    deleteAssessmentSection,
    getAssessment,
    publishAssessment,
    updateAssessmentQuestion,
    updateAssessmentSection,
    type Assessment,
    type AssessmentQuestion,
    type AssessmentSection,
    type AssessmentStatus,
} from "@/lib/services/assessments";
import { UserRole } from "@/types/user";


type StructureAction =
    | "create-section"
    | "update-section"
    | "delete-section"
    | "create-question"
    | "update-question"
    | "delete-question"
    | null;


type TeacherCourseSummary = {
    id: number;
    title: string;
};


type AssessmentDocumentRead = {
    id: number;
    assessment_id: number;
    uploaded_by_id: number;
    document_type: string;
    original_filename: string;
    mime_type: string;
    file_size_bytes: number;
    is_current: boolean;
    extraction_requested: boolean;
    extraction_completed: boolean;
    extraction_error: string | null;
    created_at: string;
    updated_at: string;
};


type AssessmentEditFormState = {
    title: string;
    description: string;
    assessmentType: string;
    academicYear: string;
    term: string;
    scheduledAt: string;
    closesAt: string;
    anonymousMarking: boolean;
};


type SectionFormState = {
    title: string;
    description: string;
    order: string;
    isOptional: boolean;
};


type QuestionFormState = {
    questionNumber: string;
    title: string;
    prompt: string;
    maximumMark: string;
    order: string;
    sectionId: string;
    parentQuestionId: string;
    isMarkable: boolean;
};


const EMPTY_SECTION_FORM: SectionFormState = {
    title: "",
    description: "",
    order: "1",
    isOptional: false,
};


const EMPTY_QUESTION_FORM: QuestionFormState = {
    questionNumber: "",
    title: "",
    prompt: "",
    maximumMark: "1",
    order: "1",
    sectionId: "",
    parentQuestionId: "",
    isMarkable: true,
};


const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL
    ?? "http://localhost:8000/api/v1";


const MAX_QUESTION_PAPER_SIZE_BYTES =
    25 * 1024 * 1024;


function getAuthToken(): string | null {
    if (typeof window === "undefined") {
        return null;
    }

    return sessionStorage.getItem(
        "mhike_token",
    );
}


async function getApiErrorMessage(
    response: Response,
    fallback: string,
): Promise<string> {
    try {
        const body =
            await response.json() as {
                detail?: unknown;
                message?: unknown;
                error?: unknown;
            };

        if (
            typeof body.detail
            === "string"
        ) {
            return body.detail;
        }

        if (
            typeof body.message
            === "string"
        ) {
            return body.message;
        }

        if (
            typeof body.error
            === "string"
        ) {
            return body.error;
        }

        if (
            body.error
            && typeof body.error
            === "object"
        ) {
            const nestedError =
                body.error as {
                    message?: unknown;
                    detail?: unknown;
                };

            if (
                typeof nestedError.message
                === "string"
            ) {
                return nestedError.message;
            }

            if (
                typeof nestedError.detail
                === "string"
            ) {
                return nestedError.detail;
            }
        }
    } catch {
        // Fall back to the supplied user-facing message.
    }

    return fallback;
}


function formatFileSize(
    sizeInBytes: number,
): string {
    if (
        !Number.isFinite(
            sizeInBytes,
        )
        || sizeInBytes < 0
    ) {
        return "Unknown size";
    }

    if (sizeInBytes < 1024) {
        return `${sizeInBytes} B`;
    }

    const sizeInKilobytes =
        sizeInBytes / 1024;

    if (sizeInKilobytes < 1024) {
        return `${sizeInKilobytes.toFixed(1)} KB`;
    }

    return `${(
        sizeInKilobytes / 1024
    ).toFixed(1)
        } MB`;
}


function formatDateTime(
    value: string | null,
): string {
    if (!value) {
        return "Not set";
    }

    return new Date(
        value,
    ).toLocaleString(
        "en-GB",
        {
            day: "2-digit",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        },
    );
}


function toDateTimeLocalValue(
    value: string | null,
): string {
    if (!value) {
        return "";
    }

    const date =
        new Date(
            value,
        );

    if (
        Number.isNaN(
            date.getTime(),
        )
    ) {
        return "";
    }

    const pad =
        (number: number) =>
            String(
                number,
            ).padStart(
                2,
                "0",
            );

    return [
        date.getFullYear(),
        "-",
        pad(
            date.getMonth() + 1,
        ),
        "-",
        pad(
            date.getDate(),
        ),
        "T",
        pad(
            date.getHours(),
        ),
        ":",
        pad(
            date.getMinutes(),
        ),
    ].join("");
}


function statusLabel(
    status: AssessmentStatus,
): string {
    if (status === "draft") {
        return "Draft";
    }

    if (status === "published") {
        return "Published";
    }

    if (status === "closed") {
        return "Closed";
    }

    return "Archived";
}


function parsePositiveInteger(
    value: string,
): number | null {
    const parsed = Number(
        value,
    );

    if (
        !Number.isInteger(
            parsed,
        )
        || parsed <= 0
    ) {
        return null;
    }

    return parsed;
}


function parseNonNegativeNumber(
    value: string,
): number | null {
    const parsed = Number(
        value,
    );

    if (
        Number.isNaN(
            parsed,
        )
        || parsed < 0
    ) {
        return null;
    }

    return parsed;
}


function sectionDisplayName(
    section: AssessmentSection,
): string {
    return `${section.order}. ${section.title}`;
}


function questionDisplayName(
    question: AssessmentQuestion,
): string {
    if (question.title) {
        return `${question.question_number} — ${question.title}`;
    }

    return question.question_number;
}


export default function TeacherAssessmentDetailPage() {
    return (
        <RoleGate
            allowedRoles={[
                UserRole.TEACHER,
                UserRole.SCHOOL_ADMIN,
                UserRole.PLATFORM_ADMIN,
            ]}
        >
            <TeacherAssessmentDetailContent />
        </RoleGate>
    );
}


function TeacherAssessmentDetailContent() {
    const params =
        useParams<{
            assessmentId: string;
        }>();

    const router =
        useRouter();

    const assessmentId =
        Number(
            params.assessmentId,
        );

    const [assessment, setAssessment] =
        useState<Assessment | null>(
            null,
        );

    const [courseTitle, setCourseTitle] =
        useState<string | null>(
            null,
        );

    const [isEditingAssessment, setIsEditingAssessment] =
        useState(
            false,
        );

    const [editForm, setEditForm] =
        useState<AssessmentEditFormState | null>(
            null,
        );

    const [isLoading, setIsLoading] =
        useState(
            true,
        );

    const [busyAction, setBusyAction] =
        useState<
            | "publish"
            | "close"
            | "archive"
            | "delete"
            | "edit"
            | null
        >(
            null,
        );

    const [structureAction, setStructureAction] =
        useState<StructureAction>(
            null,
        );

    const [error, setError] =
        useState<string | null>(
            null,
        );

    const [structureMessage, setStructureMessage] =
        useState<string | null>(
            null,
        );

    const [sectionForm, setSectionForm] =
        useState<SectionFormState>(
            EMPTY_SECTION_FORM,
        );

    const [editingSectionId, setEditingSectionId] =
        useState<number | null>(
            null,
        );

    const [questionForm, setQuestionForm] =
        useState<QuestionFormState>(
            EMPTY_QUESTION_FORM,
        );

    const [editingQuestionId, setEditingQuestionId] =
        useState<number | null>(
            null,
        );

    const [currentQuestionPaper, setCurrentQuestionPaper] =
        useState<AssessmentDocumentRead | null>(
            null,
        );

    const [isQuestionPaperLoading, setIsQuestionPaperLoading] =
        useState(
            true,
        );

    const [questionPaperAction, setQuestionPaperAction] =
        useState<
            | "upload"
            | "view"
            | null
        >(
            null,
        );

    const [selectedQuestionPaper, setSelectedQuestionPaper] =
        useState<File | null>(
            null,
        );

    const [questionPaperMessage, setQuestionPaperMessage] =
        useState<string | null>(
            null,
        );


    const isDraft =
        assessment?.status === "draft";


    const sortedSections =
        useMemo(
            () => {
                if (!assessment) {
                    return [];
                }

                return [
                    ...assessment.sections,
                ].sort(
                    (
                        first,
                        second,
                    ) =>
                        first.order
                        - second.order,
                );
            },
            [
                assessment,
            ],
        );


    const sortedQuestions =
        useMemo(
            () => {
                if (!assessment) {
                    return [];
                }

                return [
                    ...assessment.questions,
                ].sort(
                    (
                        first,
                        second,
                    ) => {
                        if (
                            first.order
                            !== second.order
                        ) {
                            return (
                                first.order
                                - second.order
                            );
                        }

                        return first.question_number.localeCompare(
                            second.question_number,
                            undefined,
                            {
                                numeric: true,
                            },
                        );
                    },
                );
            },
            [
                assessment,
            ],
        );


    const totalMarks =
        useMemo(
            () => {
                if (!assessment) {
                    return 0;
                }

                return assessment.questions.reduce(
                    (
                        total,
                        question,
                    ) => {
                        if (!question.is_markable) {
                            return total;
                        }

                        const mark =
                            Number(
                                question.maximum_mark,
                            );

                        if (
                            Number.isNaN(
                                mark,
                            )
                        ) {
                            return total;
                        }

                        return total + mark;
                    },
                    0,
                );
            },
            [
                assessment,
            ],
        );


    const loadQuestionPaper =
        useCallback(
            async () => {
                if (
                    !assessmentId
                    || Number.isNaN(
                        assessmentId,
                    )
                ) {
                    setCurrentQuestionPaper(
                        null,
                    );
                    setIsQuestionPaperLoading(
                        false,
                    );
                    return;
                }

                try {
                    setIsQuestionPaperLoading(
                        true,
                    );

                    const document =
                        await apiGet<AssessmentDocumentRead | null>(
                            `/assessments/${assessmentId}/documents/question-paper`,
                        );

                    setCurrentQuestionPaper(
                        document,
                    );
                } catch (err: unknown) {
                    setCurrentQuestionPaper(
                        null,
                    );

                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load the question paper.",
                    );
                } finally {
                    setIsQuestionPaperLoading(
                        false,
                    );
                }
            },
            [
                assessmentId,
            ],
        );


    const loadAssessment =
        useCallback(
            async () => {
                if (
                    !assessmentId
                    || Number.isNaN(
                        assessmentId,
                    )
                ) {
                    setError(
                        "Invalid assessment ID.",
                    );
                    setIsLoading(
                        false,
                    );
                    return;
                }

                try {
                    setError(
                        null,
                    );
                    setIsLoading(
                        true,
                    );

                    const data =
                        await getAssessment(
                            assessmentId,
                        );

                    setAssessment(
                        data,
                    );

                    setIsLoading(
                        false,
                    );

                    setCourseTitle(
                        null,
                    );

                    void (
                        async () => {
                            try {
                                const courses =
                                    await apiGet<TeacherCourseSummary[]>(
                                        "/courses/me",
                                    );

                                const matchingCourse =
                                    courses.find(
                                        course =>
                                            course.id
                                            === data.course_id,
                                    );

                                setCourseTitle(
                                    matchingCourse?.title
                                    ?? null,
                                );
                            } catch {
                                /*
                                 * Course-title resolution is presentation-only.
                                 * The assessment is already visible, so keep the
                                 * page usable and fall back to its course ID.
                                 */
                                setCourseTitle(
                                    null,
                                );
                            }
                        }
                    )();
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load assessment.",
                    );
                } finally {
                    setIsLoading(
                        false,
                    );
                }
            },
            [
                assessmentId,
            ],
        );


    useEffect(
        () => {
            void loadAssessment();
        },
        [
            loadAssessment,
        ],
    );


    useEffect(
        () => {
            void loadQuestionPaper();
        },
        [
            loadQuestionPaper,
        ],
    );


    useEffect(
        () => {
            if (!assessment) {
                return;
            }

            const nextSectionOrder =
                assessment.sections.length
                    ? Math.max(
                        ...assessment.sections.map(
                            section =>
                                section.order,
                        ),
                    ) + 1
                    : 1;

            const nextQuestionOrder =
                assessment.questions.length
                    ? Math.max(
                        ...assessment.questions.map(
                            question =>
                                question.order,
                        ),
                    ) + 1
                    : 1;

            if (
                editingSectionId === null
            ) {
                setSectionForm(
                    current => ({
                        ...current,
                        order: String(
                            nextSectionOrder,
                        ),
                    }),
                );
            }

            if (
                editingQuestionId === null
            ) {
                setQuestionForm(
                    current => ({
                        ...current,
                        order: String(
                            nextQuestionOrder,
                        ),
                    }),
                );
            }
        },
        [
            assessment,
            editingQuestionId,
            editingSectionId,
        ],
    );


    const beginEditAssessment =
        useCallback(
            () => {
                if (
                    !assessment
                    || assessment.status !== "draft"
                ) {
                    return;
                }

                setEditForm({
                    title:
                        assessment.title,
                    description:
                        assessment.description
                        ?? "",
                    assessmentType:
                        assessment.assessment_type
                        ?? "",
                    academicYear:
                        assessment.academic_year
                        ?? "",
                    term:
                        assessment.term
                        ?? "",
                    scheduledAt:
                        toDateTimeLocalValue(
                            assessment.scheduled_at,
                        ),
                    closesAt:
                        toDateTimeLocalValue(
                            assessment.closes_at,
                        ),
                    anonymousMarking:
                        assessment.anonymous_marking,
                });

                setError(
                    null,
                );

                setStructureMessage(
                    null,
                );

                setIsEditingAssessment(
                    true,
                );
            },
            [
                assessment,
            ],
        );


    const cancelEditAssessment =
        useCallback(
            () => {
                setIsEditingAssessment(
                    false,
                );

                setEditForm(
                    null,
                );
            },
            [],
        );


    const handleAssessmentEditSubmit =
        useCallback(
            async (
                event:
                    FormEvent<HTMLFormElement>,
            ) => {
                event.preventDefault();

                if (
                    !assessment
                    || assessment.status !== "draft"
                    || !editForm
                ) {
                    return;
                }

                const title =
                    editForm.title.trim();

                const academicYear =
                    editForm.academicYear.trim();

                if (!title) {
                    setError(
                        "Assessment title is required.",
                    );
                    return;
                }

                if (!academicYear) {
                    setError(
                        "Academic year is required.",
                    );
                    return;
                }

                if (
                    editForm.scheduledAt
                    && editForm.closesAt
                    && new Date(
                        editForm.closesAt,
                    ).getTime()
                    <= new Date(
                        editForm.scheduledAt,
                    ).getTime()
                ) {
                    setError(
                        "Closing time must be later than the scheduled start.",
                    );
                    return;
                }

                try {
                    setBusyAction(
                        "edit",
                    );

                    setError(
                        null,
                    );

                    setStructureMessage(
                        null,
                    );

                    const updated =
                        await apiPatch<Assessment>(
                            `/assessments/${assessment.id}`,
                            {
                                title,
                                description:
                                    editForm.description.trim()
                                    || null,
                                assessment_type:
                                    editForm.assessmentType.trim()
                                    || null,
                                academic_year:
                                    academicYear,
                                term:
                                    editForm.term.trim()
                                    || null,
                                anonymous_marking:
                                    editForm.anonymousMarking,
                                scheduled_at:
                                    editForm.scheduledAt
                                        ? new Date(
                                            editForm.scheduledAt,
                                        ).toISOString()
                                        : null,
                                closes_at:
                                    editForm.closesAt
                                        ? new Date(
                                            editForm.closesAt,
                                        ).toISOString()
                                        : null,
                            },
                        );

                    setAssessment(
                        updated,
                    );

                    setIsEditingAssessment(
                        false,
                    );

                    setEditForm(
                        null,
                    );

                    setStructureMessage(
                        "Assessment details updated.",
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to update assessment details.",
                    );
                } finally {
                    setBusyAction(
                        null,
                    );
                }
            },
            [
                assessment,
                editForm,
            ],
        );


    const runLifecycleAction =
        useCallback(
            async (
                action:
                    | "publish"
                    | "close"
                    | "archive",
            ) => {
                if (!assessment) {
                    return;
                }

                try {
                    setBusyAction(
                        action,
                    );
                    setError(
                        null,
                    );
                    setStructureMessage(
                        null,
                    );

                    let updated:
                        Assessment;

                    if (
                        action
                        === "publish"
                    ) {
                        updated =
                            await publishAssessment(
                                assessment.id,
                            );
                    } else if (
                        action
                        === "close"
                    ) {
                        updated =
                            await closeAssessment(
                                assessment.id,
                            );
                    } else {
                        updated =
                            await archiveAssessment(
                                assessment.id,
                            );
                    }

                    setAssessment(
                        updated,
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to update assessment.",
                    );
                } finally {
                    setBusyAction(
                        null,
                    );
                }
            },
            [
                assessment,
            ],
        );


    const handleDelete =
        useCallback(
            async () => {
                if (
                    !assessment
                    || assessment.status
                    !== "draft"
                ) {
                    return;
                }

                const confirmed =
                    window.confirm(
                        "Delete this draft assessment? This action cannot be undone.",
                    );

                if (!confirmed) {
                    return;
                }

                try {
                    setBusyAction(
                        "delete",
                    );
                    setError(
                        null,
                    );

                    await deleteAssessment(
                        assessment.id,
                    );

                    router.push(
                        "/teacher/assessments",
                    );

                    router.refresh();
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to delete assessment.",
                    );
                } finally {
                    setBusyAction(
                        null,
                    );
                }
            },
            [
                assessment,
                router,
            ],
        );


    const handleQuestionPaperSelection =
        useCallback(
            (
                file:
                    File | null,
            ) => {
                setQuestionPaperMessage(
                    null,
                );

                if (!file) {
                    setSelectedQuestionPaper(
                        null,
                    );
                    return;
                }

                const filename =
                    file.name
                        .trim()
                        .toLowerCase();

                const mimeType =
                    file.type
                        .trim()
                        .toLowerCase();

                if (
                    !filename.endsWith(
                        ".pdf",
                    )
                    || (
                        mimeType
                        && mimeType
                        !== "application/pdf"
                    )
                ) {
                    setSelectedQuestionPaper(
                        null,
                    );

                    setError(
                        "Please select a PDF question paper.",
                    );
                    return;
                }

                if (file.size === 0) {
                    setSelectedQuestionPaper(
                        null,
                    );

                    setError(
                        "The selected question paper is empty.",
                    );
                    return;
                }

                if (
                    file.size
                    > MAX_QUESTION_PAPER_SIZE_BYTES
                ) {
                    setSelectedQuestionPaper(
                        null,
                    );

                    setError(
                        "The selected question paper exceeds the 25 MB upload limit.",
                    );
                    return;
                }

                setError(
                    null,
                );

                setSelectedQuestionPaper(
                    file,
                );
            },
            [],
        );


    const handleQuestionPaperUpload =
        useCallback(
            async () => {
                if (
                    !assessment
                    || !isDraft
                    || !selectedQuestionPaper
                ) {
                    return;
                }

                const token =
                    getAuthToken();

                if (!token) {
                    setError(
                        "Your session has expired. Please sign in again.",
                    );
                    return;
                }

                const formData =
                    new FormData();

                const uploadFile =
                    selectedQuestionPaper.type
                        .trim()
                        .toLowerCase()
                        === "application/pdf"
                        ? selectedQuestionPaper
                        : new File(
                            [
                                selectedQuestionPaper,
                            ],
                            selectedQuestionPaper.name,
                            {
                                type: "application/pdf",
                            },
                        );

                formData.append(
                    "file",
                    uploadFile,
                );

                try {
                    setQuestionPaperAction(
                        "upload",
                    );

                    setError(
                        null,
                    );

                    setQuestionPaperMessage(
                        null,
                    );

                    const response =
                        await fetch(
                            `${API_BASE_URL}/assessments/${assessment.id}/documents/question-paper`,
                            {
                                method: "POST",
                                headers: {
                                    Authorization:
                                        `Bearer ${token}`,
                                },
                                body: formData,
                            },
                        );

                    if (!response.ok) {
                        throw new Error(
                            await getApiErrorMessage(
                                response,
                                "Failed to upload the question paper.",
                            ),
                        );
                    }

                    const uploaded =
                        await response.json() as AssessmentDocumentRead;

                    setCurrentQuestionPaper(
                        uploaded,
                    );

                    setSelectedQuestionPaper(
                        null,
                    );

                    setQuestionPaperMessage(
                        currentQuestionPaper
                            ? "Question paper replaced. The previous version has been retained in the assessment history."
                            : "Question paper uploaded successfully.",
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to upload the question paper.",
                    );
                } finally {
                    setQuestionPaperAction(
                        null,
                    );
                }
            },
            [
                assessment,
                currentQuestionPaper,
                isDraft,
                selectedQuestionPaper,
            ],
        );


    const handleViewQuestionPaper =
        useCallback(
            async () => {
                if (
                    !assessment
                    || !currentQuestionPaper
                ) {
                    return;
                }

                const token =
                    getAuthToken();

                if (!token) {
                    setError(
                        "Your session has expired. Please sign in again.",
                    );
                    return;
                }

                try {
                    setQuestionPaperAction(
                        "view",
                    );

                    setError(
                        null,
                    );

                    const response =
                        await fetch(
                            `${API_BASE_URL}/assessments/${assessment.id}/documents/${currentQuestionPaper.id}/download`,
                            {
                                headers: {
                                    Authorization:
                                        `Bearer ${token}`,
                                },
                            },
                        );

                    if (!response.ok) {
                        throw new Error(
                            await getApiErrorMessage(
                                response,
                                "Failed to open the question paper.",
                            ),
                        );
                    }

                    const blob =
                        await response.blob();

                    const objectUrl =
                        URL.createObjectURL(
                            blob,
                        );

                    const openedWindow =
                        window.open(
                            objectUrl,
                            "_blank",
                        );

                    if (!openedWindow) {
                        URL.revokeObjectURL(
                            objectUrl,
                        );

                        throw new Error(
                            "The browser blocked the question-paper window. Allow pop-ups for this site and try again.",
                        );
                    }

                    openedWindow.opener =
                        null;

                    window.setTimeout(
                        () => {
                            URL.revokeObjectURL(
                                objectUrl,
                            );
                        },
                        60_000,
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to open the question paper.",
                    );
                } finally {
                    setQuestionPaperAction(
                        null,
                    );
                }
            },
            [
                assessment,
                currentQuestionPaper,
            ],
        );


    const resetSectionForm =
        useCallback(
            () => {
                const nextOrder =
                    assessment?.sections.length
                        ? Math.max(
                            ...assessment.sections.map(
                                section =>
                                    section.order,
                            ),
                        ) + 1
                        : 1;

                setEditingSectionId(
                    null,
                );

                setSectionForm({
                    ...EMPTY_SECTION_FORM,
                    order: String(
                        nextOrder,
                    ),
                });
            },
            [
                assessment,
            ],
        );


    const resetQuestionForm =
        useCallback(
            () => {
                const nextOrder =
                    assessment?.questions.length
                        ? Math.max(
                            ...assessment.questions.map(
                                question =>
                                    question.order,
                            ),
                        ) + 1
                        : 1;

                setEditingQuestionId(
                    null,
                );

                setQuestionForm({
                    ...EMPTY_QUESTION_FORM,
                    order: String(
                        nextOrder,
                    ),
                });
            },
            [
                assessment,
            ],
        );


    const beginEditSection =
        useCallback(
            (
                section:
                    AssessmentSection,
            ) => {
                setEditingSectionId(
                    section.id,
                );

                setSectionForm({
                    title:
                        section.title,
                    description:
                        section.description
                        ?? "",
                    order:
                        String(
                            section.order,
                        ),
                    isOptional:
                        section.is_optional,
                });

                setStructureMessage(
                    null,
                );
                setError(
                    null,
                );
            },
            [],
        );


    const beginEditQuestion =
        useCallback(
            (
                question:
                    AssessmentQuestion,
            ) => {
                setEditingQuestionId(
                    question.id,
                );

                setQuestionForm({
                    questionNumber:
                        question.question_number,
                    title:
                        question.title
                        ?? "",
                    prompt:
                        question.prompt
                        ?? "",
                    maximumMark:
                        String(
                            question.maximum_mark,
                        ),
                    order:
                        String(
                            question.order,
                        ),
                    sectionId:
                        question.section_id
                            ? String(
                                question.section_id,
                            )
                            : "",
                    parentQuestionId:
                        question.parent_question_id
                            ? String(
                                question.parent_question_id,
                            )
                            : "",
                    isMarkable:
                        question.is_markable,
                });

                setStructureMessage(
                    null,
                );
                setError(
                    null,
                );
            },
            [],
        );


    const handleSectionSubmit =
        useCallback(
            async (
                event:
                    FormEvent<HTMLFormElement>,
            ) => {
                event.preventDefault();

                if (
                    !assessment
                    || !isDraft
                ) {
                    return;
                }

                const title =
                    sectionForm.title.trim();

                const order =
                    parsePositiveInteger(
                        sectionForm.order,
                    );

                if (!title) {
                    setError(
                        "Section title is required.",
                    );
                    return;
                }

                if (order === null) {
                    setError(
                        "Section order must be a positive whole number.",
                    );
                    return;
                }

                try {
                    setError(
                        null,
                    );
                    setStructureMessage(
                        null,
                    );

                    if (
                        editingSectionId
                        !== null
                    ) {
                        setStructureAction(
                            "update-section",
                        );

                        await updateAssessmentSection(
                            assessment.id,
                            editingSectionId,
                            {
                                title,
                                description:
                                    sectionForm.description.trim()
                                    || null,
                                order,
                                is_optional:
                                    sectionForm.isOptional,
                            },
                        );

                        setStructureMessage(
                            "Section updated.",
                        );
                    } else {
                        setStructureAction(
                            "create-section",
                        );

                        await createAssessmentSection(
                            assessment.id,
                            {
                                title,
                                description:
                                    sectionForm.description.trim()
                                    || null,
                                order,
                                is_optional:
                                    sectionForm.isOptional,
                            },
                        );

                        setStructureMessage(
                            "Section added.",
                        );
                    }

                    await loadAssessment();
                    resetSectionForm();
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to save section.",
                    );
                } finally {
                    setStructureAction(
                        null,
                    );
                }
            },
            [
                assessment,
                editingSectionId,
                isDraft,
                loadAssessment,
                resetSectionForm,
                sectionForm,
            ],
        );


    const handleDeleteSection =
        useCallback(
            async (
                section:
                    AssessmentSection,
            ) => {
                if (
                    !assessment
                    || !isDraft
                ) {
                    return;
                }

                const confirmed =
                    window.confirm(
                        `Delete "${section.title}"? Questions in the section will remain in the assessment but become unsectioned.`,
                    );

                if (!confirmed) {
                    return;
                }

                try {
                    setStructureAction(
                        "delete-section",
                    );
                    setError(
                        null,
                    );
                    setStructureMessage(
                        null,
                    );

                    const updated =
                        await deleteAssessmentSection(
                            assessment.id,
                            section.id,
                        );

                    setAssessment(
                        updated,
                    );

                    if (
                        editingSectionId
                        === section.id
                    ) {
                        resetSectionForm();
                    }

                    setStructureMessage(
                        "Section deleted. Its questions remain in the assessment.",
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to delete section.",
                    );
                } finally {
                    setStructureAction(
                        null,
                    );
                }
            },
            [
                assessment,
                editingSectionId,
                isDraft,
                resetSectionForm,
            ],
        );


    const handleQuestionSubmit =
        useCallback(
            async (
                event:
                    FormEvent<HTMLFormElement>,
            ) => {
                event.preventDefault();

                if (
                    !assessment
                    || !isDraft
                ) {
                    return;
                }

                const questionNumber =
                    questionForm
                        .questionNumber
                        .trim();

                const order =
                    parsePositiveInteger(
                        questionForm.order,
                    );

                const maximumMark =
                    parseNonNegativeNumber(
                        questionForm.maximumMark,
                    );

                const sectionId =
                    questionForm.sectionId
                        ? Number(
                            questionForm.sectionId,
                        )
                        : null;

                const parentQuestionId =
                    questionForm.parentQuestionId
                        ? Number(
                            questionForm.parentQuestionId,
                        )
                        : null;

                if (!questionNumber) {
                    setError(
                        "Question number is required.",
                    );
                    return;
                }

                if (order === null) {
                    setError(
                        "Question order must be a positive whole number.",
                    );
                    return;
                }

                if (maximumMark === null) {
                    setError(
                        "Maximum mark must be zero or greater.",
                    );
                    return;
                }

                if (
                    editingQuestionId
                    !== null
                    && parentQuestionId
                    === editingQuestionId
                ) {
                    setError(
                        "A question cannot be its own parent.",
                    );
                    return;
                }

                try {
                    setError(
                        null,
                    );
                    setStructureMessage(
                        null,
                    );

                    if (
                        editingQuestionId
                        !== null
                    ) {
                        setStructureAction(
                            "update-question",
                        );

                        await updateAssessmentQuestion(
                            assessment.id,
                            editingQuestionId,
                            {
                                question_number:
                                    questionNumber,
                                title:
                                    questionForm.title.trim()
                                    || null,
                                prompt:
                                    questionForm.prompt.trim()
                                    || null,
                                maximum_mark:
                                    maximumMark,
                                order,
                                section_id:
                                    sectionId,
                                parent_question_id:
                                    parentQuestionId,
                                is_markable:
                                    questionForm.isMarkable,
                            },
                        );

                        setStructureMessage(
                            "Question updated.",
                        );
                    } else {
                        setStructureAction(
                            "create-question",
                        );

                        await createAssessmentQuestion(
                            assessment.id,
                            {
                                question_number:
                                    questionNumber,
                                title:
                                    questionForm.title.trim()
                                    || null,
                                prompt:
                                    questionForm.prompt.trim()
                                    || null,
                                maximum_mark:
                                    maximumMark,
                                order,
                                section_id:
                                    sectionId,
                                parent_question_id:
                                    parentQuestionId,
                                is_markable:
                                    questionForm.isMarkable,
                            },
                        );

                        setStructureMessage(
                            "Question added.",
                        );
                    }

                    await loadAssessment();
                    resetQuestionForm();
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to save question.",
                    );
                } finally {
                    setStructureAction(
                        null,
                    );
                }
            },
            [
                assessment,
                editingQuestionId,
                isDraft,
                loadAssessment,
                questionForm,
                resetQuestionForm,
            ],
        );


    const handleDeleteQuestion =
        useCallback(
            async (
                question:
                    AssessmentQuestion,
            ) => {
                if (
                    !assessment
                    || !isDraft
                ) {
                    return;
                }

                const confirmed =
                    window.confirm(
                        `Delete question ${question.question_number}? Any child questions will also be deleted.`,
                    );

                if (!confirmed) {
                    return;
                }

                try {
                    setStructureAction(
                        "delete-question",
                    );
                    setError(
                        null,
                    );
                    setStructureMessage(
                        null,
                    );

                    const updated =
                        await deleteAssessmentQuestion(
                            assessment.id,
                            question.id,
                        );

                    setAssessment(
                        updated,
                    );

                    if (
                        editingQuestionId
                        === question.id
                    ) {
                        resetQuestionForm();
                    }

                    setStructureMessage(
                        "Question deleted.",
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to delete question.",
                    );
                } finally {
                    setStructureAction(
                        null,
                    );
                }
            },
            [
                assessment,
                editingQuestionId,
                isDraft,
                resetQuestionForm,
            ],
        );


    return (
        <main className="space-y-6 p-6 sm:p-8">
            <Link
                href="/teacher/assessments"
                className="text-sm font-semibold text-blue-600 hover:underline"
            >
                ← Back to assessments
            </Link>

            {isLoading && (
                <div
                    aria-label="Loading assessment"
                    className="space-y-6"
                >
                    <section className="animate-pulse rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                            <div className="min-w-0 flex-1">
                                <div className="h-9 w-80 max-w-full rounded-lg bg-slate-200" />
                                <div className="mt-4 h-4 w-96 max-w-full rounded bg-slate-100" />
                            </div>

                            <div className="h-10 w-36 rounded-lg bg-slate-200" />
                        </div>

                        <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                            {Array.from({ length: 4 }).map((_, index) => (
                                <div
                                    key={index}
                                    className="h-20 rounded-xl bg-slate-100"
                                />
                            ))}
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                            {Array.from({ length: 2 }).map((_, index) => (
                                <div
                                    key={index}
                                    className="h-16 rounded-xl border border-slate-100 bg-slate-50"
                                />
                            ))}
                        </div>
                    </section>

                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        {Array.from({ length: 4 }).map((_, index) => (
                            <div
                                key={index}
                                className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                            >
                                <div className="h-3 w-24 rounded bg-slate-200" />
                                <div className="mt-5 h-8 w-16 rounded bg-slate-200" />
                                <div className="mt-3 h-3 w-40 max-w-full rounded bg-slate-100" />
                            </div>
                        ))}
                    </div>

                    <section className="h-80 animate-pulse rounded-2xl bg-slate-950" />
                </div>
            )}
            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                    {error}
                </div>
            )}

            {structureMessage && (
                <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-700">
                    {structureMessage}
                </div>
            )}

            {!isLoading && assessment && (
                <>
                    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                            <div>
                                <div className="flex flex-wrap items-center gap-3">
                                    <h1 className="text-3xl font-extrabold text-slate-900">
                                        {assessment.title}
                                    </h1>

                                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
                                        {statusLabel(
                                            assessment.status,
                                        )}
                                    </span>

                                    {assessment.anonymous_marking && (
                                        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
                                            Anonymous marking
                                        </span>
                                    )}
                                </div>

                                <p className="mt-3 max-w-3xl text-slate-600">
                                    {assessment.description
                                        || "No description."}
                                </p>
                            </div>

                            <div className="flex flex-wrap gap-3">
                                {assessment.status === "draft" && (
                                    <>
                                        <button
                                            type="button"
                                            onClick={
                                                beginEditAssessment
                                            }
                                            disabled={
                                                busyAction !== null
                                                || structureAction !== null
                                            }
                                            className="rounded-lg border border-blue-300 bg-white px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-50 disabled:opacity-50"
                                        >
                                            Edit assessment
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() =>
                                                void runLifecycleAction(
                                                    "publish",
                                                )
                                            }
                                            disabled={
                                                busyAction !== null
                                                || structureAction !== null
                                            }
                                            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {busyAction === "publish"
                                                ? "Publishing..."
                                                : "Publish assessment"}
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() =>
                                                void handleDelete()
                                            }
                                            disabled={
                                                busyAction !== null
                                                || structureAction !== null
                                            }
                                            className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:opacity-50"
                                        >
                                            {busyAction === "delete"
                                                ? "Deleting..."
                                                : "Delete draft"}
                                        </button>
                                    </>
                                )}

                                {assessment.status === "published" && (
                                    <button
                                        type="button"
                                        onClick={() =>
                                            void runLifecycleAction(
                                                "close",
                                            )
                                        }
                                        disabled={
                                            busyAction !== null
                                        }
                                        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {busyAction === "close"
                                            ? "Closing..."
                                            : "Close assessment"}
                                    </button>
                                )}

                                {assessment.status === "closed" && (
                                    <button
                                        type="button"
                                        onClick={() =>
                                            void runLifecycleAction(
                                                "archive",
                                            )
                                        }
                                        disabled={
                                            busyAction !== null
                                        }
                                        className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-900 disabled:opacity-50"
                                    >
                                        {busyAction === "archive"
                                            ? "Archiving..."
                                            : "Archive assessment"}
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                            <div className="rounded-xl bg-slate-50 p-4">
                                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                    Course
                                </p>

                                <p className="mt-1 font-semibold text-slate-800">
                                    {courseTitle
                                        ?? `Course ${assessment.course_id}`}
                                </p>
                            </div>

                            <div className="rounded-xl bg-slate-50 p-4">
                                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                    Type
                                </p>

                                <p className="mt-1 font-semibold text-slate-800">
                                    {assessment.assessment_type
                                        || "Not set"}
                                </p>
                            </div>

                            <div className="rounded-xl bg-slate-50 p-4">
                                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                    Academic year
                                </p>

                                <p className="mt-1 font-semibold text-slate-800">
                                    {assessment.academic_year
                                        || "Not set"}
                                </p>
                            </div>

                            <div className="rounded-xl bg-slate-50 p-4">
                                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                    Term
                                </p>

                                <p className="mt-1 font-semibold text-slate-800">
                                    {assessment.term
                                        || "Not set"}
                                </p>
                            </div>
                        </div>

                        <div className="mt-4 grid gap-4 sm:grid-cols-2">
                            <div className="rounded-xl border border-slate-200 p-4">
                                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                    Scheduled start
                                </p>

                                <p className="mt-1 text-sm font-semibold text-slate-700">
                                    {formatDateTime(
                                        assessment.scheduled_at,
                                    )}
                                </p>
                            </div>

                            <div className="rounded-xl border border-slate-200 p-4">
                                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                                    Closing time
                                </p>

                                <p className="mt-1 text-sm font-semibold text-slate-700">
                                    {formatDateTime(
                                        assessment.closes_at,
                                    )}
                                </p>
                            </div>
                        </div>
                    </section>

                    {isDraft
                        && isEditingAssessment
                        && editForm && (
                            <section className="rounded-2xl border border-blue-200 bg-blue-50 p-6 shadow-sm">
                                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                                    <div>
                                        <h2 className="text-2xl font-extrabold text-slate-900">
                                            Edit assessment
                                        </h2>

                                        <p className="mt-1 text-sm text-slate-600">
                                            Update the draft assessment details before publication.
                                        </p>
                                    </div>

                                    <button
                                        type="button"
                                        onClick={
                                            cancelEditAssessment
                                        }
                                        disabled={
                                            busyAction === "edit"
                                        }
                                        className="text-sm font-semibold text-blue-700 hover:underline disabled:opacity-50"
                                    >
                                        Cancel
                                    </button>
                                </div>

                                <form
                                    onSubmit={
                                        handleAssessmentEditSubmit
                                    }
                                    className="mt-6 grid gap-4 md:grid-cols-2"
                                >
                                    <label className="block md:col-span-2">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Title
                                        </span>

                                        <input
                                            type="text"
                                            value={
                                                editForm.title
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    title:
                                                                        event.target.value,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            required
                                            maxLength={
                                                255
                                            }
                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                        />
                                    </label>

                                    <label className="block md:col-span-2">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Description
                                        </span>

                                        <textarea
                                            value={
                                                editForm.description
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    description:
                                                                        event.target.value,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            rows={
                                                3
                                            }
                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                        />
                                    </label>

                                    <label className="block">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Assessment type
                                        </span>

                                        <input
                                            type="text"
                                            value={
                                                editForm.assessmentType
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    assessmentType:
                                                                        event.target.value,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            maxLength={
                                                100
                                            }
                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                        />
                                    </label>

                                    <label className="block">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Academic year
                                        </span>

                                        <input
                                            type="text"
                                            value={
                                                editForm.academicYear
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    academicYear:
                                                                        event.target.value,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            required
                                            maxLength={
                                                50
                                            }
                                            placeholder="2026/27"
                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                        />
                                    </label>

                                    <label className="block">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Term
                                        </span>

                                        <input
                                            type="text"
                                            value={
                                                editForm.term
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    term:
                                                                        event.target.value,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            maxLength={
                                                100
                                            }
                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                        />
                                    </label>

                                    <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
                                        <input
                                            type="checkbox"
                                            checked={
                                                editForm.anonymousMarking
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    anonymousMarking:
                                                                        event.target.checked,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            className="h-4 w-4"
                                        />

                                        <span className="text-sm font-semibold text-slate-700">
                                            Anonymous marking
                                        </span>
                                    </label>

                                    <label className="block">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Scheduled start
                                        </span>

                                        <input
                                            type="datetime-local"
                                            value={
                                                editForm.scheduledAt
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    scheduledAt:
                                                                        event.target.value,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                        />
                                    </label>

                                    <label className="block">
                                        <span className="text-sm font-semibold text-slate-700">
                                            Closing time
                                        </span>

                                        <input
                                            type="datetime-local"
                                            value={
                                                editForm.closesAt
                                            }
                                            onChange={
                                                event =>
                                                    setEditForm(
                                                        current =>
                                                            current
                                                                ? {
                                                                    ...current,
                                                                    closesAt:
                                                                        event.target.value,
                                                                }
                                                                : current,
                                                    )
                                            }
                                            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                        />
                                    </label>

                                    <div className="flex flex-wrap gap-3 md:col-span-2">
                                        <button
                                            type="submit"
                                            disabled={
                                                busyAction !== null
                                                || structureAction !== null
                                            }
                                            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {busyAction === "edit"
                                                ? "Saving..."
                                                : "Save assessment"}
                                        </button>

                                        <button
                                            type="button"
                                            onClick={
                                                cancelEditAssessment
                                            }
                                            disabled={
                                                busyAction === "edit"
                                            }
                                            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </form>
                            </section>
                        )}

                    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                            <p className="text-sm font-semibold text-slate-500">
                                Sections
                            </p>

                            <p className="mt-2 text-3xl font-extrabold text-slate-900">
                                {assessment.sections.length}
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                                Assessment sections configured.
                            </p>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                            <p className="text-sm font-semibold text-slate-500">
                                Questions
                            </p>

                            <p className="mt-2 text-3xl font-extrabold text-slate-900">
                                {assessment.questions.length}
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                                Questions currently configured.
                            </p>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                            <p className="text-sm font-semibold text-slate-500">
                                Total marks
                            </p>

                            <p className="mt-2 text-3xl font-extrabold text-slate-900">
                                {totalMarks}
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                                Available across markable questions.
                            </p>
                        </div>

                        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                            <p className="text-sm font-semibold text-slate-500">
                                Marking
                            </p>

                            <p className="mt-2 text-lg font-bold text-slate-900">
                                {assessment.anonymous_marking
                                    ? "Anonymous"
                                    : "Named"}
                            </p>

                            <p className="mt-1 text-sm text-slate-500">
                                Current marking identity mode.
                            </p>
                        </div>
                    </section>

                    {isDraft && (
                    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                            <div>
                                <h2 className="text-2xl font-extrabold text-slate-900">
                                    Question paper
                                </h2>

                                <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                                    Upload the original PDF question paper and keep it attached to this assessment.
                                    Replacing a paper preserves the previous version for audit history.
                                </p>
                            </div>

                            {isDraft && currentQuestionPaper && (
                                <span className="w-fit rounded-full bg-green-50 px-3 py-1 text-xs font-bold text-green-700">
                                    Paper attached
                                </span>
                            )}
                        </div>

                        {questionPaperMessage && (
                            <div className="mt-5 rounded-xl border border-green-200 bg-green-50 p-4 text-sm font-medium text-green-700">
                                {questionPaperMessage}
                            </div>
                        )}

                        {isQuestionPaperLoading ? (
                            <div className="mt-5 rounded-xl border border-dashed border-slate-300 p-5 text-sm text-slate-500">
                                Loading question paper...
                            </div>
                        ) : currentQuestionPaper ? (
                            <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-5">
                                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                                    <div className="min-w-0">
                                        <p className="truncate font-bold text-slate-900">
                                            {currentQuestionPaper.original_filename}
                                        </p>

                                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                                            <span>
                                                {formatFileSize(
                                                    currentQuestionPaper.file_size_bytes,
                                                )}
                                            </span>

                                            <span>
                                                Uploaded{" "}
                                                {formatDateTime(
                                                    currentQuestionPaper.created_at,
                                                )}
                                            </span>

                                            <span>
                                                PDF
                                            </span>
                                        </div>

                                        {currentQuestionPaper.extraction_error && (
                                            <p className="mt-3 text-sm font-medium text-red-700">
                                                Extraction error:{" "}
                                                {currentQuestionPaper.extraction_error}
                                            </p>
                                        )}
                                    </div>

                                    <div className="flex flex-wrap gap-3">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                void handleViewQuestionPaper()
                                            }
                                            disabled={
                                                questionPaperAction !== null
                                            }
                                            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                                        >
                                            {questionPaperAction === "view"
                                                ? "Opening..."
                                                : "View uploaded paper"}
                                        </button>

                                        {isDraft && (
                                            <label className="cursor-pointer rounded-lg border border-blue-300 bg-white px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-50">
                                                Replace paper

                                                <input
                                                    type="file"
                                                    accept="application/pdf,.pdf"
                                                    className="sr-only"
                                                    disabled={
                                                        questionPaperAction !== null
                                                    }
                                                    onChange={event => {
                                                        handleQuestionPaperSelection(
                                                            event.target.files?.[0]
                                                            ?? null,
                                                        );

                                                        event.target.value = "";
                                                    }}
                                                />
                                            </label>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6">
                                <p className="font-semibold text-slate-800">
                                    No question paper has been uploaded.
                                </p>

                                <p className="mt-1 text-sm leading-6 text-slate-500">
                                    Attach the original PDF so the paper can be viewed here and used for question extraction later.
                                </p>

                                {isDraft ? (
                                    <label className="mt-4 inline-flex cursor-pointer rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700">
                                        Upload question paper

                                        <input
                                            type="file"
                                            accept="application/pdf,.pdf"
                                            className="sr-only"
                                            disabled={
                                                questionPaperAction !== null
                                            }
                                            onChange={event => {
                                                handleQuestionPaperSelection(
                                                    event.target.files?.[0]
                                                    ?? null,
                                                );

                                                event.target.value = "";
                                            }}
                                        />
                                    </label>
                                ) : (
                                    <p className="mt-4 text-sm font-medium text-slate-600">
                                        Question papers can only be added while the assessment is in draft.
                                    </p>
                                )}
                            </div>
                        )}

                        {isDraft && selectedQuestionPaper && (
                            <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-5">
                                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                                    <div>
                                        <p className="text-sm font-bold text-blue-900">
                                            Selected paper
                                        </p>

                                        <p className="mt-1 font-semibold text-slate-900">
                                            {selectedQuestionPaper.name}
                                        </p>

                                        <p className="mt-1 text-sm text-slate-600">
                                            {formatFileSize(
                                                selectedQuestionPaper.size,
                                            )}
                                        </p>
                                    </div>

                                    <div className="flex flex-wrap gap-3">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                void handleQuestionPaperUpload()
                                            }
                                            disabled={
                                                questionPaperAction !== null
                                            }
                                            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {questionPaperAction === "upload"
                                                ? "Uploading..."
                                                : currentQuestionPaper
                                                    ? "Upload replacement"
                                                    : "Upload paper"}
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() =>
                                                setSelectedQuestionPaper(
                                                    null,
                                                )
                                            }
                                            disabled={
                                                questionPaperAction !== null
                                            }
                                            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                                        >
                                            Cancel
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                    </section>
                    )}

                    {isDraft && currentQuestionPaper && (
                        <AssessmentQuestionExtractionPanel
                            assessmentId={
                                assessment.id
                            }
                            questionPaper={
                                currentQuestionPaper
                            }
                            isDraft={
                                isDraft
                            }
                            onImported={
                                loadAssessment
                            }
                        />
                    )}

                    {isDraft && (
                        <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
                        <div className="space-y-4">
                            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <h2 className="text-2xl font-extrabold text-slate-900">
                                            Sections
                                        </h2>

                                        <p className="mt-1 text-sm text-slate-600">
                                            Group related assessment questions.
                                        </p>
                                    </div>

                                    {isDraft && editingSectionId !== null && (
                                        <button
                                            type="button"
                                            onClick={
                                                resetSectionForm
                                            }
                                            className="text-sm font-semibold text-blue-600 hover:underline"
                                        >
                                            Add new section
                                        </button>
                                    )}
                                </div>

                                {sortedSections.length === 0 ? (
                                    <div className="mt-5 rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
                                        No sections have been configured.
                                        Questions can still exist without a
                                        section.
                                    </div>
                                ) : (
                                    <div className="mt-5 space-y-3">
                                        {sortedSections.map(
                                            section => (
                                                <div
                                                    key={
                                                        section.id
                                                    }
                                                    className="rounded-xl border border-slate-200 p-4"
                                                >
                                                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                                        <div>
                                                            <div className="flex flex-wrap items-center gap-2">
                                                                <h3 className="font-bold text-slate-900">
                                                                    {sectionDisplayName(
                                                                        section,
                                                                    )}
                                                                </h3>

                                                                {section.is_optional && (
                                                                    <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700">
                                                                        Optional
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {section.description && (
                                                                <p className="mt-2 text-sm text-slate-600">
                                                                    {
                                                                        section.description
                                                                    }
                                                                </p>
                                                            )}

                                                            <p className="mt-2 text-xs font-medium text-slate-400">
                                                                {
                                                                    assessment.questions.filter(
                                                                        question =>
                                                                            question.section_id
                                                                            === section.id,
                                                                    ).length
                                                                }{" "}
                                                                question(s)
                                                            </p>
                                                        </div>

                                                        {isDraft && (
                                                            <div className="flex gap-2">
                                                                <button
                                                                    type="button"
                                                                    onClick={() =>
                                                                        beginEditSection(
                                                                            section,
                                                                        )
                                                                    }
                                                                    disabled={
                                                                        structureAction
                                                                        !== null
                                                                    }
                                                                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                                                                >
                                                                    Edit
                                                                </button>

                                                                <button
                                                                    type="button"
                                                                    onClick={() =>
                                                                        void handleDeleteSection(
                                                                            section,
                                                                        )
                                                                    }
                                                                    disabled={
                                                                        structureAction
                                                                        !== null
                                                                    }
                                                                    className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                                                                >
                                                                    Delete
                                                                </button>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            ),
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                                <div>
                                    <h2 className="text-2xl font-extrabold text-slate-900">
                                        Questions
                                    </h2>

                                    <p className="mt-1 text-sm text-slate-600">
                                        Define question numbering, marks,
                                        sections and parent-child structure.
                                    </p>
                                </div>

                                {sortedQuestions.length === 0 ? (
                                    <div className="mt-5 rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
                                        No questions have been added yet.
                                    </div>
                                ) : (
                                    <div className="mt-5 space-y-3">
                                        {sortedQuestions.map(
                                            question => {
                                                const section =
                                                    assessment.sections.find(
                                                        item =>
                                                            item.id
                                                            === question.section_id,
                                                    );

                                                const parent =
                                                    assessment.questions.find(
                                                        item =>
                                                            item.id
                                                            === question.parent_question_id,
                                                    );

                                                return (
                                                    <div
                                                        key={
                                                            question.id
                                                        }
                                                        className="rounded-xl border border-slate-200 p-4"
                                                    >
                                                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                                            <div className="min-w-0">
                                                                <div className="flex flex-wrap items-center gap-2">
                                                                    <h3 className="font-bold text-slate-900">
                                                                        {questionDisplayName(
                                                                            question,
                                                                        )}
                                                                    </h3>

                                                                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
                                                                        {
                                                                            question.maximum_mark
                                                                        }{" "}
                                                                        mark(s)
                                                                    </span>

                                                                    {!question.is_markable && (
                                                                        <span className="rounded-full bg-purple-50 px-2.5 py-1 text-xs font-bold text-purple-700">
                                                                            Non-markable
                                                                        </span>
                                                                    )}
                                                                </div>

                                                                {question.prompt && (
                                                                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                                                                        {
                                                                            question.prompt
                                                                        }
                                                                    </p>
                                                                )}

                                                                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs font-medium text-slate-400">
                                                                    <span>
                                                                        Order{" "}
                                                                        {
                                                                            question.order
                                                                        }
                                                                    </span>

                                                                    <span>
                                                                        {section
                                                                            ? `Section: ${section.title}`
                                                                            : "No section"}
                                                                    </span>

                                                                    {parent && (
                                                                        <span>
                                                                            Parent:{" "}
                                                                            {
                                                                                parent.question_number
                                                                            }
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </div>

                                                            {isDraft && (
                                                                <div className="flex shrink-0 gap-2">
                                                                    <button
                                                                        type="button"
                                                                        onClick={() =>
                                                                            beginEditQuestion(
                                                                                question,
                                                                            )
                                                                        }
                                                                        disabled={
                                                                            structureAction
                                                                            !== null
                                                                        }
                                                                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                                                                    >
                                                                        Edit
                                                                    </button>

                                                                    <button
                                                                        type="button"
                                                                        onClick={() =>
                                                                            void handleDeleteQuestion(
                                                                                question,
                                                                            )
                                                                        }
                                                                        disabled={
                                                                            structureAction
                                                                            !== null
                                                                        }
                                                                        className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                                                                    >
                                                                        Delete
                                                                    </button>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            },
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>

                        {isDraft && (
                            <aside className="space-y-6">
                                <form
                                    onSubmit={
                                        handleSectionSubmit
                                    }
                                    className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                                >
                                    <h2 className="text-xl font-extrabold text-slate-900">
                                        {editingSectionId !== null
                                            ? "Edit section"
                                            : "Add section"}
                                    </h2>

                                    <div className="mt-5 space-y-4">
                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Title
                                            </span>

                                            <input
                                                type="text"
                                                value={
                                                    sectionForm.title
                                                }
                                                onChange={
                                                    event =>
                                                        setSectionForm(
                                                            current => ({
                                                                ...current,
                                                                title:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                maxLength={
                                                    255
                                                }
                                                required
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            />
                                        </label>

                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Description
                                            </span>

                                            <textarea
                                                value={
                                                    sectionForm.description
                                                }
                                                onChange={
                                                    event =>
                                                        setSectionForm(
                                                            current => ({
                                                                ...current,
                                                                description:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                rows={
                                                    3
                                                }
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            />
                                        </label>

                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Order
                                            </span>

                                            <input
                                                type="number"
                                                min={
                                                    1
                                                }
                                                step={
                                                    1
                                                }
                                                value={
                                                    sectionForm.order
                                                }
                                                onChange={
                                                    event =>
                                                        setSectionForm(
                                                            current => ({
                                                                ...current,
                                                                order:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                required
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            />
                                        </label>

                                        <label className="flex items-center gap-3">
                                            <input
                                                type="checkbox"
                                                checked={
                                                    sectionForm.isOptional
                                                }
                                                onChange={
                                                    event =>
                                                        setSectionForm(
                                                            current => ({
                                                                ...current,
                                                                isOptional:
                                                                    event.target.checked,
                                                            }),
                                                        )
                                                }
                                                className="h-4 w-4"
                                            />

                                            <span className="text-sm font-semibold text-slate-700">
                                                Optional section
                                            </span>
                                        </label>
                                    </div>

                                    <div className="mt-5 flex flex-wrap gap-3">
                                        <button
                                            type="submit"
                                            disabled={
                                                structureAction
                                                !== null
                                            }
                                            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {structureAction === "create-section"
                                                || structureAction === "update-section"
                                                ? "Saving..."
                                                : editingSectionId !== null
                                                    ? "Save section"
                                                    : "Add section"}
                                        </button>

                                        {editingSectionId !== null && (
                                            <button
                                                type="button"
                                                onClick={
                                                    resetSectionForm
                                                }
                                                disabled={
                                                    structureAction
                                                    !== null
                                                }
                                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                                            >
                                                Cancel
                                            </button>
                                        )}
                                    </div>
                                </form>

                                <form
                                    onSubmit={
                                        handleQuestionSubmit
                                    }
                                    className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <h2 className="text-xl font-extrabold text-slate-900">
                                                {editingQuestionId !== null
                                                    ? "Edit question"
                                                    : "Add question"}
                                            </h2>

                                            <p className="mt-1 text-xs leading-5 text-slate-500">
                                                Parent questions can be
                                                non-markable containers for
                                                parts such as 1(a) and 1(b).
                                            </p>
                                        </div>

                                        {editingQuestionId !== null && (
                                            <button
                                                type="button"
                                                onClick={
                                                    resetQuestionForm
                                                }
                                                className="text-xs font-semibold text-blue-600 hover:underline"
                                            >
                                                Add new
                                            </button>
                                        )}
                                    </div>

                                    <div className="mt-5 space-y-4">
                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Question number
                                            </span>

                                            <input
                                                type="text"
                                                value={
                                                    questionForm.questionNumber
                                                }
                                                onChange={
                                                    event =>
                                                        setQuestionForm(
                                                            current => ({
                                                                ...current,
                                                                questionNumber:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                placeholder="e.g. 1, 1(a), 2(b)(i)"
                                                maxLength={
                                                    50
                                                }
                                                required
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            />
                                        </label>

                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Title
                                            </span>

                                            <input
                                                type="text"
                                                value={
                                                    questionForm.title
                                                }
                                                onChange={
                                                    event =>
                                                        setQuestionForm(
                                                            current => ({
                                                                ...current,
                                                                title:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                maxLength={
                                                    255
                                                }
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            />
                                        </label>

                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Prompt
                                            </span>

                                            <textarea
                                                value={
                                                    questionForm.prompt
                                                }
                                                onChange={
                                                    event =>
                                                        setQuestionForm(
                                                            current => ({
                                                                ...current,
                                                                prompt:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                rows={
                                                    5
                                                }
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            />
                                        </label>

                                        <div className="grid grid-cols-2 gap-3">
                                            <label className="block">
                                                <span className="text-sm font-semibold text-slate-700">
                                                    Maximum mark
                                                </span>

                                                <input
                                                    type="number"
                                                    min={
                                                        0
                                                    }
                                                    step="0.01"
                                                    value={
                                                        questionForm.maximumMark
                                                    }
                                                    onChange={
                                                        event =>
                                                            setQuestionForm(
                                                                current => ({
                                                                    ...current,
                                                                    maximumMark:
                                                                        event.target.value,
                                                                }),
                                                            )
                                                    }
                                                    required
                                                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                                />
                                            </label>

                                            <label className="block">
                                                <span className="text-sm font-semibold text-slate-700">
                                                    Order
                                                </span>

                                                <input
                                                    type="number"
                                                    min={
                                                        1
                                                    }
                                                    step={
                                                        1
                                                    }
                                                    value={
                                                        questionForm.order
                                                    }
                                                    onChange={
                                                        event =>
                                                            setQuestionForm(
                                                                current => ({
                                                                    ...current,
                                                                    order:
                                                                        event.target.value,
                                                                }),
                                                            )
                                                    }
                                                    required
                                                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                                />
                                            </label>
                                        </div>

                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Section
                                            </span>

                                            <select
                                                value={
                                                    questionForm.sectionId
                                                }
                                                onChange={
                                                    event =>
                                                        setQuestionForm(
                                                            current => ({
                                                                ...current,
                                                                sectionId:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            >
                                                <option value="">
                                                    No section
                                                </option>

                                                {sortedSections.map(
                                                    section => (
                                                        <option
                                                            key={
                                                                section.id
                                                            }
                                                            value={
                                                                section.id
                                                            }
                                                        >
                                                            {sectionDisplayName(
                                                                section,
                                                            )}
                                                        </option>
                                                    ),
                                                )}
                                            </select>
                                        </label>

                                        <label className="block">
                                            <span className="text-sm font-semibold text-slate-700">
                                                Parent question
                                            </span>

                                            <select
                                                value={
                                                    questionForm.parentQuestionId
                                                }
                                                onChange={
                                                    event =>
                                                        setQuestionForm(
                                                            current => ({
                                                                ...current,
                                                                parentQuestionId:
                                                                    event.target.value,
                                                            }),
                                                        )
                                                }
                                                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500"
                                            >
                                                <option value="">
                                                    No parent question
                                                </option>

                                                {sortedQuestions
                                                    .filter(
                                                        question =>
                                                            question.id
                                                            !== editingQuestionId,
                                                    )
                                                    .map(
                                                        question => (
                                                            <option
                                                                key={
                                                                    question.id
                                                                }
                                                                value={
                                                                    question.id
                                                                }
                                                            >
                                                                {questionDisplayName(
                                                                    question,
                                                                )}
                                                            </option>
                                                        ),
                                                    )}
                                            </select>
                                        </label>

                                        <label className="flex items-center gap-3">
                                            <input
                                                type="checkbox"
                                                checked={
                                                    questionForm.isMarkable
                                                }
                                                onChange={
                                                    event =>
                                                        setQuestionForm(
                                                            current => ({
                                                                ...current,
                                                                isMarkable:
                                                                    event.target.checked,
                                                            }),
                                                        )
                                                }
                                                className="h-4 w-4"
                                            />

                                            <span className="text-sm font-semibold text-slate-700">
                                                Markable question
                                            </span>
                                        </label>
                                    </div>

                                    <div className="mt-5 flex flex-wrap gap-3">
                                        <button
                                            type="submit"
                                            disabled={
                                                structureAction
                                                !== null
                                            }
                                            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                                        >
                                            {structureAction === "create-question"
                                                || structureAction === "update-question"
                                                ? "Saving..."
                                                : editingQuestionId !== null
                                                    ? "Save question"
                                                    : "Add question"}
                                        </button>

                                        {editingQuestionId !== null && (
                                            <button
                                                type="button"
                                                onClick={
                                                    resetQuestionForm
                                                }
                                                disabled={
                                                    structureAction
                                                    !== null
                                                }
                                                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                                            >
                                                Cancel
                                            </button>
                                        )}
                                    </div>
                                </form>
                            </aside>
                        )}
                    </section>
                    )}

                    <AssessmentScannedScriptUploadPanel
                        assessmentId={assessment.id}
                    />

                    <AssessmentMarkingPanel
                        assessment={assessment}
                    />

                    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h2 className="text-2xl font-extrabold text-slate-900">
                            Assessment workflow
                        </h2>

                        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                            The assessment definition, question structure and
                            primary marking workflow are now connected.
                            Moderation, result publication and exports can be
                            connected into this workspace next.
                        </p>
                    </section>

                </>
            )}
        </main>
    );
}









