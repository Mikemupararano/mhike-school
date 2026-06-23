"use client";

import React from "react";
import "@/styles/dashboard-theme.css";

import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import type { SidebarSection } from "@/lib/navigation/sidebar";

type DashboardShellProps = {
    children: React.ReactNode;
    userId?: number | null;
    schoolId?: number | null;
    userName?: string;
    schoolName?: string;
    sidebarTitle?: string;
    sidebarSections?: SidebarSection[];
    showSidebar?: boolean;
    sidebarCollapsed?: boolean;
    showRefresh?: boolean;
    refreshLabel?: string;
    onRefresh?: () => void;
    showLogout?: boolean;
    contentClassName?: string;
};

export default function DashboardShell({
    children,
    userId,
    schoolId,
    userName = "User",
    schoolName,
    sidebarTitle,
    sidebarSections,
    showSidebar = true,
    sidebarCollapsed = false,
    showRefresh = true,
    refreshLabel = "Refresh",
    onRefresh,
    showLogout = true,
    contentClassName = "",
}: DashboardShellProps) {
    const resolvedSidebarTitle = sidebarTitle || schoolName || "Mhike School";

    return (
        <div className="dashboard-theme min-h-screen antialiased">
            <Navbar
                userId={userId}
                schoolId={schoolId}
                userName={userName}
                schoolName={schoolName}
                showRefresh={showRefresh}
                refreshLabel={refreshLabel}
                onRefresh={onRefresh}
                showLogout={showLogout}
            />

            <div className="flex min-h-[calc(100vh-56px)]">
                {showSidebar ? (
                    <Sidebar
                        title={resolvedSidebarTitle}
                        sections={sidebarSections}
                        collapsed={sidebarCollapsed}
                        className="hidden shrink-0 border-r border-white/10 lg:block"
                    />
                ) : null}

                <main
                    className={`flex-1 overflow-x-hidden px-6 py-8 lg:px-10 xl:px-12 ${contentClassName}`}
                >
                    <div className="w-full">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}