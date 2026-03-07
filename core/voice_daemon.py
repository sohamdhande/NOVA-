import threading
import asyncio
from datetime import datetime

class VoiceDaemon:
    """
    Manages the voice interface lifecycle.
    Starts/stops with the main N.O.V.A daemon.
    """
    
    def __init__(self):
        self._active = False
        self._thread = None
        self._command_log = []
    
    def start(self):
        """Initialize and start voice listening."""
        from core.voice import voice
        
        print("[VoiceDaemon] Initializing...")
        voice.initialize()
        
        # Start listening
        voice.start_listening(
            on_command=self._on_command_received,
            on_wake=self._on_wake_detected
        )
        
        self._active = True
        print("[VoiceDaemon] ✅ Voice active. "
              "Say 'Nova' to activate.")
    
    def stop(self):
        """Stop voice listening."""
        from core.voice import voice
        voice.stop_listening()
        self._active = False
        print("[VoiceDaemon] Stopped")
    
    def _on_wake_detected(self):
        """Called when wake word heard."""
        print("[VoiceDaemon] Wake word detected")
        
        # Log wake event
        self._command_log.append({
            "time": datetime.now().isoformat(),
            "type": "wake",
            "text": "Wake word detected"
        })
        
        # Publish to event bus
        try:
            from core.event_bus import (
                event_bus, NovaEvent
            )
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                event_bus.publish(NovaEvent(
                    source="voice",
                    type="wake_word_detected",
                    payload={"timestamp": 
                             datetime.now().isoformat()},
                    priority=5
                ))
            )
            loop.close()
        except:
            pass
    
    def _on_command_received(self, command: str):
        """Called when voice command transcribed."""
        print(f"[VoiceDaemon] Command: '{command}'")
        
        # Log command
        self._command_log.append({
            "time": datetime.now().isoformat(),
            "type": "command",
            "text": command
        })
        
        # Process through voice module
        from core.voice import voice
        voice.handle_voice_command(command)
    
    def get_command_log(self) -> list:
        return self._command_log[-50:]
    
    @property
    def is_active(self) -> bool:
        return self._active

voice_daemon = VoiceDaemon()
