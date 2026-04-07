"use client";

import React from "react";

type StatTone = "default" | "blue" | "green" | "amber" | "slate";

type SchoolStatItem = {
    label: string;
    value: string | number;
    tone?: StatTone;
};

type SchoolStatsCardsProps = {
    items: SchoolStatItem[];
    className?: string;
};

function toneClasses(tone: StatTone = "default") {
    switch (tone) {
        case "blue":
            return {
                card: "border-transparent bg-[linear-gradient(135deg,#2563EB_0%,#60A5FA_100%)] text-white shadow-[0_18px_40px_rgba(37,99,235,0.22)]",
                label: "text-white/80",
                value: "text-white",
            };
        case "green":
            return {
                card: "border-transparent bg-[linear-gradient(135deg,#059669_0%,#6EE7B7_100%)] text-white shadow-[0_18px_40px_rgba(16,185,129,0.20)]",
                label: "text-white/85",
                value: "text-white",
            };
        case "amber":
            return {
                card: "border-transparent bg-[linear-gradient(135deg,#D97706_0%,#FBBF24_100%)] text-white shadow-[0_18px_40px_rgba(245,158,11,0.20)]",
                label: "text-white/85",
                value: "text-white",
            };
        case "slate":
            return {
                card: "border-slate-800 bg-slate-900 text-white shadow-[0_18px_40px_rgba(15,23,42,0.24)]",
                label: "text-slate-300",
                value: "text-white",
            };
        default:
            return {
                card: "border-slate-200 bg-white text-slate-900 shadow-[0_10px_30px_rgba(15,23,42,0.06)]",
                label: "text-slate-500",
                value: "text-slate-900",
            };
    }
}

function StatCard({
    label,
    value,
    tone = "default",
}: SchoolStatItem) {
    const styles = toneClasses(tone);

    return (
        <div
            className={`
                min-h-[128px] rounded-[22px] border p-5 transition duration-200
                hover:-translate-y-0.5 hover:shadow-[0_20px_40px_rgba(15,23,42,0.10)]
                ${styles.card}
            `}
        >
            <div className={`text-sm font-semibold tracking-wide ${styles.label}`}>
                {label}
            </div>

            <div className={`mt-5 text-[40px] font-black leading-none ${styles.value}`}>
                {value}
            </div>
        </div>
    );
}

export default function SchoolStatsCards({
    items,
    className = "",
}: SchoolStatsCardsProps) {
    if (!items.length) return null;

    return (
        <section
            className={`grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 ${className}`}
        >
            {items.map((item, index) => (
                <StatCard
                    key={`${item.label}-${index}`}
                    label={item.label}
                    value={item.value}
                    tone={item.tone}
                />
            ))}
        </section>
    );
}