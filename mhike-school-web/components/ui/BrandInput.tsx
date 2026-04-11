import type { InputHTMLAttributes } from "react";

type BrandInputProps = InputHTMLAttributes<HTMLInputElement> & {
    label: string;
};

export default function BrandInput({
    label,
    className = "",
    ...props
}: BrandInputProps) {
    return (
        <label className="grid gap-3">
            <span className="text-xl font-black text-white">{label}</span>
            <input
                className={`h-[78px] w-full rounded-[22px] border border-white/20 bg-white/10 px-6 text-xl text-white outline-none placeholder:text-white/45 shadow-[0_0_0_1px_rgba(255,255,255,0.05),inset_0_1px_2px_rgba(15,23,42,0.10)] ${className}`}
                {...props}
            />
        </label>
    );
}