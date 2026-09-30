import { useRef, useState } from "react";
import type { DragEvent } from "react";

interface DocumentUploadProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

const ACCEPTED_TYPES = [".pdf", ".txt"];

export function DocumentUpload({ onUpload, isUploading }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    void onUpload(files[0]);
  };

  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setIsDragging(false);
    handleFiles(event.dataTransfer.files);
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
        disabled={isUploading}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        disabled={isUploading}
        className={`w-full rounded border border-dashed px-4 py-6 text-left transition-colors ${
          isDragging
            ? "border-gold bg-gold/5"
            : "border-ink-borderLight hover:border-gold/60 hover:bg-white/[0.02]"
        } ${isUploading ? "cursor-wait opacity-60" : "cursor-pointer"}`}
      >
        {isUploading ? (
          <div className="flex items-center gap-3">
            <span className="h-4 w-4 flex-shrink-0 animate-spin rounded-full border-2 border-gold/30 border-t-gold" />
            <span className="font-sans text-sm text-paper-muted">Indexing document…</span>
          </div>
        ) : (
          <div>
            <p className="font-sans text-sm font-medium text-paper">Upload a document</p>
            <p className="mt-1 font-sans text-xs text-paper-dim">
              Drop a PDF or TXT file here, or click to browse.
            </p>
          </div>
        )}
      </button>
    </div>
  );
}
