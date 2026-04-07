"use client";

import React from "react";
import Link from "next/link";
import PageHeader from "@/components/layout/PageHeader";

type SchoolHeroAction = {
    label: string;
    href?: string;
    onClick?: () => void;
    variant?: "primary" | "secondary";
};

type SchoolHeroProps = {
    schoolName?: string;
    roleLabel?: string;
    title: string;
    subtitle?: string;
    actions?: SchoolHeroAction[];
    rightContent?: React.ReactNode;
};

function ActionButton({
    label,
    href,
    onClick,
    variant = "primary",
}: SchoolHeroAction) {
    const base =
        "inline-flex items-center justify-center rounded-xl px-4 py-3 text-sm font-extrabold transition";

    const variantClass =
        variant === "secondary"
            ? "border border-white/20 bg-white/10 text-white hover:bg-white/15"
            : "bg-white text-[#1D4ED8] hover:bg-[#EFF6FF]";

    if (href) {
        return (
            <Link href={href} className={`${base} ${variantClass}`}>
                {label}
            </Link>
        );
    }

    return (
        <button
            type="button"
            onClick={onClick}
            className={`${base} ${variantClass}`}
        >
            {label}
        </button>
    );
}

export default function SchoolHero({
    schoolName,
    roleLabel = "Dashboard",
    title,
    subtitle,
    actions = [],
    rightContent,
}: SchoolHeroProps) {
    const eyebrow = schoolName ? `${schoolName} · ${roleLabel}` : roleLabel;

    return (
        <PageHeader
            eyebrow={eyebrow}
            title={title}
            subtitle={subtitle}
            actions={
                actions.length ? (
                    <>
                        {actions.map((action, i) => (
                            <ActionButton key={i} {...action} />
                        ))}
                    </>
                ) : undefined
            }
            rightContent={
                rightContent ?? (
                    <div className="flex h-full w-full items-center justify-center text-6xl">
                        📘
                    </div>
                )
            }
        />
    );
}