"use client";

import {
    useCallback,
    useEffect,
    useState,
} from "react";

import {
    getAssessments,
    type Assessment,
    type AssessmentListFilters,
} from "@/lib/services/assessments";


export function useAssessments(
    filters: AssessmentListFilters = {},
) {
    const [assessments, setAssessments] =
        useState<Assessment[]>([]);

    const [isLoading, setIsLoading] =
        useState<boolean>(true);

    const [error, setError] =
        useState<string | null>(null);


    const loadAssessments =
        useCallback(
            async () => {
                try {
                    setError(null);
                    setIsLoading(true);

                    const data =
                        await getAssessments(
                            filters,
                        );

                    setAssessments(
                        data ?? [],
                    );
                } catch (err: unknown) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load assessments.",
                    );
                } finally {
                    setIsLoading(false);
                }
            },
            [
                filters.academic_year,
                filters.assessment_status,
                filters.course_id,
                filters.term,
            ],
        );


    useEffect(
        () => {
            void loadAssessments();
        },
        [
            loadAssessments,
        ],
    );


    return {
        assessments,
        isLoading,
        error,
        refresh: loadAssessments,
        setAssessments,
    };
}