/**
 * Client for the ForwardCheck API.
 *
 * The backend serialises with camelCase aliases matching `types.ts`, so the
 * response is used directly with no mapping layer.
 */
import type { HealthResponse, VerifyRequest, VerifyResponse } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Thrown for any non-2xx response, carrying a message safe to show a user. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function verifyMessage(
  message: string,
  signal?: AbortSignal,
): Promise<VerifyResponse> {
  const payload: VerifyRequest = { message };

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    // Most common cause in local dev is simply that uvicorn is not running.
    throw new ApiError(
      `Could not reach the ForwardCheck API at ${API_BASE}. Is the backend running?`,
      0,
    );
  }

  if (!response.ok) {
    throw new ApiError(await readErrorDetail(response), response.status);
  }

  return (await response.json()) as VerifyResponse;
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors arrive as a list of issue objects.
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  } catch {
    // Fall through to the generic message below.
  }
  return `Verification failed (HTTP ${response.status}).`;
}

/**
 * Backend health and mode. Returns null when the API is unreachable, which the
 * UI renders as "API offline" rather than as a verification failure.
 */
export async function fetchHealth(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) return null;
    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}
