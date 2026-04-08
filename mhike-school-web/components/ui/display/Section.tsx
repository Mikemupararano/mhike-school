"use client";

import React from "react";

type SectionProps = {
    title?: string;
    subtitle?: string;
    actions?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
};

export default function Section({
    title,
    subtitle,
    actions,
    children,
    className = "",
}: SectionProps) {
    return (
        <section
            className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md ${className}`}
        >
            {(title || actions) && (
                <div className="mb-4 flex items-start justify-between gap-4">
                    <div>
                        {title && (
                            <h2 className="text-lg font-bold text-slate-900">{title}</h2>
                        )}
                        {subtitle && (
                            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
                        )}
                    </div>

                    {actions && <div className="flex gap-2">{actions}</div>}
                </div>
            )}

            <div>{children}</div>
        </section>
    );
}