"use client";

import { ReactNode, useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/providers/AuthProvider";
import { UserRole } from "@/types/user";

type RoleGateProps = {
  allowedRoles: UserRole[];
  children: ReactNode;
  fallback?: ReactNode;
  redirectTo?: string;
};

export default function RoleGate({
  allowedRoles,
  children,
  fallback = null,
  redirectTo = "/login",
}: RoleGateProps) {
  const { user, loading, hasAnyRole } = useAuth();
  const router = useRouter();

  /* =========================
     Redirect unauthenticated
  ========================= */
  useEffect(() => {
    if (!loading && !user) {
      router.replace(redirectTo);
    }
  }, [user, loading, router, redirectTo]);

  /* =========================
     Loading state
  ========================= */
  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  /* =========================
     Not logged in
  ========================= */
  if (!user) {
    return null;
  }

  /* =========================
     Role check (multi-role safe)
  ========================= */
  const isAllowed = hasAnyRole(allowedRoles);

  if (!isAllowed) {
    return (
      fallback ?? (
        <div className="p-4 text-red-500">
          You do not have permission to access this page.
        </div>
      )
    );
  }

  return <>{children}</>;
}