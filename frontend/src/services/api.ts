import type {
  ApiErrorBody,
  ChatResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  HealthResponse,
} from "../types/api";
import { getSessionId } from "./session";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/** Thrown for any non-2xx API response, carrying a human-readable message. */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body: ApiErrorBody = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((d) => d.msg).join(" ");
  } catch {
    // Response body wasn't JSON; fall through to a generic message.
  }
  return `Request failed with status ${response.status}.`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new ApiError(await parseErrorMessage(response), response.status);
  }
  return response.json();
}

function sessionHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return { "X-Session-ID": getSessionId(), ...extra };
}

export function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function listDocuments(): Promise<DocumentListResponse> {
  return request<DocumentListResponse>("/api/documents", { headers: sessionHeaders() });
}

export function uploadDocument(file: File, apiKey: string | null): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const extra: Record<string, string> = {};
  if (apiKey) extra["X-Gemini-API-Key"] = apiKey;
  return request<DocumentUploadResponse>("/api/documents/upload", {
    method: "POST",
    headers: sessionHeaders(extra), // no Content-Type: the browser sets the multipart boundary
    body: formData,
  });
}

export function askQuestion(question: string, apiKey: string | null): Promise<ChatResponse> {
  const extra: Record<string, string> = { "Content-Type": "application/json" };
  if (apiKey) extra["X-Gemini-API-Key"] = apiKey;
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: sessionHeaders(extra),
    body: JSON.stringify({ question }),
  });
}
