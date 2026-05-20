import { TimetableEntry } from "@/lib/services/timetable";

interface TimetableTableProps {
    entries: TimetableEntry[];
    emptyTitle?: string;
    emptyMessage?: string;
}

export default function TimetableTable({
    entries,
    emptyTitle = "No timetable entries found",
    emptyMessage = "No classes are scheduled for this day.",
}: TimetableTableProps) {
    const sortedEntries = [...entries].sort((a, b) => {
        return a.timetable_period_id - b.timetable_period_id;
    });

    if (sortedEntries.length === 0) {
        return (
            <div className="rounded-2xl bg-white p-10 text-center shadow-sm">
                <h2 className="text-lg font-semibold text-gray-900">
                    {emptyTitle}
                </h2>

                <p className="mt-2 text-sm text-gray-500">
                    {emptyMessage}
                </p>
            </div>
        );
    }

    return (
        <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                Period
                            </th>

                            <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                Subject
                            </th>

                            <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                Room
                            </th>

                            <th className="px-6 py-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                                Class Group
                            </th>
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-gray-100 bg-white">
                        {sortedEntries.map((entry) => (
                            <tr key={entry.id} className="hover:bg-gray-50">
                                <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                                    Period {entry.timetable_period_id}
                                </td>

                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                    {entry.title}
                                </td>

                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                    {entry.room || "-"}
                                </td>

                                <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-700">
                                    {entry.class_group_id}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}