'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import RoleGate from '@/components/auth/RoleGate'
import { UserRole } from '@/types/user'
import { createPlatformSchool } from '@/lib/services/platform-admin'

export default function CreateSchoolPage() {
  return (
    <RoleGate allowedRoles={[UserRole.PLATFORM_ADMIN]}>
      <CreateSchoolForm />
    </RoleGate>
  )
}

function CreateSchoolForm() {
  const router = useRouter()

  const [name, setName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    try {
      setIsLoading(true)

      await createPlatformSchool({
        name,
      })

      router.push('/admin/schools')
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to create school'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-xl">
      <h1 className="text-3xl font-extrabold">Create School</h1>
      <p className="mt-2 text-slate-500">
        Add a new school to the platform.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="block text-sm font-medium">School Name</label>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
            placeholder="Kent School"
          />
        </div>

        {error && (
          <div className="text-sm text-red-500">{error}</div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isLoading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Creating...' : 'Create School'}
          </button>

          <button
            type="button"
            onClick={() => router.push('/admin/schools')}
            className="rounded-lg border px-4 py-2"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}