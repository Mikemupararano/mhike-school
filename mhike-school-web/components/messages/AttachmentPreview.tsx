"use client";

import Image from "next/image";

import {
    Download,
    FileText,
    Image as ImageIcon,
} from "lucide-react";

import {
    downloadAttachment,
    getAttachmentDownloadUrl,
} from "@/lib/messages";

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
    const downloadUrl = getAttachmentDownloadUrl(attachment.id);

    if (imageAttachment) {
        return (
            <div className="mt-3 overflow-hidden rounded-2xl border border-gray-200 bg-white">
                <div className="relative h-80 w-full bg-gray-50">
                    <Image
                        src={downloadUrl}
                        alt={
                            attachment.original_filename ??
                            attachment.filename
                        }
                        fill
                        sizes="(max-width: 768px) 100vw, 640px"
                        className="object-contain"
                        unoptimized
                    />
                </div>

                <div className="flex items-center justify-between gap-3 border-t border-gray-200 px-4 py-3">
                    <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-gray-900">
                            {attachment.original_filename ??
                                attachment.filename}
                        </p>

                        <p className="text-xs text-gray-500">
                            {formatFileSize(attachment.file_size)}
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={() => downloadAttachment(attachment)}
                        className="flex shrink-0 items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium hover:bg-gray-50"
                    >
                        <Download className="h-4 w-4" />
                        Download
                    </button>
                </div>
            </div>
        );
    }

    return (
        <button
            type="button"
            onClick={() => downloadAttachment(attachment)}
            className="mt-3 flex w-full items-center gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 text-left transition hover:bg-gray-50"
        >
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-100">
                {attachment.mime_type.startsWith("image/") ? (
                    <ImageIcon className="h-5 w-5 text-gray-600" />
                ) : (
                    <FileText className="h-5 w-5 text-gray-600" />
                )}
            </div>

            <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-900">
                    {attachment.original_filename ?? attachment.filename}
                </p>

                <p className="text-xs text-gray-500">
                    {formatFileSize(attachment.file_size)}
                </p>
            </div>

            <Download className="h-4 w-4 shrink-0 text-gray-500" />
        </button>
    );
}