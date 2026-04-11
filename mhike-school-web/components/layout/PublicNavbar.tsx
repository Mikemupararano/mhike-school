"use client";

import { useState } from "react";
import Link from "next/link";
import BrandLogo from "@/components/layout/BrandLogo";

export default function PublicNavbar() {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <header className="sticky top-0 z-50 border-b border-[#1e3a5f] bg-[#0f2d4a] shadow-[0_12px_30px_rgba(15,23,42,0.14)]">
            <div className="mx-auto max-w-[1800px] px-4 sm:px-8 lg:px-16">
                <div className="flex h-20 items-center justify-between sm:h-24">
                    <BrandLogo />

                    <div className="hidden md:block text-sm font-semibold tracking-[0.08em] text-slate-300 sm:text-base">
                        Learning platform
                    </div>

                    <button
                        type="button"
                        aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
                        aria-expanded={mobileMenuOpen}
                        onClick={() => setMobileMenuOpen((prev) => !prev)}
                        className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white transition hover:bg-white/10 md:hidden"
                    >
                        <span className="sr-only">Menu</span>
                        <div className="flex w-5 flex-col gap-1.5">
                            <span
                                className={`block h-0.5 w-5 rounded bg-white transition ${mobileMenuOpen ? "translate-y-2 rotate-45" : ""
                                    }`}
                            />
                            <span
                                className={`block h-0.5 w-5 rounded bg-white transition ${mobileMenuOpen ? "opacity-0" : ""
                                    }`}
                            />
                            <span
                                className={`block h-0.5 w-5 rounded bg-white transition ${mobileMenuOpen ? "-translate-y-2 -rotate-45" : ""
                                    }`}
                            />
                        </div>
                    </button>
                </div>

                {mobileMenuOpen ? (
                    <div className="border-t border-white/10 py-4 md:hidden">
                        <div className="flex flex-col gap-3">
                            <div className="text-sm font-semibold tracking-[0.08em] text-slate-300">
                                Learning platform
                            </div>

                            <nav className="flex flex-col gap-2">
                                <Link
                                    href="/"
                                    className="rounded-xl px-3 py-2 text-sm font-semibold text-white/90 transition hover:bg-white/5 hover:text-white"
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    Home
                                </Link>
                                <Link
                                    href="/login"
                                    className="rounded-xl px-3 py-2 text-sm font-semibold text-white/90 transition hover:bg-white/5 hover:text-white"
                                    onClick={() => setMobileMenuOpen(false)}
                                >
                                    Sign in
                                </Link>
                            </nav>
                        </div>
                    </div>
                ) : null}
            </div>
        </header>
    );
}