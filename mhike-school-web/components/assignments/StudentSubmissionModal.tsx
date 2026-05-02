"use client";

import { FormEvent, useState } from "react";

type StudentSubmissionModalProps = {
    isOpen: boolean;
    assignmentTitle: string;
    isSubmitting?: boolean;
    onClose: () => void;
    onSubmit: (submissionText: string, attachmentUrl?: string) => Promise<void>;
};

export default function StudentSubmissionModal({
    isOpen,
    assignmentTitle,
    isSubmitting = false,
    onClose,
    onSubmit,
}: StudentSubmissionModalProps) {
    const [submissionText, setSubmissionText] = useState("");
    const [attachmentUrl, setAttachmentUrl] = useState("");
    const [error, setError] = useState("");

    if (!isOpen) return null;

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");

        if (!submissionText.trim() && !attachmentUrl.trim()) {
            setError("Add submission text or an attachment URL.");
            return;
        }

        await onSubmit(submissionText, attachmentUrl || undefined);

        setSubmissionText("");
        setAttachmentUrl("");
    }

    return (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
            <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-extrabold text-slate-900">
                            Submit assignment
                        </h2>
                        <p className="mt-1 text-sm text-slate-500">{assignmentTitle}</p>
                    </div>

                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-lg border px-3 py-1 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                    >
                        Close
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="mt-5 space-y-4">
                    {error && (
                        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
                            {error}
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Submission text
                        </label>
                        <textarea
                            value={submissionText}
                            onChange={(event) => setSubmissionText(event.target.value)}
                            className="mt-1 min-h-32 w-full rounded-lg border px-3 py-2 text-sm"
                            placeholder="Write your answer here..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700">
                            Attachment URL optional
                        </label>
                        <input
                            value={attachmentUrl}
                            onChange={(event) => setAttachmentUrl(event.target.value)}
                            className="mt-1 w-full rounded-lg border px-3 py-2 text-sm"
                            placeholder="https://..."
                        />
                    </div>

                    <div className="flex gap-3">
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            {isSubmitting ? "Submitting..." : "Submit"}
                        </button>

                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-lg border px-4 py-2 text-sm font-semibold"
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}