"use client";

import {
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";

import ChildSelector from "@/components/parent/ChildSelector";
import ParentPageState from "@/components/parent/ParentPageState";

import { useParentChildren } from "@/hooks/useParentChildren";

import {
    getParentReports,
    type StudentReport,
} from "@/lib/services/parentReports";

type ReportWithOptionalMetadata = StudentReport & {
    published_at?: string | null;
    subject_name?: string | null;
    teacher_name?: string | null;
    effort_grade?: string | null;
    attainment_grade?: string | null;
    target_grade?: string | null;
};

const TOKEN_STORAGE_KEY = "mhike_token";
const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

function formatDate(value: string | null | undefined): string {
    if (!value) {
        return "Date not available";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "Date not available";
    }

    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function getReportDate(report: ReportWithOptionalMetadata): string {
    return report.published_at ?? report.created_at;
}

function getReportTimestamp(report: ReportWithOptionalMetadata): number {
    const timestamp = new Date(getReportDate(report)).getTime();

    return Number.isNaN(timestamp) ? 0 : timestamp;
}

function getApiBaseUrl(): string {
    const configured =
        process.env.NEXT_PUBLIC_API_BASE_URL ??
        process.env.NEXT_PUBLIC_API_URL;

    return (configured?.trim() || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

function getDownloadFilename(
    response: Response,
    fallbackFilename: string,
): string {
    const contentDisposition = response.headers.get("Content-Disposition");

    if (!contentDisposition) {
        return fallbackFilename;
    }

    const utf8Match = contentDisposition.match(
        /filename\*=UTF-8''([^;]+)/i,
    );

    if (utf8Match?.[1]) {
        try {
            return decodeURIComponent(utf8Match[1]);
        } catch {
            return utf8Match[1];
        }
    }

    const quotedMatch = contentDisposition.match(/filename="([^"]+)"/i);

    if (quotedMatch?.[1]) {
        return quotedMatch[1];
    }

    const plainMatch = contentDisposition.match(/filename=([^;]+)/i);

    return plainMatch?.[1]?.trim() || fallbackFilename;
}

async function downloadAuthenticatedFile(
    path: string,
    fallbackFilename: string,
): Promise<void> {
    const token = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);

    if (!token) {
        throw new Error(
            "Your session has expired. Please sign in again before downloading.",
        );
    }

    const response = await fetch(`${getApiBaseUrl()}${path}`, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
    });

    if (!response.ok) {
        let message = `Download failed (${response.status}).`;

        try {
            const body = (await response.json()) as {
                detail?: unknown;
            };

            if (typeof body.detail === "string" && body.detail.trim()) {
                message = body.detail;
            }
        } catch {
            // Keep the HTTP fallback when the response is not JSON.
        }

        throw new Error(message);
    }

    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    try {
        anchor.href = objectUrl;
        anchor.download = getDownloadFilename(
            response,
            fallbackFilename,
        );
        anchor.rel = "noopener";
        document.body.appendChild(anchor);
        anchor.click();
    } finally {
        anchor.remove();
        window.URL.revokeObjectURL(objectUrl);
    }
}

export default function ParentReportsPage() {
    const {
        profiles,
        selectedStudentId,
        selectedProfile,
        setSelectedStudentId,
        loading: childrenLoading,
        error: childrenError,
    } = useParentChildren();

    const [reports, setReports] = useState<ReportWithOptionalMetadata[]>([]);
    const [reportsLoading, setReportsLoading] = useState(true);
    const [reportsError, setReportsError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [downloadingReportId, setDownloadingReportId] =
        useState<number | null>(null);

    const [academicYearFilter, setAcademicYearFilter] = useState("all");
    const [termFilter, setTermFilter] = useState("all");
    const [searchQuery, setSearchQuery] = useState("");

    const loadReports = useCallback(async () => {
        try {
            setReportsLoading(true);
            setReportsError(null);

            const data = await getParentReports();

            setReports(data);
        } catch (err) {
            setReportsError(
                err instanceof Error
                    ? err.message
                    : "Failed to load reports.",
            );
        } finally {
            setReportsLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadReports();
    }, [loadReports]);

    useEffect(() => {
        setAcademicYearFilter("all");
        setTermFilter("all");
        setSearchQuery("");
        setReportsError(null);
        setSuccessMessage(null);
    }, [selectedStudentId]);

    const reportsForSelectedStudent = useMemo(() => {
        if (!selectedStudentId) {
            return [];
        }

        return reports
            .filter((report) => report.student_id === selectedStudentId)
            .sort(
                (first, second) =>
                    getReportTimestamp(second) -
                    getReportTimestamp(first),
            );
    }, [reports, selectedStudentId]);

    const academicYears = useMemo(
        () =>
            Array.from(
                new Set(
                    reportsForSelectedStudent
                        .map((report) => report.academic_year?.trim())
                        .filter(
                            (value): value is string =>
                                Boolean(value),
                        ),
                ),
            ).sort((first, second) =>
                second.localeCompare(first, "en-GB", {
                    numeric: true,
                }),
            ),
        [reportsForSelectedStudent],
    );

    const terms = useMemo(
        () =>
            Array.from(
                new Set(
                    reportsForSelectedStudent
                        .map((report) => report.term?.trim())
                        .filter(
                            (value): value is string =>
                                Boolean(value),
                        ),
                ),
            ).sort((first, second) =>
                first.localeCompare(second, "en-GB", {
                    numeric: true,
                }),
            ),
        [reportsForSelectedStudent],
    );

    const selectedReports = useMemo(() => {
        const normalisedSearch = searchQuery.trim().toLocaleLowerCase("en-GB");

        return reportsForSelectedStudent
            .filter((report) =>
                academicYearFilter === "all"
                    ? true
                    : report.academic_year === academicYearFilter,
            )
            .filter((report) =>
                termFilter === "all"
                    ? true
                    : (report.term ?? "") === termFilter,
            )
            .filter((report) => {
                if (!normalisedSearch) {
                    return true;
                }

                const searchableText = [
                    report.title,
                    report.report_text,
                    report.academic_year,
                    report.term ?? "",
                    report.grade ?? "",
                    report.subject_name ?? "",
                    report.teacher_name ?? "",
                ]
                    .join(" ")
                    .toLocaleLowerCase("en-GB");

                return searchableText.includes(normalisedSearch);
            });
    }, [
        academicYearFilter,
        reportsForSelectedStudent,
        searchQuery,
        termFilter,
    ]);

    async function handleDownloadReport(
        report: ReportWithOptionalMetadata,
    ) {
        try {
            setDownloadingReportId(report.id);
            setReportsError(null);
            setSuccessMessage(null);

            await downloadAuthenticatedFile(
                `/student-reports/${report.id}/pdf`,
                `student_report_${report.id}.pdf`,
            );

            setSuccessMessage("Report PDF downloaded successfully.");
        } catch (err) {
            setReportsError(
                err instanceof Error
                    ? err.message
                    : "Failed to download the report PDF.",
            );
        } finally {
            setDownloadingReportId(null);
        }
    }

    const isLoading = childrenLoading || reportsLoading;
    const pageError = childrenError || reportsError;

    return (
        <main className="space-y-6 p-4 sm:p-6 lg:p-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-950">
                        Child Reports
                    </h1>

                    <p className="mt-2 max-w-3xl text-base text-slate-600">
                        View published academic reports, progress summaries and
                        teacher feedback for your child.
                    </p>
                </div>

                <button
                    type="button"
                    data-custom-button="true"
                    disabled={reportsLoading}
                    onClick={() => void loadReports()}
                    className="inline-flex w-fit items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-base font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {reportsLoading ? "Refreshing..." : "Refresh"}
                </button>
            </div>

            {successMessage && (
                <div
                    role="status"
                    aria-live="polite"
                    className="rounded-2xl border border-green-200 bg-green-50 p-4 text-base font-medium text-green-700"
                >
                    {successMessage}
                </div>
            )}

            <ParentPageState
                loading={isLoading}
                error={pageError}
                isEmpty={profiles.length === 0 || !selectedProfile}
                loadingMessage="Loading reports..."
            >
                {selectedProfile && (
                    <>
                        <ChildSelector
                            profiles={profiles}
                            selectedStudentId={selectedStudentId}
                            onSelectStudent={setSelectedStudentId}
                            title="Linked Students"
                            description="Select a child to view their published reports."
                        />

                        <section className="rounded-2xl border bg-white p-4 sm:p-6">
                            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                                <div>
                                    <h2 className="text-xl font-bold text-slate-950">
                                        Published Reports
                                    </h2>

                                    <p className="mt-2 text-base text-slate-600">
                                        Reports for{" "}
                                        <span className="font-semibold text-slate-900">
                                            {selectedProfile.student_name ??
                                                `Student ${selectedProfile.student_id}`}
                                        </span>
                                        .
                                    </p>
                                </div>

                                <div className="rounded-xl bg-blue-50 px-4 py-3 text-blue-800">
                                    <p className="text-sm font-semibold">
                                        Available reports
                                    </p>
                                    <p className="text-2xl font-bold">
                                        {reportsForSelectedStudent.length}
                                    </p>
                                </div>
                            </div>

                            {reportsForSelectedStudent.length > 0 && (
                                <div className="mt-6 grid gap-4 md:grid-cols-3">
                                    <label className="grid gap-2">
                                        <span className="text-base font-semibold text-slate-700">
                                            Academic year
                                        </span>

                                        <select
                                            value={academicYearFilter}
                                            onChange={(event) =>
                                                setAcademicYearFilter(
                                                    event.target.value,
                                                )
                                            }
                                            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base text-slate-900"
                                        >
                                            <option value="all">
                                                All academic years
                                            </option>
                                            {academicYears.map((year) => (
                                                <option
                                                    key={year}
                                                    value={year}
                                                >
                                                    {year}
                                                </option>
                                            ))}
                                        </select>
                                    </label>

                                    <label className="grid gap-2">
                                        <span className="text-base font-semibold text-slate-700">
                                            Term
                                        </span>

                                        <select
                                            value={termFilter}
                                            onChange={(event) =>
                                                setTermFilter(
                                                    event.target.value,
                                                )
                                            }
                                            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base text-slate-900"
                                        >
                                            <option value="all">
                                                All terms
                                            </option>
                                            {terms.map((term) => (
                                                <option
                                                    key={term}
                                                    value={term}
                                                >
                                                    {term}
                                                </option>
                                            ))}
                                        </select>
                                    </label>

                                    <label className="grid gap-2">
                                        <span className="text-base font-semibold text-slate-700">
                                            Search
                                        </span>

                                        <input
                                            value={searchQuery}
                                            onChange={(event) =>
                                                setSearchQuery(
                                                    event.target.value,
                                                )
                                            }
                                            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-base text-slate-900"
                                            placeholder="Title, subject or report text"
                                        />
                                    </label>
                                </div>
                            )}

                            {reportsForSelectedStudent.length === 0 ? (
                                <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-base text-slate-600">
                                    No published reports are currently
                                    available.
                                </div>
                            ) : selectedReports.length === 0 ? (
                                <div className="mt-6 rounded-2xl border border-dashed bg-slate-50 p-6 text-base text-slate-600">
                                    No reports match the selected filters.
                                </div>
                            ) : (
                                <div className="mt-6 grid gap-5">
                                    {selectedReports.map((report) => {
                                        const gradeCards = [
                                            {
                                                label: "Overall grade",
                                                value: report.grade,
                                            },
                                            {
                                                label: "Attainment",
                                                value:
                                                    report.attainment_grade,
                                            },
                                            {
                                                label: "Effort",
                                                value: report.effort_grade,
                                            },
                                            {
                                                label: "Target",
                                                value: report.target_grade,
                                            },
                                        ].filter(
                                            (
                                                item,
                                            ): item is {
                                                label: string;
                                                value: string;
                                            } =>
                                                typeof item.value ===
                                                "string" &&
                                                item.value.trim().length > 0,
                                        );

                                        return (
                                            <article
                                                key={report.id}
                                                className="overflow-hidden rounded-2xl border bg-slate-50"
                                            >
                                                <div className="p-4 sm:p-5">
                                                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                                                        <div>
                                                            <h3 className="text-lg font-bold text-slate-950">
                                                                {report.title}
                                                            </h3>

                                                            <p className="mt-1 text-base text-slate-600">
                                                                {report.subject_name
                                                                    ? `${report.subject_name} · `
                                                                    : ""}
                                                                {
                                                                    report.academic_year
                                                                }
                                                                {report.term
                                                                    ? ` · ${report.term}`
                                                                    : ""}
                                                            </p>

                                                            <p className="mt-1 text-sm text-slate-500">
                                                                Published{" "}
                                                                {formatDate(
                                                                    getReportDate(
                                                                        report,
                                                                    ),
                                                                )}
                                                                {report.teacher_name
                                                                    ? ` · ${report.teacher_name}`
                                                                    : ""}
                                                            </p>
                                                        </div>

                                                        <button
                                                            type="button"
                                                            data-custom-button="true"
                                                            disabled={
                                                                downloadingReportId ===
                                                                report.id
                                                            }
                                                            onClick={() =>
                                                                void handleDownloadReport(
                                                                    report,
                                                                )
                                                            }
                                                            className="inline-flex w-fit items-center justify-center rounded-xl bg-blue-600 px-4 py-2 text-base font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                                                        >
                                                            {downloadingReportId ===
                                                                report.id
                                                                ? "Downloading..."
                                                                : "Download PDF"}
                                                        </button>
                                                    </div>

                                                    {gradeCards.length > 0 && (
                                                        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                                            {gradeCards.map(
                                                                (item) => (
                                                                    <div
                                                                        key={
                                                                            item.label
                                                                        }
                                                                        className="rounded-xl border bg-white p-3"
                                                                    >
                                                                        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                                                            {
                                                                                item.label
                                                                            }
                                                                        </p>
                                                                        <p className="mt-1 text-lg font-bold text-blue-700">
                                                                            {
                                                                                item.value
                                                                            }
                                                                        </p>
                                                                    </div>
                                                                ),
                                                            )}
                                                        </div>
                                                    )}

                                                    <div className="mt-4">
                                                        <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                                                            Teacher report
                                                        </p>

                                                        <p className="mt-2 whitespace-pre-line rounded-xl bg-white p-4 text-base leading-7 text-slate-800">
                                                            {
                                                                report.report_text
                                                            }
                                                        </p>
                                                    </div>
                                                </div>
                                            </article>
                                        );
                                    })}
                                </div>
                            )}
                        </section>
                    </>
                )}
            </ParentPageState>
        </main>
    );
}
