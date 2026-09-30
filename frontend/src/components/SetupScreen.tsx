import { useState } from "react";
import type { FormEvent } from "react";
import type { StoredKey } from "../types/api";

interface SetupScreenProps {
  initial: StoredKey | null;
  /** Message to show at the top, e.g. "your key was rejected". */
  notice?: string | null;
  onSave: (key: StoredKey) => void;
  /** Present when editing an existing key (lets the user back out). */
  onCancel?: () => void;
}

export function SetupScreen({ initial, notice, onSave, onCancel }: SetupScreenProps) {
  const [apiKey, setApiKey] = useState(initial?.apiKey ?? "");
  const [remember, setRemember] = useState(initial?.remember ?? false);

  const ready = apiKey.trim() !== "";
  const hint = apiKey && !apiKey.trim().startsWith("AI") ? "Gemini keys usually start with \u201cAI\u201d." : null;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    onSave({ apiKey: apiKey.trim(), remember });
  };

  return (
    <div className="min-h-screen bg-ink text-paper">
      <header className="border-b border-ink-border px-6 py-5 sm:px-10">
        <h1 className="font-serif text-2xl font-semibold text-paper">AI Document Q&amp;A</h1>
        <p className="mt-1 font-sans text-sm text-paper-dim">
          Upload documents, ask questions, get answers grounded in your own text.
        </p>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10 sm:px-10">
        <h2 className="font-serif text-xl text-paper">{onCancel ? "Your Gemini API key" : "Before you start"}</h2>
        <p className="mt-2 font-sans text-sm leading-relaxed text-paper-muted">
          This app runs on <span className="text-paper">your own Gemini API key</span>, used for both
          searching your documents and writing answers. You pay Google directly for what you use —
          Gemini has a free tier that covers light use.
        </p>

        {notice && (
          <div className="mt-4 rounded border border-rust/40 bg-rust/10 px-4 py-3 font-sans text-sm text-rust">
            {notice}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <section className="rounded border border-ink-border bg-ink-panel px-5 py-4">
            <label htmlFor="gemini-key" className="font-sans text-sm font-medium text-paper">
              Gemini API key
            </label>
            <input
              id="gemini-key"
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="AIza..."
              className="mt-3 w-full rounded border border-ink-borderLight bg-ink px-3 py-2.5 font-mono text-sm text-paper placeholder:text-paper-dim focus:border-gold focus:outline-none"
            />
            {hint && <p className="mt-1 font-sans text-xs text-gold">{hint}</p>}

            <details className="mt-3 rounded border border-ink-border bg-ink/40 px-3 py-2">
              <summary className="cursor-pointer font-sans text-[13px] text-paper-muted hover:text-paper">
                How do I get a Gemini API key?
              </summary>
              <ol className="mt-2 list-decimal space-y-1 pl-5 font-sans text-[13px] leading-relaxed text-paper-muted">
                <li>
                  Go to{" "}
                  <a
                    href="https://aistudio.google.com/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gold underline hover:text-gold-hover"
                  >
                    aistudio.google.com/apikey
                  </a>{" "}
                  and sign in with any Google account.
                </li>
                <li>Click “Create API key” and choose a project (or let Google create one for you).</li>
                <li>Copy the key that appears — it starts with “AI”.</li>
                <li>Paste it into the box above. Gemini's free tier is generous enough for trying this out.</li>
              </ol>
            </details>
          </section>

          <div className="rounded border border-ink-border bg-ink-panel/60 px-5 py-4">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="mt-0.5 h-4 w-4 accent-[#C9A227]"
              />
              <span className="font-sans text-sm text-paper-muted">
                Remember my key on this device
                <span className="block text-xs text-paper-dim">
                  Leave unchecked on a shared computer — the key is then forgotten when you close this tab.
                </span>
              </span>
            </label>
            <p className="mt-3 font-sans text-xs leading-relaxed text-paper-dim">
              Your key stays in your browser. It is sent with each request to this app's server, used
              only to call Gemini on your behalf, and is not stored by the server. You can delete and
              recreate the key at any time at aistudio.google.com.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={!ready}
              className="rounded bg-gold px-6 py-2.5 font-sans text-sm font-medium text-ink transition-colors hover:bg-gold-hover disabled:cursor-not-allowed disabled:bg-ink-borderLight disabled:text-paper-dim"
            >
              {onCancel ? "Save" : "Continue"}
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="rounded border border-ink-borderLight px-6 py-2.5 font-sans text-sm text-paper-muted hover:text-paper"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
