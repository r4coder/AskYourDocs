import { useCallback, useEffect, useState } from "react";
import { ApiError, askQuestion, checkHealth, listDocuments, uploadDocument } from "../services/api";
import { clearKey, loadKey, saveKey } from "../services/keyStorage";
import type { ChatTurn, DocumentInfo, HealthResponse, StoredKey } from "../types/api";
import { ChatTurnCard } from "../components/ChatTurnCard";
import { ConversationEmptyState } from "../components/ConversationEmptyState";
import { DocumentList } from "../components/DocumentList";
import { DocumentUpload } from "../components/DocumentUpload";
import { ErrorBanner } from "../components/ErrorBanner";
import { KeyBar } from "../components/KeyBar";
import { QuestionForm } from "../components/QuestionForm";
import { SetupScreen } from "../components/SetupScreen";

export function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [storedKey, setStoredKey] = useState<StoredKey | null>(() => loadKey());
  const [showSettings, setShowSettings] = useState(false);
  const [setupNotice, setSetupNotice] = useState<string | null>(null);

  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const refreshDocuments = useCallback(async () => {
    try {
      const result = await listDocuments();
      setDocuments(result.documents);
    } catch (err) {
      setGlobalError(err instanceof ApiError ? err.message : "Failed to load documents.");
    } finally {
      setIsLoadingDocuments(false);
    }
  }, []);

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealthError("Can't reach the server. Check that the backend is running, then reload."));
    void refreshDocuments();
  }, [refreshDocuments]);

  /** A rejected key (401) reopens the key screen with an explanation. */
  const handleApiError = (err: unknown, fallback: string): string => {
    const message = err instanceof ApiError ? err.message : fallback;
    if (err instanceof ApiError && err.status === 401) {
      setSetupNotice(message);
      setShowSettings(true);
    }
    return message;
  };

  const apiKey = storedKey?.apiKey ?? null;

  const handleUpload = async (file: File) => {
    setGlobalError(null);
    setIsUploading(true);
    try {
      await uploadDocument(file, apiKey);
      await refreshDocuments();
    } catch (err) {
      setGlobalError(handleApiError(err, "Failed to upload document."));
    } finally {
      setIsUploading(false);
    }
  };

  const handleAsk = async (question: string) => {
    const turnId = crypto.randomUUID();
    setTurns((prev) => [...prev, { id: turnId, question, response: null, error: null }]);
    setIsAsking(true);
    try {
      const response = await askQuestion(question, apiKey);
      setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, response } : t)));
    } catch (err) {
      const message = handleApiError(err, "Failed to get an answer.");
      setTurns((prev) => prev.map((t) => (t.id === turnId ? { ...t, error: message } : t)));
    } finally {
      setIsAsking(false);
    }
  };

  const handleSaveKey = (key: StoredKey) => {
    saveKey(key);
    setStoredKey(key);
    setSetupNotice(null);
    setShowSettings(false);
  };

  const handleRemoveKey = () => {
    clearKey();
    setStoredKey(null);
  };

  if (healthError) {
    return (
      <div className="min-h-screen bg-ink px-6 py-10 text-paper sm:px-10">
        <ErrorBanner message={healthError} onDismiss={() => window.location.reload()} />
      </div>
    );
  }
  if (!health) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-gold/30 border-t-gold" />
      </div>
    );
  }

  const serverHasNoKey = health.api_key_required;
  const needsKey = serverHasNoKey && !apiKey;

  // First page: ask for a key whenever the server can't provide one itself.
  if (needsKey || showSettings) {
    return (
      <SetupScreen
        initial={storedKey}
        notice={setupNotice}
        onSave={handleSaveKey}
        onCancel={needsKey ? undefined : () => { setShowSettings(false); setSetupNotice(null); }}
      />
    );
  }

  const hasDocuments = documents.length > 0;

  return (
    <div className="min-h-screen bg-ink text-paper">
      <header className="border-b border-ink-border px-6 py-5 sm:px-10">
        <h1 className="font-serif text-2xl font-semibold text-paper">AI Document Q&amp;A</h1>
        <p className="mt-1 font-sans text-sm text-paper-dim">
          Upload documents, ask questions, get answers grounded in your own text.
        </p>
      </header>

      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 py-8 sm:px-10 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-6">
          <DocumentUpload onUpload={handleUpload} isUploading={isUploading} />
          <DocumentList documents={documents} isLoading={isLoadingDocuments} />
        </aside>

        <main className="space-y-6">
          {serverHasNoKey && storedKey && (
            <KeyBar storedKey={storedKey} onChange={() => setShowSettings(true)} onRemove={handleRemoveKey} />
          )}

          {globalError && <ErrorBanner message={globalError} onDismiss={() => setGlobalError(null)} />}

          <QuestionForm onAsk={handleAsk} isAsking={isAsking} disabled={!hasDocuments} />

          <div className="space-y-4">
            {turns.length === 0 ? (
              <ConversationEmptyState />
            ) : (
              [...turns].reverse().map((turn) => <ChatTurnCard key={turn.id} turn={turn} />)
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
