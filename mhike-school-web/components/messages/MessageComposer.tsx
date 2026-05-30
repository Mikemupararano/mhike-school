"use client";

import { Image as ImageIcon, Paperclip, Send } from "lucide-react";
import { useRef } from "react";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

type MessageComposerProps = {
    messageBody: string;
    sending?: boolean;
    uploadingAttachment?: boolean;

    selectedFile: File | null;

    replyToMessage?: {
        body: string;
    } | null;

    forwardMessage?: {
        body: string;
    } | null;

    onMessageChange: (value: string) => void;
    onSend: () => void;

    onFileSelect: (file: File | null) => void;

    onCancelReply: () => void;
    onCancelForward: () => void;
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

export default function MessageComposer({
    messageBody,
    sending = false,
    uploadingAttachment = false,
    selectedFile,
    replyToMessage,
    forwardMessage,
    onMessageChange,
    onSend,
    onFileSelect,
    onCancelReply,
    onCancelForward,
}: MessageComposerProps) {
    const fileInputRef = useRef<HTMLInputElement | null>(null);

    const disabled =
        sending ||
        uploadingAttachment ||
        (!messageBody.trim() && !selectedFile);

    function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
        const file = event.target.files?.[0] ?? null;

        if (!file) {
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            alert("Maximum file size is 10 MB.");
            event.target.value = "";
            return;
        }

        onFileSelect(file);
    }

    function clearSelectedFile() {
        onFileSelect(null);

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    return (
        <div className="border-t border-gray-200 bg-white px-4 py-4 shadow-lg">
            <div className="mx-auto max-w-5xl">
                {replyToMessage && (
                    <div className="mb-3 rounded-2xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                        <div className="flex items-center justify-between gap-4">
                            <div className="min-w-0">
                                <p className="font-medium">Replying to</p>

                                <p className="max-w-xl truncate text-xs">
                                    {replyToMessage.body}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={onCancelReply}
                                className="shrink-0 text-xs underline"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {forwardMessage && (
                    <div className="mb-3 rounded-2xl border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
                        <div className="flex items-center justify-between gap-4">
                            <div className="min-w-0">
                                <p className="font-medium">
                                    Forwarding message
                                </p>

                                <p className="max-w-xl truncate text-xs">
                                    {forwardMessage.body}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={onCancelForward}
                                className="shrink-0 text-xs underline"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                )}

                {selectedFile && (
                    <div className="mb-3 flex items-center justify-between rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3">
                        <div className="min-w-0">
                            <div className="truncate text-sm font-medium">
                                {selectedFile.name}
                            </div>

                            <div className="text-xs text-gray-500">
                                {formatFileSize(selectedFile.size)}
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={clearSelectedFile}
                            className="text-xs underline"
                        >
                            Remove
                        </button>
                    </div>
                )}

                <div className="flex items-center gap-3 rounded-full border border-gray-200 bg-gray-100 px-4 py-3">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
                        className="hidden"
                        onChange={handleFileChange}
                    />

                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="rounded-full p-2 transition hover:bg-gray-200"
                    >
                        <Paperclip className="h-5 w-5 text-gray-500" />
                    </button>

                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="rounded-full p-2 transition hover:bg-gray-200"
                    >
                        <ImageIcon className="h-5 w-5 text-gray-500" />
                    </button>

                    <input
                        type="text"
                        value={messageBody}
                        onChange={(event) =>
                            onMessageChange(event.target.value)
                        }
                        onKeyDown={(event) => {
                            if (event.key === "Enter" && !event.shiftKey) {
                                event.preventDefault();
                                onSend();
                            }
                        }}
                        placeholder="Type a message..."
                        className="flex-1 bg-transparent text-sm outline-none"
                    />

                    <button
                        type="button"
                        onClick={onSend}
                        disabled={disabled}
                        className="flex items-center gap-2 rounded-full bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
                    >
                        <Send className="h-4 w-4" />

                        {sending
                            ? "Sending..."
                            : uploadingAttachment
                                ? "Uploading..."
                                : "Send"}
                    </button>
                </div>
            </div>
        </div>
    );
}