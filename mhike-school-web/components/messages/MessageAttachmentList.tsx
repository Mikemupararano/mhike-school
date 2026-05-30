"use client";

import AttachmentPreview from "@/components/messages/AttachmentPreview";

import type { MessageAttachment } from "@/types/message";

type MessageAttachmentListProps = {
    attachments?: MessageAttachment[] | null;
};

export default function MessageAttachmentList({
    attachments,
}: MessageAttachmentListProps) {
    if (
        !attachments ||
        attachments.length === 0
    ) {
        return null;
    }

    return (
        <div className="mt-3 flex flex-col gap-2">
            {attachments.map(
                (attachment) => (
                    <AttachmentPreview
                        key={
                            attachment.id
                        }
                        attachment={
                            attachment
                        }
                    />
                ),
            )}
        </div>
    );
}