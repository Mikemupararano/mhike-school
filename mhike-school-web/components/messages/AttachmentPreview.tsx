"use client";

import {
    Download,
    FileText,
    Image as ImageIcon,
} from "lucide-react";

import { downloadAttachment } from "@/lib/messages";

import type { MessageAttachment } from "@/types/message";

type AttachmentPreviewProps = {
    attachment: MessageAttachment;
};

function formatFileSize(bytes: number): string {
    if (bytes < 1024) {
        return `${bytes} B`;
    }

    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function isImageAttachment(attachment: MessageAttachment): boolean {
    return attachment.mime_type.startsWith("image/");
}

export default function AttachmentPreview({
    attachment,
}: AttachmentPreviewProps) {
    const imageAttachment = isImageAttachment(attachment);

    return (
        <button
            type="button"
            onClick={() => downloadAttachment(attachment)}
            className="mt-3 flex w-full max-w-sm items-center gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 text-left transition hover:bg-gray-50"
        >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gray-100">
                {imageAttachment ? (
                    <ImageIcon className="h-5 w-5 text-gray-600" />
                ) : (
                    <FileText className="h-5 w-5 text-gray-600" />
                )}
            </div>

            <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-900">
                    {attachment.original_filename || attachment.filename}
                </p>

                <p className="text-xs text-gray-500">
                    {imageAttachment ? "Image file" : "Attachment"} ·{" "}
                    {formatFileSize(attachment.file_size)}
                </p>
            </div>

            <div className="flex shrink-0 items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700">
                <Download className="h-4 w-4" />
                Download
            </div>
        </button>
    );
}