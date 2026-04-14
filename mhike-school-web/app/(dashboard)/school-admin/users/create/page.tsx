"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

import RoleGate from "@/components/auth/RoleGate"
import { UserRole } from "@/types/user"
import { createSchoolUser } from "@/lib/services/school-admin"

// 🔥 Use your design system
import { BrandButton, BrandInput } from "@/components/ui"

export default function CreateUserPage() {
  return (
    <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
      <CreateUserForm />
    </RoleGate>
  )
}

function CreateUserForm() {
  const router = useRouter()

  const [email, setEmail] = useState("")
  const [fullName, setFullName] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<UserRole>(UserRole.STUDENT)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isFormValid = email.trim() !== "" && password.trim().length >= 6

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!isFormValid) return

    setError(null)

    try {
      setIsLoading(true)

      await createSchoolUser({
        email: email.trim(),
        password,
        full_name: fullName.trim() || undefined,
        role,
      })

      router.push("/school-admin/users")
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to create user"
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-xl">
      <h1 className="text-3xl font-extrabold">Create User</h1>
      <p className="mt-2 text-slate-500">
        Add a student or teacher to your school.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        {/* Email */}
        <BrandInput
          label="Email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        {/* Full Name */}
        <BrandInput
          label="Full Name"
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />

        {/* Password */}
        <BrandInput
          label="Password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {/* Role */}
        <div>
          <label className="block text-sm font-medium">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          >
            <option value={UserRole.STUDENT}>Student</option>
            <option value={UserRole.TEACHER}>Teacher</option>
          </select>
        </div>

        {/* Error */}
        {error && <div className="text-sm text-red-500">{error}</div>}

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <BrandButton
            type="submit"
            disabled={!isFormValid || isLoading}
          >
            {isLoading ? "Creating..." : "Create User"}
          </BrandButton>

          <button
            type="button"
            onClick={() => router.push("/school-admin/users")}
            className="rounded-lg border px-4 py-2"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}