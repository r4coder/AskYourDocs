export function ConversationEmptyState() {
  return (
    <div className="rounded border border-dashed border-ink-borderLight px-6 py-12 text-center">
      <p className="font-serif text-lg text-paper-muted">Ask something about your documents.</p>
      <p className="mt-2 font-sans text-sm text-paper-dim">
        Answers are generated only from the text you've uploaded, with sources cited below each
        response.
      </p>
    </div>
  );
}
