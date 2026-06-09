"use client";

import Image from "next/image";
import {
    Download,
    FileText,
    Video,
} from "lucide-react";

import {
    downloadAttachment,
    getAttachmentPreviewUrl,
    isImageAttachment,
} from "@/lib/messages";

import type { MessageAttachment } from "@/types/message";

type AttachmentPreviewProps = {
    attachment: MessageAttachment;
};

function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function isVideoAttachment(attachment: MessageAttachment): boolean {
    return attachment.mime_type.startsWith("video/");
}

export default function AttachmentPreview({
    attachment,
}: AttachmentPreviewProps) {
    const imageAttachment = isImageAttachment(attachment);
    const videoAttachment = isVideoAttachment(attachment);
    const previewUrl = getAttachmentPreviewUrl(attachment);

    return (
        <div className="mt-3 w-full max-w-sm overflow-hidden rounded-2xl border border-gray-200 bg-white">
            {imageAttachment ? (
                <button
                    type="button"
                    onClick={() => window.open(previewUrl, "_blank")}
                    className="block w-full bg-gray-100"
                >
                    <div className="relative h-64 w-full">
                        <Image
                            src={previewUrl}
                            alt={attachment.original_filename || attachment.filename}
                            fill
                            unoptimized
                            className="object-cover"
                        />
                    </div>
                </button>
            ) : videoAttachment ? (
                <div className="bg-black">
                    <video
                        controls
                        preload="metadata"
                        playsInline
                        className="max-h-80 w-full bg-black"
                    >
                        <source
                            src={previewUrl}
                            type={attachment.mime_type || "video/mp4"}
                        />
                        Your browser does not support video playback.
                    </video>
                </div>
            ) : (
                <div className="flex h-24 items-center justify-center bg-gray-100">
                    {attachment.mime_type === "application/pdf" ? (
                        <FileText className="h-8 w-8 text-red-600" />
                    ) : (
                        <Video className="h-8 w-8 text-gray-600" />
                    )}
                </div>
            )}

            <div className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">
                        {attachment.original_filename || attachment.filename}
                    </p>

                    <p className="text-xs text-gray-500">
                        {imageAttachment
                            ? "Image"
                            : videoAttachment
                                ? "Video"
                                : "Attachment"}{" "}
                        · {formatFileSize(attachment.file_size)}
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => downloadAttachment(attachment)}
                    className="flex shrink-0 items-center gap-2 rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                >
                    <Download className="h-4 w-4" />
                    Download
                </button>
            </div>
        </div>
    );
}