import os
import sys
import numpy as np
import hashlib
import json

# Import DEBUG configuration
try:
    from config import DEBUG
except ImportError:
    DEBUG = False  # Default to production mode

# Patching numpy for compatibility with older libraries (like pydantic v1 or chromadb deps)
if not hasattr(np, "float_"):
    np.float_ = np.float64

# Force-silence ChromaDB telemetry
try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass

import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.config import Settings
import uuid
import logging

# Suppress sentence-transformers verbose logging (unless DEBUG)
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
    
    NO SINGLETON PATTERN - designed to be instantiated once by NovaApp
    and passed as a dependency to consumers.
    
    Model loads only in __init__() and persists for the object lifetime.
    """
    
    def __init__(self):
        """Initialize ChromaDB client and load embedding model ONCE."""
        try:
            # Initialize persistent client for ChromaDB
            # ChromaDB 0.3.x uses Client with Settings, 0.4.x uses PersistentClient
            try:
                # Try modern API first (0.4.x+)
                self.client = chromadb.PersistentClient(
                    path=CHROMA_DB_DIR,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
            except AttributeError:
                # Fall back to legacy API (0.3.x)
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=CHROMA_DB_DIR,
                    anonymized_telemetry=False
                ))
            
            # Load embedding model - ONLY ONCE per VectorStore instance
            self.model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

            # Define a custom embedding function to avoid Chroma's default ONNX dependency
            class SentenceTransformerEmbeddingFunction:
                def __init__(self, model):
                    self.model = model
                    
                def __call__(self, input):
                    if isinstance(input, str):
                        input = [input]
                    embeddings = self.model.encode(input, show_progress_bar=False, convert_to_numpy=True)
                    return embeddings.tolist()
            
            self.embedding_fn = SentenceTransformerEmbeddingFunction(self.model)

            # Get or create collection with distance metric
            # Note: ChromaDB 0.3.x may not support metadata for distance config
            try:
                self.collection = self.client.get_or_create_collection(
                    name="nova_memory",
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine"}  # Use cosine similarity
                )
            except:
                # Fallback for older ChromaDB versions
                self.collection = self.client.get_or_create_collection(
                    name="nova_memory",
                    embedding_function=self.embedding_fn
                )
            
            self.ready = True
            
        except Exception as e:
            print(f"[VectorStore] Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.ready = False

    def _generate_hash(self, content):
        """Generate a deterministic hash for content deduplication."""
        # Normalize: lowercase, strip whitespace, remove extra spaces
        normalized = " ".join(content.strip().lower().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def add_entry(self, entry_id, text, metadata=None):
        """Add text entry to vector store with deduplication check."""
        if not self.ready:
            return False

        try:
            # Generate hash for the content
            content_hash = self._generate_hash(text)

            # Check for existing duplicate by hash in metadata
            try:
                existing = self.collection.get(
                    where={"content_hash": content_hash},
                    include=["metadatas"]
                )
                
                if existing and existing.get("ids") and len(existing["ids"]) > 0:
                    return False
            except Exception as query_error:
                # If query fails, proceed with caution (log but don't block)
                pass

            # Generate embedding using the model directly for consistency
            embedding = self.model.encode([text], show_progress_bar=False, convert_to_numpy=True)[0].tolist()
            
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

            # Add to collection
            self.collection.add(
                ids=[entry_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[clean_metadata]
            )
            
            return True
            
        except Exception as e:
            print(f"[VectorStore] Failed to add entry: {e}")
            import traceback
            traceback.print_exc()
            return False

    def search(self, query, top_k=5, similarity_threshold=0.7):
        """Semantic search with strict similarity thresholding and clamping."""
        if not self.ready:
            return []

        try:
            # Clamp top_k to actual collection size
            count = self.collection.count()
            if count == 0:
                return []
            
            # Request more results than needed to account for threshold filtering
            # but clamp to collection size
            request_k = min(top_k * 2, count)
            
            # Generate query embedding
            embedding = self.model.encode([query], show_progress_bar=False, convert_to_numpy=True)[0].tolist()
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=request_k,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            ids = results['ids'][0]
            distances = results['distances'][0]
            
            formatted_results = []
            
            # Helper to parse tags back to list if needed
            def parse_tags(meta):
                tags_str = meta.get("tags", "")
                if tags_str:
                    return [t.strip() for t in tags_str.split(",") if t.strip()]
                return []

            for i in range(len(ids)):
                # Distance metric depends on ChromaDB version and config
                # ChromaDB 0.3.x default: L2 (Euclidean) distance
                # ChromaDB 0.4.x with cosine: cosine distance (0-2 range)
                # 
                # For L2 distance: smaller is better (0 = identical)
                # Convert to similarity score: 1 / (1 + distance)
                # For cosine distance: 1 - (distance / 2) where distance in [0, 2]
                #
                # We'll use a robust formula that works for both:
                distance = distances[i]
                
                # Check if distance is very small (cosine-like) or larger (L2-like)
                if distance <= 2.0:
                    # Likely cosine distance [0, 2] or small L2
                    # Use cosine-style conversion
                    similarity = 1.0 - (distance / 2.0)
                else:
                    # Larger L2 distance
                    similarity = 1.0 / (1.0 + distance)
                
                # Ensure similarity is in [0, 1] range
                similarity = max(0.0, min(1.0, similarity))
                
                # Strict Threshold Filter
                if similarity < similarity_threshold:
                    continue

                formatted_results.append({
                    "id": ids[i],
                    "text": documents[i],
                    "metadata": metadatas[i],
                    "score": round(similarity, 4),
                    "tags": parse_tags(metadatas[i])
                })
            
            # Limit to top_k after filtering
            formatted_results = formatted_results[:top_k]
            
            return formatted_results
            
        except Exception as e:
            print(f"[VectorStore] Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def exists(self, where_filter):
        """Check if an entry exists."""
        if not self.ready:
            return False
        try:
            results = self.collection.get(where=where_filter)
            return len(results["ids"]) > 0
        except Exception as e:
            print(f"[VectorStore] Exists check failed: {e}")
            return False

    def cleanup_duplicates(self):
        """
        Maintenance utility to find and remove duplicate entries.
        
        Deduplication strategy:
        - Group entries by content_hash
        - Keep the earliest entry (first ID encountered)
        - Remove all subsequent duplicates
        
        Returns:
            int: Number of duplicates removed
        """
        if not self.ready:
            return 0
        
        print("[VectorStore] Starting deduplication cleanup...")
        try:
            all_data = self.collection.get(include=["metadatas", "documents"])
            ids = all_data["ids"]
            metadatas = all_data["metadatas"]
            documents = all_data["documents"]
            
            seen_hashes = {}
            ids_to_delete = []
            
            for i, meta in enumerate(metadatas):
                # Use stored hash if available, else compute it
                c_hash = meta.get("content_hash")
                if not c_hash and i < len(documents):
                    # Compute from document content if missing
                    c_hash = self._generate_hash(documents[i])

                if c_hash in seen_hashes:
                    ids_to_delete.append(ids[i])
                    print(f"  Duplicate found: {ids[i][:8]}... (same as {seen_hashes[c_hash][:8]}...)")
                else:
                    seen_hashes[c_hash] = ids[i]
            
            if ids_to_delete:
                print(f"[VectorStore] Removing {len(ids_to_delete)} duplicates...")
                self.collection.delete(ids=ids_to_delete)
                print(f"[VectorStore] Cleanup complete. Remaining entries: {self.collection.count()}")
                return len(ids_to_delete)
            
            print("[VectorStore] No duplicates found.")
            return 0
            
        except Exception as e:
            print(f"[VectorStore] Cleanup failed: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def get_stats(self):
        """Return statistics about the vector store."""
        if not self.ready:
            return {"ready": False, "count": 0}
        
        try:
            return {
                "ready": True,
                "count": self.collection.count(),
                "collection_name": self.collection.name
            }
        except Exception as e:
            print(f"[VectorStore] Stats retrieval failed: {e}")
            return {"ready": True, "count": 0, "error": str(e)}


    def _generate_hash(self, content):
        """Generate a deterministic hash for content deduplication."""
        # Normalize: lowercase, strip whitespace, remove extra spaces
        normalized = " ".join(content.strip().lower().split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def add_entry(self, entry_id, text, metadata=None):
        """Add text entry to vector store with deduplication check."""
        if not self.ready:
            print("[VectorStore] Not ready, skipping add.")
            return False

        try:
            # Generate hash for the content
            content_hash = self._generate_hash(text)

            # Check for existing duplicate by hash in metadata
            try:
                existing = self.collection.get(
                    where={"content_hash": content_hash},
                    include=["metadatas"]
                )
                
                if existing and existing.get("ids") and len(existing["ids"]) > 0:
                    if DEBUG:
                        print(f"[VectorStore] Duplicate detected (hash={content_hash[:8]}...): '{text[:50]}...'")
                    return False
            except Exception as query_error:
                # If query fails, proceed with caution (log but don't block)
                if DEBUG:
                    print(f"[VectorStore] Dedup check warning: {query_error}")

            # Generate embedding using the model directly for consistency
            embedding = self.model.encode([text], show_progress_bar=False, convert_to_numpy=True)[0].tolist()
            
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

            # Add to collection
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
            import traceback
            traceback.print_exc()
            return False

    def search(self, query, top_k=5, similarity_threshold=0.7):
        """Semantic search with strict similarity thresholding and clamping."""
        if not self.ready:
            print("[VectorStore] Not ready, returning empty results.")
            return []

        try:
            # Clamp top_k to actual collection size
            count = self.collection.count()
            if count == 0:
                return []
            
            # Request more results than needed to account for threshold filtering
            # but clamp to collection size
            request_k = min(top_k * 2, count)
            
            # Generate query embedding
            embedding = self.model.encode([query], show_progress_bar=False, convert_to_numpy=True)[0].tolist()
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=request_k,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            ids = results['ids'][0]
            distances = results['distances'][0]
            
            formatted_results = []
            
            # Helper to parse tags back to list if needed
            def parse_tags(meta):
                tags_str = meta.get("tags", "")
                if tags_str:
                    return [t.strip() for t in tags_str.split(",") if t.strip()]
                return []

            for i in range(len(ids)):
                # Distance metric depends on ChromaDB version and config
                # ChromaDB 0.3.x default: L2 (Euclidean) distance
                # ChromaDB 0.4.x with cosine: cosine distance (0-2 range)
                # 
                # For L2 distance: smaller is better (0 = identical)
                # Convert to similarity score: 1 / (1 + distance)
                # For cosine distance: 1 - (distance / 2) where distance in [0, 2]
                #
                # We'll use a robust formula that works for both:
                distance = distances[i]
                
                # Check if distance is very small (cosine-like) or larger (L2-like)
                if distance <= 2.0:
                    # Likely cosine distance [0, 2] or small L2
                    # Use cosine-style conversion
                    similarity = 1.0 - (distance / 2.0)
                else:
                    # Larger L2 distance
                    similarity = 1.0 / (1.0 + distance)
                
                # Ensure similarity is in [0, 1] range
                similarity = max(0.0, min(1.0, similarity))
                
                # Strict Threshold Filter
                if similarity < similarity_threshold:
                    continue

                formatted_results.append({
                    "id": ids[i],
                    "text": documents[i],
                    "metadata": metadatas[i],
                    "score": round(similarity, 4),
                    "tags": parse_tags(metadatas[i])
                })
            
            # Limit to top_k after filtering
            formatted_results = formatted_results[:top_k]
            
            if formatted_results:
                print(f"[VectorStore] Search returned {len(formatted_results)} results (threshold={similarity_threshold})")
            
            return formatted_results
            
        except Exception as e:
            print(f"[VectorStore] Search failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def exists(self, where_filter):
        """Check if an entry exists."""
        if not self.ready:
            return False
        try:
            results = self.collection.get(where=where_filter)
            return len(results["ids"]) > 0
        except Exception as e:
            print(f"[VectorStore] Exists check failed: {e}")
            return False

    def cleanup_duplicates(self):
        """Maintenance utility to find and remove duplicates."""
        if not self.ready:
            return 0
        
        print("[VectorStore] Starting deduplication cleanup...")
        try:
            all_data = self.collection.get(include=["metadatas", "documents"])
            ids = all_data["ids"]
            metadatas = all_data["metadatas"]
            documents = all_data["documents"]
            
            seen_hashes = {}
            ids_to_delete = []
            
            for i, meta in enumerate(metadatas):
                # Use stored hash if available, else compute it
                c_hash = meta.get("content_hash")
                if not c_hash and i < len(documents):
                    # Compute from document content if missing
                    c_hash = self._generate_hash(documents[i])

                if c_hash in seen_hashes:
                    ids_to_delete.append(ids[i])
                    print(f"  Duplicate found: {ids[i][:8]}... (same as {seen_hashes[c_hash][:8]}...)")
                else:
                    seen_hashes[c_hash] = ids[i]
            
            if ids_to_delete:
                print(f"[VectorStore] Removing {len(ids_to_delete)} duplicates...")
                self.collection.delete(ids=ids_to_delete)
                print(f"[VectorStore] Cleanup complete. Remaining entries: {self.collection.count()}")
                return len(ids_to_delete)
            
            print("[VectorStore] No duplicates found.")
            return 0
            
        except Exception as e:
            print(f"[VectorStore] Cleanup failed: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def get_stats(self):
        """Return statistics about the vector store."""
        if not self.ready:
            return {"ready": False, "count": 0}
        
        try:
            return {
                "ready": True,
                "count": self.collection.count(),
                "collection_name": self.collection.name
            }
        except Exception as e:
            print(f"[VectorStore] Stats retrieval failed: {e}")
            return {"ready": True, "count": 0, "error": str(e)}

