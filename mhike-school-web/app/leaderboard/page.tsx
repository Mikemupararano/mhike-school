"use client";

import React from "react";
import { useRouter } from "next/navigation";

export default function LeaderboardPage() {
    const router = useRouter();

    const rows = [
        ["1", "Emma W.", "1250 XP"],
        ["2", "Alex T.", "1100 XP"],
        ["3", "You", "980 XP"],
    ];

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

            <h1 style={{ fontSize: 32, fontWeight: 900, marginBottom: 8 }}>Leaderboard</h1>

            <section
                style={{
                    marginTop: 20,
                    background: "white",
                    border: "1px solid #E5E7EB",
                    borderRadius: 18,
                    padding: 20,
                }}
            >
                {rows.map(([rank, name, score]) => (
                    <div
                        key={rank}
                        style={{
                            display: "grid",
                            gridTemplateColumns: "50px 1fr auto",
                            gap: 12,
                            padding: "12px 0",
                            borderBottom: "1px solid #F3F4F6",
                        }}
                    >
                        <div style={{ fontWeight: 900, color: "#2563EB" }}>{rank}</div>
                        <div>{name}</div>
                        <div style={{ fontWeight: 800 }}>{score}</div>
                    </div>
                ))}
            </section>
        </main>
    );
}