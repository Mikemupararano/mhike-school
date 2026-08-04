export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL?.replace(
        /\/$/,
        "",
    ) ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(
        /\/$/,
        "",
    ) ||
    "http://localhost:8000/api/v1";

const TOKEN_KEY =
    "mhike_token";

type ApiErrorEnvelope = {
    detail?: unknown;
    message?: unknown;
    error?:
    | unknown
    | {
        code?: unknown;
        message?: unknown;
    };
};

export function getToken(): string | null {
    if (
        typeof window ===
        "undefined"
    ) {
        return null;
    }

    return window.sessionStorage.getItem(
        TOKEN_KEY,
    );
}

export function saveToken(
    token: string,
): void {
    if (
        typeof window ===
        "undefined"
    ) {
        return;
    }

    window.sessionStorage.setItem(
        TOKEN_KEY,
        token,
    );
}

export function clearToken(): void {
    if (
        typeof window ===
        "undefined"
    ) {
        return;
    }

    window.sessionStorage.removeItem(
        TOKEN_KEY,
    );
}

function buildUrl(
    path: string,
): string {
    const base =
        API_BASE_URL.replace(
            /\/+$/,
            "",
        );

    const normalisedPath =
        path.startsWith("/")
            ? path
            : `/${path}`;

    return `${base}${normalisedPath}`;
}

function buildHeaders(
    token?: string,
    hasBody = false,
): HeadersInit {
    const authToken =
        token ?? getToken();

    return {
        Accept: "application/json",

        ...(hasBody
            ? {
                "Content-Type":
                    "application/json",
            }
            : {}),

        ...(authToken
            ? {
                Authorization:
                    `Bearer ${authToken}`,
            }
            : {}),
    };
}

function buildFormHeaders(
    token?: string,
): HeadersInit {
    const authToken =
        token ?? getToken();

    return {
        Accept: "application/json",

        ...(authToken
            ? {
                Authorization:
                    `Bearer ${authToken}`,
            }
            : {}),
    };
}

function extractApiErrorMessage(
    data: unknown,
    fallback: string,
): string {
    if (
        typeof data !==
        "object" ||
        data === null
    ) {
        return fallback;
    }

    const envelope =
        data as ApiErrorEnvelope;

    if (
        typeof envelope.detail ===
        "string"
    ) {
        return envelope.detail;
    }

    if (
        typeof envelope.message ===
        "string"
    ) {
        return envelope.message;
    }

    if (
        typeof envelope.error ===
        "string"
    ) {
        return envelope.error;
    }

    if (
        typeof envelope.error ===
        "object" &&
        envelope.error !== null &&
        "message" in envelope.error &&
        typeof envelope.error.message ===
        "string"
    ) {
        return envelope.error.message;
    }

    try {
        return JSON.stringify(
            data,
        );
    } catch {
        return fallback;
    }
}

async function getErrorMessage(
    response: Response,
): Promise<string> {
    const fallback =
        `API error ${response.status}`;

    try {
        const contentType =
            response.headers.get(
                "content-type",
            ) ?? "";

        if (
            contentType.includes(
                "application/json",
            )
        ) {
            const data: unknown =
                await response.json();

            return extractApiErrorMessage(
                data,
                fallback,
            );
        }

        const responseText =
            await response.text();

        return (
            responseText.trim() ||
            fallback
        );
    } catch {
        return fallback;
    }
}

function handleAuthenticationFailure(
    response: Response,
): void {
    if (
        response.status === 401 ||
        response.status === 403
    ) {
        clearToken();
    }
}

async function handle<T>(
    response: Response,
): Promise<T> {
    if (!response.ok) {
        const message =
            await getErrorMessage(
                response,
            );

        handleAuthenticationFailure(
            response,
        );

        throw new Error(
            message,
        );
    }

    if (
        response.status === 204
    ) {
        return undefined as T;
    }

    const contentType =
        response.headers.get(
            "content-type",
        ) ?? "";

    if (
        !contentType.includes(
            "application/json",
        )
    ) {
        return undefined as T;
    }

    return response.json() as Promise<T>;
}

export async function apiGet<T>(
    path: string,
    token?: string,
): Promise<T> {
    const response =
        await fetch(
            buildUrl(path),
            {
                method: "GET",
                headers:
                    buildHeaders(
                        token,
                    ),
                cache: "no-store",
            },
        );

    return handle<T>(
        response,
    );
}

export async function apiGetBlob(
    path: string,
    token?: string,
): Promise<Blob> {
    const response =
        await fetch(
            buildUrl(path),
            {
                method: "GET",
                headers:
                    buildHeaders(
                        token,
                    ),
                cache: "no-store",
            },
        );

    if (!response.ok) {
        const message =
            await getErrorMessage(
                response,
            );

        handleAuthenticationFailure(
            response,
        );

        throw new Error(
            message,
        );
    }

    return response.blob();
}

export async function apiPost<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    const response =
        await fetch(
            buildUrl(path),
            {
                method: "POST",
                headers:
                    buildHeaders(
                        token,
                        body !==
                        undefined,
                    ),
                body:
                    body !==
                        undefined
                        ? JSON.stringify(
                            body,
                        )
                        : undefined,
                cache: "no-store",
            },
        );

    return handle<T>(
        response,
    );
}

export async function apiPostForm<T>(
    path: string,
    formData: FormData,
    token?: string,
): Promise<T> {
    const response =
        await fetch(
            buildUrl(path),
            {
                method: "POST",
                headers:
                    buildFormHeaders(
                        token,
                    ),
                body: formData,
                cache: "no-store",
            },
        );

    return handle<T>(
        response,
    );
}

export async function apiPut<T>(
    path: string,
    body: unknown,
    token?: string,
): Promise<T> {
    const response =
        await fetch(
            buildUrl(path),
            {
                method: "PUT",
                headers:
                    buildHeaders(
                        token,
                        true,
                    ),
                body:
                    JSON.stringify(
                        body,
                    ),
                cache: "no-store",
            },
        );

    return handle<T>(
        response,
    );
}

export async function apiPatch<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    const response =
        await fetch(
            buildUrl(path),
            {
                method: "PATCH",
                headers:
                    buildHeaders(
                        token,
                        body !==
                        undefined,
                    ),
                body:
                    body !==
                        undefined
                        ? JSON.stringify(
                            body,
                        )
                        : undefined,
                cache: "no-store",
            },
        );

    return handle<T>(
        response,
    );
}

export async function apiDelete<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    const response =
        await fetch(
            buildUrl(path),
            {
                method: "DELETE",
                headers:
                    buildHeaders(
                        token,
                        body !==
                        undefined,
                    ),
                body:
                    body !==
                        undefined
                        ? JSON.stringify(
                            body,
                        )
                        : undefined,
                cache: "no-store",
            },
        );

    return handle<T>(
        response,
    );
}