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

export default function AdminAuditLogsPage() {
    return (
        <RoleGate allowedRoles={[UserRole.PLATFORM_ADMIN]}>
            <AdminAuditLogsContent />
        </RoleGate>
    );
}

function AdminAuditLogsContent() {
    const [logs, setLogs] = useState<AuditLogItem[]>([]);
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
            setError(err instanceof Error ? err.message : "Failed to load audit logs.");
        } finally {
            setIsLoading(false);
        }
    }

    useEffect(() => {
        void loadAuditLogs();
    }, [queryString]);

    return (
        <main className="min-h-screen bg-slate-50 p-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-4xl font-black tracking-tight text-slate-950">
                        Audit Logs
                    </h1>
                    <p className="mt-2 text-base font-medium text-slate-600">
                        Review sensitive platform activity, role changes, school actions, and
                        security events.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={loadAuditLogs}
                    className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-base font-bold text-slate-900 shadow-sm hover:bg-slate-50"
                >
                    Refresh
                </button>
            </div>

            <section className="mt-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="grid gap-4 md:grid-cols-4">
                    <input
                        value={action}
                        onChange={(event) => setAction(event.target.value)}
                        placeholder="Filter action e.g. school.created"
                        className="rounded-2xl border border-slate-300 px-4 py-3 text-base font-medium text-slate-900 outline-none placeholder:text-slate-500 focus:border-slate-500"
                    />

                    <input
                        value={entityType}
                        onChange={(event) => setEntityType(event.target.value)}
                        placeholder="Entity type e.g. user"
                        className="rounded-2xl border border-slate-300 px-4 py-3 text-base font-medium text-slate-900 outline-none placeholder:text-slate-500 focus:border-slate-500"
                    />

                    <input
                        value={schoolId}
                        onChange={(event) => setSchoolId(event.target.value)}
                        placeholder="School ID"
                        inputMode="numeric"
                        className="rounded-2xl border border-slate-300 px-4 py-3 text-base font-medium text-slate-900 outline-none placeholder:text-slate-500 focus:border-slate-500"
                    />

                    <button
                        type="button"
                        onClick={() => {
                            setAction("");
                            setEntityType("");
                            setSchoolId("");
                        }}
                        className="rounded-2xl bg-slate-950 px-5 py-3 text-base font-bold text-white hover:bg-slate-800"
                    >
                        Clear filters
                    </button>
                </div>
            </section>

            <section className="mt-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5 flex items-center justify-between">
                    <h2 className="text-2xl font-black text-slate-950">
                        Recent Events
                    </h2>
                    <span className="rounded-full bg-blue-50 px-4 py-2 text-sm font-black text-blue-700">
                        {total} total
                    </span>
                </div>

                {isLoading ? (
                    <div className="space-y-3">
                        {[1, 2, 3].map((item) => (
                            <div
                                key={item}
                                className="h-24 animate-pulse rounded-2xl bg-slate-100"
                            />
                        ))}
                    </div>
                ) : error ? (
                    <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-base font-bold text-red-700">
                        {error}
                    </div>
                ) : logs.length === 0 ? (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-8 text-base font-bold text-slate-600">
                        No audit logs found.
                    </div>
                ) : (
                    <div className="overflow-hidden rounded-2xl border border-slate-200">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 text-slate-600">
                                <tr>
                                    <th className="px-4 py-4 font-black">Action</th>
                                    <th className="px-4 py-4 font-black">Entity</th>
                                    <th className="px-4 py-4 font-black">Actor</th>
                                    <th className="px-4 py-4 font-black">School</th>
                                    <th className="px-4 py-4 font-black">Date</th>
                                    <th className="px-4 py-4 font-black">Metadata</th>
                                </tr>
                            </thead>

                            <tbody>
                                {logs.map((log) => (
                                    <tr key={log.id} className="border-t border-slate-200">
                                        <td className="px-4 py-4">
                                            <span className="rounded-full bg-blue-50 px-3 py-1.5 text-sm font-black capitalize text-blue-800">
                                                {formatAction(log.action)}
                                            </span>
                                        </td>

                                        <td className="px-4 py-4 font-bold text-slate-900">
                                            {log.entity_type}
                                            {log.entity_id ? (
                                                <span className="ml-1 text-slate-500">#{log.entity_id}</span>
                                            ) : null}
                                        </td>

                                        <td className="px-4 py-4 font-semibold text-slate-700">
                                            {log.actor_email || "System"}
                                        </td>

                                        <td className="px-4 py-4 font-semibold text-slate-700">
                                            {log.school_name || log.school_id || "Global"}
                                        </td>

                                        <td className="px-4 py-4 font-semibold text-slate-700">
                                            {formatDate(log.created_at)}
                                        </td>

                                        <td className="px-4 py-4">
                                            <pre className="max-w-xs overflow-auto rounded-xl bg-slate-50 p-3 text-xs font-semibold text-slate-700">
                                                {JSON.stringify(log.metadata ?? {}, null, 2)}
                                            </pre>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
        </main>
    );
}