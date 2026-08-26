import {
    apiGet,
    apiPost,
} from "@/lib/api";


// ---------------------------------------------------------------------
// Candidate lifecycle
// ---------------------------------------------------------------------


export type AssessmentCandidateStatus =
    | "allocated"
    | "started"
    | "submitted"
    | "withdrawn"
    | "absent";


export type AssessmentScriptStatus =
    | "not_submitted"
    | "submitted"
    | "marking"
    | "marked"
    | "moderation"
    | "finalised";


// ---------------------------------------------------------------------
// Script representation
// ---------------------------------------------------------------------


export type AssessmentScript = {
    id: number;
    candidate_id: number;
    version: number;

    status: AssessmentScriptStatus;

    source_type: string | null;
    source_filename: string | null;
    storage_key: string | null;
    mime_type: string | null;
    checksum: string | null;

    created_at: string;

    submitted_at: string | null;
    marking_started_at: string | null;
    marked_at: string | null;
    finalised_at: string | null;
};


// ---------------------------------------------------------------------
// Candidate representation
// ---------------------------------------------------------------------


export type AssessmentCandidate = {
    id: number;

    assessment_id: number;
    student_id: number;

    status: AssessmentCandidateStatus;

    candidate_number: string | null;
    access_arrangements: string | null;

    allocated_at: string;
    started_at: string | null;
    submitted_at: string | null;

    scripts: AssessmentScript[];
};


// ---------------------------------------------------------------------
// Query helpers
// ---------------------------------------------------------------------


function buildCandidateStatusQuery(
    candidateStatus?: AssessmentCandidateStatus,
): string {
    if (!candidateStatus) {
        return "";
    }

    const params =
        new URLSearchParams();

    params.set(
        "candidate_status",
        candidateStatus,
    );

    return `?${params.toString()}`;
}


function buildScriptStatusQuery(
    scriptStatus?: AssessmentScriptStatus,
): string {
    if (!scriptStatus) {
        return "";
    }

    const params =
        new URLSearchParams();

    params.set(
        "script_status",
        scriptStatus,
    );

    return `?${params.toString()}`;
}


// ---------------------------------------------------------------------
// Assessment candidate reads
// ---------------------------------------------------------------------


export async function getAssessmentCandidates(
    assessmentId: number,
    candidateStatus?: AssessmentCandidateStatus,
): Promise<AssessmentCandidate[]> {
    return apiGet<AssessmentCandidate[]>(
        `/assessment-candidates/assessment/${assessmentId}${buildCandidateStatusQuery(
            candidateStatus,
        )}`,
    );
}


export async function getAssessmentCandidate(
    candidateId: number,
): Promise<AssessmentCandidate> {
    return apiGet<AssessmentCandidate>(
        `/assessment-candidates/${candidateId}`,
    );
}


// ---------------------------------------------------------------------
// Candidate scripts
// ---------------------------------------------------------------------


export async function getCandidateScripts(
    candidateId: number,
    scriptStatus?: AssessmentScriptStatus,
): Promise<AssessmentScript[]> {
    return apiGet<AssessmentScript[]>(
        `/assessment-candidates/${candidateId}/scripts${buildScriptStatusQuery(
            scriptStatus,
        )}`,
    );
}


export async function getAssessmentScript(
    scriptId: number,
): Promise<AssessmentScript> {
    return apiGet<AssessmentScript>(
        `/assessment-candidates/scripts/${scriptId}`,
    );
}


// ---------------------------------------------------------------------
// Script marking lifecycle
// ---------------------------------------------------------------------


export async function startAssessmentScriptMarking(
    scriptId: number,
): Promise<AssessmentScript> {
    return apiPost<AssessmentScript>(
        `/assessment-candidates/scripts/${scriptId}/start-marking`,
        {},
    );
}


export async function completeAssessmentScriptMarking(
    scriptId: number,
): Promise<AssessmentScript> {
    return apiPost<AssessmentScript>(
        `/assessment-candidates/scripts/${scriptId}/mark-complete`,
        {},
    );
}


export async function sendAssessmentScriptToModeration(
    scriptId: number,
): Promise<AssessmentScript> {
    return apiPost<AssessmentScript>(
        `/assessment-candidates/scripts/${scriptId}/moderation`,
        {},
    );
}


export async function finaliseAssessmentScript(
    scriptId: number,
): Promise<AssessmentScript> {
    return apiPost<AssessmentScript>(
        `/assessment-candidates/scripts/${scriptId}/finalise`,
        {},
    );
}


// ---------------------------------------------------------------------
// Marking-workspace helpers
// ---------------------------------------------------------------------


export function isScriptAvailableForMarking(
    script: AssessmentScript,
): boolean {
    return (
        script.status === "submitted"
        || script.status === "marking"
        || script.status === "marked"
        || script.status === "moderation"
    );
}


export function getLatestCandidateScript(
    candidate: AssessmentCandidate,
): AssessmentScript | null {
    if (candidate.scripts.length === 0) {
        return null;
    }

    return candidate.scripts.reduce(
        (
            latest,
            current,
        ) => (
            current.version > latest.version
                ? current
                : latest
        ),
    );
}
