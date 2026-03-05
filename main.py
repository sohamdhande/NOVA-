import asyncio
import threading
import logging
import uvicorn
import os
import sys

# Suppress Uvicorn's verbose startup logs to keep our summary clean
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

async def start_system():
    print("\n" + "="*50)
    print("  N.O.V.A System Boot Sequence")
    print("="*50)

    # 1. Encryption
    try:
        from core.encryption import encryption
        _ = encryption.get_or_create_key()
        print("[NOVA] ✓ Encryption ready")
    except Exception as e:
        print(f"[NOVA] ✗ Encryption failed: {e}")

    # 2. Event Bus
    try:
        from core.event_bus import event_bus
        await event_bus.start()
        print("[NOVA] ✓ Event Bus running")
    except Exception as e:
        print(f"[NOVA] ✗ Event Bus failed: {e}")

    # 3. System Optimizer
    try:
        from core.system_optimizer import system_optimizer
        asyncio.create_task(system_optimizer.start())
        print("[NOVA] ✓ System Optimizer running")
    except Exception as e:
        print(f"[NOVA] ✗ System Optimizer failed: {e}")

    # 4. Biometric Auth
    try:
        from core.biometric import biometric_auth
        print("[NOVA] ✓ Biometric Auth ready")
    except Exception as e:
        print(f"[NOVA] ✗ Biometric Auth failed: {e}")

    # 5. Browser
    try:
        from integrations.browser import browser
        print("[NOVA] ✓ Browser ready (lazy launch)")
    except Exception as e:
        print(f"[NOVA] ✗ Browser failed: {e}")

    # 6. Controller (Part of NovaApp)
    try:
        from nova import NovaApp
        import builtins
        
        # Suppress NovaApp's verbose stdout to keep the startup UI clean requested by user,
        # but do not silence actual exceptions.
        class DummyStream:
            def write(self, *args): pass
            def flush(self, *args): pass
            def isatty(self): return False
            
        old_stdout = sys.stdout
        sys.stdout = DummyStream()
        try:
            app_container = NovaApp()
        finally:
            sys.stdout = old_stdout
            
        print("[NOVA] ✓ Controller subscribed")
    except Exception as e:
        print(f"[NOVA] ✗ Controller failed: {e}")
        app_container = None

    # Inject initialized global instances into the API server so it doesn't try to recompute them 
    try:
        from core import api_server
        from core.auth import AuthManager
        from core.health import HealthEngine
        from core.context_engine import ContextEngine
        from core.chat_engine import ChatEngine
        
        api_server.nova_app = app_container
        api_server.auth_manager = AuthManager()
        api_server.health_engine = HealthEngine()
        
        if app_container:
            api_server.context_engine = ContextEngine(
                notion_tool=app_container.notion_tool,
                expense_manager=app_container.expense_manager,
                daemon=None,
                health_engine=api_server.health_engine
            )
            api_server.chat_engine = ChatEngine(
                controller=app_container.controller,
                health_engine=api_server.health_engine,
                context_engine=api_server.context_engine
            )
    except Exception as e:
        pass

    # 7. Daemon
    try:
        if app_container:
            from core.daemon import NovaDaemon
            daemon = NovaDaemon(
                memory_tool=app_container.memory_tool,
                notion_tool=app_container.notion_tool,
                pdf_tool=app_container.pdf_tool
            )
            api_server.daemon = daemon
            api_server.context_engine.daemon = daemon
            
            daemon_thread = threading.Thread(target=daemon.run, args=(False,), daemon=True)
            daemon_thread.start()
            api_server.daemon_thread = daemon_thread
            print("[NOVA] ✓ Daemon running")
    except Exception as e:
        print(f"[NOVA] ✗ Daemon failed: {e}")

    # 8. API Server
    print("[NOVA] ✓ API Server live on localhost:8000")
    print("="*50 + "\n")


from contextlib import asynccontextmanager

@asynccontextmanager
async def _dummy_lifespan(app):
    yield

async def main():
    await start_system()
    
    from core.api_server import app
    # Override the default heavy lifespan with a dummy to prevent double startup
    app.router.lifespan_context = _dummy_lifespan
    
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[NOVA] Shutdown requested. Goodbye.")
