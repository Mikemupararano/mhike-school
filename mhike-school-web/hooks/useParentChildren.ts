"use client";

import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    getMyChildrenAttendanceProfiles,
    type StudentAttendanceProfile,
} from "@/lib/parent";

export function useParentChildren() {
    const [profiles, setProfiles] =
        useState<StudentAttendanceProfile[]>([]);

    const [selectedStudentId, setSelectedStudentId] =
        useState<number | null>(null);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState<string | null>(null);

    useEffect(() => {
        async function loadChildren() {
            try {
                setLoading(true);
                setError(null);

                const loadedProfiles =
                    await getMyChildrenAttendanceProfiles();

                setProfiles(loadedProfiles);

                setSelectedStudentId(
                    loadedProfiles[0]?.student_id ?? null,
                );
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : "Failed to load linked children.",
                );
            } finally {
                setLoading(false);
            }
        }

        void loadChildren();
    }, []);

    const selectedProfile =
        useMemo(() => {
            return (
                profiles.find(
                    (profile) =>
                        profile.student_id ===
                        selectedStudentId,
                ) ?? null
            );
        }, [
            profiles,
            selectedStudentId,
        ]);

    return {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading,
        error,
    };
}