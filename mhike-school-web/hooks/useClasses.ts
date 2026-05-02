"use client";

import { useCallback, useEffect, useState } from "react";

import type { ClassGroup } from "@/types/class";
import {
    listClasses,
    createClass,
    updateClass,
    assignTeacher,
    enrollStudent,
    removeStudent,
} from "@/lib/services/classes";

export function useClasses() {
    const [classes, setClasses] = useState<ClassGroup[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

    const loadClasses = useCallback(async () => {
        try {
            setError(null);
            setIsLoading(true);
            const data = await listClasses();
            setClasses(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load classes");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadClasses();
    }, [loadClasses]);

    async function createNewClass(name: string, teacherId?: number | null) {
        const createdClass = await createClass({
            name,
            teacher_id: teacherId ?? null,
        });

        await loadClasses();
        return createdClass;
    }

    async function updateExistingClass(
        classId: number,
        data: Partial<ClassGroup>,
    ) {
        try {
            setActionLoadingId(classId);
            const updatedClass = await updateClass(classId, data);
            await loadClasses();
            return updatedClass;
        } finally {
            setActionLoadingId(null);
        }
    }

    async function assignClassTeacher(classId: number, teacherId: number) {
        try {
            setActionLoadingId(classId);
            const updatedClass = await assignTeacher(classId, teacherId);
            await loadClasses();
            return updatedClass;
        } finally {
            setActionLoadingId(null);
        }
    }

    async function enrollClassStudent(classId: number, studentId: number) {
        try {
            setActionLoadingId(studentId);
            await enrollStudent(classId, studentId);
            await loadClasses();
        } finally {
            setActionLoadingId(null);
        }
    }

    async function removeClassStudent(classId: number, studentId: number) {
        try {
            setActionLoadingId(studentId);
            await removeStudent(classId, studentId);
            await loadClasses();
        } finally {
            setActionLoadingId(null);
        }
    }

    return {
        classes,
        isLoading,
        error,
        actionLoadingId,
        refreshClasses: loadClasses,
        createNewClass,
        updateExistingClass,
        assignClassTeacher,
        enrollClassStudent,
        removeClassStudent,
    };
}