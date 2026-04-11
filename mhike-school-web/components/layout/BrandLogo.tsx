import Image from "next/image";
import Link from "next/link";

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
                alt="Mhike School"
                width={iconSize}
                height={iconSize}
                className="h-11 w-11 shrink-0 sm:h-[52px] sm:w-[52px] drop-shadow-[0_4px_16px_rgba(59,130,246,0.45)]"
                priority={priority}
            />

            {showText ? (
                <span
                    className={`${textSizeClass} leading-none font-extrabold tracking-tight text-white whitespace-nowrap`}
                >
                    Mhike <span className="text-[#f6c453]">School</span>
                </span>
            ) : null}
        </div>
    );

    return (
        <Link
            href={href}
            aria-label="Mhike School home"
            className="inline-flex items-center"
        >
            {content}
        </Link>
    );
}