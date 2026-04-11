export default function BrandLogo({ className = "" }: { className?: string }) {
    return (
        <div className={`flex items-center gap-2 ${className}`}>
            {/* Light/Dark switching */}
            <img
                src="/logo-light.svg"
                alt="Mhike School"
                className="block dark:hidden h-8 w-auto"
            />
            <img
                src="/logo-dark.svg"
                alt="Mhike School"
                className="hidden dark:block h-8 w-auto"
            />
        </div>
    )
}