"use client";

import React from "react";
import { useRouter } from "next/navigation";

export default function DiscussionsPage() {
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

            <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 8 }}>Discussions</h1>
            <p style={{ color: "#6B7280", marginTop: 0 }}>
                Join conversations with your classmates and instructors.
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
                <p><b>Physics Forum</b></p>
                <p style={{ color: "#6B7280" }}>
                    Discussion threads will appear here in the next version.
                </p>
            </section>
        </main>
    );
}