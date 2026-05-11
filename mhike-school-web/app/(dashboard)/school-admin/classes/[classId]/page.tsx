"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import RoleGate from "@/components/auth/RoleGate";
import AssignTeacherPanel from "@/components/school-admin/components/AssignTeacherPanel";
import ClassEnrollmentPanel from "@/components/school-admin/components/ClassEnrollmentPanel";
import { UserRole, type User } from "@/types/user";
import type { ClassGroup } from "@/types/class";

import {
  assignTeacher,
  enrollStudent,
  getClass,
  getClassStudents,
  removeStudent,
} from "@/lib/services/classes";

import { listSchoolUsers } from "@/lib/services/school-admin";

export default function ClassPage() {
  return (
    <RoleGate allowedRoles={[UserRole.SCHOOL_ADMIN, UserRole.PLATFORM_ADMIN]}>
      <ClassContent />
    </RoleGate>
  );
}

function ClassContent() {
  const params = useParams();
  const classId = Number(params.classId);

  const [classGroup, setClassGroup] = useState<ClassGroup | null>(null);
  const [students, setStudents] = useState<User[]>([]);
  const [schoolUsers, setSchoolUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const teachers = useMemo(() => {
    return schoolUsers.filter((user) => {
      const roles = user.roles?.length
        ? user.roles
        : user.role
          ? [user.role]
          : [];

      return roles.includes(UserRole.TEACHER);
    });
  }, [schoolUsers]);

  const allStudents = useMemo(() => {
    return schoolUsers.filter((user) => {
      const roles = user.roles?.length
        ? user.roles
        : user.role
          ? [user.role]
          : [];

      return roles.includes(UserRole.STUDENT);
    });
  }, [schoolUsers]);

  const currentTeacher = teachers.find(
    (teacher) => teacher.id === classGroup?.teacher_id,
  );

  async function loadData() {
    try {
      setLoading(true);
      setError(null);

      const [classData, studentsData, usersData] = await Promise.all([
        getClass(classId),
        getClassStudents(classId),
        listSchoolUsers(),
      ]);

      setClassGroup(classData);
      setStudents(studentsData);
      setSchoolUsers(usersData);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error ? err.message : "Failed to load class data",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (Number.isFinite(classId)) {
      void loadData();
    }
  }, [classId]);

  async function handleAssignTeacher(teacherId: number) {
    await assignTeacher(classId, teacherId);
    await loadData();
  }

  async function handleEnrollStudent(studentId: number) {
    await enrollStudent(classId, studentId);
    await loadData();
  }

  async function handleRemoveStudent(studentId: number) {
    await removeStudent(classId, studentId);
    await loadData();
  }

  if (loading && !classGroup) {
    return (
      <div className="p-6 text-sm text-slate-600">
        Loading class...
      </div>
    );
  }

  return (
    <div className="max-w-5xl p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">
          {classGroup ? classGroup.name : "Class"}
        </h1>

        <p className="mt-2 text-gray-500">
          Manage teacher assignment and student enrolment for this class.
        </p>

        {currentTeacher ? (
          <p className="mt-2 text-sm text-slate-600">
            Current teacher:{" "}
            <span className="font-semibold text-slate-900">
              {currentTeacher.full_name || currentTeacher.email}
            </span>
          </p>
        ) : (
          <p className="mt-2 text-sm text-slate-600">
            Current teacher:{" "}
            <span className="font-semibold text-slate-900">
              Not assigned
            </span>
          </p>
        )}
      </div>

      {error ? (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-6">
        <AssignTeacherPanel
          teachers={teachers}
          currentTeacherId={classGroup?.teacher_id}
          onAssign={handleAssignTeacher}
        />

        <ClassEnrollmentPanel
          students={students}
          allStudents={allStudents}
          onEnroll={handleEnrollStudent}
          onRemove={handleRemoveStudent}
        />
      </div>
    </div>
  );
}