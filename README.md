# NOVA - Autonomous Productivity Operator

**Version:** 2.0  
**Status:** ✅ Production Ready  
**Python:** 3.14+

## Overview

NOVA is a production-grade AI assistant with contract-hardened architecture, multi-step execution, and intelligent command processing. Built for reliability, safety, and seamless user experience.

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/sohamdhande/NOVA-.git
cd NOVA

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Google Calendar & Notion** (Optional)
   - Add `credentials.json` for Google Calendar
   - Set `NOTION_TOKEN` in `.env` for Notion integration

2. **LLM Server**
   ```bash
   # Start Ollama
   ollama serve
   
   # Pull the model (first time only)
   ollama pull mistral:7b-instruct
   ```

### Run NOVA

```bash
python3 nova.py
```

## Features

### ✅ Contract-Hardened Architecture
- **Gibberish filtering** - Rejects invalid input before LLM
- **Domain whitelisting** - Only approved domains execute
- **Action contracts** - Enforced allowed actions per domain
- **Method verification** - Prevents AttributeError crashes
- **Zero hallucinations** - No unsafe execution paths

### ✅ Intelligent Command Processing
- **Vague command handling** - "schedule something sometime" → tomorrow at 2pm
- **Context-aware parsing** - "tomorrow morning" → 9am, "afternoon" → 2pm
- **Multi-step execution** - Read tasks → Schedule review (seamless)
- **Parameter interpolation** - Data flows between steps automatically

### ✅ Memory System
- **Vector search** - Semantic memory with embeddings
- **Keyword fallback** - Always finds relevant memories
- **Duplicate detection** - No redundant storage
- **Natural queries** - "What do I remember about X?"

### ✅ Tool Integration
- **Google Calendar** - Create events, read schedule
- **Notion** - Manage tasks, track progress
- **PDF** - Extract text, summarize documents
- **System** - Morning briefings, telemetry

### ✅ Safety & Observability
- **Guardrails** - Daily mutation limits (3 creates, 5 updates)
- **Telemetry** - Track usage, mutations, failures
- **Logging** - All commands logged to SQLite
- **Error handling** - Graceful degradation

## Usage Examples

### Memory
```
NOVA > Remember that I deployed NOVA v2 successfully
Memory stored: 'that I deployed NOVA v2 successfully'

NOVA > What do I remember about deployment?
Knowledge on 'deployment':
- that I deployed NOVA v2 successfully
- that I deployed the stabilization refactor successfully
```

### Scheduling (Specific)
```
NOVA > schedule review meeting tomorrow at 3pm
✓ Event 'Review meeting' created successfully.

NOVA > create event next Monday at 10am
✓ Event created successfully.
```

### Scheduling (Vague)
```
NOVA > schedule something sometime
✓ Event 'Scheduled task' created for tomorrow at 2pm

NOVA > schedule unfinished tasks later
✓ Event 'Review 2 unfinished tasks' created for tomorrow at 2pm
```

### Tasks
```
NOVA > Show me open tasks
Found 2 task(s).

NOVA > What tasks do I have?
Found 2 task(s).
```

### Calendar
```
NOVA > What's on my calendar today?
Found 3 event(s) for today.
```

## Architecture

### Core Components

```
nova.py              # Application container & lifecycle
controller.py        # Command routing & execution
llm.py              # LLM planner integration
schema.py           # Plan validation
validator.py        # Input validation
config.py           # Configuration
```

### Tools
```
tools/
  calendar_tool.py  # Google Calendar integration
  notion_tool.py    # Notion task management
  memory_tool.py    # Memory operations
  pdf_tool.py       # PDF processing
```

### Core Services
```
core/
  system_tool.py    # System commands
  guardrail.py      # Safety limits
  telemetry.py      # Usage tracking
```

### Storage
```
storage/
  memory_store.py   # Memory management
  vector_store.py   # Semantic search
  logger.py         # Execution logging
```

### Utilities
```
utils/
  date_parser.py    # Natural language datetime parsing
```

## Command Routing

```
1. Trim & Empty Check
2. System Commands (exit, quit)
3. Explicit Memory Patterns (hard-coded)
4. Gibberish Detection (pre-filter)
5. LLM Planner Invocation
6. Plan Validation & Correction
7. Contract Verification
8. Execution (single-step or multi-step)
```

## Configuration

### Environment Variables (.env)
```bash
NOTION_TOKEN=your_notion_token_here
HF_TOKEN=your_huggingface_token_here  # Optional
```

### Config (config.py)
```python
DEBUG = False                    # Enable debug logging
MAX_CORRECTION_ATTEMPTS = 2     # Plan correction retries
DAILY_CREATE_LIMIT = 3          # Max creates per day
DAILY_UPDATE_LIMIT = 5          # Max updates per day
```

## Allowed Domains & Actions

### Calendar
- `create_event` - Create calendar event
- `read_today` - Read today's schedule

### Notion/Tasks
- `create_task` - Create new task
- `read_open` - Read open tasks
- `update_task` - Update task status

### Memory
- `store_entry` - Store memory
- `recall_topic` - Recall by topic
- `search_entries` - Search memories

### System
- `morning_briefing` - Daily summary

### PDF
- `summarize` - Summarize PDF
- `extract` - Extract text

## Performance

- **Average command:** 5.4s
- **Gibberish rejection:** <0.001s
- **Memory operations:** <0.1s
- **Multi-step scheduling:** 10-13s (LLM-dependent)
- **No memory leaks:** Vector store loaded once
- **No degradation:** Consistent performance over time

## Testing

### Stress Test Results
✅ **20 mixed commands executed**
- 17 passed
- 3 correctly rejected (gibberish)
- 0 failed
- 100% success rate

### Test Coverage
- Memory operations ✅
- Specific scheduling ✅
- Vague scheduling ✅
- Gibberish detection ✅
- System queries ✅
- Edge cases ✅

## Documentation

- **CONTRACT_HARDENING_SUMMARY.md** - Architecture & security
- **MULTI_STEP_INTERPOLATION_FIX.md** - Parameter injection logic
- **VAGUE_COMMAND_SOLUTION.md** - Intelligent default handling
- **SOLUTION_SUMMARY.md** - Comprehensive feature guide
- **STRESS_TEST_REPORT.md** - Performance validation
- **QUICK_START.md** - Setup guide

## Troubleshooting

### "Command not recognized"
- Check if command has recognized verb (schedule, create, show, etc.)
- Avoid pure gibberish
- Use natural language: "schedule meeting" not "asdfkjh"

### LLM Connection Error
- Ensure Ollama is running: `ollama serve`
- Check model is pulled: `ollama pull mistral:7b-instruct`
- Verify port 11434 is accessible

### Calendar/Notion Errors
- Check `credentials.json` exists and is valid
- Verify `NOTION_TOKEN` in `.env`
- Ensure APIs are enabled in Google Cloud Console

### Memory Not Working
- Vector store loads on first run (may take 10-15s)
- Check sufficient disk space for embeddings
- Verify write permissions in `data/` directory

## Development

### Adding New Tools
1. Create tool in `tools/`
2. Implement `execute(action, parameters)` method
3. Register in `controller.py::__init__()`
4. Add domain/actions to `ALLOWED_DOMAINS` and `ALLOWED_ACTIONS`

### Adding New Actions
1. Add action to `ALLOWED_ACTIONS` in `controller.py`
2. Implement in respective tool's `execute()` method
3. Update LLM system prompt in `llm.py`

## Security

- ✅ Input sanitization (gibberish detection)
- ✅ Domain whitelisting (only 6 approved domains)
- ✅ Action contracts (no hallucinated actions)
- ✅ Guardrails (daily mutation limits)
- ✅ Telemetry (audit trail for all mutations)
- ✅ No arbitrary code execution
- ✅ No SQL injection (parameterized queries)

## License

MIT License - See LICENSE file

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/sohamdhande/NOVA-/issues
- Email: sohamdhande@example.com

## Credits

**Author:** Soham Dhande  
**Version:** 2.0  
**Release Date:** February 14, 2026  
**Status:** Production Ready

---

**Built with:** Python, Ollama, Sentence Transformers, ChromaDB, Google APIs, Notion API
