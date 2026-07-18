import hashlib
import json
import csv
import io
from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from nova.packages.observation import build_bundle, ObservationBundle

class IngestionParseError(Exception):
    pass

class UnknownSourceTypeError(Exception):
    pass

class DuplicateArtifactError(Exception):
    pass

@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    artifact_type: str
    source_system: str
    source_identifier: str
    created_at: datetime
    ingested_at: datetime
    checksum: str
    version: int
    metadata: dict[str, Any]
    raw_payload: Any

class IngestionAdapter(ABC):
    source_type: str

    @abstractmethod
    def parse(self, raw_input: Any) -> dict:
        pass

class SlackAdapter(IngestionAdapter):
    source_type = "slack"

    def parse(self, raw_input: dict) -> dict:
        if not isinstance(raw_input, dict):
            raise IngestionParseError("SlackAdapter requires a dict input.")
        
        required_keys = {"channel", "user", "text"}
        missing = required_keys - raw_input.keys()
        if missing:
            raise IngestionParseError(f"Slack input missing required keys: {missing}")
            
        return {
            "sender": raw_input["user"],
            "content": raw_input["text"],
            "source_path": f"slack/{raw_input['channel']}"
        }

class GitCommitAdapter(IngestionAdapter):
    source_type = "git"

    def parse(self, raw_input: dict) -> dict:
        if not isinstance(raw_input, dict):
            raise IngestionParseError("GitCommitAdapter requires a dict input.")
            
        required_keys = {"author", "message", "sha"}
        missing = required_keys - raw_input.keys()
        if missing:
            raise IngestionParseError(f"Git commit missing required keys: {missing}")
            
        return {
            "sender": raw_input["author"],
            "content": raw_input["message"],
            "source_path": f"git/commit/{raw_input['sha']}"
        }

class PlaintextAdapter(IngestionAdapter):
    source_type = "plaintext"

    def parse(self, raw_input: str) -> dict:
        if not isinstance(raw_input, str):
            raise IngestionParseError("PlaintextAdapter requires a string input.")
        
        if not raw_input:
            raise IngestionParseError("Plaintext input cannot be empty.")
            
        sha = hashlib.sha256(raw_input.encode('utf-8')).hexdigest()[:8]
        
        return {
            "sender": "unknown",
            "content": raw_input,
            "source_path": f"plaintext/{sha}"
        }

class MarkdownAdapter(IngestionAdapter):
    source_type = "markdown"

    def parse(self, raw_input: str) -> dict:
        if not isinstance(raw_input, str) or not raw_input:
            raise IngestionParseError("MarkdownAdapter requires non-empty string.")
        sha = hashlib.sha256(raw_input.encode('utf-8')).hexdigest()[:8]
        return {
            "sender": "author_md",
            "content": raw_input,
            "source_path": f"markdown/{sha}"
        }

class PDFAdapter(IngestionAdapter):
    source_type = "pdf"

    def parse(self, raw_input: bytes | str) -> dict:
        if not raw_input:
            raise IngestionParseError("PDFAdapter requires payload.")
        if isinstance(raw_input, bytes):
            text = raw_input.decode('utf-8', errors='ignore')
        else:
            text = raw_input
        sha = hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]
        return {
            "sender": "pdf_author",
            "content": f"Extracted PDF: {text[:100]}",
            "source_path": f"pdf/{sha}"
        }

class EmailAdapter(IngestionAdapter):
    source_type = "email"

    def parse(self, raw_input: str | dict) -> dict:
        if isinstance(raw_input, dict):
            sender = raw_input.get("from", "unknown_email")
            body = raw_input.get("body", "")
            subject = raw_input.get("subject", "no_subject")
        elif isinstance(raw_input, str):
            sender = "unknown_email"
            body = raw_input
            subject = "parsed_email"
        else:
            raise IngestionParseError("EmailAdapter invalid input.")
            
        sha = hashlib.sha256(body.encode('utf-8')).hexdigest()[:8]
        return {
            "sender": sender,
            "content": f"Subject: {subject}\n{body}",
            "source_path": f"email/{sha}"
        }

class CalendarAdapter(IngestionAdapter):
    source_type = "calendar"

    def parse(self, raw_input: str) -> dict:
        if not isinstance(raw_input, str):
            raise IngestionParseError("CalendarAdapter requires string.")
        sha = hashlib.sha256(raw_input.encode('utf-8')).hexdigest()[:8]
        return {
            "sender": "calendar_organizer",
            "content": raw_input,
            "source_path": f"calendar/{sha}"
        }

class JSONAdapter(IngestionAdapter):
    source_type = "json"

    def parse(self, raw_input: str | dict) -> dict:
        if isinstance(raw_input, str):
            try:
                data = json.loads(raw_input)
            except Exception as e:
                raise IngestionParseError(f"Invalid JSON string: {e}")
        elif isinstance(raw_input, dict):
            data = raw_input
        else:
            raise IngestionParseError("JSONAdapter requires dict or str.")
            
        content_str = json.dumps(data, sort_keys=True)
        sha = hashlib.sha256(content_str.encode('utf-8')).hexdigest()[:8]
        return {
            "sender": data.get("sender", "json_system"),
            "content": data.get("content", content_str),
            "source_path": data.get("source_path", f"json/{sha}")
        }

class CSVAdapter(IngestionAdapter):
    source_type = "csv"

    def parse(self, raw_input: str) -> dict:
        if not isinstance(raw_input, str):
            raise IngestionParseError("CSVAdapter requires string.")
        reader = csv.reader(io.StringIO(raw_input))
        rows = list(reader)
        sha = hashlib.sha256(raw_input.encode('utf-8')).hexdigest()[:8]
        return {
            "sender": "csv_system",
            "content": {"rows": rows},
            "source_path": f"csv/{sha}"
        }

class IngestionRegistry:
    def __init__(self):
        self._adapters: dict[str, IngestionAdapter] = {}
        
    def register(self, adapter: IngestionAdapter):
        self._adapters[adapter.source_type] = adapter
        
    def ingest(self, source_type: str, raw_input: Any) -> dict:
        adapter = self._adapters.get(source_type)
        if not adapter:
            raise UnknownSourceTypeError(f"No adapter registered for source_type: '{source_type}'")
        return adapter.parse(raw_input)

class ArtifactRegistry(IngestionRegistry):
    def __init__(self):
        super().__init__()
        self._artifacts: dict[str, Artifact] = {}
        self._checksums: set[str] = set()
        
    def register_artifact(self, artifact: Artifact) -> None:
        if artifact.checksum in self._checksums:
            raise DuplicateArtifactError(f"Artifact with checksum {artifact.checksum} already registered.")
        self._checksums.add(artifact.checksum)
        self._artifacts[artifact.artifact_id] = artifact
        
    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

def normalize_parse_result(data: dict) -> dict:
    res = {}
    for k, v in sorted(data.items()):
        if isinstance(v, str):
            res[k] = v.strip()
        else:
            res[k] = v
    return res

def validate_parse_result(data: dict) -> None:
    required = {"sender", "content", "source_path"}
    missing = required - data.keys()
    if missing:
        raise IngestionParseError(f"Parse result missing required keys: {missing}")

def extract_observation_bundle(
    artifact: Artifact,
    registry: ArtifactRegistry,
    identity_reg: Any,
    temporal_idx: Any,
    prov_graph: Any,
    ai_suggestions: list = None
) -> ObservationBundle:
    registry.register_artifact(artifact)
    parsed = registry.ingest(artifact.artifact_type, artifact.raw_payload)
    normalized = normalize_parse_result(parsed)
    validate_parse_result(normalized)
    return build_bundle(normalized, identity_reg, temporal_idx, prov_graph, ai_suggestions=ai_suggestions)

__all__ = [
    "IngestionParseError",
    "UnknownSourceTypeError",
    "DuplicateArtifactError",
    "Artifact",
    "IngestionAdapter",
    "SlackAdapter",
    "GitCommitAdapter",
    "PlaintextAdapter",
    "MarkdownAdapter",
    "PDFAdapter",
    "EmailAdapter",
    "CalendarAdapter",
    "JSONAdapter",
    "CSVAdapter",
    "IngestionRegistry",
    "ArtifactRegistry",
    "normalize_parse_result",
    "validate_parse_result",
    "extract_observation_bundle"
]
