interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div className="flex items-start justify-between gap-3 rounded border border-rust/40 bg-rust/10 px-4 py-3">
      <p className="font-sans text-sm text-rust">{message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="flex-shrink-0 font-sans text-xs text-rust/70 hover:text-rust"
        aria-label="Dismiss error"
      >
        Dismiss
      </button>
    </div>
  );
}
