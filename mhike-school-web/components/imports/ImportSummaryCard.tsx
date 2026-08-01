import type { ReactNode } from "react";

export type ImportSummaryCardTone =
    | "default"
    | "blue"
    | "green"
    | "amber"
    | "red"
    | "violet";

export type ImportSummaryCardProps = {
    /**
     * Preferred heading shown above the summary value.
     */
    title?: string;

    /**
     * Compatibility alias for older callers.
     * New code should prefer ``title``.
     */
    label?: string;

    /**
     * Preferred value rendered by the card.
     */
    value?: string | number;

    /**
     * Compatibility alias for older callers.
     * New code should prefer ``value``.
     */
    count?: string | number;

    description?: string;
    icon?: ReactNode;
    tone?: ImportSummaryCardTone;
    className?: string;

    /**
     * Optional accessible label for the complete card.
     */
    ariaLabel?: string;
};

type ToneClasses = {
    card: string;
    icon: string;
    value: string;
};

const TONE_CLASSES: Record<
    ImportSummaryCardTone,
    ToneClasses
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

function resolveTitle(
    title: string | undefined,
    label: string | undefined,
): string {
    const resolvedTitle =
        title?.trim() ||
        label?.trim();

    return resolvedTitle || "Summary";
}

function resolveValue(
    value: string | number | undefined,
    count: string | number | undefined,
): string | number {
    return value ?? count ?? 0;
}

function formatValue(
    value: string | number,
): string {
    if (
        typeof value === "number" &&
        Number.isFinite(value)
    ) {
        return new Intl.NumberFormat(
            "en-GB",
        ).format(value);
    }

    return String(value);
}

export default function ImportSummaryCard({
    title,
    label,
    value,
    count,
    description,
    icon,
    tone = "default",
    className = "",
    ariaLabel,
}: ImportSummaryCardProps) {
    const styles =
        TONE_CLASSES[tone] ??
        TONE_CLASSES.default;

    const resolvedTitle =
        resolveTitle(
            title,
            label,
        );

    const resolvedValue =
        resolveValue(
            value,
            count,
        );

    const formattedValue =
        formatValue(
            resolvedValue,
        );

    const resolvedAriaLabel =
        ariaLabel?.trim() ||
        `${resolvedTitle}: ${formattedValue}`;

    return (
        <article
            className={[
                "rounded-2xl border p-5 shadow-sm",
                styles.card,
                className,
            ]
                .filter(Boolean)
                .join(" ")}
            aria-label={resolvedAriaLabel}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-600">
                        {resolvedTitle}
                    </p>

                    <p
                        className={[
                            "mt-2 break-words text-3xl font-bold tracking-tight",
                            styles.value,
                        ].join(" ")}
                    >
                        {formattedValue}
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
        </article>
    );
}
