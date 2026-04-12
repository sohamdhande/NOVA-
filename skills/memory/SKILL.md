---
name: memory
description: Use this skill to store, recall, and search the user's long-term memory. Extract the topic clearly before recalling.
license: Proprietary. LICENSE.txt has complete terms
---

# Memory Assistant Guide

## Overview

This guide covers how to use the memory assistant to store, recall, and search the user's long-term memory. The memory assistant helps NOVA remember important information about the user, their preferences, projects, and other details that should be retained across conversations.

## Quick Start

```python
# Store a memory
memory.store(topic="work", content="My manager's name is John Doe and he prefers weekly status reports.")

# Recall a memory
memory.recall(topic="work")

# Search memories
memory.search(query="manager")
```

## Memory Operations

### Store Memory

Use `memory.store()` to save information for future recall. The `topic` parameter helps organize memories, and `content` holds the details.

```python
# Store personal information
memory.store(topic="personal", content="My birthday is on October 26th and I prefer tea over coffee.")

# Store project details
memory.store(topic="project_alpha", content="The project deadline is December 15th and the key stakeholders are Sarah and Mike.")

# Store preferences
memory.store(topic="preferences", content="I like dark mode and prefer concise responses.")
```

### Recall Memory

Use `memory.recall()` to retrieve stored information. Always extract the topic clearly before recalling.

```python
# Recall specific topic
memory.recall(topic="work")

# Recall multiple topics
memory.recall(topics=["work", "personal"])

# Recall all memories
memory.recall()
```

### Search Memory

Use `memory.search()` to find relevant memories based on a query.

```python
# Search for specific keywords
memory.search(query="manager")

# Search with multiple keywords
memory.search(query="project deadline")

# Search with topic filter
memory.search(query="deadline", topic="project_alpha")
```

## Memory Management

### List Topics

```python
# List all topics
memory.list_topics()
```

### Delete Memory

```python
# Delete specific memory
memory.delete(topic="project_alpha")

# Delete multiple memories
memory.delete(topics=["work", "personal"])

# Delete all memories
memory.delete_all()
```

## Best Practices

### 1. Extract Topic Clearly

Before recalling or searching, always determine the specific topic to ensure accurate results:

```python
# Good: Clear topic specified
memory.recall(topic="work")

# Bad: Vague query
memory.recall("my manager")  # Should be topic="work"
```

### 2. Use Specific Topics

Use descriptive topics to organize information effectively:

```python
# Good: Specific topics
topic="project_alpha"
topic="personal_preferences"
topic="work_contacts"

# Bad: Generic topics
topic="info"
topic="data"
topic="stuff"
```

### 3. Combine Search with Recall

For complex queries, use search first to find relevant memories, then recall the specific details:

```python
# Find memories about projects
results = memory.search(query="project")

# Recall specific project details
if results:
    memory.recall(topic=results[0].topic)
```

## Example Workflows

### Workflow 1: Daily Standup Preparation

```python
# 1. Recall project status
project_status = memory.recall(topic="project_alpha")

# 2. Check recent updates
updates = memory.search(query="recent updates")

# 3. Prepare for standup
print(f"Project Alpha Status: {project_status}")
print(f"Recent Updates: {updates}")
```

### Workflow 2: Meeting Preparation

```python
# 1. Recall stakeholder information
stakeholder_info = memory.recall(topic="stakeholders")

# 2. Search for recent communications
communications = memory.search(query="communications")

# 3. Prepare for meeting
print(f"Stakeholder Info: {stakeholder_info}")
print(f"Recent Communications: {communications}")
```

### Workflow 3: Personal Information Management

```python
# 1. Store new personal information
memory.store(topic="personal", content="My favorite color is blue and I enjoy hiking on weekends.")

# 2. Recall personal preferences
preferences = memory.recall(topic="personal")

# 3. Use preferences in conversation
print(f"User preferences: {preferences}")
```

## Error Handling

### Topic Not Found

```python
# Topic doesn't exist
result = memory.recall(topic="non_existent_topic")

# Handle gracefully
if result is None:
    print("No memory found for this topic.")
```

### Search Returns No Results

```python
# Search with no matches
results = memory.search(query="xyz123")

# Handle gracefully
if not results:
    print("No memories found matching your query.")
```

## Advanced Usage

### Memory Organization

Use nested topics for better organization:

```python
# Nested topics
memory.store(topic="work/project_alpha/status", content="Status: In progress")
memory.store(topic="work/project_alpha/tasks", content="Tasks: Task 1, Task 2")

# Recall specific nested topic
memory.recall(topic="work/project_alpha/status")
```

### Memory Updates

To update existing memory, simply store with the same topic:

```python
# Update existing memory
memory.store(topic="work", content="New update: Project deadline moved to January 15th.")
```

### Memory Search Filters

Use filters to narrow down search results:

```python
# Filter by date (if supported)
memory.search(query="update", date_range="last_week")

# Filter by relevance
memory.search(query="important", min_relevance=0.8)
```

## Security Considerations

- Be mindful of storing sensitive personal information
- Use clear topic names to avoid accidental exposure
- Implement proper access controls for memory operations

## Troubleshooting

### Memory not being stored

```python
# Check if topic already exists
if memory.recall(topic="test"):
    print("Topic already exists")

# Try with different topic name
memory.store(topic="test_new", content="Test content")
```

### Recall returning incomplete information

```python
# Check if there are multiple memories with same topic
all_memories = memory.list_topics()

# Recall all memories for that topic
memories = memory.recall(topic="work", all=True)
```

## License

This skill is proprietary and subject to the terms in LICENSE.txt.
