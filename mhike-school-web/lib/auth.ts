const API_URL = "http://localhost:8000"; // adjust if needed


// -----------------------------
// LOGIN
// -----------------------------
export async function login({
    email,
    password,
    school_id,
}: {
    email: string;
    password: string;
    school_id: number;
}) {
    const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            password,
            school_id,
        }),
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Login failed");
    }

    const data = await res.json();

    // save token
    localStorage.setItem("token", data.access_token);

    return data;
}


// -----------------------------
// REGISTER
// -----------------------------
export async function register({
    email,
    password,
    school_id,
}: {
    email: string;
    password: string;
    school_id: number;
}) {
    const res = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email,
            password,
            school_id,
        }),
    });

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Register failed");
    }

    return await res.json();
}


// -----------------------------
// GET TOKEN
// -----------------------------
export function getToken() {
    return localStorage.getItem("token");
}


// -----------------------------
// AUTH HEADER
// -----------------------------
export function getAuthHeaders() {
    const token = getToken();

    return {
        Authorization: `Bearer ${token}`,
    };
}


// -----------------------------
// LOGOUT
// -----------------------------
export function logout() {
    localStorage.removeItem("token");
}