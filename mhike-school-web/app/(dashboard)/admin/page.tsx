"use client";

const metricCards = [
    {
        label: "Total Schools",
        value: "12",
        change: "+2 this week",
        tone: "blue",
    },
    {
        label: "Total Users",
        value: "1,284",
        change: "+85 this week",
        tone: "green",
    },
    {
        label: "Active Sessions",
        value: "342",
        change: "+18 this week",
        tone: "purple",
    },
    {
        label: "Published Content",
        value: "156",
        change: "+9 this week",
        tone: "orange",
    },
];

const recentSchools = [
    ["Kent School", "Mary Huck", "86", "Active"],
    ["Greenwood High", "John Doe", "320", "Active"],
    ["Riverside Academy", "Jane Smith", "215", "Active"],
    ["Mountain View School", "Michael Brown", "198", "Pending"],
];

const activity = [
    "New school “Kent School” was updated",
    "85 new users registered this week",
    "Mary Huck signed in as school admin",
    "Platform content was published",
];

export default function AdminPage() {
    return (
        <div className="min-h-screen bg-slate-50 p-10">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                    <h1 className="text-5xl font-black tracking-tight text-slate-950">
                        Platform Admin Dashboard
                    </h1>
                    <p className="mt-3 text-lg font-medium text-slate-600">
                        Overview of platform activity, schools, users, and content.
                    </p>
                </div>

                <button className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-base font-bold text-slate-900 shadow-sm hover:bg-slate-50">
                    This Week
                </button>
            </div>

            <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
                {metricCards.map((card) => (
                    <div
                        key={card.label}
                        className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm"
                    >
                        <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                            {card.label}
                        </p>
                        <p className="mt-3 text-4xl font-black tracking-tight text-slate-950">
                            {card.value}
                        </p>
                        <p className="mt-3 text-sm font-bold text-blue-600">
                            {card.change}
                        </p>
                    </div>
                ))}
            </div>

            <div className="mt-8 grid gap-6 xl:grid-cols-[1.35fr_1fr]">
                <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-black text-slate-950">
                            User Registrations
                        </h2>
                        <span className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-bold text-slate-700">
                            Last 7 days
                        </span>
                    </div>

                    <div className="mt-8 flex h-72 items-end gap-4 border-b border-slate-200">
                        {[42, 64, 78, 56, 48, 70, 92].map((height, index) => (
                            <div key={index} className="flex flex-1 flex-col items-center gap-3">
                                <div
                                    className="w-full rounded-t-2xl bg-blue-600"
                                    style={{ height: `${height}%` }}
                                />
                                <span className="text-xs font-bold text-slate-500">
                                    D{index + 1}
                                </span>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-black text-slate-950">
                            Recent Schools
                        </h2>
                        <span className="text-sm font-bold text-blue-600">
                            View all
                        </span>
                    </div>

                    <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200">
                        <table className="w-full text-left text-sm">
                            <thead className="bg-slate-50 text-slate-500">
                                <tr>
                                    <th className="px-4 py-3 font-black">School</th>
                                    <th className="px-4 py-3 font-black">Admin</th>
                                    <th className="px-4 py-3 font-black">Users</th>
                                    <th className="px-4 py-3 font-black">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentSchools.map(([school, admin, users, status]) => (
                                    <tr key={school} className="border-t border-slate-200">
                                        <td className="px-4 py-4 font-bold text-slate-950">
                                            {school}
                                        </td>
                                        <td className="px-4 py-4 font-semibold text-slate-700">
                                            {admin}
                                        </td>
                                        <td className="px-4 py-4 font-bold text-slate-900">
                                            {users}
                                        </td>
                                        <td className="px-4 py-4">
                                            <span
                                                className={`rounded-full px-3 py-1 text-xs font-black ${status === "Active"
                                                    ? "bg-green-100 text-green-800"
                                                    : "bg-amber-100 text-amber-800"
                                                    }`}
                                            >
                                                {status}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>
            </div>

            <div className="mt-8 grid gap-6 xl:grid-cols-[1fr_1fr]">
                <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                    <h2 className="text-2xl font-black text-slate-950">
                        Platform Health
                    </h2>

                    <div className="mt-6 space-y-5">
                        {[
                            ["API uptime", "99.98%"],
                            ["Average response", "124ms"],
                            ["Failed logins", "7"],
                        ].map(([label, value]) => (
                            <div
                                key={label}
                                className="flex items-center justify-between rounded-2xl bg-slate-50 p-5"
                            >
                                <span className="text-base font-bold text-slate-700">
                                    {label}
                                </span>
                                <span className="text-xl font-black text-slate-950">
                                    {value}
                                </span>
                            </div>
                        ))}
                    </div>
                </section>

                <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-black text-slate-950">
                            Recent Activity
                        </h2>
                        <span className="text-sm font-bold text-blue-600">
                            View all
                        </span>
                    </div>

                    <div className="mt-6 space-y-4">
                        {activity.map((item, index) => (
                            <div key={item} className="flex items-start gap-4">
                                <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-full bg-blue-50 text-sm font-black text-blue-700">
                                    {index + 1}
                                </div>
                                <div>
                                    <p className="text-base font-bold text-slate-900">
                                        {item}
                                    </p>
                                    <p className="mt-1 text-sm font-medium text-slate-500">
                                        {index + 1}h ago
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        </div>
    );
}