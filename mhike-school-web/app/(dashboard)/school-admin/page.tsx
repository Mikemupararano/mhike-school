"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import RoleGate from "@/components/auth/RoleGate";
import { UserRole } from "@/types/user";

export default function SchoolAdminDashboardPage() {
    const router = useRouter();

    useEffect(() => {
        router.replace("/school-admin/users");
    }, [router]);

    return (
        <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
            <div className="p-6 text-sm text-slate-500">
                Redirecting to users...
            </div>
        </RoleGate>
    );
}