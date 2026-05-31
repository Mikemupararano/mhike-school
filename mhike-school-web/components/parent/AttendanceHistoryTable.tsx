"use client";

import type { StudentAttendanceHistoryRecord } from "@/lib/parent";

type AttendanceHistoryTableProps = {
    records: StudentAttendanceHistoryRecord[];
    emptyMessage?: string;
};

function formatStatus(status: StudentAttendanceHistoryRecord["status"]) {
    return status.replaceAll("_", " ");
}

function getStatusBadge(status: StudentAttendanceHistoryRecord["status"]) {
    switch (status) {
        case "present":
            return "bg-green-100 text-green-700";

        case "late":
            return "bg-yellow-100 text-yellow-700";

        case "authorised_absence":
            return "bg-blue-100 text-blue-700";

        case "unauthorised_absence":
            return "bg-red-100 text-red-700";

        default:
            return "bg-slate-100 text-slate-700";
    }
}

export default function AttendanceHistoryTable({
    records,
    emptyMessage = "No attendance history found.",
}: AttendanceHistoryTableProps) {
    if (records.length === 0) {
        return (
            <p className="mt-6 text-slate-500">
                {emptyMessage}
            </p>
        );
    }

    return (
        <div className="mt-6 overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead className="border-b text-slate-500">
                    <tr>
                        <th className="py-3 pr-4">Date</th>
                        <th className="py-3 pr-4">Session</th>
                        <th className="py-3 pr-4">Class</th>
                        <th className="py-3 pr-4">Status</th>
                        <th className="py-3 pr-4">Notes</th>
                    </tr>
                </thead>

                <tbody>
                    {records.map((record) => (
                        <tr
                            key={record.record_id}
                            className="border-b last:border-0"
                        >
                            <td className="py-4 pr-4 font-semibold">
                                {record.session_date}
                            </td>

                            <td className="py-4 pr-4 uppercase">
                                {record.session_type}
                            </td>

                            <td className="py-4 pr-4">
                                {record.class_name ??
                                    `Class ${record.class_group_id}`}
                            </td>

                            <td className="py-4 pr-4">
                                <span
                                    className={`rounded-full px-3 py-1 text-xs font-bold capitalize ${getStatusBadge(
                                        record.status,
                                    )}`}
                                >
                                    {formatStatus(record.status)}
                                </span>
                            </td>

                            <td className="py-4 pr-4">
                                {record.notes ?? "—"}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}