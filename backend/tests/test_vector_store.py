"""Tests for the FAISS-backed vector store."""
from __future__ import annotations

import shutil

import numpy as np
import pytest

from app.models.chunk import DocumentChunk


@pytest.fixture
def isolated_index_dir(tmp_path, monkeypatch):
    """Point the vector store at a temporary directory so tests don't
    pollute (or depend on) the real data/index directory."""
    import app.services.vector_store as vs_module

    monkeypatch.setattr(vs_module, "INDEX_PATH", tmp_path / "faiss.index")
    monkeypatch.setattr(vs_module, "METADATA_PATH", tmp_path / "chunks_metadata.json")
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def make_chunk(chunk_id: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        document_name="test.txt",
        text=text,
        page_number=1,
        chunk_index=0,
    )


class TestVectorStore:
    def test_add_and_search_returns_closest_match(self, isolated_index_dir):
        from app.services.vector_store import VectorStore

        store = VectorStore(dimension=4)
        chunks = [make_chunk("c1", "first"), make_chunk("c2", "second")]
        embeddings = np.array(
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype="float32"
        )
        store.add(embeddings, chunks)

        query = np.array([[0.9, 0.1, 0.0, 0.0]], dtype="float32")
        results = store.search(query, top_k=1)

        assert len(results) == 1
        assert results[0].chunk.chunk_id == "c1"

    def test_search_on_empty_index_returns_empty_list(self, isolated_index_dir):
        from app.services.vector_store import VectorStore

        store = VectorStore(dimension=4)
        query = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")
        results = store.search(query, top_k=5)
        assert results == []

    def test_total_chunks_reflects_additions(self, isolated_index_dir):
        from app.services.vector_store import VectorStore

        store = VectorStore(dimension=4)
        assert store.total_chunks == 0

        chunks = [make_chunk("c1", "first")]
        embeddings = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")
        store.add(embeddings, chunks)
        assert store.total_chunks == 1

    def test_top_k_larger_than_index_size_is_capped(self, isolated_index_dir):
        from app.services.vector_store import VectorStore

        store = VectorStore(dimension=4)
        chunks = [make_chunk("c1", "only one chunk")]
        embeddings = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")
        store.add(embeddings, chunks)

        query = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")
        results = store.search(query, top_k=10)
        assert len(results) == 1


class TestVectorStoreExtras:
    def test_persist_false_writes_nothing_to_disk(self, isolated_index_dir):
        from app.services.vector_store import VectorStore

        store = VectorStore(dimension=4, persist=False)
        store.add(
            np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32"), [make_chunk("c1", "first")]
        )
        assert list(isolated_index_dir.iterdir()) == []

    def test_remove_document_keeps_other_documents(self, isolated_index_dir):
        from app.services.vector_store import VectorStore

        store = VectorStore(dimension=4, persist=False)
        keep = make_chunk("keep", "kept")
        drop = make_chunk("drop", "dropped")
        drop.document_id = "doc-2"
        store.add(
            np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype="float32"), [keep, drop]
        )

        store.remove_document("doc-2")

        assert store.total_chunks == 1
        results = store.search(np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32"), top_k=5)
        assert [r.chunk.chunk_id for r in results] == ["keep"]
