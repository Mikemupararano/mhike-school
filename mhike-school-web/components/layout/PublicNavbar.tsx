"use client";

import { useState } from "react";
import Link from "next/link";

import BrandLogo from "@/components/layout/BrandLogo";

export default function PublicNavbar() {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    function closeMobileMenu() {
        setMobileMenuOpen(false);
    }

    return (
        <header className="sticky top-0 z-50 h-20 shrink-0 border-b border-white/10 bg-[#0F2D4A] shadow-[0_10px_30px_rgba(15,23,42,0.16)] sm:h-24">
            <div className="mx-auto h-full max-w-[1800px] px-4 sm:px-8 lg:px-16">
                <div className="flex h-full items-center justify-between">
                    <BrandLogo />

                    <nav
                        aria-label="Public navigation"
                        className="hidden items-center gap-3 md:flex"
                    >
                        <Link
                            href="/"
                            className="rounded-xl px-4 py-3 text-base font-bold text-slate-200 transition hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/20"
                        >
                            Home
                        </Link>

                        <Link
                            href="/login"
                            aria-current="page"
                            className="rounded-xl border border-white/15 bg-white/10 px-5 py-3 text-base font-black text-white transition hover:bg-white/15 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/20"
                        >
                            Sign in
                        </Link>
                    </nav>

                    <button
                        type="button"
                        aria-label={
                            mobileMenuOpen
                                ? "Close navigation menu"
                                : "Open navigation menu"
                        }
                        aria-expanded={mobileMenuOpen}
                        aria-controls="public-mobile-navigation"
                        onClick={() => setMobileMenuOpen((current) => !current)}
                        className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-white transition hover:bg-white/10 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-white/20 md:hidden"
                    >
                        <span className="sr-only">
                            {mobileMenuOpen ? "Close menu" : "Open menu"}
                        </span>

                        <span className="flex w-5 flex-col gap-1.5">
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
                        </span>
                    </button>
                </div>

                {mobileMenuOpen ? (
                    <nav
                        id="public-mobile-navigation"
                        aria-label="Mobile public navigation"
                        className="absolute inset-x-0 top-20 border-t border-white/10 bg-[#0F2D4A] px-4 py-4 shadow-lg sm:top-24 sm:px-8 md:hidden"
                    >
                        <div className="mx-auto flex max-w-[1800px] flex-col gap-2">
                            <Link
                                href="/"
                                onClick={closeMobileMenu}
                                className="rounded-xl px-4 py-3 text-base font-bold text-slate-200 transition hover:bg-white/10 hover:text-white"
                            >
                                Home
                            </Link>

                            <Link
                                href="/login"
                                aria-current="page"
                                onClick={closeMobileMenu}
                                className="rounded-xl bg-white/10 px-4 py-3 text-base font-black text-white transition hover:bg-white/15"
                            >
                                Sign in
                            </Link>
                        </div>
                    </nav>
                ) : null}
            </div>
        </header>
    );
}