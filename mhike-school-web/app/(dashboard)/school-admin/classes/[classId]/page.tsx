'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'

import RoleGate from '@/components/auth/RoleGate'
import { UserRole, type User } from '@/types/user'

import {
  getClassStudents,
  assignStudentToClass,
  removeStudentFromClass,
  getClassById,
  assignTeacher,
  type ClassGroup,
} from '@/lib/services/classes'

import { getSchoolUsers } from '@/lib/services/school-admin'

export default function ClassPage() {
  return (
    <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
      <ClassContent />
    </RoleGate>
  )
}

function ClassContent() {
  const params = useParams()
  const classId = Number(params.classId)

  const [classGroup, setClassGroup] = useState<ClassGroup | null>(null)
  const [students, setStudents] = useState<User[]>([])
  const [allStudents, setAllStudents] = useState<User[]>([])
  const [teachers, setTeachers] = useState<User[]>([])

  const [selectedUser, setSelectedUser] = useState<number | null>(null)
  const [selectedTeacher, setSelectedTeacher] = useState<number | null>(null)

  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [teacherSubmitting, setTeacherSubmitting] = useState(false)
  const [removingId, setRemovingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const assignedStudentIds = useMemo(
    () => new Set(students.map((s) => s.id)),
    [students]
  )

  const availableStudents = useMemo(
    () => allStudents.filter((u) => !assignedStudentIds.has(u.id)),
    [allStudents, assignedStudentIds]
  )

  async function loadData() {
    setLoading(true)
    setError(null)

    try {
      const [classData, studentsData, usersData] = await Promise.all([
        getClassById(classId),
        getClassStudents(classId),
        getSchoolUsers(),
      ])

      const teacherUsers = usersData.filter((u) => u.role === UserRole.TEACHER)
      const studentUsers = usersData.filter((u) => u.role === UserRole.STUDENT)

      setClassGroup(classData)
      setStudents(studentsData)
      setAllStudents(studentUsers)
      setTeachers(teacherUsers)
      setSelectedTeacher(classData.teacher_id ?? null)
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to load data'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (classId) {
      void loadData()
    }
  }, [classId])

  async function handleAssignStudent() {
    if (!selectedUser) return

    try {
      setSubmitting(true)
      setError(null)

      await assignStudentToClass({
        user_id: selectedUser,
        class_id: classId,
      })

      setSelectedUser(null)
      await loadData()
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to assign student'
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRemoveStudent(userId: number) {
    try {
      setRemovingId(userId)
      setError(null)

      await removeStudentFromClass({
        user_id: userId,
        class_id: classId,
      })

      await loadData()
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to remove student'
      setError(message)
    } finally {
      setRemovingId(null)
    }
  }

  async function handleAssignTeacher() {
    if (!selectedTeacher) return

    try {
      setTeacherSubmitting(true)
      setError(null)

      await assignTeacher(classId, selectedTeacher)
      await loadData()
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Failed to assign teacher'
      setError(message)
    } finally {
      setTeacherSubmitting(false)
    }
  }

  const currentTeacher = teachers.find((t) => t.id === classGroup?.teacher_id)

  return (
    <div className="max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">
          {classGroup ? classGroup.name : 'Class'}
        </h1>

        <p className="mt-2 text-gray-500">
          Manage teacher assignment and students in this class.
        </p>
      </div>

      <div className="grid gap-6">
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold">Assigned teacher</h2>

          <p className="mb-3 text-sm text-gray-500">
            Current teacher:{' '}
            <span className="font-medium text-gray-900">
              {currentTeacher?.full_name || currentTeacher?.email || 'Not assigned'}
            </span>
          </p>

          <div className="flex flex-col gap-3 sm:flex-row">
            <select
              value={selectedTeacher ?? ''}
              onChange={(e) =>
                setSelectedTeacher(e.target.value ? Number(e.target.value) : null)
              }
              className="w-full rounded border px-3 py-2"
              disabled={loading || teacherSubmitting}
            >
              <option value="">Select teacher</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.full_name || t.email}
                </option>
              ))}
            </select>

            <button
              onClick={handleAssignTeacher}
              disabled={!selectedTeacher || teacherSubmitting || loading}
              className="rounded bg-emerald-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {teacherSubmitting ? 'Assigning...' : 'Assign Teacher'}
            </button>
          </div>
        </div>

        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold">Add student</h2>

          <div className="flex flex-col gap-3 sm:flex-row">
            <select
              value={selectedUser ?? ''}
              onChange={(e) =>
                setSelectedUser(e.target.value ? Number(e.target.value) : null)
              }
              className="w-full rounded border px-3 py-2"
              disabled={loading || submitting}
            >
              <option value="">Select student</option>
              {availableStudents.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.email}
                </option>
              ))}
            </select>

            <button
              onClick={handleAssignStudent}
              disabled={!selectedUser || submitting || loading}
              className="rounded bg-blue-600 px-4 py-2 text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? 'Adding...' : 'Add Student'}
            </button>
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-500">{error}</p>
        )}

        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Students</h2>

          {loading ? (
            <p>Loading students...</p>
          ) : students.length === 0 ? (
            <p>No students in this class yet.</p>
          ) : (
            <ul className="space-y-2">
              {students.map((s) => (
                <li
                  key={s.id}
                  className="flex items-center justify-between rounded border p-3"
                >
                  <div>
                    <div className="font-semibold">
                      {s.full_name || 'No name'}
                    </div>
                    <div className="text-sm text-gray-500">
                      {s.email}
                    </div>
                  </div>

                  <button
                    onClick={() => handleRemoveStudent(s.id)}
                    disabled={removingId === s.id}
                    className="text-sm text-red-500 disabled:opacity-50"
                  >
                    {removingId === s.id ? 'Removing...' : 'Remove'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}