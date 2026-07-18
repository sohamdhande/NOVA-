import os
import sys
import threading
import numpy as np
import hashlib
import json

# Import DEBUG configuration
try:
    from config import DEBUG
except ImportError:
    DEBUG = False  # Default to production mode

# Patching numpy for compatibility with older libraries
if not hasattr(np, "float_"):
    np.float_ = np.float64

# Force-silence ChromaDB telemetry
try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass

import chromadb

from chromadb.config import Settings
import uuid
import logging

# Suppress sentence-transformers verbose logging
if not DEBUG:
    logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
else:
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

# Path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_DIR = os.path.join(BASE_DIR, "../data/chroma_db")


class VectorStore:
    """
    Vector storage with embedding model for semantic memory.
    """
    
    def __init__(self):
        try:
            try:
                self.client = chromadb.PersistentClient(
                    path=CHROMA_DB_DIR,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            except AttributeError:
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=CHROMA_DB_DIR,
                    anonymized_telemetry=False
                ))
            
            class SentenceTransformerEmbeddingFunction:
                def __init__(self, model_name):
                    self.model_name = model_name
                    self.model = None
                    
                def __call__(self, input):
                    if self.model is None:
                        from sentence_transformers import SentenceTransformer
                        self.model = SentenceTransformer(self.model_name, device='cpu')
                    if isinstance(input, str):
                        input = [input]
                    embeddings = self.model.encode(input, show_progress_bar=False, convert_to_numpy=True)
                    return embeddings.tolist()
            
            self.embedding_fn = SentenceTransformerEmbeddingFunction('all-MiniLM-L6-v2')

            try:
                self.collection = self.client.get_or_create_collection(
                    name="nova_memory",
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine"}
                )
            except:
                self.collection = self.client.get_or_create_collection(
                    name="nova_memory",
                    embedding_function=self.embedding_fn
                )
            
            self.ready = True
            self._add_lock = threading.Lock()
            
        except Exception as e:
            print(f"[VectorStore] Initialization failed: {e}")
            self.ready = False

    def _generate_hash(self, content):
        """Generate a deterministic hash for content deduplication."""
        normalized = " ".join(content.strip().lower().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def add_entry(self, entry_id, text, metadata=None, embed_text=None):
        """Add text entry to vector store with deduplication check."""
        if not self.ready:
            print("[VectorStore] Not ready, skipping add.")
            return False

        try:
            # Determine which text represents the semantic content for embedding and hashing
            semantic_text = embed_text if embed_text is not None else text

            # Generate hash for the semantic content (allows deduping even if text is randomly encrypted)
            content_hash = self._generate_hash(semantic_text)

            # Generate embedding OUTSIDE the lock
            embedding = self.embedding_fn([semantic_text])[0]

            # Prepare metadata
            clean_metadata = {}
            if metadata:
                for k, v in metadata.items():
                    if isinstance(v, list):
                        clean_metadata[k] = ", ".join(str(item) for item in v)
                    elif v is None:
                        clean_metadata[k] = ""
                    else:
                        clean_metadata[k] = str(v)
            
            # Add hash to metadata for future deduplication checks
            clean_metadata["content_hash"] = content_hash

            # Atomic dedup-check-and-insert under lock
            with self._add_lock:
                # Check for existing duplicate by hash in metadata
                try:
                    existing = self.collection.get(
                        where={"content_hash": content_hash},
                        include=["metadatas"]
                    )
                    
                    if existing and existing.get("ids") and len(existing["ids"]) > 0:
                        if DEBUG:
                            print(f"[VectorStore] Duplicate detected (hash={content_hash[:8]}...): '{semantic_text[:50]}...'")
                        return False
                except Exception as query_error:
                    if DEBUG:
                        print(f"[VectorStore] Dedup check warning: {query_error}")

                # Add to collection (storing `text`, which may be ciphertext, in the documents field)
                self.collection.add(
                    ids=[entry_id],
                    embeddings=[embedding],
                    documents=[text],
                    metadatas=[clean_metadata]
                )
            
            print(f"[VectorStore] Added entry {entry_id[:8]}... (total: {self.collection.count()})")
            return True
            
        except Exception as e:
            print(f"[VectorStore] Failed to add entry: {e}")
            return False

    def search(self, query, top_k=5, similarity_threshold=0.7, where=None):
        """Semantic search with strict similarity thresholding and clamping.
        
        Args:
            query: Search query string
            top_k: Max results to return
            similarity_threshold: Minimum similarity score
            where: Optional ChromaDB where filter dict (e.g., {"project": "huntrd"})
        """
        if not self.ready:
            print("[VectorStore] Not ready, returning empty results.")
            return []

        try:
            count = self.collection.count()
            if count == 0:
                return []
            
            request_k = min(top_k * 2, count)
            embedding = self.embedding_fn([query])[0]
            
            query_kwargs = {
                "query_embeddings": [embedding],
                "n_results": request_k,
                "include": ["documents", "metadatas", "distances"]
            }
            if where:
                query_kwargs["where"] = where
            
            results = self.collection.query(**query_kwargs)
            
            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            ids = results['ids'][0]
            distances = results['distances'][0]
            
            formatted_results = []
            
            def parse_tags(meta):
                tags_str = meta.get("tags", "")
                if tags_str:
                    return [t.strip() for t in tags_str.split(",") if t.strip()]
                return []

            for i in range(len(ids)):
                distance = distances[i]
                
                if distance <= 2.0:
                    similarity = max(0.0, 1.0 - (distance / 2.0))
                else:
                    similarity = max(0.0, 1.0 / (1.0 + distance))
                    
                if similarity >= similarity_threshold:
                    formatted_results.append({
                        "id": ids[i],
                        "text": documents[i],
                        "metadata": metadatas[i],
                        "score": similarity,
                        "tags": parse_tags(metadatas[i])
                    })
                    
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            return formatted_results[:top_k]
            
        except Exception as e:
            print(f"[VectorStore] Search failed: {e}")
            return []

    def get_stats(self):
        """Return basic stats about the vector store."""
        if not self.ready:
            return {"ready": False, "count": 0}
        try:
            return {
                "ready": True,
                "count": self.collection.count()
            }
        except Exception as e:
            print(f"[VectorStore] Stats retrieval failed: {e}")
            return {"ready": True, "count": 0, "error": str(e)}
