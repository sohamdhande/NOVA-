import psutil
import os
import time
import asyncio

def get_nova_stats() -> dict:
    process = psutil.Process(os.getpid())
    return {
        "cpu_percent": process.cpu_percent(interval=None),
        "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
        "memory_percent": round(process.memory_percent(), 2),
        "threads": process.num_threads(),
        "uptime_seconds": int(time.time() - process.create_time()),
        "system_cpu": psutil.cpu_percent(interval=None),
        "system_memory_percent": psutil.virtual_memory().percent,
        "system_memory_free_gb": round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 2)
    }

def format_stats_summary(stats: dict) -> str:
    return (f"NOVA: {stats['memory_mb']}MB RAM | {stats['cpu_percent']}% CPU | "
            f"System: {stats['system_cpu']}% CPU | {stats['system_memory_free_gb']}GB free")

async def start_resource_monitor(send_to_dashboard):
    import json
    import os
    print("[NOVA] ✓ Resource monitor started")
    # Initial interval to prime cpu_percent
    psutil.cpu_percent(interval=None)
    psutil.Process(os.getpid()).cpu_percent(interval=None)
    
    while True:
        # Dynamically load interval
        interval = 300
        if os.path.exists("nova_settings.json"):
            try:
                with open("nova_settings.json") as f:
                    interval = json.load(f).get("interval_telemetry", 300)
            except Exception:
                pass
        
        await asyncio.sleep(interval)
        try:
            stats = get_nova_stats()
            
            # Warn locally if breaching thresholds
            if stats["cpu_percent"] > 40:
                print(f"[Resource Warning] NOVA CPU high: {stats['cpu_percent']}%")
            if stats["memory_mb"] > 500:
                print(f"[Resource Warning] NOVA Memory high: {stats['memory_mb']}MB")
            if stats["system_memory_free_gb"] < 1:
                print(f"[Resource Warning] System Memory low: {stats['system_memory_free_gb']}GB free")
            
            # Send to dashboard
            await send_to_dashboard("resource_stats", stats)
        except Exception as e:
            print(f"[ResourceMonitor] Error: {e}")
