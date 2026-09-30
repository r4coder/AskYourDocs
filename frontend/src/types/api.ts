// Types mirroring the backend's Pydantic schemas (see backend/app/schemas).

export interface DocumentInfo {
  document_id: string;
  filename: string;
  file_type: string;
  num_chunks: number;
  num_pages: number | null;
  uploaded_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentInfo;
  message: string;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
  total: number;
}

export interface SourceReference {
  document_name: string;
  page_number: number | null;
  chunk_id: string;
  snippet: string;
  similarity_score: number;
}

export interface ChatResponse {
  answer: string;
  sources: SourceReference[];
  grounded: boolean;
}

export interface HealthResponse {
  status: string;
  llm_model: string;
  embedding_model: string;
  /** True if visitors must supply their own Gemini API key. */
  api_key_required: boolean;
  active_sessions: number;
}

/** The Gemini API key the visitor entered; kept in the browser only. */
export interface StoredKey {
  apiKey: string;
  /** true = localStorage (survives closing the tab), false = sessionStorage (this tab only). */
  remember: boolean;
}

/** A single turn in the on-screen conversation history. */
export interface ChatTurn {
  id: string;
  question: string;
  response: ChatResponse | null;
  error: string | null;
}

/** Shape of a FastAPI validation/HTTP error response body. */
export interface ApiErrorBody {
  detail?: string | { msg: string }[];
}
