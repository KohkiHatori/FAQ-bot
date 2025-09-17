"""
Vector store management for RAG operations.
"""

import json
import pickle
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from .config import settings
from .exceptions import CacheError


class VectorStore:
    """Manages vector embeddings and similarity search using FAISS."""

    def __init__(
        self, model_name: str = None, cache_dir: str = None, distance_metric: str = None
    ):
        """Initialize vector store with embedding model."""
        self.model_name = model_name or settings.embedding_model
        self.cache_dir = cache_dir or settings.rag_cache_dir
        self.distance_metric = distance_metric or settings.vector_distance_metric
        self.embedder = None
        self.index = None
        self.documents = []
        self.document_texts = []  # Store formatted texts like legacy
        self._initialized = False

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

    def initialize(self, faq_manager) -> bool:
        """Initialize the RAG system with FAQ data."""
        try:
            print("📚 Initializing vector store...")

            # Try to build index (will load from cache if available)
            success = self._build_index_from_service(faq_manager)

            if success:
                print("✅ Vector store ready")
                self._initialized = True
                return True
            else:
                print("❌ Failed to initialize vector store")
                self._initialized = False
                return False

        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
            self._initialized = False
            return False

    def is_ready(self) -> bool:
        """Check if RAG system is ready."""
        return self._initialized and self.index is not None

    def search_similar_faqs(self, query: str, top_k: int = None) -> str:
        """Search for similar FAQs using RAG and return formatted context string."""
        if not self.is_ready():
            raise CacheError("RAG system not initialized")

        top_k = top_k or settings.default_top_k

        # Initialize embedder if needed
        self._initialize_embedder()

        # Use legacy dual query strategy
        # Query 1: Japanese-specific format
        query_vector = self.embedder.encode([f"query: SUSTENについて：{query}"])
        query_vector = np.array(query_vector).astype("float32")

        # Query 2: Simple format
        query_vector_2 = self.embedder.encode([f"query:{query}"])
        query_vector_2 = np.array(query_vector_2).astype("float32")

        # Normalize if using cosine similarity
        if self.distance_metric == "cosine":
            faiss.normalize_L2(query_vector)
            faiss.normalize_L2(query_vector_2)

        # Search with both queries
        _, top_indices = self.index.search(query_vector, top_k)
        _, top_indices_2 = self.index.search(query_vector_2, top_k)

        # Combine results from both queries (legacy behavior)
        retrieved_context = "\n\n".join(
            [self.document_texts[i] for i in top_indices[0]]
        )
        retrieved_context_2 = "\n\n".join(
            [self.document_texts[i] for i in top_indices_2[0]]
        )
        retrieved_context = retrieved_context + "\n\n" + retrieved_context_2

        return retrieved_context

    def rebuild_cache(self, faq_manager) -> Dict[str, Any]:
        """Rebuild RAG cache with current FAQ data."""
        try:
            # Clear existing cache
            self._clear_cache()

            # Force rebuild from manager
            success = self._build_index_from_service(faq_manager, force_rebuild=True)

            if not success:
                raise CacheError("Failed to rebuild index")

            # Restore FAQ statuses after successful rebuild
            restore_result = faq_manager.restore_faq_statuses_after_rebuild()

            faq_count = len(self.documents)
            return {
                "success": True,
                "message": f"RAG cache rebuilt with {faq_count} FAQs, restored {restore_result['restored_count']} FAQ statuses",
                "faq_count": faq_count,
                "restored_count": restore_result["restored_count"],
                "cleared_pending_count": restore_result["cleared_count"],
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            raise CacheError(f"Failed to rebuild cache: {e}")

    def invalidate_cache(self):
        """Invalidate cache when FAQs are modified."""
        try:
            self._clear_cache()
        except Exception as e:
            print(f"Warning: Failed to clear RAG cache: {e}")

    def _build_index_from_service(
        self, faq_manager, force_rebuild: bool = False
    ) -> bool:
        """Build index from FAQ manager data with cache checking."""
        # Try to load from cache first (unless force rebuild)
        if not force_rebuild and self._load_from_cache():
            return True

        # Load and format FAQ data only when cache doesn't exist or force rebuild
        print("📖 Loading FAQ database...")
        faq_data = faq_manager.load_faqs_for_rag()
        faq_count = len(faq_data)
        print(f"✅ Loaded {faq_count} FAQ entries from database")

        # Format texts using legacy format
        print("🔄 Formatting FAQ texts...")
        formatted_texts = self._format_faq_texts(faq_data)

        # Build the index
        return self._build_index(faq_data, formatted_texts)

    def _format_faq_texts(self, faq_data: List[Dict[str, Any]]) -> List[str]:
        """Format FAQ data into texts using legacy format."""
        texts = []
        for faq in faq_data:
            formatted_text = f"passage: Q: {faq['question']}\nA: {faq['answer']}"
            texts.append(formatted_text)
        return texts

    def _build_index(self, documents: List[Dict[str, Any]], texts: List[str]) -> bool:
        """Build vector index from documents and texts."""
        print("🔍 Building vector search index...")

        # Initialize embedder
        self._initialize_embedder()

        # Store documents and texts
        self.documents = documents
        self.document_texts = texts

        # Create embeddings
        print(f"🔄 Creating embeddings for {len(texts)} texts...")
        embeddings = self.embedder.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings).astype("float32")

        # Build FAISS index based on distance metric
        dimension = embeddings.shape[1]
        if self.distance_metric == "cosine":
            self.index = faiss.IndexFlatIP(
                dimension
            )  # Inner product for cosine similarity
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
        else:  # L2 distance (default)
            self.index = faiss.IndexFlatL2(dimension)  # L2 distance

        self.index.add(embeddings)

        print(
            f"✅ Built FAISS index with {len(documents)} documents, dimension: {dimension}, metric: {self.distance_metric}"
        )

        # Save to cache
        self._save_to_cache(embeddings)

        return True

    def _initialize_embedder(self):
        """Lazy initialization of the embedding model."""
        if self.embedder is None:
            print(f"📚 Loading embedding model: {self.model_name}")
            self.embedder = SentenceTransformer(self.model_name)

    def _get_cache_paths(self) -> Dict[str, str]:
        """Get file paths for cached data."""
        return {
            "documents": os.path.join(self.cache_dir, "documents.pkl"),
            "embeddings": os.path.join(self.cache_dir, "embeddings.npy"),
            "faiss_index": os.path.join(self.cache_dir, "faiss_index.bin"),
            "metadata": os.path.join(self.cache_dir, "metadata.json"),
        }

    def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        if not self.index or not self.documents:
            raise CacheError("Vector index not built. Call build_index() first.")

        # Initialize embedder if needed
        self._initialize_embedder()

        # Create query embedding
        query_embedding = self.embedder.encode([query])
        query_embedding = np.array(query_embedding).astype("float32")

        # Normalize if using cosine similarity
        if self.distance_metric == "cosine":
            faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self.index.search(query_embedding, top_k)

        # Format results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(self.documents):
                result = self.documents[idx].copy()
                result["similarity_score"] = float(score)
                result["rank"] = i + 1
                results.append(result)

        return results

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the vector store cache."""
        cache_paths = self._get_cache_paths()
        metadata_path = cache_paths["metadata"]

        if not os.path.exists(metadata_path):
            return {
                "cached": False,
                "message": "No cache found",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            cache_info = {
                "cached": True,
                "model_name": metadata.get("model_name"),
                "document_count": metadata.get("document_count"),
                "embedding_dimension": metadata.get("embedding_dimension"),
                "distance_metric": metadata.get("distance_metric"),
                "created_at": metadata.get("created_at"),
                "cache_dir": self.cache_dir,
                "timestamp": datetime.now().isoformat(),
            }
            return cache_info
        except Exception as e:
            return {
                "cached": False,
                "message": f"Failed to read cache metadata: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def _clear_cache(self) -> Dict[str, Any]:
        """Clear all cached data."""
        try:
            cache_paths = self._get_cache_paths()

            for file_path in cache_paths.values():
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🗑️ Removed {file_path}")
                    except Exception as e:
                        print(f"⚠️ Failed to remove {file_path}: {e}")

            # Reset in-memory data
            self.index = None
            self.documents = []
            self.document_texts = []

            print("✅ Vector store cache cleared")
            return {
                "success": True,
                "message": "RAG cache cleared successfully",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {e}")

    def _save_to_cache(self, embeddings: np.ndarray):
        """Save vector store data to cache files."""
        cache_paths = self._get_cache_paths()

        try:
            # Save documents
            with open(cache_paths["documents"], "wb") as f:
                pickle.dump(self.documents, f)

            # Save embeddings
            np.save(cache_paths["embeddings"], embeddings)

            # Save FAISS index
            faiss.write_index(self.index, cache_paths["faiss_index"])

            # Save metadata
            metadata = {
                "model_name": self.model_name,
                "document_count": len(self.documents),
                "embedding_dimension": embeddings.shape[1],
                "distance_metric": self.distance_metric,
                "created_at": str(np.datetime64("now")),
                "cache_version": "1.0",
            }

            with open(cache_paths["metadata"], "w") as f:
                json.dump(metadata, f, indent=2)

            print(f"✅ Vector store cache saved to {self.cache_dir}")
            return True

        except Exception as e:
            print(f"⚠️ Failed to save vector store cache: {e}")
            return False

    def _load_from_cache(self) -> bool:
        """Load vector store data from cache files."""
        cache_paths = self._get_cache_paths()

        # Check if all required files exist
        required_files = ["documents", "embeddings", "faiss_index", "metadata"]
        for file_key in required_files:
            if not os.path.exists(cache_paths[file_key]):
                return False

        try:
            # Load metadata first to verify compatibility
            with open(cache_paths["metadata"], "r") as f:
                metadata = json.load(f)

            # Check if model matches
            if metadata.get("model_name") != self.model_name:
                print(
                    f"⚠️ Model mismatch: cached={metadata.get('model_name')}, current={self.model_name}"
                )
                return False

            # Adapt to cached distance metric if different
            cached_metric = metadata.get("distance_metric")
            if cached_metric and cached_metric != self.distance_metric:
                print(
                    f"🔄 Adapting distance metric from config ({self.distance_metric}) to cached ({cached_metric})"
                )
                self.distance_metric = cached_metric

            # Load documents
            with open(cache_paths["documents"], "rb") as f:
                self.documents = pickle.load(f)

            # Load FAISS index
            self.index = faiss.read_index(cache_paths["faiss_index"])

            # Reconstruct document_texts from documents using legacy format
            self.document_texts = self._format_faq_texts(self.documents)

            print(f"✅ Vector store cache loaded from {self.cache_dir}")
            print(
                f"📊 Loaded {len(self.documents)} documents, dimension: {metadata['embedding_dimension']}, metric: {metadata.get('distance_metric')}"
            )
            print(f"🕒 Cache created: {metadata.get('created_at', 'unknown')}")

            return True

        except Exception as e:
            print(f"⚠️ Failed to load vector store cache: {e}")
            return False
