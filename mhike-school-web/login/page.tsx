import PublicNavbar from "@/components/layout/PublicNavbar";

export default function AuthLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-slate-100">
            <PublicNavbar />
            <main className="min-h-[calc(100vh-6rem)]">{children}</main>
        </div>
    );
}