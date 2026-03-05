import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class NovaEvent:
    """Represents a discrete event within the N.O.V.A system."""
    source: str
    type: str
    payload: dict
    priority: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __lt__(self, other):
        """
        Sort events so higher priority comes first.
        If priority is equal, older events (smaller timestamp) come first.
        """
        if not isinstance(other, NovaEvent):
            return NotImplemented
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority > other.priority


class EventBus:
    """Async Pub/Sub Event Bus for routing system events."""

    def __init__(self):
        """Initialize the internal priority queue and subscribers dictionary."""
        self._queue = asyncio.PriorityQueue()
        self._subscribers = {}
        self._running = False
        self._task = None

    def subscribe(self, event_type: str, callback):
        """
        Subscribe an async callback coroutine to a specific event type.
        Use '*' to subscribe to ALL events.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    async def publish(self, event: NovaEvent):
        """Publish an event to the queue for processing."""
        logger.info(f"[EVENT BUS] {event.timestamp} | {event.source} → {event.type} | priority={event.priority}")
        await self._queue.put(event)

    async def start(self):
        """Start the continuous async loop to pull and dispatch events."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_events())

    async def stop(self):
        """Stop the event bus cleanly."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_events(self):
        """Continuously pull events from the queue and dispatch to matching subscribers."""
        while self._running:
            try:
                event = await self._queue.get()
            except asyncio.CancelledError:
                break

            # Collect all distinct callbacks for this event
            callbacks = []
            
            # Specific type subscribers
            if event.type in self._subscribers:
                callbacks.extend(self._subscribers[event.type])
                
            # Wildcard subscribers
            if "*" in self._subscribers:
                for cb in self._subscribers["*"]:
                    if cb not in callbacks:
                        callbacks.append(cb)

            # Dispatch
            for callback in callbacks:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Error in subscriber callback for event '{event.type}': {e}", exc_info=True)

            self._queue.task_done()


# Export a single module-level instance
event_bus = EventBus()
