"use client";

import { useEffect, useMemo, useState } from "react";

import RoleGate from "@/components/auth/RoleGate";
import { apiGet } from "@/lib/api";
import { UserRole } from "@/types/user";

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

function formatDate(value: string) {
    return new Intl.DateTimeFormat("en-GB", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

function formatAction(action: string) {
    return action.replaceAll("_", " ").replaceAll(".", " ");
}

function metadataPreview(metadata: Record<string, unknown> | null) {
    if (!metadata) return "—";

    const entries = Object.entries(metadata);

    if (entries.length === 0) return "—";

    return entries
        .slice(0, 3)
        .map(([key, value]) => `${key}: ${String(value)}`)
        .join(" | ");
}

export default function AdminAuditLogsPage() {
    return (
        <RoleGate allowedRoles={[UserRole.PLATFORM_ADMIN]}>
            <AdminAuditLogsContent />
        </RoleGate>
    );
}

function AdminAuditLogsContent() {
    const [logs, setLogs] = useState<AuditLogItem[]>([]);
    const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

    const [total, setTotal] = useState(0);
    const [action, setAction] = useState("");
    const [entityType, setEntityType] = useState("");
    const [schoolId, setSchoolId] = useState("");

    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const queryString = useMemo(() => {
        const params = new URLSearchParams();

        if (action.trim()) params.set("action", action.trim());
        if (entityType.trim()) params.set("entity_type", entityType.trim());
        if (schoolId.trim()) params.set("school_id", schoolId.trim());

        params.set("limit", "50");

        return params.toString();
    }, [action, entityType, schoolId]);

    async function loadAuditLogs() {
        try {
            setIsLoading(true);
            setError(null);

            const data = await apiGet<AuditLogsResponse>(
                `/admin/audit-logs?${queryString}`,
            );

            setLogs(data.items);
            setTotal(data.total);
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Failed to load audit logs.",
            );
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadAuditLogs();
    }, [queryString]);

    return (
        <main className="p-8 space-y-6">
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

                <button
                    type="button"
                    onClick={loadAuditLogs}
                    className="rounded-xl border bg-white px-5 py-3 font-semibold hover:bg-slate-50"
                >
                    Refresh
                </button>
            </div>

            <section className="rounded-2xl border bg-white p-5">
                <div className="grid gap-4 md:grid-cols-4">
                    <input
                        value={action}
                        onChange={(event) => setAction(event.target.value)}
                        placeholder="Action e.g. user_created"
                        className="rounded-xl border px-4 py-3"
                    />

                    <input
                        value={entityType}
                        onChange={(event) => setEntityType(event.target.value)}
                        placeholder="Entity e.g. user"
                        className="rounded-xl border px-4 py-3"
                    />

                    <input
                        value={schoolId}
                        onChange={(event) => setSchoolId(event.target.value)}
                        placeholder="School ID"
                        inputMode="numeric"
                        className="rounded-xl border px-4 py-3"
                    />

                    <button
                        type="button"
                        onClick={() => {
                            setAction("");
                            setEntityType("");
                            setSchoolId("");
                        }}
                        className="rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800"
                    >
                        Clear Filters
                    </button>
                </div>
            </section>

            <section className="rounded-2xl border bg-white p-6">
                <div className="mb-5 flex items-center justify-between">
                    <h2 className="text-xl font-bold text-slate-950">
                        Recent Events
                    </h2>

                    <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font-bold text-blue-700">
                        {total} total
                    </span>
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
                    <div className="overflow-hidden rounded-xl border">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 text-slate-600">
                                <tr>
                                    <th className="px-4 py-4 font-bold">Action</th>
                                    <th className="px-4 py-4 font-bold">Entity</th>
                                    <th className="px-4 py-4 font-bold">Actor</th>
                                    <th className="px-4 py-4 font-bold">Target</th>
                                    <th className="px-4 py-4 font-bold">School</th>
                                    <th className="px-4 py-4 font-bold">Date</th>
                                    <th className="px-4 py-4 font-bold">Metadata</th>
                                </tr>
                            </thead>

                            <tbody>
                                {logs.map((log) => (
                                    <tr key={log.id} className="border-t">
                                        <td className="px-4 py-4">
                                            <span className="rounded-full bg-blue-50 px-3 py-1.5 font-bold capitalize text-blue-800">
                                                {formatAction(log.action)}
                                            </span>
                                        </td>

                                        <td className="px-4 py-4 font-semibold">
                                            {log.entity_type}
                                            {log.entity_id ? (
                                                <span className="ml-1 text-slate-500">
                                                    #{log.entity_id}
                                                </span>
                                            ) : null}
                                        </td>

                                        <td className="px-4 py-4 text-slate-700">
                                            {log.actor_email || "System"}
                                        </td>

                                        <td className="px-4 py-4 text-slate-700">
                                            {log.target_user_email || "—"}
                                        </td>

                                        <td className="px-4 py-4 text-slate-700">
                                            {log.school_name || log.school_id || "Global"}
                                        </td>

                                        <td className="px-4 py-4 text-slate-700">
                                            {formatDate(log.created_at)}
                                        </td>

                                        <td className="px-4 py-4">
                                            <button
                                                type="button"
                                                onClick={() => setSelectedLog(log)}
                                                className="max-w-xs truncate rounded-lg bg-slate-100 px-3 py-2 text-left text-xs font-semibold text-slate-700 hover:bg-slate-200"
                                            >
                                                {metadataPreview(log.metadata)}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
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