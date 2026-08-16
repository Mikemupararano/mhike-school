import {
    apiDelete,
    apiGet,
    apiPatch,
    apiPost,
} from "@/lib/api";


export type AssessmentStatus =
    | "draft"
    | "published"
    | "closed"
    | "archived";


export type AssessmentSection = {
    id: number;
    assessment_id: number;
    title: string;
    description: string | null;
    order: number;
    is_optional: boolean;
};


export type AssessmentQuestion = {
    id: number;
    assessment_id: number;
    section_id: number | null;
    parent_question_id: number | null;
    question_number: string;
    title: string | null;
    prompt: string | null;
    maximum_mark: string | number;
    order: number;
    is_markable: boolean;
};


export type Assessment = {
    id: number;
    school_id: number;
    course_id: number;
    created_by_id: number;

    title: string;
    description: string | null;
    assessment_type: string | null;
    academic_year: string | null;
    term: string | null;

    status: AssessmentStatus;
    anonymous_marking: boolean;

    scheduled_at: string | null;
    closes_at: string | null;

    created_at: string;
    updated_at: string;

    sections: AssessmentSection[];
    questions: AssessmentQuestion[];
};


export type AssessmentCreate = {
    course_id: number;
    title: string;
    description?: string | null;
    assessment_type?: string | null;
    academic_year?: string | null;
    term?: string | null;
    anonymous_marking?: boolean;
    scheduled_at?: string | null;
    closes_at?: string | null;
};


export type AssessmentUpdate = {
    title?: string | null;
    description?: string | null;
    assessment_type?: string | null;
    academic_year?: string | null;
    term?: string | null;
    anonymous_marking?: boolean | null;
    scheduled_at?: string | null;
    closes_at?: string | null;
};


export type AssessmentListFilters = {
    course_id?: number;
    assessment_status?: AssessmentStatus;
    academic_year?: string;
    term?: string;
};


export type AssessmentSectionCreate = {
    title: string;
    description?: string | null;
    order?: number;
    is_optional?: boolean;
};


export type AssessmentSectionUpdate = {
    title?: string | null;
    description?: string | null;
    order?: number | null;
    is_optional?: boolean | null;
};


export type AssessmentQuestionCreate = {
    section_id?: number | null;
    parent_question_id?: number | null;
    question_number: string;
    title?: string | null;
    prompt?: string | null;
    maximum_mark: string | number;
    order?: number;
    is_markable?: boolean;
};


export type AssessmentQuestionUpdate = {
    section_id?: number | null;
    parent_question_id?: number | null;
    question_number?: string | null;
    title?: string | null;
    prompt?: string | null;
    maximum_mark?: string | number | null;
    order?: number | null;
    is_markable?: boolean | null;
};


function buildAssessmentQuery(
    filters: AssessmentListFilters,
): string {
    const params =
        new URLSearchParams();

    if (filters.course_id !== undefined) {
        params.set(
            "course_id",
            String(
                filters.course_id,
            ),
        );
    }

    if (filters.assessment_status) {
        params.set(
            "assessment_status",
            filters.assessment_status,
        );
    }

    if (filters.academic_year) {
        params.set(
            "academic_year",
            filters.academic_year,
        );
    }

    if (filters.term) {
        params.set(
            "term",
            filters.term,
        );
    }

    const query =
        params.toString();

    return query
        ? `?${query}`
        : "";
}


// ---------------------------------------------------------------------
// Assessment definition
// ---------------------------------------------------------------------


export async function getAssessments(
    filters: AssessmentListFilters = {},
): Promise<Assessment[]> {
    return apiGet<Assessment[]>(
        `/assessments${buildAssessmentQuery(filters)}`,
    );
}


export async function getAssessment(
    assessmentId: number,
): Promise<Assessment> {
    return apiGet<Assessment>(
        `/assessments/${assessmentId}`,
    );
}


export async function createAssessment(
    payload: AssessmentCreate,
): Promise<Assessment> {
    return apiPost<Assessment>(
        "/assessments",
        payload,
    );
}


export async function updateAssessment(
    assessmentId: number,
    payload: AssessmentUpdate,
): Promise<Assessment> {
    return apiPatch<Assessment>(
        `/assessments/${assessmentId}`,
        payload,
    );
}


export async function transitionAssessmentStatus(
    assessmentId: number,
    assessmentStatus: AssessmentStatus,
): Promise<Assessment> {
    return apiPatch<Assessment>(
        `/assessments/${assessmentId}/status`,
        {
            status: assessmentStatus,
        },
    );
}


export async function publishAssessment(
    assessmentId: number,
): Promise<Assessment> {
    return apiPost<Assessment>(
        `/assessments/${assessmentId}/publish`,
        {},
    );
}


export async function closeAssessment(
    assessmentId: number,
): Promise<Assessment> {
    return apiPost<Assessment>(
        `/assessments/${assessmentId}/close`,
        {},
    );
}


export async function archiveAssessment(
    assessmentId: number,
): Promise<Assessment> {
    return apiPost<Assessment>(
        `/assessments/${assessmentId}/archive`,
        {},
    );
}


export async function deleteAssessment(
    assessmentId: number,
): Promise<void> {
    await apiDelete<void>(
        `/assessments/${assessmentId}`,
    );
}


// ---------------------------------------------------------------------
// Assessment sections
// ---------------------------------------------------------------------


export async function getAssessmentSections(
    assessmentId: number,
): Promise<AssessmentSection[]> {
    return apiGet<AssessmentSection[]>(
        `/assessments/${assessmentId}/sections`,
    );
}


export async function getAssessmentSection(
    assessmentId: number,
    sectionId: number,
): Promise<AssessmentSection> {
    return apiGet<AssessmentSection>(
        `/assessments/${assessmentId}/sections/${sectionId}`,
    );
}


export async function createAssessmentSection(
    assessmentId: number,
    payload: AssessmentSectionCreate,
): Promise<AssessmentSection> {
    return apiPost<AssessmentSection>(
        `/assessments/${assessmentId}/sections`,
        payload,
    );
}


export async function updateAssessmentSection(
    assessmentId: number,
    sectionId: number,
    payload: AssessmentSectionUpdate,
): Promise<AssessmentSection> {
    return apiPatch<AssessmentSection>(
        `/assessments/${assessmentId}/sections/${sectionId}`,
        payload,
    );
}


export async function deleteAssessmentSection(
    assessmentId: number,
    sectionId: number,
): Promise<Assessment> {
    return apiDelete<Assessment>(
        `/assessments/${assessmentId}/sections/${sectionId}`,
    );
}


// ---------------------------------------------------------------------
// Assessment questions
// ---------------------------------------------------------------------


export async function getAssessmentQuestions(
    assessmentId: number,
): Promise<AssessmentQuestion[]> {
    return apiGet<AssessmentQuestion[]>(
        `/assessments/${assessmentId}/questions`,
    );
}


export async function getAssessmentQuestion(
    assessmentId: number,
    questionId: number,
): Promise<AssessmentQuestion> {
    return apiGet<AssessmentQuestion>(
        `/assessments/${assessmentId}/questions/${questionId}`,
    );
}


export async function createAssessmentQuestion(
    assessmentId: number,
    payload: AssessmentQuestionCreate,
): Promise<AssessmentQuestion> {
    return apiPost<AssessmentQuestion>(
        `/assessments/${assessmentId}/questions`,
        payload,
    );
}


export async function updateAssessmentQuestion(
    assessmentId: number,
    questionId: number,
    payload: AssessmentQuestionUpdate,
): Promise<AssessmentQuestion> {
    return apiPatch<AssessmentQuestion>(
        `/assessments/${assessmentId}/questions/${questionId}`,
        payload,
    );
}


export async function deleteAssessmentQuestion(
    assessmentId: number,
    questionId: number,
): Promise<Assessment> {
    return apiDelete<Assessment>(
        `/assessments/${assessmentId}/questions/${questionId}`,
    );
}