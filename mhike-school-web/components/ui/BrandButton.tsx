import type { ButtonHTMLAttributes, ReactNode } from "react";

type BrandButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
    children: ReactNode;
    variant?: "primary" | "secondary";
    fullWidth?: boolean;
};

export default function BrandButton({
    children,
    variant = "primary",
    fullWidth = false,
    className = "",
    type = "button",
    ...props
}: BrandButtonProps) {
    const base =
        "rounded-[22px] font-black transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-75";
    const size = "h-[74px] px-6 text-xl";
    const width = fullWidth ? "w-full" : "";
    const styles =
        variant === "primary"
            ? "border-none bg-gradient-to-r from-brand-blueHover to-brand-blue text-white shadow-glow hover:-translate-y-0.5"
            : "border border-white/10 bg-white/10 text-white hover:bg-white/15";

    return (
        <button
            type={type}
            className={`${base} ${size} ${width} ${styles} ${className}`}
            {...props}
        >
            {children}
        </button>
    );
}