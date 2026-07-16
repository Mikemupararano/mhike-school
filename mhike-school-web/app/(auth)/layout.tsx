import type { ReactNode } from "react";

import PublicNavbar from "@/components/layout/PublicNavbar";

type AuthLayoutProps = {
    children: ReactNode;
};

export default function AuthLayout({
    children,
}: AuthLayoutProps) {
    return (
        <div className="min-h-screen bg-[#F4F7FB]">
            <PublicNavbar />

            <main>{children}</main>
        </div>
    );
}