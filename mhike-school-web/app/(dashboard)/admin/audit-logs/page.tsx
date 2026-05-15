"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { apiGet } from "@/lib/api";

type AuditLogItem = {
    id: number;
    action: string;
    entity_type: string;
    entity_id: number | null;
    actor_id: number | null;
    actor_email: string | null;
    target_user_id: number | null;
    target_user_email: string | null;
    school_id: number | null;
    school_name: string | null;
    metadata: Record<string, unknown> | null;
    created_at: string;
};

type AuditLogsResponse = {
    items: AuditLogItem[];
    total: number;
    skip: number;
    limit: number;
};

const ACTION_STYLES: Record<string, string> = {
    create: "bg-green-50 text-green-800",
    created: "bg-green-50 text-green-800",
    update: "bg-blue-50 text-blue-800",
    updated: "bg-blue-50 text-blue-800",
    delete: "bg-red-50 text-red-800",
    deleted: "bg-red-50 text-red-800",
    login: "bg-purple-50 text-purple-800",
    logout: "bg-purple-50 text-purple-800",
};

const ACTION_OPTIONS = [
    "",
    "user_created",
    "school_created",
    "role_assigned",
    "login",
    "logout",
    "create",
    "update",
    "delete",
];

function formatDate(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function formatAction(action: string) {
    return action.replaceAll("_", " ").replaceAll(".", " ");
}

function getActionStyle(action: string) {
    const normalized = action.toLowerCase();

    const matchedKey = Object.keys(ACTION_STYLES).find((key) =>
        normalized.includes(key),
    );

    return matchedKey
        ? ACTION_STYLES[matchedKey]
        : "bg-slate-100 text-slate-800";
}

function metadataPreview(metadata: Record<string, unknown> | null) {
    if (!metadata || Object.keys(metadata).length === 0) {
        return "—";
    }

    return Object.entries(metadata)
        .slice(0, 3)
        .map(([key, value]) => `${key}: ${String(value)}`)
        .join(" | ");
}

function escapeCsvValue(value: unknown) {
    return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

export default function AdminAuditLogsPage() {
    return <AdminAuditLogsContent />;
}

function AdminAuditLogsContent() {
    const [logs, setLogs] = useState<AuditLogItem[]>([]);
    const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

    const [total, setTotal] = useState(0);
    const [action, setAction] = useState("");
    const [entityType, setEntityType] = useState("");
    const [schoolId, setSchoolId] = useState("");
    const [actorEmail, setActorEmail] = useState("");
    const [targetEmail, setTargetEmail] = useState("");
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");

    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);

    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const canGoPrevious = page > 1;
    const canGoNext = page < totalPages;

    const queryString = useMemo(() => {
        const params = new URLSearchParams();

        if (action.trim()) params.set("action", action.trim());
        if (entityType.trim()) params.set("entity_type", entityType.trim());
        if (schoolId.trim()) params.set("school_id", schoolId.trim());
        if (actorEmail.trim()) params.set("actor_email", actorEmail.trim());
        if (targetEmail.trim()) {
            params.set("target_user_email", targetEmail.trim());
        }
        if (dateFrom) params.set("date_from", dateFrom);
        if (dateTo) params.set("date_to", dateTo);

        params.set("limit", String(pageSize));
        params.set("offset", String((page - 1) * pageSize));

        return params.toString();
    }, [
        action,
        entityType,
        schoolId,
        actorEmail,
        targetEmail,
        dateFrom,
        dateTo,
        page,
        pageSize,
    ]);

    const loadAuditLogs = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);

            const endpoint = queryString
                ? `/admin/audit-logs?${queryString}`
                : "/admin/audit-logs";

            const data = await apiGet<AuditLogsResponse>(endpoint);

            setLogs(data.items);
            setTotal(data.total);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Failed to load audit logs.",
            );
        } finally {
            setIsLoading(false);
        }
    }, [queryString]);

    useEffect(() => {
        void loadAuditLogs();
    }, [loadAuditLogs]);

    function resetFilters() {
        setAction("");
        setEntityType("");
        setSchoolId("");
        setActorEmail("");
        setTargetEmail("");
        setDateFrom("");
        setDateTo("");
        setPage(1);
    }

    function handlePageSizeChange(value: string) {
        setPageSize(Number(value));
        setPage(1);
    }

    function downloadFile(content: string, filename: string, type: string) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.setAttribute("download", filename);

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        URL.revokeObjectURL(url);
    }

    function exportToCsv() {
        if (logs.length === 0) return;

        const headers = [
            "ID",
            "Action",
            "Entity Type",
            "Entity ID",
            "Actor Email",
            "Target Email",
            "School",
            "Created At",
            "Metadata",
        ];

        const rows = logs.map((log) => [
            log.id,
            log.action,
            log.entity_type,
            log.entity_id ?? "",
            log.actor_email ?? "",
            log.target_user_email ?? "",
            log.school_name ?? log.school_id ?? "Global",
            log.created_at,
            log.metadata ? JSON.stringify(log.metadata) : "",
        ]);

        const csvContent = [
            headers.map(escapeCsvValue).join(","),
            ...rows.map((row) => row.map(escapeCsvValue).join(",")),
        ].join("\n");

        downloadFile(
            csvContent,
            `audit-logs-page-${page}.csv`,
            "text/csv;charset=utf-8;",
        );
    }

    function exportToJson() {
        if (logs.length === 0) return;

        const jsonContent = JSON.stringify(
            {
                exported_at: new Date().toISOString(),
                page,
                page_size: pageSize,
                total,
                filters: {
                    action,
                    entity_type: entityType,
                    school_id: schoolId,
                    actor_email: actorEmail,
                    target_email: targetEmail,
                    date_from: dateFrom,
                    date_to: dateTo,
                },
                items: logs,
            },
            null,
            2,
        );

        downloadFile(
            jsonContent,
            `audit-logs-page-${page}.json`,
            "application/json;charset=utf-8;",
        );
    }

    return (
        <main className="space-y-6 p-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Audit Logs
                    </h1>

                    <p className="mt-2 text-slate-500">
                        Review platform activity, role changes, school actions,
                        and security events.
                    </p>
                </div>

                <div className="flex flex-wrap gap-3">
                    <button
                        type="button"
                        onClick={exportToCsv}
                        disabled={logs.length === 0}
                        className="rounded-xl bg-emerald-600 px-5 py-3 font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Export CSV
                    </button>

                    <button
                        type="button"
                        onClick={exportToJson}
                        disabled={logs.length === 0}
                        className="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Export JSON
                    </button>

                    <button
                        type="button"
                        onClick={() => void loadAuditLogs()}
                        className="rounded-xl border bg-white px-5 py-3 font-semibold hover:bg-slate-50"
                    >
                        Refresh
                    </button>
                </div>
            </div>

            <section className="rounded-2xl border bg-white p-5">
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-8">
                    <select
                        value={action}
                        onChange={(event) => {
                            setAction(event.target.value);
                            setPage(1);
                        }}
                        className="rounded-xl border bg-white px-4 py-3"
                    >
                        <option value="">All actions</option>

                        {ACTION_OPTIONS.filter(Boolean).map((option) => (
                            <option key={option} value={option}>
                                {formatAction(option)}
                            </option>
                        ))}
                    </select>

                    <input
                        value={entityType}
                        onChange={(event) => {
                            setEntityType(event.target.value);
                            setPage(1);
                        }}
                        placeholder="Entity e.g. user"
                        className="rounded-xl border px-4 py-3"
                    />

                    <input
                        value={schoolId}
                        onChange={(event) => {
                            setSchoolId(event.target.value);
                            setPage(1);
                        }}
                        placeholder="School ID"
                        inputMode="numeric"
                        className="rounded-xl border px-4 py-3"
                    />

                    <input
                        value={actorEmail}
                        onChange={(event) => {
                            setActorEmail(event.target.value);
                            setPage(1);
                        }}
                        placeholder="Actor email"
                        className="rounded-xl border px-4 py-3"
                    />

                    <input
                        value={targetEmail}
                        onChange={(event) => {
                            setTargetEmail(event.target.value);
                            setPage(1);
                        }}
                        placeholder="Target email"
                        className="rounded-xl border px-4 py-3"
                    />

                    <input
                        type="date"
                        value={dateFrom}
                        onChange={(event) => {
                            setDateFrom(event.target.value);
                            setPage(1);
                        }}
                        className="rounded-xl border px-4 py-3"
                    />

                    <input
                        type="date"
                        value={dateTo}
                        onChange={(event) => {
                            setDateTo(event.target.value);
                            setPage(1);
                        }}
                        className="rounded-xl border px-4 py-3"
                    />

                    <button
                        type="button"
                        onClick={resetFilters}
                        className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800"
                    >
                        Clear Filters
                    </button>
                </div>
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-slate-950">
                            Recent Events
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            Page {page} of {totalPages}
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <label className="text-sm font-semibold text-slate-600">
                            Page size
                        </label>

                        <select
                            value={pageSize}
                            onChange={(event) =>
                                handlePageSizeChange(event.target.value)
                            }
                            className="rounded-lg border bg-white px-3 py-2 text-sm"
                        >
                            <option value={10}>10</option>
                            <option value={25}>25</option>
                            <option value={50}>50</option>
                            <option value={100}>100</option>
                        </select>

                        <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font-bold text-blue-700">
                            {total} total
                        </span>
                    </div>
                </div>

                {isLoading ? (
                    <div className="space-y-3">
                        {[1, 2, 3].map((item) => (
                            <div
                                key={item}
                                className="h-20 animate-pulse rounded-xl bg-slate-100"
                            />
                        ))}
                    </div>
                ) : error ? (
                    <div className="rounded-xl border border-red-200 bg-red-50 p-4 font-semibold text-red-700">
                        {error}
                    </div>
                ) : logs.length === 0 ? (
                    <div className="rounded-xl border bg-slate-50 p-8 text-slate-500">
                        No audit logs found.
                    </div>
                ) : (
                    <>
                        <div className="overflow-x-auto rounded-xl border">
                            <table className="w-full text-left text-sm">
                                <thead className="sticky top-0 z-10 bg-slate-50 text-slate-600">
                                    <tr>
                                        <th className="px-4 py-4 font-bold">
                                            Action
                                        </th>
                                        <th className="px-4 py-4 font-bold">
                                            Entity
                                        </th>
                                        <th className="px-4 py-4 font-bold">
                                            Actor
                                        </th>
                                        <th className="px-4 py-4 font-bold">
                                            Target
                                        </th>
                                        <th className="px-4 py-4 font-bold">
                                            School
                                        </th>
                                        <th className="px-4 py-4 font-bold">
                                            Date
                                        </th>
                                        <th className="px-4 py-4 font-bold">
                                            Metadata
                                        </th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {logs.map((log) => (
                                        <tr key={log.id} className="border-t">
                                            <td className="px-4 py-4">
                                                <span
                                                    className={`rounded-full px-3 py-1.5 font-bold capitalize ${getActionStyle(
                                                        log.action,
                                                    )}`}
                                                >
                                                    {formatAction(log.action)}
                                                </span>
                                            </td>

                                            <td className="px-4 py-4 font-semibold">
                                                {log.entity_type}
                                                {log.entity_id !== null ? (
                                                    <span className="ml-1 text-slate-500">
                                                        #{log.entity_id}
                                                    </span>
                                                ) : null}
                                            </td>

                                            <td className="px-4 py-4 text-slate-700">
                                                {log.actor_email ?? "System"}
                                            </td>

                                            <td className="px-4 py-4 text-slate-700">
                                                {log.target_user_email ?? "—"}
                                            </td>

                                            <td className="px-4 py-4 text-slate-700">
                                                {log.school_name ??
                                                    log.school_id ??
                                                    "Global"}
                                            </td>

                                            <td className="px-4 py-4 text-slate-700">
                                                {formatDate(log.created_at)}
                                            </td>

                                            <td className="px-4 py-4">
                                                <button
                                                    type="button"
                                                    onClick={() =>
                                                        setSelectedLog(log)
                                                    }
                                                    className="max-w-xs truncate rounded-lg bg-slate-100 px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-200"
                                                >
                                                    {metadataPreview(
                                                        log.metadata,
                                                    )}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <p className="text-sm text-slate-500">
                                Showing {(page - 1) * pageSize + 1}-
                                {Math.min(page * pageSize, total)} of {total}
                            </p>

                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    disabled={!canGoPrevious || isLoading}
                                    onClick={() =>
                                        setPage((current) =>
                                            Math.max(1, current - 1),
                                        )
                                    }
                                    className="rounded-lg border px-4 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    Previous
                                </button>

                                <button
                                    type="button"
                                    disabled={!canGoNext || isLoading}
                                    onClick={() =>
                                        setPage((current) => current + 1)
                                    }
                                    className="rounded-lg border px-4 py-2 font-semibold disabled:cursor-not-allowed disabled:opacity-50"
                                >
                                    Next
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </section>

            {selectedLog ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
                    <div className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-xl">
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <h3 className="text-xl font-bold">
                                    Audit Event #{selectedLog.id}
                                </h3>

                                <p className="mt-1 text-sm text-slate-500">
                                    {formatAction(selectedLog.action)} ·{" "}
                                    {formatDate(selectedLog.created_at)}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={() => setSelectedLog(null)}
                                className="rounded-lg border px-3 py-2 font-semibold hover:bg-slate-50"
                            >
                                Close
                            </button>
                        </div>

                        <pre className="mt-5 max-h-[60vh] overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-50">
                            {JSON.stringify(selectedLog, null, 2)}
                        </pre>
                    </div>
                </div>
            ) : null}
        </main>
    );
}