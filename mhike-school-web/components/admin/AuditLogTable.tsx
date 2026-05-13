'use client'

import { AuditLog } from '@/lib/services/platform-admin'

type Props = {
    logs: AuditLog[]
    loading?: boolean
}

const ACTION_COLORS: Record<string, string> = {
    CREATE: 'bg-green-100 text-green-700',
    UPDATE: 'bg-blue-100 text-blue-700',
    DELETE: 'bg-red-100 text-red-700',
    LOGIN: 'bg-purple-100 text-purple-700',
}

export default function AuditLogTable({
    logs,
    loading = false,
}: Props) {
    if (loading) {
        return (
            <div className="p-6 text-sm text-gray-500">
                Loading audit logs...
            </div>
        )
    }

    if (!logs.length) {
        return (
            <div className="p-6 text-sm text-gray-500">
                No audit logs found.
            </div>
        )
    }

    return (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            Timestamp
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            Action
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            Entity
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            Entity ID
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            Actor
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            School
                        </th>

                        <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            Metadata
                        </th>
                    </tr>
                </thead>

                <tbody className="divide-y divide-gray-200 bg-white">
                    {logs.map((log) => (
                        <tr key={log.id}>
                            <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                                {new Date(log.created_at).toLocaleString()}
                            </td>

                            <td className="px-4 py-3">
                                <span
                                    className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${ACTION_COLORS[log.action] ||
                                        'bg-gray-100 text-gray-700'
                                        }`}
                                >
                                    {log.action}
                                </span>
                            </td>

                            <td className="px-4 py-3 text-sm text-gray-700">
                                {log.entity_type}
                            </td>

                            <td className="px-4 py-3 text-sm text-gray-700">
                                {log.entity_id ?? '-'}
                            </td>

                            <td className="px-4 py-3 text-sm text-gray-700">
                                {log.actor_user_id ?? '-'}
                            </td>

                            <td className="px-4 py-3 text-sm text-gray-700">
                                {log.school_id ?? '-'}
                            </td>

                            <td className="max-w-xs truncate px-4 py-3 font-mono text-xs text-gray-600">
                                {log.metadata
                                    ? JSON.stringify(log.metadata)
                                    : '-'}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}