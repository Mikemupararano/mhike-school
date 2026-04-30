"use client";

import { useCallback, useEffect, useState } from "react";

import { apiGet } from "@/lib/api";

export type RecentSchool = {
    id: number;
    name: string;
    admin_name: string;
    users: number;
    status: string;
};

export type AdminDashboardData = {
    total_schools: number;
    total_users: number;
    active_users: number;
    total_courses: number;
    published_content: number;
    total_enrollments: number;
    recent_schools: RecentSchool[];
};

export function useAdminDashboard() {
    const [data, setData] = useState<AdminDashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            const result = await apiGet<AdminDashboardData>("/admin/dashboard");
            setData(result);
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to load dashboard data",
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void refresh();
    }, [refresh]);

    return {
        data,
        loading,
        error,
        refresh,
    };
}