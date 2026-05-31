"use client";

type ParentPageStateProps = {
    loading: boolean;
    error?: string | null;
    isEmpty: boolean;
    loadingMessage?: string;
    emptyMessage?: string;
    children: React.ReactNode;
};

export default function ParentPageState({
    loading,
    error,
    isEmpty,
    loadingMessage = "Loading parent portal data...",
    emptyMessage = "No linked students found for this parent account.",
    children,
}: ParentPageStateProps) {
    if (loading) {
        return (
            <section className="rounded-2xl border bg-white p-6 text-slate-500">
                {loadingMessage}
            </section>
        );
    }

    if (error) {
        return (
            <section className="rounded-2xl border border-red-200 bg-red-50 p-6 font-semibold text-red-700">
                {error}
            </section>
        );
    }

    if (isEmpty) {
        return (
            <section className="rounded-2xl border bg-white p-6 text-slate-500">
                {emptyMessage}
            </section>
        );
    }

    return <>{children}</>;
}