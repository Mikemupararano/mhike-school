export default function AdminNotificationsPage() {
    return (
        <div className="p-6">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">
                    Notification Monitoring
                </h1>

                <p className="mt-2 text-sm text-gray-500">
                    Monitor platform-wide notification delivery, failures, and
                    school-level activity.
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
                {[
                    ["Notifications sent", "0"],
                    ["Failed deliveries", "0"],
                    ["Pending queue", "0"],
                    ["Active schools", "3"],
                ].map(([label, value]) => (
                    <div
                        key={label}
                        className="rounded-2xl bg-white p-5 shadow-sm"
                    >
                        <p className="text-sm text-gray-500">{label}</p>
                        <p className="mt-2 text-2xl font-bold text-gray-900">
                            {value}
                        </p>
                    </div>
                ))}
            </div>

            <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-gray-900">
                    Recent Notification Activity
                </h2>

                <p className="mt-2 text-sm text-gray-500">
                    Delivery logs and notification events will appear here once
                    monitoring endpoints are connected.
                </p>
            </div>
        </div>
    );
}