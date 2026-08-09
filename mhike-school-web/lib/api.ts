export const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL?.replace(
        /\/+$/,
        "",
    )
    || process.env.NEXT_PUBLIC_API_BASE_URL?.replace(
        /\/+$/,
        "",
    )
    || "http://localhost:8000/api/v1";


const TOKEN_KEY = "mhike_token";

const SESSION_EXPIRED_REASON =
    "session_expired";


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


type ApiRequestOptions = {
    method:
    | "GET"
    | "POST"
    | "PUT"
    | "PATCH"
    | "DELETE";

    token?: string;
    body?: unknown;
    formData?: FormData;
};


type BuildHeaderOptions = {
    hasJsonBody: boolean;
};


type ThrowApiErrorOptions = {
    response: Response;
    path: string;
    authToken: string | null;
};


type AuthenticationFailureOptions = {
    response: Response;
    path: string;
    authToken: string | null;
};


export class ApiError extends Error {
    readonly status: number;
    readonly path: string;

    constructor(
        message: string,
        options: {
            status: number;
            path: string;
        },
    ) {
        super(message);

        this.name = "ApiError";
        this.status = options.status;
        this.path = options.path;

        Object.setPrototypeOf(
            this,
            ApiError.prototype,
        );
    }
}


export function getToken(): string | null {
    if (typeof window === "undefined") {
        return null;
    }

    return window.sessionStorage.getItem(
        TOKEN_KEY,
    );
}


export function saveToken(
    token: string,
): void {
    if (typeof window === "undefined") {
        return;
    }

    const cleanedToken =
        token.trim();

    if (!cleanedToken) {
        clearToken();
        return;
    }

    window.sessionStorage.setItem(
        TOKEN_KEY,
        cleanedToken,
    );
}


export function clearToken(): void {
    if (typeof window === "undefined") {
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


function resolveAuthToken(
    token?: string,
): string | null {
    if (typeof token === "string") {
        const cleanedToken =
            token.trim();

        if (cleanedToken) {
            return cleanedToken;
        }
    }

    return getToken();
}


function buildHeaders(
    authToken: string | null,
    options: BuildHeaderOptions,
): HeadersInit {
    return {
        Accept: "application/json",

        ...(options.hasJsonBody
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
    authToken: string | null,
): HeadersInit {
    /*
     * Do not set Content-Type for FormData.
     *
     * The browser must generate the multipart/form-data
     * boundary automatically.
     */
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
        typeof data !== "object"
        || data === null
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
        "object"
        && envelope.error !== null
        && "message" in envelope.error
        && typeof envelope.error.message ===
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
            responseText.trim()
            || fallback
        );
    } catch {
        return fallback;
    }
}


function normaliseApiPath(
    path: string,
): string {
    const queryIndex =
        path.indexOf("?");

    const cleanPath =
        queryIndex >= 0
            ? path.slice(
                0,
                queryIndex,
            )
            : path;

    return cleanPath.startsWith("/")
        ? cleanPath
        : `/${cleanPath}`;
}


function isLoginRequest(
    path: string,
): boolean {
    return (
        normaliseApiPath(path)
        === "/auth/login"
    );
}


function isLoginPage(): boolean {
    if (typeof window === "undefined") {
        return false;
    }

    return (
        window.location.pathname
        === "/login"
    );
}


function buildReturnTo(): string | null {
    if (typeof window === "undefined") {
        return null;
    }

    const {
        pathname,
        search,
        hash,
    } = window.location;

    if (
        !pathname
        || pathname === "/login"
        || !pathname.startsWith("/")
    ) {
        return null;
    }

    return `${pathname}${search}${hash}`;
}


function redirectToLogin(): void {
    if (
        typeof window === "undefined"
        || isLoginPage()
    ) {
        return;
    }

    const params =
        new URLSearchParams();

    params.set(
        "reason",
        SESSION_EXPIRED_REASON,
    );

    const returnTo =
        buildReturnTo();

    if (returnTo) {
        params.set(
            "returnTo",
            returnTo,
        );
    }

    window.location.replace(
        `/login?${params.toString()}`,
    );
}


function handleAuthenticationFailure(
    options: AuthenticationFailureOptions,
): void {
    const {
        response,
        path,
        authToken,
    } = options;

    /*
     * A 401 means that authentication credentials are
     * absent, expired or otherwise invalid.
     *
     * A 403 is deliberately NOT handled here. A forbidden
     * response normally means authentication succeeded but
     * the user does not have permission for that action.
     */
    if (response.status !== 401) {
        return;
    }

    /*
     * Incorrect login credentials must remain a normal login
     * error rather than being interpreted as session expiry.
     */
    if (isLoginRequest(path)) {
        return;
    }

    /*
     * If no token was sent, there is no authenticated session
     * to clear or resume.
     */
    if (!authToken) {
        return;
    }

    clearToken();

    redirectToLogin();
}


async function throwApiError(
    options: ThrowApiErrorOptions,
): Promise<never> {
    const {
        response,
        path,
        authToken,
    } = options;

    const message =
        await getErrorMessage(
            response,
        );

    handleAuthenticationFailure({
        response,
        path,
        authToken,
    });

    throw new ApiError(
        message,
        {
            status:
                response.status,

            path:
                normaliseApiPath(
                    path,
                ),
        },
    );
}


async function parseJsonResponse<T>(
    response: Response,
): Promise<T> {
    if (response.status === 204) {
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


async function request<T>(
    path: string,
    options: ApiRequestOptions,
): Promise<T> {
    const authToken =
        resolveAuthToken(
            options.token,
        );

    const hasFormData =
        options.formData !==
        undefined;

    const hasJsonBody =
        !hasFormData
        && options.body !==
        undefined;

    let requestBody:
        BodyInit | null | undefined;

    if (hasFormData) {
        requestBody =
            options.formData;
    } else if (hasJsonBody) {
        requestBody =
            JSON.stringify(
                options.body,
            );
    } else {
        requestBody =
            undefined;
    }

    const response =
        await fetch(
            buildUrl(path),
            {
                method:
                    options.method,

                headers:
                    hasFormData
                        ? buildFormHeaders(
                            authToken,
                        )
                        : buildHeaders(
                            authToken,
                            {
                                hasJsonBody,
                            },
                        ),

                body:
                    requestBody,

                cache:
                    "no-store",
            },
        );

    if (!response.ok) {
        return throwApiError({
            response,
            path,
            authToken,
        });
    }

    return parseJsonResponse<T>(
        response,
    );
}


export async function apiGet<T>(
    path: string,
    token?: string,
): Promise<T> {
    return request<T>(
        path,
        {
            method: "GET",
            token,
        },
    );
}


export async function apiGetBlob(
    path: string,
    token?: string,
): Promise<Blob> {
    const authToken =
        resolveAuthToken(
            token,
        );

    const response =
        await fetch(
            buildUrl(path),
            {
                method: "GET",

                headers:
                    buildHeaders(
                        authToken,
                        {
                            hasJsonBody:
                                false,
                        },
                    ),

                cache:
                    "no-store",
            },
        );

    if (!response.ok) {
        return throwApiError({
            response,
            path,
            authToken,
        });
    }

    return response.blob();
}


export async function apiPost<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    return request<T>(
        path,
        {
            method: "POST",
            token,
            body,
        },
    );
}


export async function apiPostForm<T>(
    path: string,
    formData: FormData,
    token?: string,
): Promise<T> {
    return request<T>(
        path,
        {
            method: "POST",
            token,
            formData,
        },
    );
}


export async function apiPut<T>(
    path: string,
    body: unknown,
    token?: string,
): Promise<T> {
    return request<T>(
        path,
        {
            method: "PUT",
            token,
            body,
        },
    );
}


export async function apiPatch<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    return request<T>(
        path,
        {
            method: "PATCH",
            token,
            body,
        },
    );
}


export async function apiDelete<T>(
    path: string,
    body?: unknown,
    token?: string,
): Promise<T> {
    return request<T>(
        path,
        {
            method: "DELETE",
            token,
            body,
        },
    );
}