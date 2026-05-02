import { type User, UserStatus } from "@/types/user";

type UserStatusBadgeProps = {
    user: User;
};

export default function UserStatusBadge({ user }: UserStatusBadgeProps) {
    const status = user.status;

    // ✅ Highest priority: anonymised
    if (user.is_anonymised || status === UserStatus.ANONYMISED) {
        return (
            <span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700">
                Anonymised
            </span>
        );
    }

    // ✅ GDPR erasure flow
    if (
        user.erasure_requested_at != null ||
        status === UserStatus.PENDING_ERASURE
    ) {
        return (
            <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-700">
                Erasure requested
            </span>
        );
    }

    // ✅ Deactivated / inactive
    if (user.is_active === false || status === UserStatus.DEACTIVATED) {
        return (
            <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700">
                Inactive
            </span>
        );
    }

    // ✅ Default: active
    return (
        <span className="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700">
            Active
        </span>
    );
}