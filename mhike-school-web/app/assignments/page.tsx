"use client";

import React from "react";
import { useRouter } from "next/navigation";

export default function AssignmentsPage() {
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

            <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 8 }}>Assignments</h1>
            <p style={{ color: "#6B7280", marginTop: 0 }}>
                View and submit coursework.
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
                <div style={{ fontSize: 22, fontWeight: 800 }}>Project Report Submission</div>
                <p style={{ color: "#6B7280" }}>Due this week</p>
                <button
                    style={{
                        padding: "12px 16px",
                        borderRadius: 12,
                        border: "none",
                        background: "#2563EB",
                        color: "white",
                        fontWeight: 800,
                        cursor: "pointer",
                    }}
                >
                    Upload Submission
                </button>
            </section>
        </main>
    );
}