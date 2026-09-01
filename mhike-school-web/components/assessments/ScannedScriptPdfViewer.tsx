"use client";

import {
    useEffect,
    useRef,
    useState,
} from "react";

import type {
    PDFDocumentProxy,
    RenderTask,
} from "pdfjs-dist";

import {
    getAssessmentScriptFileBlob,
} from "@/lib/services/assessment-candidates";
import type {
    MarkingAnnotation,
} from "@/lib/services/assessment-marking";


// ---------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------


type ScannedScriptPdfViewerProps = {
    scriptId: number;
    filename?: string | null;
    annotations?: MarkingAnnotation[];
    targetPageNumber?: number | null;
    pointPlacementEnabled?: boolean;
    annotationDeleteEnabled?: boolean;
    onDeleteAnnotation?: (
        annotation: MarkingAnnotation,
    ) => void;
    onPagePoint?: (
        pageNumber: number,
        x: number,
        y: number,
    ) => void;
};


// ---------------------------------------------------------------------
// Viewer
// ---------------------------------------------------------------------


export default function ScannedScriptPdfViewer({
    scriptId,
    filename,
    annotations = [],
    targetPageNumber = null,
    pointPlacementEnabled = false,
    annotationDeleteEnabled = false,
    onDeleteAnnotation,
    onPagePoint,
}: ScannedScriptPdfViewerProps) {
    const canvasRef =
        useRef<HTMLCanvasElement | null>(
            null,
        );

    const documentRef =
        useRef<PDFDocumentProxy | null>(
            null,
        );

    const renderTaskRef =
        useRef<RenderTask | null>(
            null,
        );

    const [
        pageNumber,
        setPageNumber,
    ] = useState(
        1,
    );

    const [
        pageCount,
        setPageCount,
    ] = useState(
        0,
    );

    const [
        loadingDocument,
        setLoadingDocument,
    ] = useState(
        true,
    );

    const [
        renderingPage,
        setRenderingPage,
    ] = useState(
        false,
    );

    const [
        errorMessage,
        setErrorMessage,
    ] = useState<string | null>(
        null,
    );


    useEffect(
        () => {
            let cancelled =
                false;

            let loadingTask:
                ReturnType<
                    typeof import("pdfjs-dist")["getDocument"]
                >
                | null =
                null;

            const loadDocument =
                async () => {
                    setLoadingDocument(
                        true,
                    );

                    setErrorMessage(
                        null,
                    );

                    setPageNumber(
                        1,
                    );

                    setPageCount(
                        0,
                    );

                    try {
                        const [
                            pdfjs,
                            blob,
                        ] =
                            await Promise.all([
                                import(
                                    "pdfjs-dist"
                                ),
                                getAssessmentScriptFileBlob(
                                    scriptId,
                                ),
                            ]);

                        if (cancelled) {
                            return;
                        }

                        pdfjs.GlobalWorkerOptions.workerSrc =
                            new URL(
                                "pdfjs-dist/build/pdf.worker.mjs",
                                import.meta.url,
                            ).toString();

                        const bytes =
                            new Uint8Array(
                                await blob.arrayBuffer(),
                            );

                        if (cancelled) {
                            return;
                        }

                        loadingTask =
                            pdfjs.getDocument({
                                data: bytes,
                            });

                        const document =
                            await loadingTask.promise;

                        if (cancelled) {
                            return;
                        }

                        documentRef.current =
                            document;

                        setPageCount(
                            document.numPages,
                        );
                    } catch (error) {
                        if (cancelled) {
                            return;
                        }

                        setErrorMessage(
                            error instanceof Error
                                ? error.message
                                : "Unable to load the scanned script.",
                        );
                    } finally {
                        if (!cancelled) {
                            setLoadingDocument(
                                false,
                            );
                        }
                    }
                };

            void loadDocument();

            return () => {
                cancelled =
                    true;

                const renderTask =
                    renderTaskRef.current;

                renderTaskRef.current =
                    null;

                if (renderTask) {
                    renderTask.cancel();
                }

                documentRef.current =
                    null;


                if (loadingTask) {
                    void loadingTask.destroy();
                }
            };
        },
        [
            scriptId,
        ],
    );


    useEffect(
        () => {
            const document =
                documentRef.current;

            const canvas =
                canvasRef.current;

            if (
                !document
                || !canvas
                || pageCount === 0
            ) {
                return;
            }

            let cancelled =
                false;

            const renderPage =
                async () => {
                    setRenderingPage(
                        true,
                    );

                    setErrorMessage(
                        null,
                    );

                    try {
                        const existingTask =
                            renderTaskRef.current;

                        if (existingTask) {
                            existingTask.cancel();

                            try {
                                await existingTask.promise;
                            } catch {
                                // Expected when replacing an active render.
                            }
                        }

                        const page =
                            await document.getPage(
                                pageNumber,
                            );

                        if (cancelled) {
                            return;
                        }

                        const viewport =
                            page.getViewport({
                                scale: 1.5,
                            });

                        const context =
                            canvas.getContext(
                                "2d",
                                {
                                    alpha: false,
                                },
                            );

                        if (!context) {
                            throw new Error(
                                "Unable to create the PDF canvas.",
                            );
                        }

                        canvas.width =
                            Math.ceil(
                                viewport.width,
                            );

                        canvas.height =
                            Math.ceil(
                                viewport.height,
                            );

                        const task =
                            page.render({
                                canvas,
                                canvasContext: context,
                                viewport,
                            });

                        renderTaskRef.current =
                            task;

                        await task.promise;

                        if (
                            renderTaskRef.current
                            === task
                        ) {
                            renderTaskRef.current =
                                null;
                        }
                    } catch (error) {
                        if (
                            cancelled
                            || (
                                error instanceof Error
                                && error.name
                                    === "RenderingCancelledException"
                            )
                        ) {
                            return;
                        }

                        setErrorMessage(
                            error instanceof Error
                                ? error.message
                                : "Unable to render this PDF page.",
                        );
                    } finally {
                        if (!cancelled) {
                            setRenderingPage(
                                false,
                            );
                        }
                    }
                };

            void renderPage();

            return () => {
                cancelled =
                    true;

                const task =
                    renderTaskRef.current;

                if (task) {
                    task.cancel();
                }
            };
        },
        [
            pageCount,
            pageNumber,
        ],
    );



    useEffect(
        () => {
            if (
                targetPageNumber === null
                || targetPageNumber === undefined
                || pageCount <= 0
                || !Number.isInteger(
                    targetPageNumber,
                )
            ) {
                return;
            }

            const nextPageNumber =
                Math.min(
                    pageCount,
                    Math.max(
                        1,
                        targetPageNumber,
                    ),
                );

            setPageNumber(
                nextPageNumber,
            );
        },
        [
            targetPageNumber,
            pageCount,
        ],
    );

    function handleCanvasPointerDown(
        event: React.PointerEvent<HTMLCanvasElement>,
    ): void {
        if (
            !pointPlacementEnabled
            || !onPagePoint
            || renderingPage
            || loadingDocument
        ) {
            return;
        }

        const bounds =
            event.currentTarget.getBoundingClientRect();

        if (
            bounds.width <= 0
            || bounds.height <= 0
        ) {
            return;
        }

        const x =
            Math.min(
                1,
                Math.max(
                    0,
                    (
                        event.clientX
                        - bounds.left
                    ) / bounds.width,
                ),
            );

        const y =
            Math.min(
                1,
                Math.max(
                    0,
                    (
                        event.clientY
                        - bounds.top
                    ) / bounds.height,
                ),
            );

        event.preventDefault();

        onPagePoint(
            pageNumber,
            x,
            y,
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-700 bg-black/20 px-4 py-3">
                <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        Scanned assessment script
                    </div>

                    <div className="mt-1 text-sm font-semibold text-white">
                        {
                            filename
                            ?? `Script ${scriptId}`
                        }
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        disabled={
                            loadingDocument
                            || pageNumber <= 1
                        }
                        onClick={
                            () => {
                                setPageNumber(
                                    current => (
                                        Math.max(
                                            1,
                                            current - 1,
                                        )
                                    ),
                                );
                            }
                        }
                        className="rounded-lg border border-slate-600 px-3 py-2 text-sm font-semibold text-white transition hover:border-blue-400 hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                        ← Previous page
                    </button>

                    <div className="min-w-24 text-center text-sm font-semibold text-slate-200">
                        {
                            pageCount > 0
                                ? (
                                    `Page ${pageNumber} of ${pageCount}`
                                )
                                : "Loading…"
                        }
                    </div>

                    <button
                        type="button"
                        disabled={
                            loadingDocument
                            || pageCount === 0
                            || pageNumber >= pageCount
                        }
                        onClick={
                            () => {
                                setPageNumber(
                                    current => (
                                        Math.min(
                                            pageCount,
                                            current + 1,
                                        )
                                    ),
                                );
                            }
                        }
                        className="rounded-lg border border-slate-600 px-3 py-2 text-sm font-semibold text-white transition hover:border-blue-400 hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                        Next page →
                    </button>
                </div>
            </div>

            {
                errorMessage
                    ? (
                        <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                            {errorMessage}
                        </div>
                    )
                    : null
            }

            {
                loadingDocument
                    ? (
                        <div className="rounded-xl border border-slate-700 bg-slate-950/40 py-16 text-center text-slate-400">
                            Loading scanned script…
                        </div>
                    )
                    : (
                        <div className="relative overflow-auto rounded-xl border border-slate-700 bg-slate-900/60 p-4">
                            {
                                renderingPage
                                    ? (
                                        <div className="absolute right-6 top-6 z-10 rounded-lg bg-slate-950/90 px-3 py-2 text-xs font-semibold text-slate-300 shadow-lg">
                                            Rendering page…
                                        </div>
                                    )
                                    : null
                            }

                            <div className="flex min-h-96 justify-center">
                                <div className="relative inline-block">
                                    <canvas
                                        ref={canvasRef}
                                        onPointerDown={
                                            handleCanvasPointerDown
                                        }
                                        className={[
                                            "block h-auto max-w-none bg-white shadow-2xl",
                                            pointPlacementEnabled
                                                ? "cursor-crosshair"
                                                : "",
                                        ].join(" ")}
                                    />

                                    <div
                                        className="pointer-events-none absolute inset-0 z-20"
                                        aria-hidden="true"
                                    >
                                        {
                                            annotations
                                                .filter(
                                                    (annotation) => (
                                                        annotation.surface_type
                                                        === "script_page"
                                                        && annotation.page_number
                                                        === pageNumber
                                                        && annotation.deleted_at
                                                        === null
                                                    ),
                                                )
                                                .map(
                                                    (annotation) => {
                                                        const x =
                                                            Math.min(
                                                                1,
                                                                Math.max(
                                                                    0,
                                                                    Number(
                                                                        annotation.x,
                                                                    ),
                                                                ),
                                                            );

                                                        const y =
                                                            Math.min(
                                                                1,
                                                                Math.max(
                                                                    0,
                                                                    Number(
                                                                        annotation.y,
                                                                    ),
                                                                ),
                                                            );

                                                        const displayValue =
                                                            annotation.annotation_type
                                                            === "text"
                                                                ? annotation.text
                                                                : annotation.value;

                                                        if (!displayValue) {
                                                            return null;
                                                        }

                                                        return (
                                                            <button
                                                                key={
                                                                    annotation.id
                                                                }
                                                                type="button"
                                                                disabled={
                                                                    !annotationDeleteEnabled
                                                                }
                                                                title={
                                                                    annotationDeleteEnabled
                                                                        ? "Delete this examiner mark"
                                                                        : undefined
                                                                }
                                                                onPointerDown={
                                                                    (event) => {
                                                                        if (
                                                                            annotationDeleteEnabled
                                                                        ) {
                                                                            event.preventDefault();
                                                                            event.stopPropagation();
                                                                        }
                                                                    }
                                                                }
                                                                onClick={
                                                                    (event) => {
                                                                        if (
                                                                            !annotationDeleteEnabled
                                                                            || !onDeleteAnnotation
                                                                        ) {
                                                                            return;
                                                                        }

                                                                        event.preventDefault();
                                                                        event.stopPropagation();

                                                                        onDeleteAnnotation(
                                                                            annotation,
                                                                        );
                                                                    }
                                                                }
                                                                className={[
                                                                    "absolute flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-md border-0 bg-transparent p-0 text-2xl font-bold leading-none text-red-600",
                                                                    annotationDeleteEnabled
                                                                        ? "pointer-events-auto cursor-pointer hover:bg-red-100/70 hover:ring-2 hover:ring-red-400"
                                                                        : "pointer-events-none",
                                                                ].join(" ")}
                                                                style={{
                                                                    left:
                                                                        `${x * 100}%`,
                                                                    top:
                                                                        `${y * 100}%`,
                                                                }}
                                                            >
                                                                {
                                                                    displayValue
                                                                }
                                                            </button>
                                                        );
                                                    },
                                                )
                                        }
                                    </div>
                                </div>
                            </div>
                        </div>
                    )
            }
        </div>
    );
}





