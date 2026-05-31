"use client";

export type ChildSelectorOption = {
    student_id: number;
    student_name: string | null;
};

type ChildSelectorProps = {
    profiles: ChildSelectorOption[];
    selectedStudentId: number | null;
    onSelectStudent: (studentId: number) => void;
    title?: string;
    description?: string;
};

export default function ChildSelector({
    profiles,
    selectedStudentId,
    onSelectStudent,
    title = "Linked Students",
    description = "Select a child to view their profile.",
}: ChildSelectorProps) {
    if (profiles.length === 0) {
        return null;
    }

    return (
        <section className="rounded-2xl border bg-white p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                    <h2 className="text-xl font-bold text-slate-950">
                        {title}
                    </h2>

                    <p className="mt-1 text-sm text-slate-500">
                        {description}
                    </p>
                </div>

                <select
                    value={selectedStudentId ?? ""}
                    onChange={(event) =>
                        onSelectStudent(Number(event.target.value))
                    }
                    className="rounded-xl border px-4 py-3"
                >
                    {profiles.map((profile) => (
                        <option
                            key={profile.student_id}
                            value={profile.student_id}
                        >
                            {profile.student_name ??
                                `Student ${profile.student_id}`}
                        </option>
                    ))}
                </select>
            </div>
        </section>
    );
}