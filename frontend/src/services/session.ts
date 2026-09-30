const STORAGE_KEY = "ai-document-qa:session-id";
let memoryId: string | null = null;

function randomId(): string {
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID(); // 36 chars: letters, digits, dashes
  }
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * A random id that identifies this browser to the backend. Each id gets its own
 * private document store, so visitors never see each other's documents.
 */
export function getSessionId(): string {
  try {
    const existing = window.localStorage.getItem(STORAGE_KEY);
    if (existing) return existing;
    const fresh = randomId();
    window.localStorage.setItem(STORAGE_KEY, fresh);
    return fresh;
  } catch {
    // Storage blocked (e.g. some private modes): keep an id for this page load only.
    if (!memoryId) memoryId = randomId();
    return memoryId;
  }
}
