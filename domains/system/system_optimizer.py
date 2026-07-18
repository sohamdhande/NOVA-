import os
import shutil
import psutil
import pathlib
import logging
import asyncio
import time
from core.event_bus import event_bus, NovaEvent

logger = logging.getLogger(__name__)

class SystemOptimizer:
    """macOS system optimization engine for N.O.V.A."""
    
    def __init__(self):
        self._running = False

    async def poll(self):
        """Monitor system metrics and publish events."""
        # psutil.cpu_percent blocks for 'interval', doing this async blockingly inside an async def is
        # okay if interval=1, though it pauses the event loop for 1s.
        # Alternatively, we can use interval=None but it requires two calls. We'll follow the exact requirements.
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        battery_info = psutil.sensors_battery()
        battery_percent = battery_info.percent if battery_info else 100
        disk = psutil.disk_usage('/').percent
        
        # Publish metrics
        await event_bus.publish(NovaEvent(
            source="system_optimizer",
            type="system_metrics",
            payload={"cpu": cpu, "memory": mem, "battery": battery_percent, "disk": disk},
            priority=2
        ))
        
        battery_low = False
        
        # Alert thresholds
        if cpu > 85:
            await event_bus.publish(NovaEvent(
                source="system_optimizer",
                type="cpu_spike",
                payload={"cpu": cpu},
                priority=7
            ))
            
        if mem > 85:
            await event_bus.publish(NovaEvent(
                source="system_optimizer",
                type="memory_pressure",
                payload={"memory": mem},
                priority=7
            ))
            
        if battery_percent < 15:
            battery_low = True
            await event_bus.publish(NovaEvent(
                source="system_optimizer",
                type="battery_low",
                payload={"battery": battery_percent},
                priority=9
            ))
            
        if disk > 90:
            await event_bus.publish(NovaEvent(
                source="system_optimizer",
                type="disk_critical",
                payload={"disk": disk},
                priority=8
            ))
            
        return battery_low

    async def run_cleanup(self):
        """Perform low-risk filesystem cleanup."""
        files_removed = 0
        space_freed_bytes = 0
        now = time.time()
        
        # Clear ~/Library/Caches (files older than 24 hours)
        cache_dir = pathlib.Path.home() / "Library" / "Caches"
        if cache_dir.exists() and cache_dir.is_dir():
            for item in cache_dir.iterdir():
                try:
                    stat = item.stat(follow_symlinks=False)
                    # Skip if modified in last 24hrs (86400s)
                    if now - stat.st_mtime > 86400:
                        size = 0
                        if item.is_file() or item.is_symlink():
                            size = stat.st_size
                            item.unlink()
                        elif item.is_dir():
                            # Sum sizes of files in directory tree before removal
                            size = sum(f.stat(follow_symlinks=False).st_size for f in item.rglob('*') if f.is_file() or f.is_symlink())
                            shutil.rmtree(item, ignore_errors=True)
                        files_removed += 1
                        space_freed_bytes += size
                        logger.info(f"Deleted cache item: {item}")
                except Exception as e:
                    logger.debug(f"Skipping {item} during cache cleanup: {e}")
                    
        # Clear ~/.Trash contents older than 7 days
        trash_dir = pathlib.Path.home() / ".Trash"
        if trash_dir.exists() and trash_dir.is_dir():
            try:
                for item in trash_dir.iterdir():
                    try:
                        stat = item.stat(follow_symlinks=False)
                        # Skip if modified in last 7 days (604800s)
                        if now - stat.st_mtime > 604800:
                            size = 0
                            if item.is_file() or item.is_symlink():
                                size = stat.st_size
                                item.unlink()
                            elif item.is_dir():
                                size = sum(f.stat(follow_symlinks=False).st_size for f in item.rglob('*') if f.is_file() or f.is_symlink())
                                shutil.rmtree(item, ignore_errors=True)
                            files_removed += 1
                            space_freed_bytes += size
                            logger.info(f"Deleted trash item: {item}")
                    except Exception as e:
                        logger.debug(f"Skipping {item} during trash cleanup: {e}")
            except PermissionError:
                logger.debug("Permission denied accessing ~/.Trash")

        mb_freed = round(space_freed_bytes / (1024 * 1024), 2)
        
        await event_bus.publish(NovaEvent(
            source="system_optimizer",
            type="cleanup_completed",
            payload={"files_removed": files_removed, "space_freed_mb": mb_freed},
            priority=2
        ))

    async def start(self, interval_seconds=3600):
        """Run the optimization loop periodically."""
        self._running = True
        while self._running:
            try:
                battery_low = await self.poll()
                # Skip cleanup if battery is low to avoid disk I/O cost while draining
                if not battery_low:
                    await self.run_cleanup()
            except Exception as e:
                logger.error(f"Error in SystemOptimizer loop: {e}", exc_info=True)
                
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                self._running = False
                break

system_optimizer = SystemOptimizer()
