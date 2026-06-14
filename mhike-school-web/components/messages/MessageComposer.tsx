"use client";

import { Image as ImageIcon, Paperclip, Send, X } from "lucide-react";
import { useRef } from "react";

const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200 MB

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
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;

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

        if (!file) return;

        if (file.size > MAX_FILE_SIZE) {
            alert("Maximum file size is 200 MB.");
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
        <div className="bg-white px-4 py-4">
            <div className="mx-auto w-full max-w-5xl">
                {replyToMessage && (
                    <div className="mb-3 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 shadow-sm">
                        <div className="flex items-center justify-between gap-4">
                            <div className="min-w-0">
                                <p className="font-semibold">Replying to</p>

                                <p className="mt-0.5 max-w-2xl truncate text-sm text-blue-800">
                                    {replyToMessage.body}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={onCancelReply}
                                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition hover:bg-blue-100"
                                aria-label="Cancel reply"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                    </div>
                )}

                {forwardMessage && (
                    <div className="mb-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 shadow-sm">
                        <div className="flex items-center justify-between gap-4">
                            <div className="min-w-0">
                                <p className="font-semibold">
                                    Forwarding message
                                </p>

                                <p className="mt-0.5 max-w-2xl truncate text-sm text-slate-600">
                                    {forwardMessage.body}
                                </p>
                            </div>

                            <button
                                type="button"
                                onClick={onCancelForward}
                                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition hover:bg-slate-200"
                                aria-label="Cancel forward"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                    </div>
                )}

                {selectedFile && (
                    <div className="mb-3 flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm">
                        <div className="min-w-0">
                            <div className="truncate text-sm font-semibold text-slate-800">
                                {selectedFile.name}
                            </div>

                            <div className="text-xs text-slate-500">
                                {formatFileSize(selectedFile.size)}
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={clearSelectedFile}
                            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition hover:bg-slate-200"
                            aria-label="Remove selected file"
                        >
                            <X className="h-4 w-4 text-slate-500" />
                        </button>
                    </div>
                )}

                <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 shadow-md">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*,video/*,.mp4,.mov,.m4v,.webm,.avi,.mpeg,.mpg,.3gp,.3g2,.ogv,.mkv,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
                        className="hidden"
                        onChange={handleFileChange}
                    />

                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition hover:bg-slate-200"
                        aria-label="Attach file"
                    >
                        <Paperclip className="h-5 w-5 text-slate-500" />
                    </button>

                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition hover:bg-slate-200"
                        aria-label="Attach image"
                    >
                        <ImageIcon className="h-5 w-5 text-slate-500" />
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
                        className="min-h-10 flex-1 bg-transparent px-2 text-base text-slate-800 outline-none placeholder:text-slate-400"
                    />

                    <button
                        type="button"
                        onClick={onSend}
                        disabled={disabled}
                        className="flex h-11 shrink-0 items-center gap-2 rounded-full bg-blue-600 px-5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        <Send className="h-4 w-4" />

                        <span>
                            {sending
                                ? "Sending..."
                                : uploadingAttachment
                                    ? "Uploading..."
                                    : "Send"}
                        </span>
                    </button>
                </div>
            </div>
        </div>
    );
}