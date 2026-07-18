# NOVA Knowledge Compiler

NOVA is a deterministic knowledge compiler framework that ingests diverse sources (Slack, Git, plaintext), lowers them to dialect-specific Intermediate Representations (KIR), runs deterministic topological passes, and compiles them into an immutable chronological commit hash chain. 

## Command Line Interface (CLI)

The NOVA CLI allows you to directly interact with the persistent SQLite backend storing compiled `KnowledgeCommit` data. 

*Note: Since NOVA is deterministic, it persists execution logs (commits). Systems like `IdentityRegistry`, `TemporalIndex`, `ProvenanceGraph`, and `DependencyGraph` exist ephemerally per-session right now and will be expanded in the future.*

### CLI Commands

- `nova ingest <source_type> <file_or_text>`: Parse raw input (types: `slack`, `git`, `plaintext`) and compile it into a KnowledgeCommit on disk.
- `nova log`: Print the full chain of commits.
- `nova show <commit_hash_prefix>`: Show the full KIR structural detail for a specific hash.
- `nova ask <intent>`: Execute the Reasoning Compiler against the persistent timeline to answer queries based on accumulated knowledge.
- `nova explain <fact_id>`: Query the provenance engine (currently informs you it is not persisted).
- `nova reset`: Deletes the SQLite database with an interactive confirmation prompt.

---

### End-to-End Tutorial (5 minutes)

#### 1. Ingest Knowledge
Provide plaintext inputs to compile into knowledge.
```bash
$ python3 nova/packages/cli/main.py ingest plaintext "Soham and Alice decided to build a deterministic compiler."
Successfully committed: 5ea751d9e2a8...

$ python3 nova/packages/cli/main.py ingest plaintext "The compiler must be query-driven, not stage-driven."
Successfully committed: b258ff093b12...
```

#### 2. View the Log
Query the timeline to ensure both facts chained correctly.
```bash
$ python3 nova/packages/cli/main.py log
commit 5ea751d9 - 2026-06-26 12:00:00 - GENERIC:OBSERVE 'Soham and Alice decided to build a de...'
commit b258ff09 - 2026-06-26 12:00:15 - GENERIC:OBSERVE 'The compiler must be query-driven, no...'
```

#### 3. Ask NOVA a Question
Use the `ask` feature to engage the Reasoning Compiler on top of the persisted dataset.
```bash
$ python3 nova/packages/cli/main.py ask "What was decided about the compiler?"
NOTE: IdentityRegistry, TemporalIndex, and DependencyGraph are currently session-only.
      This reasoning pass evaluates directly off raw SQLite commits.

Compiled Context:
- Fact obs_123 [ARTIFACT]: ... "Soham and Alice decided to build a deterministic compiler."
- Fact obs_456 [ARTIFACT]: ... "The compiler must be query-driven, not stage-driven."
```

#### 4. Show Commit Details
Inspect the exact deterministic KIR output generated for the specific commit.
```bash
$ python3 nova/packages/cli/main.py show 5ea751d9
Commit: 5ea751d9e2a8...
Parent: None
Date:   2026-06-26 12:00:00+00:00
----------------------------------------
KIRNode (GENERIC - OBSERVE)
  ID: out_123
  Inputs: []
  Metadata: {
    "content": "Soham and Alice decided to build a deterministic compiler."
  }
```

#### 5. Reset the Chain
If you want to clear your timeline, reset the database.
```bash
$ python3 nova/packages/cli/main.py reset
Are you sure you want to delete /Users/name/.nova/knowledge.db? (y/N): y
Database deleted.
```
