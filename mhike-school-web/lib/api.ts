export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://localhost:8000/api/v1";

const TOKEN_KEY = "mhike_token";

export function getToken(): string | null {
    if (typeof window === "undefined") {
        return null;
    }

    return sessionStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
    if (typeof window === "undefined") {
        return;
    }

    sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
    if (typeof window === "undefined") {
        return;
    }

    sessionStorage.removeItem(TOKEN_KEY);
}

function buildUrl(path: string): string {
    const base = API_BASE_URL.replace(/\/+$/, "");

    const normalizedPath = path.startsWith("/")
        ? path
        : `/${path}`;

    return `${base}${normalizedPath}`;
}

function buildHeaders(
    token?: string,
    hasBody = false,
): HeadersInit {
    const authToken = token ?? getToken();

    return {
        Accept: "application/json",

        ...(hasBody
            ? {
                "Content-Type": "application/json",
            }
            : {}),

        ...(authToken
            ? {
                Authorization: `Bearer ${authToken}`,
            }
            : {}),
    };
}

async function handle<T>(
    res: Response,
): Promise<T> {
    if (!res.ok) {
        let message = `API error ${res.status}`;

        try {
            const contentType =
                res.headers.get("content-type") ?? "";

            if (
                contentType.includes(
                    "application/json",
                )
            ) {
                const data = await res.json();

                if (
                    typeof data?.detail === "string"
                ) {
                    message = data.detail;
                } else if (
                    typeof data?.message === "string"
                ) {
                    message = data.message;
                } else if (
                    typeof data?.error === "string"
                ) {
                    message = data.error;
                } else {
                    message = JSON.stringify(data);
                }
            } else {
                message = await res.text();
            }
        } catch {
            // Keep default message
        }

        if (
            res.status === 401 ||
            res.status === 403
        ) {
            clearToken();
        }

        throw new Error(message);
    }

    if (res.status === 204) {
        return undefined as T;
    }

    const contentType =
        res.headers.get("content-type") ?? "";

    if (
        !contentType.includes(
            "application/json",
        )
    ) {
        return undefined as T;
    }

    return res.json() as Promise<T>;
}

export async function apiGet<T>(
    path: string,
    token?: string,
): Promise<T> {
    return handle<T>(
        await fetch(buildUrl(path), {
            method: "GET",
            headers: buildHeaders(token),
            cache: "no-store",
        }),
    );
}

export async function apiPost<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    return handle<T>(
        await fetch(buildUrl(path), {
            method: "POST",
            headers: buildHeaders(
                token,
                body !== undefined,
            ),

            body:
                body !== undefined
                    ? JSON.stringify(body)
                    : undefined,

            cache: "no-store",
        }),
    );
}

export async function apiPut<T>(
    path: string,
    body: unknown,
    token?: string,
): Promise<T> {
    return handle<T>(
        await fetch(buildUrl(path), {
            method: "PUT",
            headers: buildHeaders(token, true),

            body: JSON.stringify(body),

            cache: "no-store",
        }),
    );
}

export async function apiPatch<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    return handle<T>(
        await fetch(buildUrl(path), {
            method: "PATCH",

            headers: buildHeaders(
                token,
                body !== undefined,
            ),

            body:
                body !== undefined
                    ? JSON.stringify(body)
                    : undefined,

            cache: "no-store",
        }),
    );
}

export async function apiDelete<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    return handle<T>(
        await fetch(buildUrl(path), {
            method: "DELETE",

            headers: buildHeaders(
                token,
                body !== undefined,
            ),

            body:
                body !== undefined
                    ? JSON.stringify(body)
                    : undefined,

            cache: "no-store",
        }),
    );
}