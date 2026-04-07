"use client";

import React from "react";

type PageHeaderProps = {
    eyebrow?: string;
    title: string;
    subtitle?: string;
    actions?: React.ReactNode;
    rightContent?: React.ReactNode;
};

export default function PageHeader({
    eyebrow,
    title,
    subtitle,
    actions,
    rightContent,
}: PageHeaderProps) {
    return (
        <div
            className="
                relative overflow-hidden rounded-[28px]
                border border-white/10
                bg-[radial-gradient(circle_at_top_left,_rgba(255,255,255,0.18),_transparent_28%),linear-gradient(135deg,_#163B66_0%,_#1D4ED8_45%,_#60A5FA_100%)]
                p-7 text-white shadow-[0_24px_60px_rgba(29,78,216,0.22)]
                sm:p-8
            "
        >
            <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,rgba(255,255,255,0.06),transparent_45%,rgba(255,255,255,0.04))]" />
            <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-white/10 blur-3xl" />
            <div className="pointer-events-none absolute -bottom-24 left-24 h-48 w-48 rounded-full bg-cyan-300/10 blur-3xl" />

            <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1.5fr)_340px] lg:items-center">
                <div className="max-w-3xl">
                    {eyebrow ? (
                        <p className="mb-3 text-sm font-semibold tracking-wide text-blue-100/95">
                            {eyebrow}
                        </p>
                    ) : null}

                    <h1 className="max-w-4xl text-4xl font-black leading-[1.02] tracking-tight sm:text-5xl">
                        {title}
                    </h1>

                    {subtitle ? (
                        <p className="mt-4 max-w-3xl text-base leading-7 text-blue-50/90 sm:text-lg">
                            {subtitle}
                        </p>
                    ) : null}

                    {actions ? (
                        <div className="mt-6 flex flex-wrap gap-3">
                            {actions}
                        </div>
                    ) : null}
                </div>

                {rightContent ? (
                    <div
                        className="
                            rounded-[24px] border border-white/15 bg-white/10 p-5
                            shadow-[inset_0_1px_0_rgba(255,255,255,0.14),0_20px_40px_rgba(15,23,42,0.18)]
                            backdrop-blur-md
                        "
                    >
                        {rightContent}
                    </div>
                ) : null}
            </div>
        </div>
    );
}