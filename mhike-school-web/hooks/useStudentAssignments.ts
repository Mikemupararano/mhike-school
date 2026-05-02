"use client";

import { useCallback, useEffect, useState } from "react";
import {
    type AssignmentOut,
    type AssignmentSubmissionOut,
    getMyStudentAssignments,
    getMySubmission,
    submitAssignment,
} from "@/lib/assignmentApi";

export function useStudentAssignments() {
    const [assignments, setAssignments] = useState<AssignmentOut[]>([]);
    const [submissions, setSubmissions] = useState<
        Record<number, AssignmentSubmissionOut | null>
    >({});
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [busyId, setBusyId] = useState<number | null>(null);
    const [error, setError] = useState<string>("");

    const loadAssignments = useCallback(async () => {
        try {
            setError("");
            setIsLoading(true);

            const assignmentData = (await getMyStudentAssignments()) ?? [];
            setAssignments(assignmentData);

            const entries = await Promise.all(
                assignmentData.map(async (assignment) => {
                    try {
                        const submission = await getMySubmission(assignment.id);
                        return [assignment.id, submission] as const;
                    } catch {
                        return [assignment.id, null] as const;
                    }
                }),
            );

            setSubmissions(Object.fromEntries(entries));
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to load assignments",
            );
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadAssignments();
    }, [loadAssignments]);

    async function submitStudentAssignment(
        assignmentId: number,
        submissionText: string,
        attachmentUrl?: string,
    ) {
        try {
            setBusyId(assignmentId);
            setError("");

            await submitAssignment(assignmentId, {
                submission_text: submissionText.trim() || null,
                attachment_url: attachmentUrl?.trim() || null,
            });

            await loadAssignments();
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to submit assignment",
            );
        } finally {
            setBusyId(null);
        }
    }

    return {
        assignments,
        submissions,
        isLoading,
        busyId,
        error,
        refresh: loadAssignments,
        submitStudentAssignment,
    };
}