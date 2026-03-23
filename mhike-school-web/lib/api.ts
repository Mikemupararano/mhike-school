export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * Safely get token from localStorage
 */
export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("mhike_token");
}

export function setToken(token: string) {
    if (typeof window === "undefined") return;
    localStorage.setItem("mhike_token", token);
}

export function clearToken() {
    if (typeof window === "undefined") return;
    localStorage.removeItem("mhike_token");
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
 * Unified response handler
 */
async function handle<T>(res: Response): Promise<T> {
    if (!res.ok) {
        let message = `API error ${res.status}`;

        try {
            const data = await res.json();
            message = data?.detail || JSON.stringify(data);
        } catch {
            try {
                message = await res.text();
            } catch {
                // fallback stays
            }
        }

        throw new Error(message);
    }

    return res.json() as Promise<T>;
}

/**
 * GET request
 */
export async function apiGet<T>(path: string, token?: string): Promise<T> {
    const authToken = token ?? getToken();

    const url = buildUrl(path);

    const res = await fetch(url, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
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
    const authToken = token ?? getToken();

    const url = buildUrl(path);

    const res = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify(body),
        cache: "no-store",
    });

    return handle<T>(res);
}