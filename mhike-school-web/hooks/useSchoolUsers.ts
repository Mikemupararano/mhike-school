"use client";

import { useCallback, useEffect, useState } from "react";

import type { User } from "@/types/user";
import {
    listSchoolUsers,
    deactivateSchoolUser,
    requestUserErasure,
    anonymiseSchoolUser,
} from "@/lib/services/school-admin";

export function useSchoolUsers() {
    const [users, setUsers] = useState<User[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

    const loadUsers = useCallback(async () => {
        try {
            setError(null);
            setIsLoading(true);
            const data = await listSchoolUsers();
            setUsers(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load users");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadUsers();
    }, [loadUsers]);

    async function deactivateUser(userId: number) {
        try {
            setActionLoadingId(userId);
            await deactivateSchoolUser(userId);
            await loadUsers();
        } finally {
            setActionLoadingId(null);
        }
    }

    async function requestErasure(userId: number) {
        try {
            setActionLoadingId(userId);
            await requestUserErasure(userId);
            await loadUsers();
        } finally {
            setActionLoadingId(null);
        }
    }

    async function anonymiseUser(userId: number) {
        try {
            setActionLoadingId(userId);
            await anonymiseSchoolUser(userId);
            await loadUsers();
        } finally {
            setActionLoadingId(null);
        }
    }

    return {
        users,
        isLoading,
        error,
        actionLoadingId,
        refreshUsers: loadUsers,
        deactivateUser,
        requestErasure,
        anonymiseUser,
    };
}