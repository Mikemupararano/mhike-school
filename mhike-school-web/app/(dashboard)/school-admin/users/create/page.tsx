"use client";

import { useRouter } from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";
import SchoolUserForm from "@/components/school-admin/components/SchoolUserForm";
import { UserRole } from "@/types/user";
import { createSchoolUser } from "@/lib/services/school-admin";

export default function CreateUserPage() {
  return (
    <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
      <CreateUserContent />
    </RoleGate>
  );
}

function CreateUserContent() {
  const router = useRouter();

  return (
    <div className="max-w-xl p-6">
      <h1 className="text-3xl font-extrabold">Create User</h1>
      <p className="mt-2 text-slate-500">Add a new user to your school.</p>

      <div className="mt-6">
        <SchoolUserForm
          submitLabel="Create user"
          onSubmit={async (data) => {
            await createSchoolUser(data);
            router.push("/school-admin/users");
            router.refresh();
          }}
        />
      </div>

      <button
        type="button"
        onClick={() => router.push("/school-admin/users")}
        className="mt-4 rounded-lg border px-4 py-2"
      >
        Cancel
      </button>
    </div>
  );
}