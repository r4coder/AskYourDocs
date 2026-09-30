import type { SourceReference } from "../types/api";

interface SourceCitationListProps {
  sources: SourceReference[];
}

export function SourceCitationList({ sources }: SourceCitationListProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-4 border-t border-ink-border pt-3">
      <p className="font-sans text-xs font-medium uppercase tracking-wide text-paper-dim">
        Sources
      </p>
      <ul className="mt-2 space-y-2">
        {sources.map((source, i) => (
          <li key={source.chunk_id} className="rounded border border-ink-border bg-ink/40 p-2.5">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs text-gold">[{i + 1}]</span>
              <span className="font-sans text-sm text-paper">{source.document_name}</span>
              {source.page_number !== null && (
                <span className="font-mono text-xs text-paper-dim">
                  page {source.page_number}
                </span>
              )}
              <span className="ml-auto font-mono text-[11px] text-paper-dim">
                {Math.round(source.similarity_score * 100)}% match
              </span>
            </div>
            <p className="mt-1.5 font-serif text-[13px] leading-relaxed text-paper-muted">
              "{source.snippet}"
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
