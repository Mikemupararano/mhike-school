"use client";

import { useCallback, useEffect, useState } from "react";
import {
    getTeacherCourses,
    type TeacherCourse,
} from "@/lib/services/teacher";

export function useTeacherCourses() {
    const [courses, setCourses] = useState<TeacherCourse[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const loadCourses = useCallback(async () => {
        try {
            setError(null);
            setIsLoading(true);

            const data = await getTeacherCourses();
            setCourses(data ?? []);
        } catch (err: unknown) {
            setError(
                err instanceof Error ? err.message : "Failed to load courses",
            );
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadCourses();
    }, [loadCourses]);

    return {
        courses,
        isLoading,
        error,
        refresh: loadCourses,
    };
}