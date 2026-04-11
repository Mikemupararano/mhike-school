import PublicNavbar from "@/components/layout/PublicNavbar";

export default function AuthLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex min-h-screen flex-col bg-slate-100">
            <PublicNavbar />
            <main className="flex-1 w-full">{children}</main>
        </div>
    );
}