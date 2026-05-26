"use client";

import { useState } from "react";

import { apiPost } from "@/lib/api";

export default function BroadcastNotificationForm() {
    const [loading, setLoading] = useState(false);

    const [success, setSuccess] = useState("");
    const [error, setError] = useState("");

    const [formData, setFormData] = useState({
        school_id: "",
        target: "all",
        title: "",
        message: "",
        category: "announcement",
        priority: "normal",
        email_enabled: false,
        push_enabled: true,
        sms_enabled: false,
    });

    async function handleSubmit(
        event: React.FormEvent<HTMLFormElement>,
    ) {
        event.preventDefault();

        try {
            setLoading(true);

            setSuccess("");
            setError("");

            await apiPost(
                "/notifications/broadcast",
                {
                    school_id: formData.school_id
                        ? Number(formData.school_id)
                        : null,

                    target: formData.target,

                    title: formData.title,

                    message: formData.message,

                    category: formData.category,

                    priority: formData.priority,

                    email_enabled: formData.email_enabled,

                    push_enabled: formData.push_enabled,

                    sms_enabled: formData.sms_enabled,
                },
            );

            setSuccess(
                "Broadcast notification sent successfully.",
            );

            setFormData({
                school_id: "",
                target: "all",
                title: "",
                message: "",
                category: "announcement",
                priority: "normal",
                email_enabled: false,
                push_enabled: true,
                sms_enabled: false,
            });
        } catch (err) {
            console.error(err);

            setError(
                "Failed to send broadcast notification.",
            );
        } finally {
            setLoading(false);
        }
    }

    function handleChange(
        event: React.ChangeEvent<
            HTMLInputElement |
            HTMLSelectElement |
            HTMLTextAreaElement
        >,
    ) {
        const target = event.target;

        const value =
            target instanceof HTMLInputElement &&
                target.type === "checkbox"
                ? target.checked
                : target.value;

        setFormData((prev) => ({
            ...prev,
            [target.name]: value,
        }));
    }

    return (
        <form
            onSubmit={handleSubmit}
            className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm"
        >
            {success ? (
                <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
                    {success}
                </div>
            ) : null}

            {error ? (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {error}
                </div>
            ) : null}

            <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                    School ID
                </label>

                <input
                    type="number"
                    name="school_id"
                    value={formData.school_id}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
                />
            </div>

            <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                    Target Audience
                </label>

                <select
                    name="target"
                    value={formData.target}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
                >
                    <option value="all">All Users</option>
                    <option value="teachers">Teachers</option>
                    <option value="students">Students</option>
                    <option value="parents">Parents</option>
                </select>
            </div>

            <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                    Title
                </label>

                <input
                    type="text"
                    name="title"
                    value={formData.title}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
                />
            </div>

            <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                    Message
                </label>

                <textarea
                    name="message"
                    rows={6}
                    value={formData.message}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-gray-300 px-4 py-3 outline-none focus:border-blue-500"
                />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
                <label className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        name="email_enabled"
                        checked={formData.email_enabled}
                        onChange={handleChange}
                    />

                    <span>Email</span>
                </label>

                <label className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        name="push_enabled"
                        checked={formData.push_enabled}
                        onChange={handleChange}
                    />

                    <span>Push</span>
                </label>

                <label className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        name="sms_enabled"
                        checked={formData.sms_enabled}
                        onChange={handleChange}
                    />

                    <span>SMS</span>
                </label>
            </div>

            <button
                type="submit"
                disabled={loading}
                className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
            >
                {loading ? "Sending..." : "Send Broadcast"}
            </button>
        </form>
    );
}