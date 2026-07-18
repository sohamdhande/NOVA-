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
    Supports project-scoped memory entries for multi-project distillation.
    """
    
    def __init__(self, vector_store=None):
        self.file_path = MEMORY_FILE
        self._ensure_file()
        
        if vector_store is not None:
            self.vector_store = vector_store
            self.use_vector = vector_store.ready
        else:
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

    def add_entry(self, project, source_type, title, summary, tags):
        """Add a memory entry scoped to a project with deduplication via VectorStore.
        
        Args:
            project: Project name (e.g., "huntrd", "nova")
            source_type: Type of source (e.g., "distillation", "manual", "claude_thread")
            title: Human-readable title
            summary: Content summary
            tags: List of tag strings
        """
        entry_id = str(uuid.uuid4())
        
        enc_title = encryption.encrypt_db_field(title)
        enc_summary = encryption.encrypt_db_field(summary)
        
        vector_text = f"{enc_title}: {enc_summary}"

        if self.use_vector:
            success = self.vector_store.add_entry(
                entry_id=entry_id,
                text=enc_summary,  # Ciphertext stored in Chroma documents
                embed_text=summary,  # Plaintext for embedding model
                metadata={
                    "title": enc_title,
                    "project": project,
                    "timestamp": datetime.now().isoformat(),
                    "tags": tags,
                    "source_type": source_type,
                    "full_text": vector_text
                }
            )
            
            if not success:
                if DEBUG:
                    print(f"[MemoryStore] Entry rejected by VectorStore: '{title}'")
                return {
                    "status": "duplicate",
                    "message": "Memory already exists (deduplicated by VectorStore).",
                    "title": title
                }

        entries = self._load()
        entry = {
            "id": entry_id,
            "project": project,
            "timestamp": datetime.now().isoformat(),
            "source_type": source_type,
            "title": enc_title,
            "summary": enc_summary,
            "tags": tags
        }
        entries.append(entry)
        self._save(entries)
        
        if DEBUG:
            print(f"[MemoryStore] Entry stored: '{title}' (project={project}, id={entry_id[:8]}...)")
            
        ret_entry = entry.copy()
        ret_entry["title"] = title
        ret_entry["summary"] = summary
        return ret_entry

    def search(self, query, project=None, top_k=5, similarity_threshold=0.65):
        """Semantic search with optional project filter and keyword fallback.
        
        Args:
            query: Search query string
            project: Optional project name to filter results. None searches all projects.
            top_k: Max results to return
            similarity_threshold: Minimum similarity score
        """
        if self.use_vector:
            # Build where clause for project filtering
            where_filter = None
            if project:
                where_filter = {"project": project}
            
            results = self.vector_store.search(
                query=query, 
                top_k=top_k, 
                similarity_threshold=similarity_threshold,
                where=where_filter
            )
            
            if results:
                normalized = []
                for r in results:
                    tags = r.get("tags", [])
                    if not tags and r["metadata"].get("tags"):
                        tags_str = r["metadata"]["tags"]
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

                    # r["text"] is now returned as ciphertext, just like memory.json
                    summary_text = r["text"]

                    normalized.append({
                        "id": r["id"],
                        "project": r["metadata"].get("project", "general"),
                        "title": encryption.decrypt_db_field(r["metadata"].get("title", "")),
                        "summary": encryption.decrypt_db_field(summary_text), 
                        "timestamp": r["metadata"].get("timestamp", ""),
                        "source_type": r["metadata"].get("source_type", ""),
                        "tags": tags,
                        "score": r["score"]
                    })
                
                print(f"[MemoryStore] Semantic search found {len(normalized)} results" +
                      (f" for project '{project}'" if project else ""))
                return normalized
        
        # Keyword fallback
        print("[MemoryStore] Fallback to keyword search")
        entries = self._load()
        query_lower = query.lower()
        results = []
        for e in entries:
            # Filter by project if specified
            if project and e.get("project", "general") != project:
                continue
                
            dec_title = encryption.decrypt_db_field(e['title'])
            dec_summary = encryption.decrypt_db_field(e['summary'])
            content = f"{dec_title} {dec_summary} {' '.join(e.get('tags', []))}".lower()
            if query_lower in content:
                e_copy = e.copy()
                e_copy["title"] = dec_title
                e_copy["summary"] = dec_summary
                results.append(e_copy)
        
        print(f"[MemoryStore] Keyword search found {len(results)} results")
        return results[:top_k]

    def get_projects(self):
        """Returns list of all unique project names in memory.
        
        Used by frontend to populate project dropdown.
        """
        entries = self._load()
        projects = set()
        for e in entries:
            projects.add(e.get("project", "general"))
        return sorted(list(projects))

    def get_project_summary(self, project):
        """Returns a high-level summary of what's stored about a project.
        
        Args:
            project: Project name
            
        Returns:
            dict with source_types, tags, entry_count, and recent_entries
        """
        entries = self._load()
        project_entries = [e for e in entries if e.get("project", "general") == project]
        
        source_types = set()
        all_tags = set()
        
        for e in project_entries:
            source_types.add(e.get("source_type", "unknown"))
            for tag in e.get("tags", []):
                all_tags.add(tag)
        
        # Get recent entries (last 5), decrypted
        recent = []
        for e in project_entries[-5:]:
            try:
                recent.append({
                    "id": e["id"],
                    "title": encryption.decrypt_db_field(e["title"]),
                    "summary": encryption.decrypt_db_field(e["summary"]),
                    "source_type": e.get("source_type", "unknown"),
                    "timestamp": e.get("timestamp", ""),
                    "tags": e.get("tags", [])
                })
            except Exception:
                # Skip entries with corrupted/unreadable ciphertext
                recent.append({
                    "id": e.get("id", "unknown"),
                    "title": "[decryption failed]",
                    "summary": "",
                    "source_type": e.get("source_type", "unknown"),
                    "timestamp": e.get("timestamp", ""),
                    "tags": e.get("tags", [])
                })
        
        return {
            "project": project,
            "entry_count": len(project_entries),
            "source_types": sorted(list(source_types)),
            "tags": sorted(list(all_tags)),
            "recent_entries": list(reversed(recent))  # Most recent first
        }

    def get_all_entries(self, project):
        """Returns ALL entries for a project (not paginated), fully decrypted.
        
        Args:
            project: Project name
        """
        entries = self._load()
        project_entries = [e for e in entries if e.get("project", "general") == project]
        
        decrypted = []
        for e in project_entries:
            try:
                decrypted.append({
                    "id": e["id"],
                    "title": encryption.decrypt_db_field(e["title"]),
                    "summary": encryption.decrypt_db_field(e["summary"]),
                    "source_type": e.get("source_type", "unknown"),
                    "timestamp": e.get("timestamp", ""),
                    "tags": e.get("tags", [])
                })
            except Exception:
                decrypted.append({
                    "id": e.get("id", "unknown"),
                    "title": "[decryption failed]",
                    "summary": "",
                    "source_type": e.get("source_type", "unknown"),
                    "timestamp": e.get("timestamp", ""),
                    "tags": e.get("tags", [])
                })
        # Sort by timestamp descending (newest first)
        decrypted.sort(key=lambda x: x["timestamp"], reverse=True)
        return decrypted

    def export_narrative(self, project):
        """Builds a professional markdown narrative summarizing the project."""
        entries = self.get_all_entries(project)
        summary = self.get_project_summary(project)
        return self._format_markdown_narrative(project, entries, summary)

    def _format_markdown_narrative(self, project, entries, summary):
        import json
        
        # We will parse out structured sections from 'distillation' type entries
        decisions = []
        assumptions = []
        uncertainties = []
        next_actions = []
        contradictions = []
        
        for e in entries:
            if e["source_type"] == "distillation":
                try:
                    # The summary field of a distillation entry is stringified JSON
                    data = json.loads(e["summary"])
                    if isinstance(data, dict):
                        # Tag each item with the date it was distilled
                        ts = e["timestamp"][:10] if e["timestamp"] else "unknown date"
                        
                        for d in data.get("decided", []):
                            d["_date"] = ts
                            decisions.append(d)
                        for a in data.get("assumed", []):
                            a["_date"] = ts
                            assumptions.append(a)
                        for u in data.get("uncertain", []):
                            u["_date"] = ts
                            uncertainties.append(u)
                        for na in data.get("next_actions", []):
                            na["_date"] = ts
                            next_actions.append(na)
                        for c in data.get("contradictions", []):
                            contradictions.append({"text": c, "_date": ts})
                except Exception:
                    pass

        # Build Markdown
        md = []
        md.append(f"# Project: {project.capitalize() if project else 'Unknown'}")
        md.append("**Status:** Active  ")
        md.append(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        md.append(f"**Total Memories:** {summary['entry_count']}  ")
        if summary['source_types']:
            md.append(f"**Source Types:** {', '.join(summary['source_types'])}")
        md.append("\n## Executive Summary")
        md.append(f"Project **{project}** has {summary['entry_count']} recorded memories. "
                  f"This document represents a consolidated narrative of all extracted decisions, "
                  f"assumptions, and actions.")

        if decisions:
            md.append("\n## Decisions")
            for d in decisions:
                md.append(f"### Decision: {d.get('decision', 'Unknown')}")
                md.append(f"- **Reasoning:** {d.get('reasoning', 'N/A')}")
                md.append(f"- **Confidence:** {d.get('confidence', 'N/A')}")
                md.append(f"- **Made:** {d.get('_date')}")
                if d.get('contradicts_prior'):
                    md.append("- **Contradictions:** ⚡ Contradicts prior decisions")

        if assumptions:
            md.append("\n## Assumptions")
            for a in assumptions:
                md.append(f"### Assumption: {a.get('assumption', 'Unknown')}")
                md.append(f"- **Why It Matters:** {a.get('why', 'N/A')}")
                md.append(f"- **Could Break If:** {a.get('could_break_if', 'N/A')}")

        if uncertainties:
            md.append("\n## Uncertainties & Open Questions")
            for u in uncertainties:
                md.append(f"### Question: {u.get('question', 'Unknown')}")
                md.append(f"- **Why It Matters:** {u.get('why_it_matters', 'N/A')}")
                md.append(f"- **Blocker:** {'Yes 🔴' if u.get('blocker') else 'No 🟡'}")

        if next_actions:
            md.append("\n## Next Actions")
            for na in next_actions:
                md.append(f"### Action: {na.get('action', 'Unknown')}")
                md.append(f"- **Owner:** {na.get('owner') or 'TBD'}")
                md.append(f"- **Timeline:** {na.get('timeline') or 'TBD'}")
                if na.get('depends_on'):
                    md.append(f"- **Depends On:** {na.get('depends_on')}")

        if contradictions:
            md.append("\n## Risk Register (Contradictions)")
            for c in contradictions:
                md.append(f"- ⚡ **{c['_date']}**: {c.get('text', '')}")

        md.append("\n## Appendix: Raw Memory Entries")
        for e in entries:
            ts = e["timestamp"][:10] if e["timestamp"] else "unknown"
            tags = ", ".join(e["tags"]) if e["tags"] else "none"
            md.append(f"**[{ts}] {e['title']}** (Source: {e['source_type']} | Tags: {tags})")
            
        return "\n".join(md)

    def recall_topic(self, topic):
        """Retrieve entries about a topic using semantic search."""
        return self.search(topic)
