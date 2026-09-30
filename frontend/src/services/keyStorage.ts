import type { StoredKey } from "../types/api";

const STORAGE_KEY = "ai-document-qa:gemini-key";

/**
 * The API key lives only in this browser. "Remember" uses localStorage (kept
 * until removed); otherwise sessionStorage (cleared when the tab closes) —
 * the safer default on a shared computer.
 */
export function loadKey(): StoredKey | null {
  for (const store of [window.localStorage, window.sessionStorage]) {
    try {
      const raw = store.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw) as StoredKey;
    } catch {
      // ignore unreadable/blocked storage
    }
  }
  return null;
}

export function saveKey(key: StoredKey): void {
  clearKey();
  try {
    (key.remember ? window.localStorage : window.sessionStorage).setItem(
      STORAGE_KEY,
      JSON.stringify(key)
    );
  } catch {
    // Storage unavailable: the key stays in memory (React state) for this page load only.
  }
}

export function clearKey(): void {
  for (const store of [window.localStorage, window.sessionStorage]) {
    try {
      store.removeItem(STORAGE_KEY);
    } catch {
      // nothing to do
    }
  }
}
