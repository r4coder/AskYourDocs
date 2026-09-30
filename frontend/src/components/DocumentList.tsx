import type { DocumentInfo } from "../types/api";

interface DocumentListProps {
  documents: DocumentInfo[];
  isLoading: boolean;
}

function formatUploadedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function DocumentList({ documents, isLoading }: DocumentListProps) {
  return (
    <div>
      <h2 className="font-sans text-xs font-medium uppercase tracking-wide text-paper-dim">
        Documents
      </h2>

      {isLoading && (
        <p className="mt-3 font-sans text-sm text-paper-dim">Loading documents…</p>
      )}

      {!isLoading && documents.length === 0 && (
        <div className="mt-3 rounded border border-ink-border bg-ink-panel/40 px-3 py-4">
          <p className="font-sans text-sm text-paper-muted">No documents yet.</p>
          <p className="mt-1 font-sans text-xs text-paper-dim">
            Upload a PDF or TXT file to start asking questions about it. Your documents are private to this browser and are cleared after a period of inactivity.
          </p>
        </div>
      )}

      {!isLoading && documents.length > 0 && (
        <ul className="mt-3 space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.document_id}
              className="rounded border border-ink-border bg-ink-panel/60 px-3 py-2.5"
            >
              <p className="truncate font-sans text-sm text-paper" title={doc.filename}>
                {doc.filename}
              </p>
              <p className="mt-0.5 font-mono text-[11px] text-paper-dim">
                {doc.num_chunks} chunk{doc.num_chunks === 1 ? "" : "s"}
                {doc.num_pages ? ` · ${doc.num_pages} page${doc.num_pages === 1 ? "" : "s"}` : ""}
                {" · "}
                {formatUploadedAt(doc.uploaded_at)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
