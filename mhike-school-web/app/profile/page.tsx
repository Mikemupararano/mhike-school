"use client";

import React from "react";
import { useRouter } from "next/navigation";

export default function ProfilePage() {
    const router = useRouter();

    return (
        <main style={{ maxWidth: 900, margin: "0 auto", padding: 24 }}>
            <button
                onClick={() => router.push("/dashboard")}
                style={{
                    marginBottom: 16,
                    padding: "10px 14px",
                    borderRadius: 10,
                    border: "1px solid #E5E7EB",
                    background: "white",
                    cursor: "pointer",
                }}
            >
                ← Back to Dashboard
            </button>

            <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 8 }}>My Profile</h1>
            <p style={{ color: "#6B7280", marginTop: 0 }}>
                Student information and account overview.
            </p>

            <section
                style={{
                    marginTop: 20,
                    background: "white",
                    border: "1px solid #E5E7EB",
                    borderRadius: 18,
                    padding: 20,
                }}
            >
                <p><b>Name:</b> John Doe</p>
                <p><b>Email:</b> student@example.com</p>
                <p><b>Role:</b> Student</p>
                <p><b>Status:</b> Active learner</p>
            </section>
        </main>
    );
}