"""
NOVA Reminder Daemon — Phase B
Background async loop that checks for due reminders every 60 seconds
and broadcasts them to the dashboard via the event bus.
"""

import asyncio
from datetime import datetime
from core.event_bus import event_bus, NovaEvent


async def reminder_loop():
    """
    Every 60 seconds, check for pending reminders that are due.
    For each due reminder, publish an event to the event bus and mark it done.
    """
    # Lazy import to avoid circular dependency at module level
    from tools.reminder_tool import get_pending_reminders, mark_done

    print("[NOVA] ✓ Reminder daemon started (300s poll)")

    while True:
        try:
            due = get_pending_reminders()
            for r in due:
                msg = f"🔔 REMINDER: {r['message']}"
                print(f"[Reminder] Firing: {msg}")

                # Publish to event bus so listeners (dashboard WS, etc.) can pick it up
                await event_bus.publish(NovaEvent(
                    source="reminder_daemon",
                    type="reminder_fired",
                    payload={
                        "id": r["id"],
                        "message": msg,
                        "scheduled_at": r["remind_at"],
                        "fired_at": datetime.utcnow().isoformat() + "Z",
                    },
                    priority=7,
                ))

                mark_done(r["id"])

        except Exception as e:
            print(f"[Reminder] Error in daemon loop: {e}")

        await asyncio.sleep(300)
