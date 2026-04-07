"use client";

import React, { useMemo, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import SchoolHero from "@/components/school/SchoolHero";
import SchoolStatsCards from "@/components/school/SchoolStatsCards";

type TeacherCourse = {
    id: number;
    title: string;
    published: boolean;
};

function SectionCard({
    title,
    children,
}: {
    title: string;
    children: React.ReactNode;
}) {
    return (
        <section
            style={{
                background: "#FFFFFF",
                border: "1px solid #E5E7EB",
                borderRadius: 20,
                padding: 20,
                boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
            }}
        >
            <h3
                style={{
                    margin: "0 0 16px 0",
                    fontSize: 18,
                    fontWeight: 800,
                    color: "#111827",
                }}
            >
                {title}
            </h3>
            {children}
        </section>
    );
}

export default function TeacherPage() {
    const displayName = "Teacher";
    const displaySchoolName = "Your School";

    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const [courseTitle, setCourseTitle] = useState("");
    const [courseDesc, setCourseDesc] = useState("");
    const [courses, setCourses] = useState<TeacherCourse[]>([]);
    const [selectedCourse, setSelectedCourse] = useState<TeacherCourse | null>(null);

    const courseStats = useMemo(
        () => ({
            total: courses.length,
            published: courses.filter((c) => c.published).length,
        }),
        [courses]
    );

    async function loadCourses() {
        // TODO: replace with real API call
    }

    async function onCreateCourse() {
        if (!courseTitle.trim()) return;

        setBusy(true);
        setError("");

        try {
            const newCourse: TeacherCourse = {
                id: Date.now(),
                title: courseTitle.trim(),
                published: false,
            };

            setCourses((prev) => [newCourse, ...prev]);
            setSelectedCourse(newCourse);
            setCourseTitle("");
            setCourseDesc("");
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to create course.");
        } finally {
            setBusy(false);
        }
    }

    async function onPublishCourse() {
        if (!selectedCourse) return;

        setBusy(true);
        setError("");

        try {
            setCourses((prev) =>
                prev.map((course) =>
                    course.id === selectedCourse.id
                        ? { ...course, published: true }
                        : course
                )
            );

            setSelectedCourse((prev) =>
                prev ? { ...prev, published: true } : prev
            );
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Failed to publish course.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <DashboardShell
            userName={displayName}
            schoolName={displaySchoolName}
            onRefresh={() => void loadCourses()}
            sidebarItems={[
                { label: "Dashboard", href: "/teacher", icon: "/icons/dashboard.svg" },
                { label: "Courses", href: "/courses", icon: "/icons/book.svg" },
                {
                    label: "Assignments",
                    href: "/teacher/assignments",
                    icon: "/icons/quiz.svg",
                },
                { label: "Classes", href: "/teacher/classes", icon: "/icons/class.svg" },
                {
                    label: "Notifications",
                    href: "/notifications",
                    icon: "/icons/bell.svg",
                },
                { label: "Profile", href: "/profile", icon: "/icons/user.svg" },
            ]}
        >
            <div style={{ maxWidth: 1280, margin: "0 auto" }}>
                <SchoolHero
                    schoolName={displaySchoolName}
                    roleLabel="Teacher dashboard"
                    title={`Welcome back, ${displayName}!`}
                    subtitle="Create courses, organize modules, and build lessons."
                    actions={[
                        {
                            label: "Create Course",
                            onClick: () => {
                                const input = document.getElementById("teacher-course-title");
                                if (input instanceof HTMLElement) {
                                    input.focus();
                                }
                            },
                            variant: "primary",
                        },
                        {
                            label: "Teacher View",
                            href: "/teacher",
                            variant: "secondary",
                        },
                    ]}
                    rightContent={<div className="text-6xl">🧑‍🏫</div>}
                />

                {error ? (
                    <div
                        style={{
                            marginTop: 18,
                            padding: 14,
                            borderRadius: 14,
                            background: "#FEF2F2",
                            color: "#991B1B",
                            border: "1px solid #FECACA",
                        }}
                    >
                        {error}
                    </div>
                ) : null}

                <div style={{ marginTop: 22 }}>
                    <SchoolStatsCards
                        items={[
                            {
                                label: "My courses",
                                value: courseStats.total,
                                tone: "blue",
                            },
                            {
                                label: "Published",
                                value: courseStats.published,
                            },
                            {
                                label: "Next action",
                                value:
                                    courses.length === 0
                                        ? "Create your first course"
                                        : "Add modules and lessons",
                            },
                        ]}
                    />
                </div>

                <section
                    style={{
                        marginTop: 22,
                        display: "grid",
                        gridTemplateColumns: "1fr 2fr",
                        gap: 18,
                        alignItems: "start",
                    }}
                >
                    <SectionCard title="Create course">
                        <div style={{ display: "grid", gap: 8 }}>
                            <input
                                id="teacher-course-title"
                                value={courseTitle}
                                onChange={(e) => setCourseTitle(e.target.value)}
                                placeholder="Course title"
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                }}
                            />
                            <textarea
                                value={courseDesc}
                                onChange={(e) => setCourseDesc(e.target.value)}
                                placeholder="Description"
                                rows={3}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "1px solid #E5E7EB",
                                }}
                            />
                            <button
                                type="button"
                                disabled={busy || !courseTitle.trim()}
                                onClick={() => void onCreateCourse()}
                                style={{
                                    padding: 12,
                                    borderRadius: 12,
                                    border: "none",
                                    background: "#2563EB",
                                    color: "white",
                                    fontWeight: 900,
                                    cursor:
                                        busy || !courseTitle.trim()
                                            ? "not-allowed"
                                            : "pointer",
                                    opacity: busy || !courseTitle.trim() ? 0.7 : 1,
                                }}
                            >
                                {busy ? "Working..." : "Create"}
                            </button>
                        </div>
                    </SectionCard>

                    <SectionCard title="My courses">
                        {courses.length === 0 ? (
                            <div style={{ color: "#6B7280" }}>No courses yet.</div>
                        ) : (
                            <div style={{ display: "grid", gap: 10 }}>
                                <select
                                    value={selectedCourse?.id ?? ""}
                                    onChange={(e) => {
                                        const id = Number(e.target.value);
                                        setSelectedCourse(
                                            courses.find((c) => c.id === id) ?? null
                                        );
                                    }}
                                    style={{
                                        padding: 12,
                                        borderRadius: 12,
                                        border: "1px solid #E5E7EB",
                                    }}
                                >
                                    {courses.map((c) => (
                                        <option key={c.id} value={c.id}>
                                            {c.title} {c.published ? "(Published)" : "(Draft)"}
                                        </option>
                                    ))}
                                </select>

                                <button
                                    type="button"
                                    onClick={() => void onPublishCourse()}
                                    disabled={busy || !selectedCourse || selectedCourse.published}
                                    style={{
                                        padding: 12,
                                        borderRadius: 12,
                                        border: "none",
                                        background: "#111827",
                                        color: "white",
                                        fontWeight: 900,
                                        cursor:
                                            busy || !selectedCourse || selectedCourse.published
                                                ? "not-allowed"
                                                : "pointer",
                                        opacity:
                                            busy || !selectedCourse || selectedCourse.published
                                                ? 0.7
                                                : 1,
                                    }}
                                >
                                    {selectedCourse?.published ? "Published" : "Publish"}
                                </button>
                            </div>
                        )}
                    </SectionCard>
                </section>
            </div>
        </DashboardShell>
    );
}