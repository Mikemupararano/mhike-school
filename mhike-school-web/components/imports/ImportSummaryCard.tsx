import type { ReactNode } from "react";

type ImportSummaryCardTone =
    | "default"
    | "blue"
    | "green"
    | "amber"
    | "red"
    | "violet";

type ImportSummaryCardProps = {
    title: string;
    value: string | number;
    description?: string;
    icon?: ReactNode;
    tone?: ImportSummaryCardTone;
    className?: string;
};

const TONE_CLASSES: Record<
    ImportSummaryCardTone,
    {
        card: string;
        icon: string;
        value: string;
    }
> = {
    default: {
        card: "border-slate-200 bg-white",
        icon: "bg-slate-100 text-slate-700",
        value: "text-slate-950",
    },
    blue: {
        card: "border-blue-200 bg-blue-50/60",
        icon: "bg-blue-100 text-blue-700",
        value: "text-blue-950",
    },
    green: {
        card: "border-emerald-200 bg-emerald-50/60",
        icon: "bg-emerald-100 text-emerald-700",
        value: "text-emerald-950",
    },
    amber: {
        card: "border-amber-200 bg-amber-50/60",
        icon: "bg-amber-100 text-amber-700",
        value: "text-amber-950",
    },
    red: {
        card: "border-red-200 bg-red-50/60",
        icon: "bg-red-100 text-red-700",
        value: "text-red-950",
    },
    violet: {
        card: "border-violet-200 bg-violet-50/60",
        icon: "bg-violet-100 text-violet-700",
        value: "text-violet-950",
    },
};

export default function ImportSummaryCard({
    title,
    value,
    description,
    icon,
    tone = "default",
    className = "",
}: ImportSummaryCardProps) {
    const styles = TONE_CLASSES[tone];

    return (
        <section
            className={[
                "rounded-2xl border p-5 shadow-sm",
                styles.card,
                className,
            ]
                .filter(Boolean)
                .join(" ")}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-600">
                        {title}
                    </p>

                    <p
                        className={[
                            "mt-2 text-3xl font-bold tracking-tight",
                            styles.value,
                        ].join(" ")}
                    >
                        {value}
                    </p>

                    {description ? (
                        <p className="mt-2 text-sm leading-6 text-slate-600">
                            {description}
                        </p>
                    ) : null}
                </div>

                {icon ? (
                    <span
                        className={[
                            "flex h-11 w-11 shrink-0 items-center justify-center",
                            "rounded-xl",
                            styles.icon,
                        ].join(" ")}
                        aria-hidden="true"
                    >
                        {icon}
                    </span>
                ) : null}
            </div>
        </section>
    );
}