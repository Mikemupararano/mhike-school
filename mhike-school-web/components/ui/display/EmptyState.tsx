"use client";

import React from "react";

type EmptyStateProps = {
    title?: string;
    description?: string;
    action?: React.ReactNode;
};

export default function EmptyState({
    title = "No data available",
    description,
    action,
}: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-12 text-center">
            <div className="text-lg font-bold text-slate-900">{title}</div>

            {description && (
                <p className="mt-2 max-w-md text-sm text-slate-500">
                    {description}
                </p>
            )}

            {action && <div className="mt-4">{action}</div>}
        </div>
    );
}