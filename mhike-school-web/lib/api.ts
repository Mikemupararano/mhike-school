export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL!;

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

async function handle<T>(res: Response): Promise<T> {
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`API error ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string, token?: string): Promise<T> {
    const authToken = token ?? getToken();

    const res = await fetch(`${API_BASE_URL}${path}`, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        cache: "no-store",
    });

    return handle<T>(res);
}

export async function apiPost<T>(path: string, body: unknown, token?: string): Promise<T> {
    const authToken = token ?? getToken();

    const res = await fetch(`${API_BASE_URL}${path}`, {
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