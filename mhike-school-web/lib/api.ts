export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "mhike_token";

/**
 * Safely get token from sessionStorage
 */
export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return sessionStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string) {
    if (typeof window === "undefined") return;
    sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    if (typeof window === "undefined") return;
    sessionStorage.removeItem(TOKEN_KEY);
}

/**
 * Normalize URL to avoid double slashes
 */
function buildUrl(path: string): string {
    const base = API_BASE_URL.replace(/\/+$/, "");
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    return `${base}${cleanPath}`;
}

/**
 * Build headers safely
 */
function buildHeaders(token?: string): HeadersInit {
    const authToken = token ?? getToken();

    return {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    };
}

/**
 * Unified response handler
 */
async function handle<T>(res: Response): Promise<T> {
    if (!res.ok) {
        let message = `API error ${res.status}`;

        try {
            const data = await res.json();
            message = data?.detail || data?.message || JSON.stringify(data);
        } catch {
            try {
                message = await res.text();
            } catch {
                // fallback
            }
        }

        if (res.status === 401 || res.status === 403) {
            clearToken();
        }

        throw new Error(message);
    }

    // Important for DELETE 204 responses
    if (res.status === 204) {
        return undefined as T;
    }

    return res.json() as Promise<T>;
}

/**
 * GET request
 */
export async function apiGet<T>(path: string, token?: string): Promise<T> {
    const res = await fetch(buildUrl(path), {
        method: "GET",
        headers: buildHeaders(token),
        cache: "no-store",
    });

    return handle<T>(res);
}

/**
 * POST request
 */
export async function apiPost<T>(
    path: string,
    body: unknown,
    token?: string
): Promise<T> {
    const res = await fetch(buildUrl(path), {
        method: "POST",
        headers: buildHeaders(token),
        body: JSON.stringify(body),
        cache: "no-store",
    });

    return handle<T>(res);
}

/**
 * PUT request
 */
export async function apiPut<T>(
    path: string,
    body: unknown,
    token?: string
): Promise<T> {
    const res = await fetch(buildUrl(path), {
        method: "PUT",
        headers: buildHeaders(token),
        body: JSON.stringify(body),
        cache: "no-store",
    });

    return handle<T>(res);
}

/**
 * PATCH request
 */
export async function apiPatch<T>(
    path: string,
    body: unknown,
    token?: string
): Promise<T> {
    const res = await fetch(buildUrl(path), {
        method: "PATCH",
        headers: buildHeaders(token),
        body: JSON.stringify(body),
        cache: "no-store",
    });

    return handle<T>(res);
}

/**
 * DELETE request
 */
export async function apiDelete<T>(path: string, token?: string): Promise<T> {
    const res = await fetch(buildUrl(path), {
        method: "DELETE",
        headers: buildHeaders(token),
        cache: "no-store",
    });

    return handle<T>(res);
}