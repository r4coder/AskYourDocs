"""
Vector store backed by FAISS.

Wraps a FAISS `IndexFlatIP` (inner product). Because embeddings are
L2-normalized, inner product equals cosine similarity.

`persist=True` saves the index and chunk metadata to disk (single-user use).
`persist=False` keeps everything in memory only — used for per-visitor
sessions in the web app, so uploaded content is never written to disk.
"""
from __future__ import annotations

import json
import threading

import faiss
import numpy as np

from app.config import INDEX_DIR
from app.models.chunk import DocumentChunk, RetrievedChunk

INDEX_PATH = INDEX_DIR / "faiss.index"
METADATA_PATH = INDEX_DIR / "chunks_metadata.json"


class VectorStore:
    """A thread-safe wrapper around a FAISS flat index plus chunk metadata."""

    def __init__(self, dimension: int, persist: bool = True):
        self.dimension = dimension
        self.persist = persist
        self._lock = threading.Lock()
        self.index: faiss.Index = faiss.IndexFlatIP(dimension)
        # FAISS only stores vectors, so metadata lives in a parallel list
        # (row position in the index -> DocumentChunk).
        self.chunks: list[DocumentChunk] = []
        if persist:
            self._load_from_disk()

    def add(self, embeddings: np.ndarray, chunks: list[DocumentChunk]) -> None:
        """Add vectors and their metadata to the index."""
        if embeddings.shape[0] != len(chunks):
            raise ValueError("Number of embeddings must match number of chunks.")
        if embeddings.shape[0] == 0:
            return
        with self._lock:
            self.index.add(embeddings)
            self.chunks.extend(chunks)
            self._save_to_disk()

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[RetrievedChunk]:
        """Return the top-k most similar chunks to the query embedding."""
        with self._lock:
            if self.index.ntotal == 0:
                return []
            top_k = min(top_k, self.index.ntotal)
            scores, indices = self.index.search(query_embedding, top_k)
            chunks = list(self.chunks)

        results: list[RetrievedChunk] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append(RetrievedChunk(chunk=chunks[idx], similarity_score=float(score)))
        return results

    def remove_document(self, document_id: str) -> None:
        """
        Remove every chunk of a document. Flat FAISS indexes can't delete rows,
        so we rebuild the index from the vectors we keep (`reconstruct`).
        """
        with self._lock:
            keep = [i for i, c in enumerate(self.chunks) if c.document_id != document_id]
            if len(keep) == len(self.chunks):
                return
            new_index = faiss.IndexFlatIP(self.dimension)
            if keep:
                vectors = np.vstack([self.index.reconstruct(i) for i in keep]).astype("float32")
                new_index.add(vectors)
            self.index = new_index
            self.chunks = [self.chunks[i] for i in keep]
            self._save_to_disk()

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    # -- Persistence (only when persist=True) ------------------------------------

    def _save_to_disk(self) -> None:
        if not self.persist:
            return
        faiss.write_index(self.index, str(INDEX_PATH))
        with open(METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump([c.to_metadata_dict() for c in self.chunks], f)

    def _load_from_disk(self) -> None:
        if INDEX_PATH.exists() and METADATA_PATH.exists():
            try:
                index = faiss.read_index(str(INDEX_PATH))
                if index.d != self.dimension:
                    return  # index from a different embedding model; start fresh
                with open(METADATA_PATH, encoding="utf-8") as f:
                    raw = json.load(f)
                self.index = index
                self.chunks = [DocumentChunk.from_metadata_dict(d) for d in raw]
            except Exception:
                self.index = faiss.IndexFlatIP(self.dimension)
                self.chunks = []
