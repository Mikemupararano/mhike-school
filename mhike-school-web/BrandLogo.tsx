import Image from "next/image";
import { brand } from "@/lib/brand";

type BrandLogoProps = {
    className?: string;
    variant?: "navbar" | "light" | "dark" | "icon";
    size?: "sm" | "md" | "lg";
    showTagline?: boolean;
};

const sizeMap = {
    sm: { width: 120, height: 32, icon: 28 },
    md: { width: 148, height: 40, icon: 36 },
    lg: { width: 172, height: 46, icon: 42 },
} as const;

export default function BrandLogo({
    className = "",
    variant = "navbar",
    size = "md",
    showTagline = false,
}: BrandLogoProps) {
    const dimensions = sizeMap[size];

    const srcMap = {
        navbar: "/branding/logo-navbar.svg",
        light: "/branding/logo-light.svg",
        dark: "/branding/logo-dark.svg",
        icon: "/branding/icon.svg",
    } as const;

    return (
        <div className={`flex items-center gap-3 ${className}`}>
            <Image
                src={srcMap[variant]}
                alt={brand.name}
                width={variant === "icon" ? dimensions.icon : dimensions.width}
                height={variant === "icon" ? dimensions.icon : dimensions.height}
                className={variant === "icon" ? "h-auto w-7 sm:w-8" : "h-8 w-auto"}
                priority
            />

            {showTagline && (
                <span className="text-xs font-medium text-slate-300">
                    {brand.tagline}
                </span>
            )}
        </div>
    );
}