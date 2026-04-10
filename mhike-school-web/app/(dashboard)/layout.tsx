import DashboardShellWrapper from "@/components/layout/DashboardShellWrapper";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return <DashboardShellWrapper>{children}</DashboardShellWrapper>;
}