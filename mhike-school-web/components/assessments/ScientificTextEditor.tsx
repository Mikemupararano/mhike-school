"use client";

import {
    ChangeEvent,
    KeyboardEvent,
    MouseEvent,
    useCallback,
    useEffect,
    useRef,
} from "react";

type ScientificTextEditorProps = {
    value: string;
    onChange: (value: string) => void;
    disabled?: boolean;
    rows?: number;
    maxLength?: number;
    placeholder?: string;
    className?: string;
    id?: string;
    name?: string;
    ariaLabel?: string;
};

const SUPERSCRIPT_MAP: Record<string, string> = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    "+": "⁺", "-": "⁻", "=": "⁼", "(": "⁽", ")": "⁾",
    a: "ᵃ", b: "ᵇ", c: "ᶜ", d: "ᵈ", e: "ᵉ", f: "ᶠ",
    g: "ᵍ", h: "ʰ", i: "ⁱ", j: "ʲ", k: "ᵏ", l: "ˡ",
    m: "ᵐ", n: "ⁿ", o: "ᵒ", p: "ᵖ", r: "ʳ", s: "ˢ",
    t: "ᵗ", u: "ᵘ", v: "ᵛ", w: "ʷ", x: "ˣ", y: "ʸ", z: "ᶻ",
};

const SUBSCRIPT_MAP: Record<string, string> = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
    "+": "₊", "-": "₋", "=": "₌", "(": "₍", ")": "₎",
    a: "ₐ", e: "ₑ", h: "ₕ", i: "ᵢ", j: "ⱼ", k: "ₖ", l: "ₗ",
    m: "ₘ", n: "ₙ", o: "ₒ", p: "ₚ", r: "ᵣ", s: "ₛ", t: "ₜ", x: "ₓ",
};

const NORMAL_MAP: Record<string, string> = {};

for (const [normal, formatted] of Object.entries(SUPERSCRIPT_MAP)) {
    NORMAL_MAP[formatted] = normal;
}

for (const [normal, formatted] of Object.entries(SUBSCRIPT_MAP)) {
    NORMAL_MAP[formatted] = normal;
}

function transformCharacters(
    value: string,
    map: Record<string, string>,
): string {
    return Array.from(value)
        .map(character => map[character] ?? character)
        .join("");
}

export default function ScientificTextEditor({
    value,
    onChange,
    disabled = false,
    rows = 3,
    maxLength = 20_000,
    placeholder,
    className = "",
    id,
    name,
    ariaLabel,
}: ScientificTextEditorProps) {
    const textareaRef =
        useRef<HTMLTextAreaElement | null>(null);

    const resizeTextarea =
        useCallback(
            () => {
                const textarea =
                    textareaRef.current;

                if (!textarea) {
                    return;
                }

                textarea.style.height =
                    "auto";

                textarea.style.height =
                    `${textarea.scrollHeight}px`;
            },
            [],
        );

    useEffect(
        () => {
            resizeTextarea();
        },
        [
            resizeTextarea,
            value,
        ],
    );

    const applySelectionTransform =
        useCallback(
            (
                map:
                    Record<string, string>,
            ) => {
                const textarea =
                    textareaRef.current;

                if (
                    !textarea
                    || disabled
                ) {
                    return;
                }

                const selectionStart =
                    textarea.selectionStart;

                const selectionEnd =
                    textarea.selectionEnd;

                if (
                    selectionStart
                    === selectionEnd
                ) {
                    textarea.focus();
                    return;
                }

                const selectedText =
                    value.slice(
                        selectionStart,
                        selectionEnd,
                    );

                const transformedText =
                    transformCharacters(
                        selectedText,
                        map,
                    );

                const nextValue =
                    value.slice(
                        0,
                        selectionStart,
                    )
                    + transformedText
                    + value.slice(
                        selectionEnd,
                    );

                onChange(
                    nextValue,
                );

                window.requestAnimationFrame(
                    () => {
                        const current =
                            textareaRef.current;

                        if (!current) {
                            return;
                        }

                        current.focus();

                        resizeTextarea();

                        current.setSelectionRange(
                            selectionStart,
                            selectionStart
                            + transformedText.length,
                        );
                    },
                );
            },
            [
                disabled,
                onChange,
                resizeTextarea,
                value,
            ],
        );

    const handleToolbarMouseDown =
        useCallback(
            (
                event:
                    MouseEvent<HTMLButtonElement>,
            ) => {
                event.preventDefault();
            },
            [],
        );

    const handleChange =
        useCallback(
            (
                event:
                    ChangeEvent<HTMLTextAreaElement>,
            ) => {
                onChange(
                    event.target.value,
                );

                window.requestAnimationFrame(
                    () => {
                        resizeTextarea();
                    },
                );
            },
            [
                onChange,
                resizeTextarea,
            ],
        );

    const handleKeyDown =
        useCallback(
            (
                event:
                    KeyboardEvent<HTMLTextAreaElement>,
            ) => {
                if (
                    disabled
                    || !event.ctrlKey
                ) {
                    return;
                }

                if (
                    event.key === "."
                ) {
                    event.preventDefault();

                    applySelectionTransform(
                        SUPERSCRIPT_MAP,
                    );
                }

                if (
                    event.key === ","
                ) {
                    event.preventDefault();

                    applySelectionTransform(
                        SUBSCRIPT_MAP,
                    );
                }
            },
            [
                applySelectionTransform,
                disabled,
            ],
        );

    return (
        <div className="overflow-hidden rounded-lg border border-slate-300 bg-white focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
            <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-slate-50 px-2 py-2">
                <span className="mr-1 text-xs font-bold uppercase tracking-wide text-slate-400">
                    Scientific formatting
                </span>

                <button
                    type="button"
                    onMouseDown={
                        handleToolbarMouseDown
                    }
                    onClick={() =>
                        applySelectionTransform(
                            SUBSCRIPT_MAP,
                        )
                    }
                    disabled={
                        disabled
                    }
                    title="Subscript selected text (Ctrl+,)"
                    className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-bold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    x₂
                </button>

                <button
                    type="button"
                    onMouseDown={
                        handleToolbarMouseDown
                    }
                    onClick={() =>
                        applySelectionTransform(
                            SUPERSCRIPT_MAP,
                        )
                    }
                    disabled={
                        disabled
                    }
                    title="Superscript selected text (Ctrl+.)"
                    className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-bold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    x²
                </button>

                <button
                    type="button"
                    onMouseDown={
                        handleToolbarMouseDown
                    }
                    onClick={() =>
                        applySelectionTransform(
                            NORMAL_MAP,
                        )
                    }
                    disabled={
                        disabled
                    }
                    title="Return selected subscript/superscript text to normal"
                    className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    Normal
                </button>

                <span className="ml-auto text-xs text-slate-400">
                    Select text, then choose x₂ or x²
                </span>
            </div>

            <textarea
                ref={
                    textareaRef
                }
                id={
                    id
                }
                name={
                    name
                }
                aria-label={
                    ariaLabel
                }
                value={
                    value
                }
                onChange={
                    handleChange
                }
                onKeyDown={
                    handleKeyDown
                }
                disabled={
                    disabled
                }
                rows={
                    rows
                }
                maxLength={
                    maxLength
                }
                placeholder={
                    placeholder
                }
                className={`block min-h-28 w-full resize-none overflow-hidden border-0 bg-white px-3 py-3 text-sm leading-7 text-slate-900 outline-none disabled:bg-slate-100 disabled:text-slate-500 ${className}`}
            />
        </div>
    );
}