"use client";

import { useCallback, useEffect, useState } from "react";
import {
    getTeacherAssignments,
    type TeacherAssignment,
} from "@/lib/services/teacher";

export function useTeacherAssignments() {
    const [assignments, setAssignments] = useState<TeacherAssignment[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const loadAssignments = useCallback(async () => {
        try {
            setError(null);
            setIsLoading(true);

            const data = await getTeacherAssignments();
            setAssignments(data ?? []);
        } catch (err: unknown) {
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

    return {
        assignments,
        isLoading,
        error,
        refresh: loadAssignments, // ✅ cleaner API name
        setAssignments, // 🔥 optional (useful for optimistic UI later)
    };
}