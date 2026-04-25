"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/providers/AuthProvider";
import { UserRole } from "@/types/user";

type ProtectedRouteProps = {
    children: ReactNode;
    allowedRoles?: UserRole[];
    redirectTo?: string;
    fallback?: ReactNode;
};

export default function ProtectedRoute({
    children,
    allowedRoles,
    redirectTo = "/login",
    fallback = null,
}: ProtectedRouteProps) {
    const { user, loading, hasAnyRole } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!loading && !user) {
            router.replace(redirectTo);
        }
    }, [loading, user, router, redirectTo]);

    if (loading) {
        return <div className="p-4">Loading...</div>;
    }

    if (!user) {
        return null;
    }

    if (allowedRoles && allowedRoles.length > 0 && !hasAnyRole(allowedRoles)) {
        return (
            fallback ?? (
                <div className="p-4 text-red-500">
                    You do not have permission to access this page.
                </div>
            )
        );
    }

    return <>{children}</>;
}