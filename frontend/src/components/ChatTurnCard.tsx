import type { ChatTurn } from "../types/api";
import { SourceCitationList } from "./SourceCitationList";

interface ChatTurnCardProps {
  turn: ChatTurn;
}

export function ChatTurnCard({ turn }: ChatTurnCardProps) {
  return (
    <div className="rounded border border-ink-border bg-ink-panel px-5 py-4">
      <p className="font-sans text-sm font-medium text-paper">{turn.question}</p>

      <div className="mt-3 border-t border-ink-border pt-3">
        {turn.error && (
          <div className="rounded border border-rust/40 bg-rust/10 px-3 py-2">
            <p className="font-sans text-sm text-rust">{turn.error}</p>
          </div>
        )}

        {!turn.error && turn.response === null && (
          <div className="flex items-center gap-3">
            <span className="h-4 w-4 flex-shrink-0 animate-spin rounded-full border-2 border-gold/30 border-t-gold" />
            <span className="font-sans text-sm text-paper-muted">Thinking through the documents…</span>
          </div>
        )}

        {!turn.error && turn.response !== null && (
          <>
            <p className="font-serif text-[15px] leading-relaxed text-paper">
              {turn.response.answer}
            </p>
            {turn.response.grounded && (
              <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-moss/10 px-2.5 py-1">
                <span className="h-1.5 w-1.5 rounded-full bg-moss" />
                <span className="font-mono text-[11px] text-moss">Grounded in documents</span>
              </div>
            )}
            <SourceCitationList sources={turn.response.sources} />
          </>
        )}
      </div>
    </div>
  );
}
