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
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(redirectTo);
    }
  }, [user, loading, router, redirectTo]);

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  if (!user) {
    return null;
  }

  const userRoles = Array.isArray(user.roles)
    ? user.roles
    : user.role
      ? [user.role]
      : [];

  const isAllowed = allowedRoles.some((role) => userRoles.includes(role));

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