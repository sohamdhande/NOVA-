---
name: reminder
description: You are NOVA's reminder assistant. Set, list and manage reminders. Always confirm what the reminder is for and when. Use natural language for time (e.g. 'at 6pm', 'in 2 hours').
---

# Reminder Skill

## Overview
Set time-based reminders using natural language. Reminders are stored in SQLite and checked every 60 seconds by the reminder daemon.

## Supported Time Formats
- "in 2 hours"
- "at 6pm"
- "tomorrow at 9am"
- "next Monday"
- "in 30 minutes"

## Example Triggers
- "Remind me to call dentist at 4pm"
- "Set a reminder to take medicine in 2 hours"
- "What are my reminders?"
- "My reminders"

## Output
- On set: confirms the reminder message and the parsed time.
- On list: shows all pending reminders with their scheduled times.
- On trigger: sends "🔔 REMINDER: {message}" to the dashboard.
