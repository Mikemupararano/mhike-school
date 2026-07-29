type ImportStatusBadgeProps = {
    status: string;
    className?: string;
};

type StatusStyle = {
    label: string;
    classes: string;
};

const STATUS_STYLES: Record<string, StatusStyle> = {
    pending: {
        label: "Pending",
        classes:
            "border-amber-200 bg-amber-50 text-amber-800",
    },
    created: {
        label: "Created",
        classes:
            "border-slate-200 bg-slate-50 text-slate-700",
    },
    uploaded: {
        label: "Uploaded",
        classes:
            "border-blue-200 bg-blue-50 text-blue-800",
    },
    validating: {
        label: "Validating",
        classes:
            "border-indigo-200 bg-indigo-50 text-indigo-800",
    },
    validated: {
        label: "Validated",
        classes:
            "border-cyan-200 bg-cyan-50 text-cyan-800",
    },
    processing: {
        label: "Processing",
        classes:
            "border-violet-200 bg-violet-50 text-violet-800",
    },
    importing: {
        label: "Importing",
        classes:
            "border-violet-200 bg-violet-50 text-violet-800",
    },
    completed: {
        label: "Completed",
        classes:
            "border-emerald-200 bg-emerald-50 text-emerald-800",
    },
    partially_completed: {
        label: "Partially completed",
        classes:
            "border-orange-200 bg-orange-50 text-orange-800",
    },
    failed: {
        label: "Failed",
        classes:
            "border-red-200 bg-red-50 text-red-800",
    },
    cancelled: {
        label: "Cancelled",
        classes:
            "border-slate-300 bg-slate-100 text-slate-700",
    },
    archived: {
        label: "Archived",
        classes:
            "border-zinc-300 bg-zinc-100 text-zinc-700",
    },
};

function normaliseStatus(status: string): string {
    return status.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function formatUnknownStatus(status: string): string {
    const normalised = normaliseStatus(status);

    if (!normalised) {
        return "Unknown";
    }

    return normalised
        .split("_")
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

export default function ImportStatusBadge({
    status,
    className = "",
}: ImportStatusBadgeProps) {
    const normalisedStatus = normaliseStatus(status);

    const style = STATUS_STYLES[normalisedStatus] ?? {
        label: formatUnknownStatus(status),
        classes:
            "border-slate-200 bg-slate-50 text-slate-700",
    };

    return (
        <span
            className={[
                "inline-flex items-center rounded-full border px-2.5 py-1",
                "text-xs font-semibold leading-none",
                style.classes,
                className,
            ]
                .filter(Boolean)
                .join(" ")}
            title={`Import status: ${style.label}`}
        >
            {style.label}
        </span>
    );
}