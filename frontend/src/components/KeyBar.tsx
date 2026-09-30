import type { StoredKey } from "../types/api";

interface KeyBarProps {
  storedKey: StoredKey;
  onChange: () => void;
  onRemove: () => void;
}

/** Compact bar shown once a key is set, so it can be changed or forgotten. */
export function KeyBar({ storedKey, onChange, onRemove }: KeyBarProps) {
  return (
    <div className="flex items-center justify-between rounded border border-moss/30 bg-moss/[0.06] px-4 py-2.5">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-moss" />
        <span className="font-sans text-sm text-paper">
          Gemini key saved {storedKey.remember ? "on this device" : "for this tab only"}
        </span>
      </div>
      <div className="flex gap-3">
        <button type="button" onClick={onChange} className="font-sans text-xs text-paper-muted hover:text-paper">
          Change
        </button>
        <button type="button" onClick={onRemove} className="font-sans text-xs text-rust/80 hover:text-rust">
          Remove
        </button>
      </div>
    </div>
  );
}
