import Image from "next/image";
import Link from "next/link";
import { brand, brandColors } from "@/lib/brand";

type BrandLogoProps = {
    href?: string;
    showText?: boolean;
    iconSize?: number;
    textSizeClass?: string;
    className?: string;
    priority?: boolean;
};

export default function BrandLogo({
    href = "/",
    showText = true,
    iconSize = 52,
    textSizeClass = "text-2xl sm:text-3xl",
    className = "",
    priority = true,
}: BrandLogoProps) {
    const content = (
        <div className={`flex items-center gap-3 sm:gap-4 ${className}`}>
            <Image
                src="/logo-icon.svg"
                alt={brand.name}
                width={iconSize}
                height={iconSize}
                priority={priority}
                className="h-11 w-11 shrink-0 sm:h-[52px] sm:w-[52px]"
                style={{
                    filter: `drop-shadow(0 4px 16px ${brandColors.blue}73)`,
                }}
            />

            {showText ? (
                <span
                    className={`${textSizeClass} whitespace-nowrap font-extrabold leading-none tracking-tight text-white`}
                >
                    {brand.shortName}{" "}
                    <span style={{ color: brandColors.gold }}>School</span>
                </span>
            ) : null}
        </div>
    );

    return (
        <Link
            href={href}
            aria-label={`${brand.name} home`}
            className="inline-flex items-center"
        >
            {content}
        </Link>
    );
}