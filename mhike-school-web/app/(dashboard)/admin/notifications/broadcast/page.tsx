import BroadcastNotificationForm from "@/components/notifications/BroadcastNotificationForm";

export default function BroadcastNotificationPage() {
    return (
        <div className="mx-auto max-w-4xl space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-gray-900">
                    Broadcast Notifications
                </h1>

                <p className="mt-2 text-gray-600">
                    Send announcements to teachers, students, parents,
                    or the entire school.
                </p>
            </div>

            <BroadcastNotificationForm />
        </div>
    );
}