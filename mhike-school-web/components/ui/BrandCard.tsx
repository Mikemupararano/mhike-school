import type { ReactNode } from "react";

type BrandCardProps = {
    children: ReactNode;
    className?: string;
};

export default function BrandCard({
    children,
    className = "",
}: BrandCardProps) {
    return (
        <section
            className={`rounded-[36px] border border-white/10 bg-brand-navy text-white shadow-brand ${className}`}
        >
            {children}
        </section>
    );
}