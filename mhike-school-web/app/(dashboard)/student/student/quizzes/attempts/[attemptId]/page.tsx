"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
    type MouseEvent,
    type PointerEvent,
} from "react";

type QuestionType =
    | "written"
    | "numeric"
    | "structural"
    | "multiple_choice"
    | "multiple_choice_single"
    | "multiple_choice_multiple"
    | "true_false"
    | "diagram_annotation"
    | string;

type ResponseStatus =
    | "not_started"
    | "in_progress"
    | "submitted"
    | "void"
    | string;

type AssessmentOption = {
    id: number;
    text: string;
    order: number;
};

type AssessmentAsset = {
    id: number;
    asset_type: string;
    alt_text: string | null;
    caption: string | null;
    order: number;
    content_url: string;
};

type AssessmentInteractionTool = {
    tool_id: string;
    tool_type: string;
    label: string;
    symbol?: string | null;
    subject?: string | null;
};

type AssessmentInteractionConfig = {
    version: number;
    mode: string;
    palette_id: string | null;
    palette_label: string | null;
    coordinate_system: string;
    snap_to_grid: boolean;
    tools: AssessmentInteractionTool[];
    max_annotations?: number | null;
    allow_undo: boolean;
    allow_clear: boolean;
};

type AssessmentQuestion = {
    id: number;
    assessment_id: number;
    section_id: number | null;
    parent_question_id: number | null;
    question_number: string;
    title: string | null;
    prompt: string | null;
    question_type: QuestionType;
    maximum_mark: number | string;
    order: number;
    is_markable: boolean;
    options: AssessmentOption[];
    assets: AssessmentAsset[];
    interaction_config: AssessmentInteractionConfig | null;
};

type AssessmentSection = {
    id: number;
    assessment_id: number;
    title: string;
    description: string | null;
    order: number;
    is_optional: boolean;
};

type AssessmentResponse = {
    id: number;
    question_id: number;
    status: ResponseStatus;
    response_text: string | null;
    response_data: string | null;
    created_at: string;
    updated_at: string;
    submitted_at: string | null;
};

type AssessmentScript = {
    id: number;
    version: number;
    status: string;
    created_at: string;
    submitted_at: string | null;
};

type AssessmentSummary = {
    assessment_id: number;
    title: string;
    description: string | null;
    assessment_type: string | null;
    academic_year: string | null;
    term: string | null;
    assessment_status: string;
    candidate_status: string;
    scheduled_at: string | null;
    closes_at: string | null;
    started_at: string | null;
    submitted_at: string | null;
    can_start: boolean;
    can_resume: boolean;
    is_submitted: boolean;
};

type AssessmentAttempt = AssessmentSummary & {
    script: AssessmentScript;
    sections: AssessmentSection[];
    questions: AssessmentQuestion[];
    responses: AssessmentResponse[];
};

type AssessmentStart = AssessmentAttempt & {
    message: string;
};

type AssessmentSubmit = {
    assessment_id: number;
    candidate_status: string;
    script_status: string;
    submitted_at: string;
    message: string;
};

type DiagramAnnotation = {
    id: string;
    symbol: string;
    x: number;
    y: number;
};

type DiagramData = {
    type: "diagram_annotation";
    version: 1;
    asset_id: number;
    annotations: DiagramAnnotation[];
};

type OptionData = {
    type: "option_selection";
    version: 1;
    option_id: number;
};

type LocalResponse = {
    text: string;
    data: DiagramData | OptionData | null;
    status: ResponseStatus;
    saveState: "idle" | "dirty" | "saving" | "saved" | "error";
    error: string | null;
};

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL
    ?? "http://localhost:8000/api/v1";

const AUTOSAVE_MS = 700;

function getToken(): string | null {
    if (typeof window === "undefined") {
        return null;
    }

    return sessionStorage.getItem("mhike_token");
}

function resolveStudentAssetContentUrl(
    contentUrl: string,
): string {
    if (/^https?:\/\//i.test(contentUrl)) {
        return contentUrl;
    }

    const normalisedBase =
        API_BASE_URL.replace(/\/+$/, "");

    const apiPrefix =
        "/api/v1";

    if (
        contentUrl.startsWith(`${apiPrefix}/`)
        && normalisedBase.endsWith(apiPrefix)
    ) {
        return `${normalisedBase.slice(
            0,
            -apiPrefix.length,
        )}${contentUrl}`;
    }

    if (contentUrl.startsWith("/")) {
        return contentUrl;
    }

    return `${normalisedBase}/${contentUrl.replace(
        /^\/+/, 
        "",
    )}`;
}

function visualShouldAppearBeforePrompt(
    prompt: string | null,
): boolean {
    if (!prompt) {
        return false;
    }

    const normalised =
        prompt.toLowerCase();

    return (
        /\b(?:figure|diagram|graph|image|model)s?\s+(?:shown\s+)?above\b/.test(
            normalised,
        )
        || /\babove\s+(?:figure|diagram|graph|image|model)s?\b/.test(
            normalised,
        )
        || /\bshown\s+in\s+(?:the\s+)?above\s+(?:figure|diagram|graph|image|model)s?\b/.test(
            normalised,
        )
    );
}


function errorMessage(
    body: unknown,
    fallback: string,
): string {
    if (
        typeof body !== "object"
        || body === null
    ) {
        return fallback;
    }

    const value = body as Record<string, unknown>;

    if (
        typeof value.detail === "string"
        && value.detail.trim()
    ) {
        return value.detail;
    }

    if (
        typeof value.message === "string"
        && value.message.trim()
    ) {
        return value.message;
    }

    const nested = value.error;

    if (
        typeof nested === "object"
        && nested !== null
    ) {
        const record = nested as Record<string, unknown>;

        if (
            typeof record.message === "string"
            && record.message.trim()
        ) {
            return record.message;
        }

        if (
            typeof record.detail === "string"
            && record.detail.trim()
        ) {
            return record.detail;
        }
    }

    return fallback;
}

async function api<T>(
    path: string,
    init: RequestInit = {},
): Promise<T> {
    const token = getToken();

    if (!token) {
        throw new Error(
            "Your session has expired. Please sign in again.",
        );
    }

    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${token}`);

    if (
        init.body !== undefined
        && !headers.has("Content-Type")
    ) {
        headers.set("Content-Type", "application/json");
    }

    const response = await fetch(
        `${API_BASE_URL}${path}`,
        {
            ...init,
            headers,
            cache: "no-store",
        },
    );

    if (!response.ok) {
        let body: unknown = null;

        try {
            body = await response.json();
        } catch {
            body = null;
        }

        throw new Error(
            errorMessage(
                body,
                `Request failed with status ${response.status}.`,
            ),
        );
    }

    return await response.json() as T;
}

function humanise(value: string | null | undefined): string {
    if (!value) {
        return "Not specified";
    }

    return value
        .replace(/[_-]+/g, " ")
        .replace(
            /\b\w/g,
            character => character.toUpperCase(),
        );
}

function formatDateTime(value: string | null): string {
    if (!value) {
        return "Not set";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            dateStyle: "medium",
            timeStyle: "short",
        },
    ).format(date);
}

function parseData(
    value: string | null,
): DiagramData | OptionData | null {
    if (!value) {
        return null;
    }

    try {
        const decoded = JSON.parse(value) as unknown;

        if (
            typeof decoded !== "object"
            || decoded === null
        ) {
            return null;
        }

        const record = decoded as Record<string, unknown>;

        if (
            record.type === "diagram_annotation"
            && record.version === 1
            && typeof record.asset_id === "number"
            && Array.isArray(record.annotations)
        ) {
            return decoded as DiagramData;
        }

        if (
            record.type === "option_selection"
            && record.version === 1
            && typeof record.option_id === "number"
        ) {
            return decoded as OptionData;
        }
    } catch {
        return null;
    }

    return null;
}

function toLocalResponse(
    response: AssessmentResponse | undefined,
): LocalResponse {
    return {
        text: response?.response_text ?? "",
        data: parseData(response?.response_data ?? null),
        status: response?.status ?? "not_started",
        saveState: "idle",
        error: null,
    };
}

function hasAnswer(value: LocalResponse | undefined): boolean {
    return Boolean(
        value
        && (
            value.text.trim()
            || value.data
        ),
    );
}

function timeRemaining(
    closesAt: string | null,
    now: number,
): string | null {
    if (!closesAt) {
        return null;
    }

    const end = new Date(closesAt).getTime();

    if (Number.isNaN(end)) {
        return null;
    }

    const milliseconds = Math.max(0, end - now);

    if (milliseconds === 0) {
        return "Closed";
    }

    const seconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainder = seconds % 60;

    return hours > 0
        ? `${hours}h ${minutes}m ${remainder}s remaining`
        : `${minutes}m ${remainder}s remaining`;
}

function hasClosed(
    closesAt: string | null,
    now: number,
): boolean {
    if (!closesAt) {
        return false;
    }

    const end = new Date(closesAt).getTime();

    return (
        !Number.isNaN(end)
        && now >= end
    );
}

function SecureAsset({
    asset,
}: {
    asset: AssessmentAsset;
}) {
    const [url, setUrl] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(
        () => {
            let cancelled = false;
            let objectUrl: string | null = null;

            async function load() {
                const token = getToken();

                if (!token) {
                    setError("Your session has expired.");
                    return;
                }

                try {
                    const response = await fetch(
                        resolveStudentAssetContentUrl(
                            asset.content_url,
                        ),
                        {
                            headers: {
                                Authorization: `Bearer ${token}`,
                            },
                            cache: "no-store",
                        },
                    );

                    if (!response.ok) {
                        throw new Error(
                            "Unable to load this assessment image.",
                        );
                    }

                    objectUrl = URL.createObjectURL(
                        await response.blob(),
                    );

                    if (!cancelled) {
                        setUrl(objectUrl);
                    }
                } catch (loadError: unknown) {
                    if (!cancelled) {
                        setError(
                            loadError instanceof Error
                                ? loadError.message
                                : "Unable to load this assessment image.",
                        );
                    }
                }
            }

            void load();

            return () => {
                cancelled = true;

                if (objectUrl) {
                    URL.revokeObjectURL(objectUrl);
                }
            };
        },
        [asset.content_url],
    );

    if (error) {
        return (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
                {error}
            </div>
        );
    }

    if (!url) {
        return (
            <div className="flex min-h-48 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-sm font-semibold text-slate-500">
                Loading assessment image...
            </div>
        );
    }

    return (
        <figure className="space-y-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
                src={url}
                alt={asset.alt_text ?? "Assessment question image"}
                className="max-h-[560px] w-full rounded-xl border border-slate-200 bg-white object-contain"
            />
            {asset.caption && (
                <figcaption className="text-sm text-slate-600">
                    {asset.caption}
                </figcaption>
            )}
        </figure>
    );
}

function DiagramEditor({
    asset,
    annotations,
    interactionConfig,
    disabled,
    onChange,
}: {
    asset: AssessmentAsset;
    annotations: DiagramAnnotation[];
    interactionConfig: AssessmentInteractionConfig | null;
    disabled: boolean;
    onChange: (annotations: DiagramAnnotation[]) => void;
}) {
    const symbolTools = useMemo(
        () => (
            interactionConfig?.tools.filter(
                tool =>
                    tool.tool_type === "symbol"
                    && typeof tool.symbol === "string"
                    && tool.symbol.trim().length > 0,
            ) ?? []
        ),
        [interactionConfig],
    );

    const [selectedToolId, setSelectedToolId] = useState<string | null>(
        symbolTools[0]?.tool_id ?? null,
    );
    const [legacySymbol, setLegacySymbol] = useState("×");
    const [selectedAnnotationId, setSelectedAnnotationId] =
        useState<string | null>(null);
    const [draggingAnnotationId, setDraggingAnnotationId] =
        useState<string | null>(null);
    const [url, setUrl] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const diagramRef = useRef<HTMLDivElement | null>(null);
    const dragStartRef = useRef<{
        annotationId: string;
        pointerId: number;
        clientX: number;
        clientY: number;
        x: number;
        y: number;
        moved: boolean;
    } | null>(null);

    useEffect(
        () => {
            if (symbolTools.length === 0) {
                setSelectedToolId(null);
                return;
            }

            setSelectedToolId(current => (
                current
                && symbolTools.some(tool => tool.tool_id === current)
                    ? current
                    : symbolTools[0].tool_id
            ));
        },
        [symbolTools],
    );

    useEffect(
        () => {
            if (
                selectedAnnotationId
                && !annotations.some(
                    annotation => annotation.id === selectedAnnotationId,
                )
            ) {
                setSelectedAnnotationId(null);
            }
        },
        [annotations, selectedAnnotationId],
    );

    useEffect(
        () => {
            let cancelled = false;
            let objectUrl: string | null = null;

            async function load() {
                const token = getToken();

                if (!token) {
                    setError("Your session has expired.");
                    return;
                }

                try {
                    const response = await fetch(
                        resolveStudentAssetContentUrl(
                            asset.content_url,
                        ),
                        {
                            headers: {
                                Authorization: `Bearer ${token}`,
                            },
                            cache: "no-store",
                        },
                    );

                    if (!response.ok) {
                        throw new Error("Unable to load the diagram.");
                    }

                    objectUrl = URL.createObjectURL(
                        await response.blob(),
                    );

                    if (!cancelled) {
                        setUrl(objectUrl);
                    }
                } catch (loadError: unknown) {
                    if (!cancelled) {
                        setError(
                            loadError instanceof Error
                                ? loadError.message
                                : "Unable to load the diagram.",
                        );
                    }
                }
            }

            void load();

            return () => {
                cancelled = true;

                if (objectUrl) {
                    URL.revokeObjectURL(objectUrl);
                }
            };
        },
        [asset.content_url],
    );

    const selectedTool =
        symbolTools.find(tool => tool.tool_id === selectedToolId)
        ?? symbolTools[0]
        ?? null;

    const selectedAnnotation =
        annotations.find(
            annotation => annotation.id === selectedAnnotationId,
        ) ?? null;

    const symbol =
        selectedTool?.symbol?.trim()
        || legacySymbol.trim();

    const configuredPalette = symbolTools.length > 0;
    const maxAnnotations =
        interactionConfig?.max_annotations
        && interactionConfig.max_annotations > 0
            ? interactionConfig.max_annotations
            : null;

    function place(event: MouseEvent<HTMLDivElement>) {
        if (
            disabled
            || !symbol
            || draggingAnnotationId
            || (
                maxAnnotations !== null
                && annotations.length >= maxAnnotations
            )
        ) {
            return;
        }

        const box = event.currentTarget.getBoundingClientRect();

        if (
            box.width <= 0
            || box.height <= 0
        ) {
            return;
        }

        const x = Math.min(
            1,
            Math.max(
                0,
                (event.clientX - box.left) / box.width,
            ),
        );

        const y = Math.min(
            1,
            Math.max(
                0,
                (event.clientY - box.top) / box.height,
            ),
        );

        setSelectedAnnotationId(null);

        onChange([
            ...annotations,
            {
                id: `annotation-${Date.now()}-${Math.random()
                    .toString(36)
                    .slice(2, 8)}`,
                symbol,
                x,
                y,
            },
        ]);
    }

    function removeAnnotation(annotationId: string) {
        if (disabled) {
            return;
        }

        setSelectedAnnotationId(null);

        onChange(
            annotations.filter(
                item => item.id !== annotationId,
            ),
        );
    }

    function undoLast() {
        if (
            disabled
            || annotations.length === 0
        ) {
            return;
        }

        setSelectedAnnotationId(null);
        onChange(annotations.slice(0, -1));
    }

    function beginDrag(
        event: PointerEvent<HTMLButtonElement>,
        annotation: DiagramAnnotation,
    ) {
        if (disabled) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const diagram = diagramRef.current;

        if (!diagram) {
            return;
        }

        try {
            diagram.setPointerCapture(event.pointerId);
        } catch {
            // Pointer capture is best-effort; dragging still works in-bounds.
        }

        dragStartRef.current = {
            annotationId: annotation.id,
            pointerId: event.pointerId,
            clientX: event.clientX,
            clientY: event.clientY,
            x: annotation.x,
            y: annotation.y,
            moved: false,
        };

        setDraggingAnnotationId(annotation.id);
    }

    function moveDrag(event: PointerEvent<HTMLDivElement>) {
        const drag = dragStartRef.current;
        const diagram = diagramRef.current;

        if (
            disabled
            || !drag
            || !diagram
            || drag.pointerId !== event.pointerId
        ) {
            return;
        }

        event.preventDefault();

        const box = diagram.getBoundingClientRect();

        if (
            box.width <= 0
            || box.height <= 0
        ) {
            return;
        }

        const deltaX = event.clientX - drag.clientX;
        const deltaY = event.clientY - drag.clientY;

        if (
            !drag.moved
            && Math.hypot(deltaX, deltaY) >= 6
        ) {
            drag.moved = true;
            setSelectedAnnotationId(null);
        }

        if (!drag.moved) {
            return;
        }

        const nextX = Math.min(
            1,
            Math.max(
                0,
                drag.x + (deltaX / box.width),
            ),
        );

        const nextY = Math.min(
            1,
            Math.max(
                0,
                drag.y + (deltaY / box.height),
            ),
        );

        onChange(
            annotations.map(annotation => (
                annotation.id === drag.annotationId
                    ? {
                        ...annotation,
                        x: nextX,
                        y: nextY,
                    }
                    : annotation
            )),
        );
    }

    function endDrag(event: PointerEvent<HTMLDivElement>) {
        const drag = dragStartRef.current;
        const diagram = diagramRef.current;

        if (
            !drag
            || drag.pointerId !== event.pointerId
        ) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        if (
            diagram
            && diagram.hasPointerCapture(event.pointerId)
        ) {
            try {
                diagram.releasePointerCapture(event.pointerId);
            } catch {
                // Ignore a capture already released by the browser.
            }
        }

        dragStartRef.current = null;
        setDraggingAnnotationId(null);

        if (!drag.moved) {
            setSelectedAnnotationId(current =>
                current === drag.annotationId
                    ? null
                    : drag.annotationId,
            );
        }
    }

    function cancelDrag(event: PointerEvent<HTMLDivElement>) {
        const drag = dragStartRef.current;

        if (
            !drag
            || drag.pointerId !== event.pointerId
        ) {
            return;
        }

        dragStartRef.current = null;
        setDraggingAnnotationId(null);
    }

    return (
        <div className="space-y-4">
            {configuredPalette ? (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <p className="text-sm font-extrabold text-blue-950">
                                {interactionConfig?.palette_label
                                    ?? "Annotation tools"}
                            </p>
                            <p className="mt-1 text-sm font-semibold text-blue-900">
                                Select a particle and click the diagram to place it.
                            </p>
                        </div>

                        {interactionConfig?.palette_id && (
                            <span className="rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-bold text-blue-800">
                                {interactionConfig.palette_id}
                            </span>
                        )}
                    </div>

                    <div
                        className="mt-4 flex flex-wrap gap-3"
                        role="toolbar"
                        aria-label={interactionConfig?.palette_label ?? "Annotation tools"}
                    >
                        {symbolTools.map(tool => {
                            const selected =
                                tool.tool_id === selectedTool?.tool_id;

                            return (
                                <button
                                    key={tool.tool_id}
                                    type="button"
                                    disabled={disabled}
                                    aria-pressed={selected}
                                    onClick={() => setSelectedToolId(tool.tool_id)}
                                    className={`flex min-w-32 items-center gap-3 rounded-xl border px-4 py-3 text-left transition ${
                                        selected
                                            ? "border-blue-700 bg-blue-700 text-white shadow-sm"
                                            : "border-blue-200 bg-white text-blue-950 hover:border-blue-400 hover:bg-blue-100"
                                    } disabled:cursor-not-allowed disabled:opacity-50`}
                                >
                                    <span
                                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-2xl font-black ${
                                            selected
                                                ? "bg-white/15 text-white"
                                                : "bg-blue-50 text-blue-950"
                                        }`}
                                        aria-hidden="true"
                                    >
                                        {tool.symbol}
                                    </span>
                                    <span className="font-extrabold">
                                        {tool.label}
                                    </span>
                                </button>
                            );
                        })}
                    </div>

                    {annotations.length > 0 && (
                        <p className="mt-3 text-sm font-semibold text-blue-900">
                            Drag a placed symbol to reposition it. Tap or click it to show removal controls.
                        </p>
                    )}
                </div>
            ) : (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                    <label className="text-sm font-extrabold text-blue-950">
                        Symbol to place
                    </label>
                    <div className="mt-2 flex flex-wrap items-center gap-3">
                        <input
                            value={legacySymbol}
                            onChange={event => setLegacySymbol(event.target.value)}
                            maxLength={20}
                            disabled={disabled}
                            className="w-32 rounded-lg border border-blue-200 bg-white px-3 py-2 text-xl font-black text-slate-950 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 disabled:bg-slate-100"
                        />
                        <p className="text-sm font-semibold text-blue-900">
                            Enter the symbol required by the question, then click the correct position on the diagram.
                        </p>
                    </div>
                </div>
            )}

            {maxAnnotations !== null
                && annotations.length >= maxAnnotations
                && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
                        Maximum number of annotations reached.
                    </div>
                )}

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">
                    {error}
                </div>
            )}

            {!url && !error && (
                <div className="flex min-h-64 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 font-semibold text-slate-500">
                    Loading diagram...
                </div>
            )}

            {url && (
                <div
                    ref={diagramRef}
                    onClick={place}
                    onPointerMove={moveDrag}
                    onPointerUp={endDrag}
                    onPointerCancel={cancelDrag}
                    onDragStart={event => event.preventDefault()}
                    className={`relative select-none overflow-hidden rounded-xl border border-slate-300 bg-white ${
                        disabled
                            ? "cursor-not-allowed"
                            : "cursor-crosshair"
                    }`}
                    style={{ touchAction: "none" }}
                >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                        src={url}
                        alt={asset.alt_text ?? "Interactive assessment diagram"}
                        className="pointer-events-none block h-auto w-full select-none"
                        draggable={false}
                    />

                    {annotations.map(annotation => (
                        <button
                            key={annotation.id}
                            type="button"
                            title="Drag to reposition; tap for options"
                            disabled={disabled}
                            draggable={false}
                            onDragStart={event => event.preventDefault()}
                            onPointerDown={event => beginDrag(event, annotation)}
                            onClick={event => {
                                event.preventDefault();
                                event.stopPropagation();
                            }}
                            className={`absolute flex h-5 w-5 -translate-x-1/2 -translate-y-1/2 select-none items-center justify-center rounded-full border bg-white text-[13px] font-black shadow-sm ${
                                draggingAnnotationId === annotation.id
                                    ? "z-30 cursor-grabbing border-blue-800 text-blue-950 ring-4 ring-blue-200"
                                    : "z-10 cursor-grab border-blue-600 text-blue-950 hover:border-blue-800 hover:ring-2 hover:ring-blue-100"
                            } disabled:cursor-not-allowed`}
                            style={{
                                left: `${annotation.x * 100}%`,
                                top: `${annotation.y * 100}%`,
                                touchAction: "none",
                                WebkitUserSelect: "none",
                                userSelect: "none",
                            }}
                        >
                            <span
                                className="pointer-events-none select-none"
                                aria-hidden="true"
                            >
                                {annotation.symbol}
                            </span>
                        </button>
                    ))}

                    {selectedAnnotation && (
                        <div
                            className="absolute z-40 flex -translate-x-1/2 items-center gap-2 rounded-lg border border-slate-300 bg-white px-2 py-2 shadow-lg"
                            style={{
                                left: `${selectedAnnotation.x * 100}%`,
                                top: `${selectedAnnotation.y * 100}%`,
                                transform:
                                    selectedAnnotation.y < 0.18
                                        ? "translate(-50%, 16px)"
                                        : "translate(-50%, calc(-100% - 16px))",
                            }}
                            onPointerDown={event => event.stopPropagation()}
                            onClick={event => event.stopPropagation()}
                        >
                            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-100 text-base font-black text-slate-900">
                                {selectedAnnotation.symbol}
                            </span>

                            <button
                                type="button"
                                disabled={disabled}
                                onClick={() => removeAnnotation(selectedAnnotation.id)}
                                className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-extrabold text-white hover:bg-red-700 disabled:opacity-50"
                            >
                                Remove
                            </button>

                            <button
                                type="button"
                                onClick={() => setSelectedAnnotationId(null)}
                                className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50"
                            >
                                Cancel
                            </button>
                        </div>
                    )}
                </div>
            )}

            {annotations.length > 0 && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <span className="text-sm font-semibold text-slate-700">
                        {annotations.length} annotation{annotations.length === 1 ? "" : "s"} placed
                    </span>

                    <div className="flex flex-wrap gap-2">
                        {(interactionConfig?.allow_undo ?? true) && (
                            <button
                                type="button"
                                disabled={disabled || annotations.length === 0}
                                onClick={undoLast}
                                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                            >
                                Undo last
                            </button>
                        )}

                        {(interactionConfig?.allow_clear ?? true) && (
                            <button
                                type="button"
                                disabled={disabled}
                                onClick={() => {
                                    setSelectedAnnotationId(null);
                                    onChange([]);
                                }}
                                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                            >
                                Clear diagram
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function StudentAssessmentAttemptPage() {
    const router = useRouter();
    const params = useParams<{ attemptId: string }>();
    const assessmentId = Number(params.attemptId);

    const [summary, setSummary] = useState<AssessmentSummary | null>(null);
    const [attempt, setAttempt] = useState<AssessmentAttempt | null>(null);
    const [responses, setResponses] =
        useState<Record<number, LocalResponse>>({});
    const [questionIndex, setQuestionIndex] = useState(0);
    const [loading, setLoading] = useState(true);
    const [starting, setStarting] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);
    const [submitted, setSubmitted] = useState<AssessmentSubmit | null>(null);
    const [now, setNow] = useState(Date.now());

    const timers = useRef<
        Record<number, ReturnType<typeof setTimeout>>
    >({});

    const saveVersion = useRef<Record<number, number>>({});

    const initialiseAttempt = useCallback(
        (value: AssessmentAttempt) => {
            const stored = new Map(
                value.responses.map(
                    response => [response.question_id, response],
                ),
            );

            const next: Record<number, LocalResponse> = {};

            value.questions.forEach(question => {
                next[question.id] = toLocalResponse(
                    stored.get(question.id),
                );
            });

            setSummary(value);
            setAttempt(value);
            setResponses(next);
            setQuestionIndex(current =>
                Math.min(
                    current,
                    Math.max(0, value.questions.length - 1),
                ),
            );
        },
        [],
    );

    const load = useCallback(
        async () => {
            if (
                !Number.isInteger(assessmentId)
                || assessmentId < 1
            ) {
                setError("This assessment link is invalid.");
                setLoading(false);
                return;
            }

            try {
                setLoading(true);
                setError(null);

                const value = await api<AssessmentSummary>(
                    `/student-assessments/${assessmentId}`,
                );

                setSummary(value);

                if (
                    value.can_resume
                    && !value.is_submitted
                ) {
                    initialiseAttempt(
                        await api<AssessmentAttempt>(
                            `/student-assessments/${assessmentId}/attempt`,
                        ),
                    );
                }
            } catch (loadError: unknown) {
                const text =
                    loadError instanceof Error
                        ? loadError.message
                        : "Unable to load this assessment.";

                setError(text);

                if (text.toLowerCase().includes("sign in")) {
                    router.replace("/login");
                }
            } finally {
                setLoading(false);
            }
        },
        [assessmentId, initialiseAttempt, router],
    );

    useEffect(
        () => {
            void load();
        },
        [load],
    );

    useEffect(
        () => {
            const interval = window.setInterval(
                () => setNow(Date.now()),
                1000,
            );

            return () => window.clearInterval(interval);
        },
        [],
    );

    useEffect(
        () => {
            const activeTimers = timers.current;

            return () => {
                Object.values(activeTimers).forEach(clearTimeout);
            };
        },
        [],
    );

    const questions = useMemo(
        () => (
            attempt
                ? [...attempt.questions]
                    .filter(
                        question =>
                            question.is_markable
                            && question.question_type !== "structural",
                    )
                    .sort(
                        (a, b) => a.order - b.order || a.id - b.id,
                    )
                : []
        ),
        [attempt],
    );

    const currentQuestion =
        questions[questionIndex] ?? null;

    const answered = useMemo(
        () => questions.filter(
            question => hasAnswer(responses[question.id]),
        ).length,
        [questions, responses],
    );

    const progress =
        questions.length > 0
            ? Math.round((answered / questions.length) * 100)
            : 0;

    const closed = hasClosed(
        summary?.closes_at ?? null,
        now,
    );

    const remaining = timeRemaining(
        summary?.closes_at ?? null,
        now,
    );

    const persist = useCallback(
        async (
            question: AssessmentQuestion,
            state: LocalResponse,
            version: number,
        ) => {
            try {
                setResponses(current => ({
                    ...current,
                    [question.id]: {
                        ...(current[question.id] ?? state),
                        saveState: "saving",
                        error: null,
                    },
                }));

                const saved = await api<AssessmentResponse>(
                    `/student-assessments/${assessmentId}/responses/${question.id}`,
                    {
                        method: "PUT",
                        body: JSON.stringify({
                            response_text:
                                state.text.trim()
                                    ? state.text
                                    : null,
                            response_data: state.data,
                        }),
                    },
                );

                if (saveVersion.current[question.id] !== version) {
                    return;
                }

                setResponses(current => {
                    const live =
                        current[question.id]
                        ?? state;

                    return {
                        ...current,
                        [question.id]: {
                            ...live,
                            status: saved.status,
                            saveState: "saved",
                            error: null,
                        },
                    };
                });
            } catch (saveError: unknown) {
                if (saveVersion.current[question.id] !== version) {
                    return;
                }

                setResponses(current => ({
                    ...current,
                    [question.id]: {
                        ...(current[question.id] ?? state),
                        saveState: "error",
                        error:
                            saveError instanceof Error
                                ? saveError.message
                                : "Autosave failed.",
                    },
                }));
            }
        },
        [assessmentId],
    );

    const queueSave = useCallback(
        (
            question: AssessmentQuestion,
            state: LocalResponse,
        ) => {
            if (
                closed
                || summary?.is_submitted
            ) {
                return;
            }

            const existing = timers.current[question.id];

            if (existing) {
                clearTimeout(existing);
            }

            const version =
                (saveVersion.current[question.id] ?? 0) + 1;

            saveVersion.current[question.id] = version;

            timers.current[question.id] = setTimeout(
                () => {
                    void persist(question, state, version);
                },
                AUTOSAVE_MS,
            );
        },
        [closed, persist, summary?.is_submitted],
    );

    const update = useCallback(
        (
            question: AssessmentQuestion,
            producer: (value: LocalResponse) => LocalResponse,
        ) => {
            const base =
                responses[question.id]
                ?? toLocalResponse(undefined);

            const next = {
                ...producer(base),
                saveState: "dirty" as const,
                error: null,
            };

            setResponses(current => ({
                ...current,
                [question.id]: next,
            }));

            queueSave(question, next);
        },
        [queueSave, responses],
    );

    const flush = useCallback(
        async () => {
            for (const question of questions) {
                const timer = timers.current[question.id];

                if (timer) {
                    clearTimeout(timer);
                    delete timers.current[question.id];
                }

                const state = responses[question.id];

                if (
                    !state
                    || !(
                        state.saveState === "dirty"
                        || state.saveState === "error"
                    )
                ) {
                    continue;
                }

                const version =
                    (saveVersion.current[question.id] ?? 0) + 1;

                saveVersion.current[question.id] = version;

                await persist(question, state, version);
            }
        },
        [persist, questions, responses],
    );

    async function startAssessment() {
        try {
            setStarting(true);
            setError(null);

            const value = await api<AssessmentStart>(
                `/student-assessments/${assessmentId}/start`,
                { method: "POST" },
            );

            initialiseAttempt(value);
            setMessage(value.message);
        } catch (startError: unknown) {
            setError(
                startError instanceof Error
                    ? startError.message
                    : "Unable to start this assessment.",
            );
        } finally {
            setStarting(false);
        }
    }

    async function submitAssessment() {
        if (
            !attempt
            || submitting
            || closed
        ) {
            return;
        }

        const confirmed = window.confirm(
            "Submit this assessment now? You will not be able to change your answers afterwards.",
        );

        if (!confirmed) {
            return;
        }

        try {
            setSubmitting(true);
            setError(null);
            setMessage("Saving your latest answers...");

            await flush();

            const value = await api<AssessmentSubmit>(
                `/student-assessments/${assessmentId}/submit`,
                { method: "POST" },
            );

            setSubmitted(value);
            setMessage(value.message || "Assessment submitted.");
        } catch (submitError: unknown) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : "Unable to submit the assessment.",
            );
        } finally {
            setSubmitting(false);
        }
    }

    if (loading) {
        return (
            <main className="min-h-screen bg-slate-100 px-4 py-10 sm:px-6">
                <div className="mx-auto max-w-5xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
                    <div className="h-7 w-64 animate-pulse rounded bg-slate-200" />
                    <div className="mt-4 h-4 w-full animate-pulse rounded bg-slate-100" />
                    <div className="mt-2 h-4 w-3/4 animate-pulse rounded bg-slate-100" />
                </div>
            </main>
        );
    }

    if (
        error
        && !summary
    ) {
        return (
            <main className="min-h-screen bg-slate-100 px-4 py-10 sm:px-6">
                <div className="mx-auto max-w-3xl rounded-2xl border border-red-200 bg-white p-8 shadow-sm">
                    <h1 className="text-2xl font-black text-slate-950">
                        Unable to open assessment
                    </h1>
                    <p className="mt-3 text-red-700">
                        {error}
                    </p>
                    <Link
                        href="/student"
                        className="mt-6 inline-flex rounded-xl bg-blue-700 px-5 py-3 font-bold text-white hover:bg-blue-800"
                    >
                        Return to Student Dashboard
                    </Link>
                </div>
            </main>
        );
    }

    if (
        summary?.is_submitted
        || submitted
    ) {
        return (
            <main className="min-h-screen bg-slate-100 px-4 py-10 sm:px-6">
                <div className="mx-auto max-w-3xl rounded-2xl border border-emerald-200 bg-white p-8 shadow-sm">
                    <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-extrabold text-emerald-800">
                        Submitted
                    </span>
                    <h1 className="mt-4 text-3xl font-black text-slate-950">
                        {summary?.title ?? "Assessment submitted"}
                    </h1>
                    <p className="mt-3 text-slate-600">
                        Your assessment has been submitted successfully. Your answers can no longer be changed.
                    </p>
                    <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
                        Submitted:{" "}
                        <strong>
                            {formatDateTime(
                                submitted?.submitted_at
                                ?? summary?.submitted_at
                                ?? null,
                            )}
                        </strong>
                    </div>
                    <Link
                        href="/student"
                        className="mt-6 inline-flex rounded-xl bg-blue-700 px-5 py-3 font-bold text-white hover:bg-blue-800"
                    >
                        Return to Student Dashboard
                    </Link>
                </div>
            </main>
        );
    }

    if (
        summary
        && !attempt
    ) {
        return (
            <main className="min-h-screen bg-slate-100 px-4 py-10 sm:px-6">
                <div className="mx-auto max-w-4xl">
                    <Link
                        href="/student"
                        className="mb-5 inline-flex text-sm font-bold text-blue-700 hover:text-blue-900"
                    >
                        ← Student Dashboard
                    </Link>

                    <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
                        <p className="text-sm font-extrabold uppercase tracking-[0.16em] text-blue-700">
                            Online assessment
                        </p>
                        <h1 className="mt-2 text-3xl font-black text-slate-950">
                            {summary.title}
                        </h1>
                        {summary.description && (
                            <p className="mt-3 max-w-3xl leading-7 text-slate-600">
                                {summary.description}
                            </p>
                        )}

                        <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            {[
                                ["Type", humanise(summary.assessment_type)],
                                ["Term", summary.term ?? "Not specified"],
                                ["Opens", formatDateTime(summary.scheduled_at)],
                                ["Closes", formatDateTime(summary.closes_at)],
                            ].map(([label, value]) => (
                                <div
                                    key={label}
                                    className="rounded-xl border border-slate-200 bg-slate-50 p-4"
                                >
                                    <div className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                        {label}
                                    </div>
                                    <div className="mt-1 font-bold text-slate-900">
                                        {value}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {error && (
                            <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 font-semibold text-red-700">
                                {error}
                            </div>
                        )}

                        <div className="mt-7">
                            {summary.can_start ? (
                                <button
                                    type="button"
                                    data-custom-button="true"
                                    onClick={() => void startAssessment()}
                                    disabled={starting || closed}
                                    className="rounded-xl bg-blue-700 px-6 py-3 font-extrabold text-white hover:bg-blue-800 disabled:opacity-50"
                                >
                                    {starting
                                        ? "Starting..."
                                        : "Start assessment"}
                                </button>
                            ) : (
                                <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-3 font-semibold text-amber-900">
                                    This assessment cannot be started at the moment.
                                </div>
                            )}
                        </div>
                    </section>
                </div>
            </main>
        );
    }

    if (
        !attempt
        || !summary
    ) {
        return null;
    }

    const currentState =
        currentQuestion
            ? responses[currentQuestion.id]
            : undefined;

    return (
        <main className="min-h-screen bg-slate-100">
            <header className="sticky top-0 z-30 border-b border-slate-200 bg-[#0E1433] text-white shadow-sm">
                <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
                    <div className="min-w-0">
                        <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-200">
                            Online assessment
                        </p>
                        <h1 className="truncate text-xl font-black sm:text-2xl">
                            {attempt.title}
                        </h1>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                        {remaining && (
                            <span className={`rounded-full px-3 py-2 text-sm font-extrabold ${
                                closed
                                    ? "bg-red-100 text-red-800"
                                    : "bg-white/10 text-white"
                            }`}>
                                {remaining}
                            </span>
                        )}
                        <span className="rounded-full bg-white/10 px-3 py-2 text-sm font-bold">
                            {answered}/{questions.length} answered
                        </span>
                    </div>
                </div>

                <div className="h-1 bg-white/10">
                    <div
                        className="h-full bg-blue-400 transition-all"
                        style={{ width: `${progress}%` }}
                    />
                </div>
            </header>

            <div className="mx-auto grid max-w-[1500px] gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[280px_minmax(0,1fr)_280px]">
                <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:sticky lg:top-28">
                    <div className="flex items-center justify-between gap-2">
                        <h2 className="text-lg font-black text-slate-950">
                            Questions
                        </h2>
                        <span className="text-sm font-semibold text-slate-500">
                            {progress}%
                        </span>
                    </div>

                    <div className="mt-4 grid grid-cols-5 gap-2 lg:grid-cols-4">
                        {questions.map((question, index) => {
                            const selected = index === questionIndex;
                            const answeredQuestion =
                                hasAnswer(responses[question.id]);

                            return (
                                <button
                                    key={question.id}
                                    type="button"
                                    onClick={() => setQuestionIndex(index)}
                                    className={`aspect-square rounded-lg border text-sm font-extrabold ${
                                        selected
                                            ? "border-blue-700 bg-blue-700 text-white"
                                            : answeredQuestion
                                                ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                                                : "border-slate-200 bg-white text-slate-700"
                                    }`}
                                >
                                    {question.question_number}
                                </button>
                            );
                        })}
                    </div>
                </aside>

                <section className="min-w-0 space-y-5">
                    {closed && (
                        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 font-bold text-red-800">
                            This assessment has closed. Further answers cannot be saved or submitted.
                        </div>
                    )}

                    {error && (
                        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 font-semibold text-red-700">
                            {error}
                        </div>
                    )}

                    {message && (
                        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5 font-semibold text-blue-900">
                            {message}
                        </div>
                    )}

                    {currentQuestion ? (
                        <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <p className="text-sm font-extrabold uppercase tracking-[0.14em] text-blue-700">
                                        Question {currentQuestion.question_number}
                                    </p>
                                    {currentQuestion.title && (
                                        <h2 className="mt-2 text-2xl font-black text-slate-950">
                                            {currentQuestion.title}
                                        </h2>
                                    )}
                                </div>
                                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-extrabold text-slate-700">
                                    {Number(currentQuestion.maximum_mark)} mark{Number(currentQuestion.maximum_mark) === 1 ? "" : "s"}
                                </span>
                            </div>

                            {currentQuestion.question_type !== "diagram_annotation"
                                && currentQuestion.assets.length > 0
                                && visualShouldAppearBeforePrompt(
                                    currentQuestion.prompt,
                                )
                                && (
                                    <div className="mt-6 space-y-4">
                                        {[...currentQuestion.assets]
                                            .sort((a, b) => a.order - b.order)
                                            .map(asset => (
                                                <SecureAsset
                                                    key={asset.id}
                                                    asset={asset}
                                                />
                                            ))}
                                    </div>
                                )}

                            {currentQuestion.prompt && (
                                <div className="mt-5 whitespace-pre-wrap text-lg font-semibold leading-8 text-slate-900">
                                    {currentQuestion.prompt}
                                </div>
                            )}

                            {currentQuestion.question_type !== "diagram_annotation"
                                && currentQuestion.assets.length > 0
                                && !visualShouldAppearBeforePrompt(
                                    currentQuestion.prompt,
                                )
                                && (
                                    <div className="mt-6 space-y-4">
                                        {[...currentQuestion.assets]
                                            .sort((a, b) => a.order - b.order)
                                            .map(asset => (
                                                <SecureAsset
                                                    key={asset.id}
                                                    asset={asset}
                                                />
                                            ))}
                                    </div>
                                )}

                            <div className="mt-7 border-t border-slate-200 pt-6">
                                {(currentQuestion.question_type === "multiple_choice"
                                    || currentQuestion.question_type === "multiple_choice_single"
                                    || currentQuestion.question_type === "true_false") && (
                                    <div className="space-y-3">
                                        {[...currentQuestion.options]
                                            .sort((a, b) => a.order - b.order)
                                            .map(option => {
                                                const selected =
                                                    currentState?.data?.type === "option_selection"
                                                    && currentState.data.option_id === option.id;

                                                return (
                                                    <button
                                                        key={option.id}
                                                        type="button"
                                                        disabled={closed}
                                                        onClick={() => update(
                                                            currentQuestion,
                                                            state => ({
                                                                ...state,
                                                                text: "",
                                                                data: {
                                                                    type: "option_selection",
                                                                    version: 1,
                                                                    option_id: option.id,
                                                                },
                                                            }),
                                                        )}
                                                        className={`flex w-full items-start gap-3 rounded-xl border p-4 text-left ${
                                                            selected
                                                                ? "border-blue-600 bg-blue-50 ring-2 ring-blue-100"
                                                                : "border-slate-200 bg-white hover:bg-slate-50"
                                                        }`}
                                                    >
                                                        <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 ${
                                                            selected
                                                                ? "border-blue-700 bg-blue-700 text-white"
                                                                : "border-slate-300 bg-white"
                                                        }`}>
                                                            {selected ? "✓" : ""}
                                                        </span>
                                                        <span className="font-semibold text-slate-900">
                                                            {option.text}
                                                        </span>
                                                    </button>
                                                );
                                            })}
                                    </div>
                                )}

                                {currentQuestion.question_type === "diagram_annotation" && (
                                    currentQuestion.assets.length > 0
                                        ? (
                                            <DiagramEditor
                                                asset={currentQuestion.assets[0]}
                                                interactionConfig={currentQuestion.interaction_config}
                                                disabled={closed}
                                                annotations={
                                                    currentState?.data?.type === "diagram_annotation"
                                                        ? currentState.data.annotations
                                                        : []
                                                }
                                                onChange={annotations => update(
                                                    currentQuestion,
                                                    state => ({
                                                        ...state,
                                                        text: "",
                                                        data: {
                                                            type: "diagram_annotation",
                                                            version: 1,
                                                            asset_id: currentQuestion.assets[0].id,
                                                            annotations,
                                                        },
                                                    }),
                                                )}
                                            />
                                        )
                                        : (
                                            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 font-semibold text-amber-900">
                                                This diagram question does not have a candidate-visible diagram.
                                            </div>
                                        )
                                )}

                                {currentQuestion.question_type === "multiple_choice_multiple" && (
                                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 font-semibold text-amber-900">
                                        This multiple-answer question type is not yet enabled in the pupil assessment interface.
                                    </div>
                                )}

                                {![
                                    "multiple_choice",
                                    "multiple_choice_single",
                                    "multiple_choice_multiple",
                                    "true_false",
                                    "diagram_annotation",
                                ].includes(currentQuestion.question_type) && (
                                    currentQuestion.question_type === "numeric"
                                        ? (
                                            <input
                                                inputMode="decimal"
                                                value={currentState?.text ?? ""}
                                                disabled={closed}
                                                onChange={event => update(
                                                    currentQuestion,
                                                    state => ({
                                                        ...state,
                                                        text: event.target.value,
                                                        data: null,
                                                    }),
                                                )}
                                                className="w-full max-w-md rounded-xl border border-slate-300 px-4 py-3 text-lg font-semibold text-slate-950 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                                                placeholder="Your answer"
                                            />
                                        )
                                        : (
                                            <textarea
                                                value={currentState?.text ?? ""}
                                                disabled={closed}
                                                rows={8}
                                                onChange={event => update(
                                                    currentQuestion,
                                                    state => ({
                                                        ...state,
                                                        text: event.target.value,
                                                        data: null,
                                                    }),
                                                )}
                                                className="w-full resize-y rounded-xl border border-slate-300 px-4 py-3 leading-7 text-slate-950 outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                                                placeholder="Type your answer here..."
                                            />
                                        )
                                )}

                                <div className="mt-4 min-h-6 text-sm font-semibold">
                                    {currentState?.saveState === "saving" && (
                                        <span className="text-blue-700">Saving...</span>
                                    )}
                                    {currentState?.saveState === "dirty" && (
                                        <span className="text-slate-500">Waiting to save...</span>
                                    )}
                                    {currentState?.saveState === "saved" && (
                                        <span className="text-emerald-700">Saved</span>
                                    )}
                                    {currentState?.saveState === "error" && (
                                        <span className="text-red-700">
                                            Save failed: {currentState.error}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </article>
                    ) : (
                        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
                            <h2 className="text-xl font-black text-slate-950">
                                No candidate-visible questions
                            </h2>
                        </div>
                    )}

                    <div className="flex items-center justify-between gap-3">
                        <button
                            type="button"
                            disabled={questionIndex <= 0}
                            onClick={() => setQuestionIndex(
                                current => Math.max(0, current - 1),
                            )}
                            className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-extrabold text-slate-800 disabled:opacity-40"
                        >
                            ← Previous
                        </button>

                        <button
                            type="button"
                            disabled={questionIndex >= questions.length - 1}
                            onClick={() => setQuestionIndex(
                                current => Math.min(
                                    questions.length - 1,
                                    current + 1,
                                ),
                            )}
                            className="rounded-xl bg-blue-700 px-5 py-3 font-extrabold text-white disabled:opacity-40"
                        >
                            Next →
                        </button>
                    </div>
                </section>

                <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:sticky lg:top-28">
                    <h2 className="text-lg font-black text-slate-950">
                        Assessment
                    </h2>

                    <dl className="mt-4 space-y-4 text-sm">
                        <div>
                            <dt className="font-bold uppercase tracking-wide text-slate-500">
                                Progress
                            </dt>
                            <dd className="mt-1 text-lg font-black text-slate-950">
                                {answered} of {questions.length}
                            </dd>
                        </div>
                        <div>
                            <dt className="font-bold uppercase tracking-wide text-slate-500">
                                Started
                            </dt>
                            <dd className="mt-1 font-semibold text-slate-800">
                                {formatDateTime(attempt.started_at)}
                            </dd>
                        </div>
                        <div>
                            <dt className="font-bold uppercase tracking-wide text-slate-500">
                                Closes
                            </dt>
                            <dd className="mt-1 font-semibold text-slate-800">
                                {formatDateTime(attempt.closes_at)}
                            </dd>
                        </div>
                    </dl>

                    <button
                        type="button"
                        data-custom-button="true"
                        disabled={
                            submitting
                            || closed
                            || questions.length === 0
                        }
                        onClick={() => void submitAssessment()}
                        className="mt-5 w-full rounded-xl bg-emerald-700 px-5 py-3 font-extrabold text-white hover:bg-emerald-800 disabled:opacity-50"
                    >
                        {submitting
                            ? "Submitting..."
                            : "Submit assessment"}
                    </button>

                    <p className="mt-3 text-xs leading-5 text-slate-500">
                        Submission is final. Your latest unsaved answers will be saved first.
                    </p>

                    <Link
                        href="/student"
                        className="mt-5 inline-flex w-full items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-extrabold text-slate-700 hover:bg-slate-50"
                    >
                        Return to Student Dashboard
                    </Link>
                </aside>
            </div>
        </main>
    );
}

