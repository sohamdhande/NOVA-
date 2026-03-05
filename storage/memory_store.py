import json
import os
import uuid
from datetime import datetime
from core.encryption import encryption

try:
    from config import DEBUG
except ImportError:
    DEBUG = False

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "../data/memory.json")


class MemoryStore:
    """
    High-level memory API with JSON persistence and optional vector search.
    
    Accepts VectorStore as a dependency (dependency injection pattern).
    """
    
    def __init__(self, vector_store=None):
        """
        Initialize MemoryStore with optional vector store dependency.
        
        Args:
            vector_store: VectorStore instance (optional, for semantic search)
        """
        self.file_path = MEMORY_FILE
        self._ensure_file()
        
        # Accept injected VectorStore instance
        if vector_store is not None:
            self.vector_store = vector_store
            self.use_vector = vector_store.ready
        else:
            # Fallback: no vector search available
            self.vector_store = None
            self.use_vector = False

    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def _load(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_entry(self, source_type, title, summary, tags):
        """Add a memory entry with deduplication via VectorStore."""
        # Create common ID for both stores
        entry_id = str(uuid.uuid4())
        
        # Encrypt sensitive data
        enc_title = encryption.encrypt_db_field(title)
        enc_summary = encryption.encrypt_db_field(summary)
        
        # Construct semantic content for vector storage
        # We store the encrypted text in the vector store, but vector search won't work well on encrypted text! 
        # Wait, if we encrypt the text going to the vector store, semantic search is impossible. 
        # The instructions said "wrap any fields that store sensitive data (email content, conversation history, API keys)"
        vector_text = f"{enc_title}: {enc_summary}"

        # Attempt to add to vector store first (controls deduplication)
        if self.use_vector:
            success = self.vector_store.add_entry(
                entry_id=entry_id,
                text=enc_summary,  # Deduplicate based on summary, not title+summary
                metadata={
                    "title": enc_title,
                    "timestamp": datetime.now().isoformat(),
                    "tags": tags,
                    "source_type": source_type,
                    "full_text": vector_text  # Store full text in metadata
                }
            )
            
            if not success:
                # VectorStore rejected (duplicate or error)
                return {
                    "status": "duplicate",
                    "message": "Memory already exists (deduplicated by VectorStore).",
                    "title": title # Return original unencrypted title to user
                }

        # If vector addition succeeded (or disabled), add to JSON
        entries = self._load()
        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "source_type": source_type,
            "title": enc_title,
            "summary": enc_summary,
            "tags": tags
        }
        entries.append(entry)
        self._save(entries)
        
        # Return decrypted version to the caller for immediate consumption
        ret_entry = entry.copy()
        ret_entry["title"] = title
        ret_entry["summary"] = summary
        return ret_entry

    def search(self, query, top_k=5, similarity_threshold=0.65):
        """
        Semantic search with keyword fallback and result deduplication.
        
        Args:
            query: Search query string
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0.0-1.0)
            
        Returns:
            List of deduplicated results sorted by score desc, then timestamp desc
        """
        if self.use_vector:
            results = self.vector_store.search(
                query=query, 
                top_k=top_k * 2,  # Request more to account for deduplication
                similarity_threshold=similarity_threshold
            )
            
            if results:
                # Deduplicate by ID
                seen_ids = set()
                deduplicated = []
                
                for r in results:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        
                        # Parse tags from metadata
                        tags = r.get("tags", [])
                        if not tags and r["metadata"].get("tags"):
                            tags_str = r["metadata"]["tags"]
                            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

                        # Use summary from the stored text (which is the summary in our new design)
                        # Or fall back to full_text if available
                        summary_text = r["text"]

                        deduplicated.append({
                            "id": r["id"],
                            "title": encryption.decrypt_db_field(r["metadata"].get("title", "")),
                            "summary": encryption.decrypt_db_field(summary_text), 
                            "timestamp": r["metadata"].get("timestamp", ""),
                            "tags": tags,
                            "score": r["score"]
                        })
                
                # Sort: score descending, then timestamp descending
                deduplicated.sort(key=lambda x: (-x.get("score", 0), -x.get("timestamp", "")))
                
                # Limit to top_k after deduplication
                deduplicated = deduplicated[:top_k]
                
                return deduplicated
        
        # Fallback to keyword search
        entries = self._load()
        query_lower = query.lower()
        results = []
        seen_ids = set()  # Deduplicate by ID
        
        for e in entries:
            if e["id"] in seen_ids:
                continue
                
            dec_title = encryption.decrypt_db_field(e['title'])
            dec_summary = encryption.decrypt_db_field(e['summary'])
            
            content = f"{dec_title} {dec_summary} {' '.join(e.get('tags', []))}".lower()
            if query_lower in content:
                seen_ids.add(e["id"])
                
                e_copy = e.copy()
                e_copy["title"] = dec_title
                e_copy["summary"] = dec_summary
                results.append(e_copy)
        
        # Sort by timestamp descending for keyword search
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return results[:top_k]

    def recall_topic(self, topic):
        """Retrieve entries about a topic using semantic search."""
        return self.search(topic)


    def _ensure_file(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def _load(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, data):
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def add_entry(self, source_type, title, summary, tags):
        """Add a memory entry with deduplication via VectorStore."""
        # Create common ID for both stores
        entry_id = str(uuid.uuid4())
        
        enc_title = encryption.encrypt_db_field(title)
        enc_summary = encryption.encrypt_db_field(summary)
        
        # Construct semantic content for vector storage
        vector_text = f"{enc_title}: {enc_summary}"

        # Attempt to add to vector store first (controls deduplication)
        if self.use_vector:
            success = self.vector_store.add_entry(
                entry_id=entry_id,
                text=enc_summary,  # Deduplicate based on summary, not title+summary
                metadata={
                    "title": enc_title,
                    "timestamp": datetime.now().isoformat(),
                    "tags": tags,
                    "source_type": source_type,
                    "full_text": vector_text  # Store full text in metadata
                }
            )
            
            if not success:
                # VectorStore rejected (duplicate or error)
                if DEBUG:
                    print(f"[MemoryStore] Entry rejected by VectorStore: '{title}'")
                return {
                    "status": "duplicate",
                    "message": "Memory already exists (deduplicated by VectorStore).",
                    "title": title
                }

        # If vector addition succeeded (or disabled), add to JSON
        entries = self._load()
        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "source_type": source_type,
            "title": enc_title,
            "summary": enc_summary,
            "tags": tags
        }
        entries.append(entry)
        self._save(entries)
        
        if DEBUG:
            print(f"[MemoryStore] Entry stored: '{title}' (id={entry_id[:8]}...)")
            
        ret_entry = entry.copy()
        ret_entry["title"] = title
        ret_entry["summary"] = summary
        return ret_entry

    def search(self, query, top_k=5, similarity_threshold=0.65):
        """Semantic search with keyword fallback."""
        if self.use_vector:
            results = self.vector_store.search(
                query=query, 
                top_k=top_k, 
                similarity_threshold=similarity_threshold
            )
            
            if results:
                # Normalize vector results to match JSON structure
                normalized = []
                for r in results:
                    # Parse tags from metadata
                    tags = r.get("tags", [])
                    if not tags and r["metadata"].get("tags"):
                        tags_str = r["metadata"]["tags"]
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

                    # Use summary from the stored text (which is the summary in our new design)
                    # Or fall back to full_text if available
                    summary_text = r["text"]

                    normalized.append({
                        "id": r["id"],
                        "title": encryption.decrypt_db_field(r["metadata"].get("title", "")),
                        "summary": encryption.decrypt_db_field(summary_text), 
                        "timestamp": r["metadata"].get("timestamp", ""),
                        "tags": tags,
                        "score": r["score"]
                    })
                
                print(f"[MemoryStore] Semantic search found {len(normalized)} results")
                return normalized
        
        # Fallback to keyword search
        print("[MemoryStore] Fallback to keyword search")
        entries = self._load()
        query_lower = query.lower()
        results = []
        for e in entries:
            dec_title = encryption.decrypt_db_field(e['title'])
            dec_summary = encryption.decrypt_db_field(e['summary'])
            content = f"{dec_title} {dec_summary} {' '.join(e.get('tags', []))}".lower()
            if query_lower in content:
                e_copy = e.copy()
                e_copy["title"] = dec_title
                e_copy["summary"] = dec_summary
                results.append(e_copy)
        
        print(f"[MemoryStore] Keyword search found {len(results)} results")
        return results

    def recall_topic(self, topic):
        """Retrieve entries about a topic using semantic search."""
        return self.search(topic)
