import { useState } from "react";
import type { FormEvent } from "react";

interface QuestionFormProps {
  onAsk: (question: string) => void;
  isAsking: boolean;
  disabled: boolean;
}

export function QuestionForm({ onAsk, isAsking, disabled }: QuestionFormProps) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isAsking || disabled) return;
    onAsk(trimmed);
    setQuestion("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder={
          disabled ? "Upload a document to start asking questions…" : "What database does the system use?"
        }
        disabled={disabled || isAsking}
        className="flex-1 rounded border border-ink-borderLight bg-ink-panel px-4 py-3 font-sans text-sm text-paper placeholder:text-paper-dim focus:border-gold focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || isAsking || !question.trim()}
        className="rounded bg-gold px-5 py-3 font-sans text-sm font-medium text-ink transition-colors hover:bg-gold-hover disabled:cursor-not-allowed disabled:bg-ink-borderLight disabled:text-paper-dim"
      >
        {isAsking ? "Asking…" : "Ask"}
      </button>
    </form>
  );
}
