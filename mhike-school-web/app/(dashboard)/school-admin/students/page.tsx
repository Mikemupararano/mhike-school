"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

type Student = {
    id: number;
    fullName: string;
    email: string;
    className: string;
    yearGroup: string;
    status: "Active" | "Pending" | "Suspended";
};

const mockStudents: Student[] = [
    {
        id: 1,
        fullName: "John Gibbs",
        email: "john.gibbs@school.com",
        className: "Form 1A",
        yearGroup: "Year 7",
        status: "Active",
    },
    {
        id: 2,
        fullName: "Mary Huck",
        email: "mary.huck@school.com",
        className: "Form 2B",
        yearGroup: "Year 8",
        status: "Active",
    },
    {
        id: 3,
        fullName: "Tariro Moyo",
        email: "tariro.moyo@school.com",
        className: "Form 3A",
        yearGroup: "Year 9",
        status: "Pending",
    },
    {
        id: 4,
        fullName: "Blessing Ncube",
        email: "blessing.ncube@school.com",
        className: "Form 4C",
        yearGroup: "Year 10",
        status: "Suspended",
    },
];

function statusClasses(status: Student["status"]) {
    switch (status) {
        case "Active":
            return "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200";
        case "Pending":
            return "bg-amber-50 text-amber-700 ring-1 ring-amber-200";
        case "Suspended":
            return "bg-rose-50 text-rose-700 ring-1 ring-rose-200";
        default:
            return "bg-slate-100 text-slate-700 ring-1 ring-slate-200";
    }
}

export default function SchoolAdminStudentsPage() {
    const [query, setQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState("All");

    const filteredStudents = useMemo(() => {
        return mockStudents.filter((student) => {
            const matchesQuery =
                student.fullName.toLowerCase().includes(query.toLowerCase()) ||
                student.email.toLowerCase().includes(query.toLowerCase()) ||
                student.className.toLowerCase().includes(query.toLowerCase()) ||
                student.yearGroup.toLowerCase().includes(query.toLowerCase());

            const matchesStatus =
                statusFilter === "All" || student.status === statusFilter;

            return matchesQuery && matchesStatus;
        });
    }, [query, statusFilter]);

    return (
        <div className="p-6 sm:p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                        Students
                    </h1>
                    <p className="mt-2 text-base text-slate-600 sm:text-lg">
                        Manage student records, enrolment status, and class placement.
                    </p>
                </div>

                <Link
                    href="/school-admin/students/new"
                    className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
                >
                    Add student
                </Link>
            </div>

            <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="w-full lg:max-w-md">
                        <label htmlFor="student-search" className="sr-only">
                            Search students
                        </label>
                        <input
                            id="student-search"
                            type="text"
                            placeholder="Search by name, email, class, or year group"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                        />
                    </div>

                    <div className="flex flex-col gap-3 sm:flex-row">
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                        >
                            <option value="All">All statuses</option>
                            <option value="Active">Active</option>
                            <option value="Pending">Pending</option>
                            <option value="Suspended">Suspended</option>
                        </select>
                    </div>
                </div>

                <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-slate-600">
                    <span className="rounded-full bg-slate-100 px-3 py-1.5 font-medium text-slate-700">
                        {filteredStudents.length} student
                        {filteredStudents.length === 1 ? "" : "s"}
                    </span>
                </div>
            </div>

            <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200">
                        <thead className="bg-slate-50">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                    Student
                                </th>
                                <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                    Class
                                </th>
                                <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                    Year group
                                </th>
                                <th className="px-6 py-4 text-left text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                    Status
                                </th>
                                <th className="px-6 py-4 text-right text-xs font-bold uppercase tracking-[0.14em] text-slate-500">
                                    Actions
                                </th>
                            </tr>
                        </thead>

                        <tbody className="divide-y divide-slate-200">
                            {filteredStudents.length > 0 ? (
                                filteredStudents.map((student) => (
                                    <tr key={student.id} className="hover:bg-slate-50/80">
                                        <td className="px-6 py-5 align-top">
                                            <div className="font-semibold text-slate-900">
                                                {student.fullName}
                                            </div>
                                            <div className="mt-1 text-sm text-slate-500">
                                                {student.email}
                                            </div>
                                        </td>

                                        <td className="px-6 py-5 text-sm font-medium text-slate-700">
                                            {student.className}
                                        </td>

                                        <td className="px-6 py-5 text-sm font-medium text-slate-700">
                                            {student.yearGroup}
                                        </td>

                                        <td className="px-6 py-5">
                                            <span
                                                className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusClasses(
                                                    student.status
                                                )}`}
                                            >
                                                {student.status}
                                            </span>
                                        </td>

                                        <td className="px-6 py-5 text-right">
                                            <div className="flex justify-end gap-2">
                                                <Link
                                                    href={`/school-admin/students/${student.id}`}
                                                    className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                                                >
                                                    View
                                                </Link>
                                                <Link
                                                    href={`/school-admin/students/${student.id}/edit`}
                                                    className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
                                                >
                                                    Edit
                                                </Link>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={5} className="px-6 py-14 text-center">
                                        <div className="text-lg font-semibold text-slate-900">
                                            No students found
                                        </div>
                                        <p className="mt-2 text-sm text-slate-500">
                                            Try changing your search or filter settings.
                                        </p>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}