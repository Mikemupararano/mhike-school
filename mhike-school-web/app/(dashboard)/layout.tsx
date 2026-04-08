import React from "react";
import DashboardShell from "@/components/layout/DashboardShell";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <DashboardShell
            userName="User"
            schoolName="Mhike School"
            showSidebar={true}
            showRefresh={false}
            showLogout={true}
        >
            {children}
        </DashboardShell>
    );
}