import { apiGet } from "@/lib/api";
import type { AssignmentOut } from "@/lib/assignmentApi";

/* =========================
   Types
========================= */

export type TeacherDashboard = {
    teacher_id: number;
    total_courses: number;
    total_students: number;
    total_assignments: number;
    pending_submissions: number;
};

export type TeacherCourse = {
    id: number;
    title: string;
    students: number;
    assignments: number;
};

export type TeacherAssignment = AssignmentOut;

/* =========================
   API Calls
========================= */

export async function getTeacherDashboard(): Promise<TeacherDashboard> {
    return apiGet<TeacherDashboard>("/teacher-dashboard/me");
}

export async function getTeacherCourses(): Promise<TeacherCourse[]> {
    return apiGet<TeacherCourse[]>("/teacher-dashboard/courses");
}

export async function getTeacherAssignments(): Promise<TeacherAssignment[]> {
    return apiGet<TeacherAssignment[]>("/assignments/me");
}