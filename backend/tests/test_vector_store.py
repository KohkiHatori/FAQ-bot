"""
Tests for VectorStore functionality.
"""

import pytest
import os
import tempfile
import json
import pickle
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from core.vector_store import VectorStore
from core.faq import FAQManager
from core.exceptions import CacheError


class TestVectorStore:
    """Test the VectorStore class."""

    def setup_method(self):
        """Set up test environment for each test."""
        # Create a temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        self.vector_store = VectorStore(
            model_name="all-MiniLM-L6-v2",
            cache_dir=self.temp_dir,
            distance_metric="cosine",
        )
        self.mock_faq_manager = Mock(spec=FAQManager)

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test VectorStore initialization."""
        assert self.vector_store.model_name == "all-MiniLM-L6-v2"
        assert self.vector_store.cache_dir == self.temp_dir
        assert self.vector_store.distance_metric == "cosine"
        assert self.vector_store.embedder is None
        assert self.vector_store.index is None
        assert self.vector_store.documents == []
        assert self.vector_store.document_texts == []
        assert self.vector_store._initialized is False

    def test_initialization_with_defaults(self):
        """Test VectorStore initialization with default settings."""
        with patch("core.vector_store.settings") as mock_settings:
            mock_settings.embedding_model = "default-model"
            mock_settings.rag_cache_dir = tempfile.mkdtemp()
            mock_settings.vector_distance_metric = "l2"

            vector_store = VectorStore()

            assert vector_store.model_name == "default-model"
            assert vector_store.cache_dir == mock_settings.rag_cache_dir
            assert vector_store.distance_metric == "l2"

    def test_is_ready_false_initially(self):
        """Test is_ready returns False initially."""
        assert self.vector_store.is_ready() is False

    def test_is_ready_true_when_initialized(self):
        """Test is_ready returns True when properly initialized."""
        self.vector_store._initialized = True
        self.vector_store.index = Mock()
        assert self.vector_store.is_ready() is True

    def test_is_ready_false_without_index(self):
        """Test is_ready returns False without index."""
        self.vector_store._initialized = True
        self.vector_store.index = None
        assert self.vector_store.is_ready() is False

    @patch("core.vector_store.SentenceTransformer")
    def test_initialize_embedder(self, mock_sentence_transformer):
        """Test lazy initialization of embedder."""
        mock_embedder = Mock()
        mock_sentence_transformer.return_value = mock_embedder

        self.vector_store._initialize_embedder()

        assert self.vector_store.embedder == mock_embedder
        mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2")

    def test_get_cache_paths(self):
        """Test cache paths generation."""
        paths = self.vector_store._get_cache_paths()

        expected_paths = {
            "documents": os.path.join(self.temp_dir, "documents.pkl"),
            "embeddings": os.path.join(self.temp_dir, "embeddings.npy"),
            "faiss_index": os.path.join(self.temp_dir, "faiss_index.bin"),
            "metadata": os.path.join(self.temp_dir, "metadata.json"),
        }

        assert paths == expected_paths

    def test_format_faq_texts(self):
        """Test FAQ text formatting."""
        faq_data = [
            {"question": "What is Python?", "answer": "A programming language."},
            {"question": "What is FastAPI?", "answer": "A web framework."},
        ]

        formatted_texts = self.vector_store._format_faq_texts(faq_data)

        expected = [
            "passage: Q: What is Python?\nA: A programming language.",
            "passage: Q: What is FastAPI?\nA: A web framework.",
        ]

        assert formatted_texts == expected

    def test_format_faq_texts_empty(self):
        """Test FAQ text formatting with empty list."""
        formatted_texts = self.vector_store._format_faq_texts([])
        assert formatted_texts == []

    @patch("core.vector_store.faiss")
    @patch("core.vector_store.SentenceTransformer")
    def test_build_index_cosine_similarity(self, mock_sentence_transformer, mock_faiss):
        """Test building index with cosine similarity."""
        # Setup mocks
        mock_embedder = Mock()
        mock_embeddings = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
        mock_embedder.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_embedder

        mock_index = Mock()
        mock_faiss.IndexFlatIP.return_value = mock_index

        documents = [{"id": 1, "question": "Q1", "answer": "A1"}]
        texts = ["passage: Q: Q1\nA: A1"]

        result = self.vector_store._build_index(documents, texts)

        assert result is True
        assert self.vector_store.documents == documents
        assert self.vector_store.document_texts == texts
        mock_faiss.IndexFlatIP.assert_called_once_with(3)  # dimension
        mock_faiss.normalize_L2.assert_called_once()
        mock_index.add.assert_called_once()

    @patch("core.vector_store.faiss")
    @patch("core.vector_store.SentenceTransformer")
    def test_build_index_l2_distance(self, mock_sentence_transformer, mock_faiss):
        """Test building index with L2 distance."""
        self.vector_store.distance_metric = "l2"

        # Setup mocks
        mock_embedder = Mock()
        mock_embeddings = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        mock_embedder.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_embedder

        mock_index = Mock()
        mock_faiss.IndexFlatL2.return_value = mock_index

        documents = [{"id": 1, "question": "Q1", "answer": "A1"}]
        texts = ["passage: Q: Q1\nA: A1"]

        result = self.vector_store._build_index(documents, texts)

        assert result is True
        mock_faiss.IndexFlatL2.assert_called_once_with(3)  # dimension
        mock_faiss.normalize_L2.assert_not_called()  # No normalization for L2

    def test_search_similar_faqs_not_ready(self):
        """Test search_similar_faqs when not ready."""
        with pytest.raises(CacheError, match="RAG system not initialized"):
            self.vector_store.search_similar_faqs("test query")

    @patch("core.vector_store.settings")
    @patch("core.vector_store.faiss")
    @patch("core.vector_store.SentenceTransformer")
    def test_search_similar_faqs_success(
        self, mock_sentence_transformer, mock_faiss, mock_settings
    ):
        """Test successful search_similar_faqs."""
        mock_settings.default_top_k = 3

        # Setup vector store as ready
        self.vector_store._initialized = True
        mock_index = Mock()
        self.vector_store.index = mock_index
        self.vector_store.document_texts = ["text1", "text2", "text3"]

        # Setup embedder
        mock_embedder = Mock()
        mock_embedder.encode.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_sentence_transformer.return_value = mock_embedder

        # Setup search results
        mock_index.search.return_value = (
            np.array([[0.9, 0.8, 0.7]]),  # scores
            np.array([[0, 1, 2]]),  # indices
        )

        result = self.vector_store.search_similar_faqs("test query")

        # Should combine results from both queries
        expected = "text1\n\ntext2\n\ntext3\n\ntext1\n\ntext2\n\ntext3"
        assert result == expected

        # Should call encode twice (dual query strategy)
        assert mock_embedder.encode.call_count == 2

    def test_search_similar_not_built(self):
        """Test search_similar when index not built."""
        with pytest.raises(CacheError, match="Vector index not built"):
            self.vector_store.search_similar("test query")

    @patch("core.vector_store.faiss")
    @patch("core.vector_store.SentenceTransformer")
    def test_search_similar_success(self, mock_sentence_transformer, mock_faiss):
        """Test successful search_similar."""
        # Setup
        self.vector_store.index = Mock()
        self.vector_store.documents = [
            {"id": 1, "question": "Q1", "answer": "A1"},
            {"id": 2, "question": "Q2", "answer": "A2"},
        ]

        mock_embedder = Mock()
        mock_embedder.encode.return_value = np.array([[1.0, 2.0]], dtype=np.float32)
        mock_sentence_transformer.return_value = mock_embedder

        self.vector_store.index.search.return_value = (
            np.array([[0.9, 0.8]]),  # scores
            np.array([[0, 1]]),  # indices
        )

        results = self.vector_store.search_similar("test query", top_k=2)

        assert len(results) == 2
        assert results[0]["id"] == 1
        assert results[0]["similarity_score"] == 0.9
        assert results[0]["rank"] == 1
        assert results[1]["id"] == 2
        assert results[1]["similarity_score"] == 0.8
        assert results[1]["rank"] == 2

    def test_get_cache_info_no_cache(self):
        """Test get_cache_info when no cache exists."""
        info = self.vector_store.get_cache_info()

        assert info["cached"] is False
        assert info["message"] == "No cache found"
        assert "timestamp" in info

    def test_get_cache_info_with_cache(self):
        """Test get_cache_info when cache exists."""
        # Create metadata file
        metadata = {
            "model_name": "test-model",
            "document_count": 10,
            "embedding_dimension": 384,
            "distance_metric": "cosine",
            "created_at": "2024-01-01T12:00:00",
        }

        metadata_path = os.path.join(self.temp_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        info = self.vector_store.get_cache_info()

        assert info["cached"] is True
        assert info["model_name"] == "test-model"
        assert info["document_count"] == 10
        assert info["embedding_dimension"] == 384
        assert info["distance_metric"] == "cosine"
        assert info["created_at"] == "2024-01-01T12:00:00"
        assert info["cache_dir"] == self.temp_dir

    def test_get_cache_info_corrupted_metadata(self):
        """Test get_cache_info with corrupted metadata."""
        # Create invalid metadata file
        metadata_path = os.path.join(self.temp_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            f.write("invalid json")

        info = self.vector_store.get_cache_info()

        assert info["cached"] is False
        assert "Failed to read cache metadata" in info["message"]

    def test_clear_cache(self):
        """Test cache clearing."""
        # Create some cache files
        cache_paths = self.vector_store._get_cache_paths()
        for path in cache_paths.values():
            with open(path, "w") as f:
                f.write("test data")

        # Set some in-memory data
        self.vector_store.index = Mock()
        self.vector_store.documents = [{"test": "data"}]
        self.vector_store.document_texts = ["test text"]

        result = self.vector_store._clear_cache()

        # Check files are removed
        for path in cache_paths.values():
            assert not os.path.exists(path)

        # Check in-memory data is cleared
        assert self.vector_store.index is None
        assert self.vector_store.documents == []
        assert self.vector_store.document_texts == []

        assert result["success"] is True
        assert result["message"] == "RAG cache cleared successfully"

    def test_invalidate_cache(self):
        """Test cache invalidation."""
        # Create some cache files
        cache_paths = self.vector_store._get_cache_paths()
        for path in cache_paths.values():
            with open(path, "w") as f:
                f.write("test data")

        self.vector_store.invalidate_cache()

        # Check files are removed
        for path in cache_paths.values():
            assert not os.path.exists(path)

    @patch("core.vector_store.pickle")
    @patch("core.vector_store.np")
    @patch("core.vector_store.faiss")
    def test_save_to_cache(self, mock_faiss, mock_np, mock_pickle):
        """Test saving data to cache."""
        # Setup test data
        self.vector_store.documents = [{"id": 1, "question": "Q1"}]
        mock_embeddings = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        self.vector_store.index = Mock()

        # Mock datetime for consistent testing
        with patch("core.vector_store.np.datetime64") as mock_datetime:
            mock_datetime.return_value = "2024-01-01T12:00:00"

            result = self.vector_store._save_to_cache(mock_embeddings)

        assert result is True

        # Check that files were written
        mock_pickle.dump.assert_called_once()
        mock_np.save.assert_called_once()
        mock_faiss.write_index.assert_called_once()

        # Check metadata was saved
        metadata_path = os.path.join(self.temp_dir, "metadata.json")
        assert os.path.exists(metadata_path)

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        assert metadata["model_name"] == "all-MiniLM-L6-v2"
        assert metadata["document_count"] == 1
        assert metadata["distance_metric"] == "cosine"

    def test_load_from_cache_missing_files(self):
        """Test loading from cache when files are missing."""
        result = self.vector_store._load_from_cache()
        assert result is False

    def test_load_from_cache_model_mismatch(self):
        """Test loading from cache with model mismatch."""
        # Create metadata with different model
        metadata = {
            "model_name": "different-model",
            "document_count": 1,
            "embedding_dimension": 384,
            "distance_metric": "cosine",
        }

        metadata_path = os.path.join(self.temp_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Create other required files
        cache_paths = self.vector_store._get_cache_paths()
        for key, path in cache_paths.items():
            if key != "metadata":
                with open(path, "w") as f:
                    f.write("dummy data")

        result = self.vector_store._load_from_cache()
        assert result is False

    @patch("core.vector_store.pickle")
    @patch("core.vector_store.faiss")
    def test_load_from_cache_success(self, mock_faiss, mock_pickle):
        """Test successful loading from cache."""
        # Create metadata
        metadata = {
            "model_name": "all-MiniLM-L6-v2",
            "document_count": 1,
            "embedding_dimension": 384,
            "distance_metric": "cosine",
        }

        metadata_path = os.path.join(self.temp_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Create other required files
        cache_paths = self.vector_store._get_cache_paths()
        for key, path in cache_paths.items():
            if key != "metadata":
                with open(path, "w") as f:
                    f.write("dummy data")

        # Setup mocks
        mock_documents = [{"question": "Q1", "answer": "A1"}]
        mock_pickle.load.return_value = mock_documents
        mock_index = Mock()
        mock_faiss.read_index.return_value = mock_index

        result = self.vector_store._load_from_cache()

        assert result is True
        assert self.vector_store.documents == mock_documents
        assert self.vector_store.index == mock_index
        assert self.vector_store.document_texts == ["passage: Q: Q1\nA: A1"]

    def test_initialize_success(self):
        """Test successful initialization."""
        self.mock_faq_manager.load_faqs_for_rag.return_value = [
            {"question": "Q1", "answer": "A1"}
        ]

        with patch.object(
            self.vector_store, "_build_index_from_service", return_value=True
        ):
            result = self.vector_store.initialize(self.mock_faq_manager)

        assert result is True
        assert self.vector_store._initialized is True

    def test_initialize_failure(self):
        """Test initialization failure."""
        with patch.object(
            self.vector_store, "_build_index_from_service", return_value=False
        ):
            result = self.vector_store.initialize(self.mock_faq_manager)

        assert result is False
        assert self.vector_store._initialized is False

    def test_initialize_exception(self):
        """Test initialization with exception."""
        with patch.object(
            self.vector_store,
            "_build_index_from_service",
            side_effect=Exception("Test error"),
        ):
            result = self.vector_store.initialize(self.mock_faq_manager)

        assert result is False
        assert self.vector_store._initialized is False

    def test_build_index_from_service_with_cache(self):
        """Test building index when cache exists."""
        with patch.object(self.vector_store, "_load_from_cache", return_value=True):
            result = self.vector_store._build_index_from_service(self.mock_faq_manager)

        assert result is True
        # Should not call load_faqs_for_rag when cache exists
        self.mock_faq_manager.load_faqs_for_rag.assert_not_called()

    def test_build_index_from_service_force_rebuild(self):
        """Test building index with force rebuild."""
        self.mock_faq_manager.load_faqs_for_rag.return_value = [
            {"question": "Q1", "answer": "A1"}
        ]

        with patch.object(self.vector_store, "_load_from_cache", return_value=True):
            with patch.object(self.vector_store, "_build_index", return_value=True):
                result = self.vector_store._build_index_from_service(
                    self.mock_faq_manager, force_rebuild=True
                )

        assert result is True
        # Should call load_faqs_for_rag even when cache exists due to force rebuild
        self.mock_faq_manager.load_faqs_for_rag.assert_called_once()

    def test_rebuild_cache_success(self):
        """Test successful cache rebuild."""
        self.mock_faq_manager.load_faqs_for_rag.return_value = [
            {"question": "Q1", "answer": "A1"}
        ]
        self.mock_faq_manager.restore_faq_statuses_after_rebuild.return_value = {
            "restored_count": 1,
            "cleared_count": 1,
        }

        with patch.object(
            self.vector_store, "_build_index_from_service", return_value=True
        ):
            with patch.object(self.vector_store, "_clear_cache"):
                self.vector_store.documents = [{"question": "Q1", "answer": "A1"}]

                result = self.vector_store.rebuild_cache(self.mock_faq_manager)

        assert result["success"] is True
        assert result["faq_count"] == 1
        assert result["restored_count"] == 1
        assert result["cleared_pending_count"] == 1
        assert "timestamp" in result

    def test_rebuild_cache_failure(self):
        """Test cache rebuild failure."""
        with patch.object(
            self.vector_store, "_build_index_from_service", return_value=False
        ):
            with patch.object(self.vector_store, "_clear_cache"):
                with pytest.raises(CacheError, match="Failed to rebuild index"):
                    self.vector_store.rebuild_cache(self.mock_faq_manager)


if __name__ == "__main__":
    pytest.main([__file__])
