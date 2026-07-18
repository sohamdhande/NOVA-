import os
import io
import time
import queue
import threading
import asyncio
import tempfile
import subprocess
import numpy as np
import sounddevice as sd
import soundfile as sf
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable

@dataclass
class VoiceConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration: float = 0.5    # seconds per chunk
    wake_word: str = "nova"
    silence_threshold: float = 0.02
    silence_duration: float = 1.5  # stop after 1.5s silence
    max_record_duration: float = 30.0
    whisper_model: str = "base"    # tiny/base/small
    tts_voice: str = "af_sky"      # Kokoro voice
    tts_speed: float = 1.0

class VoiceModule:
    """
    N.O.V.A's ears and voice.
    Always listening for wake word "Nova",
    transcribes speech, responds with Kokoro TTS.
    """
    
    def __init__(self, config: VoiceConfig = None):
        self.config = config or VoiceConfig()
        self._listening = False
        self._speaking = False
        self._wake_detected = False
        self._stt_model = None
        self._kokoro = None
        self._audio_queue = queue.Queue()
        self._on_command: Optional[Callable] = None
        self._on_wake: Optional[Callable] = None
        self._thread: Optional[threading.Thread] = None
        
    # ─────────────────────────────────────────
    # INITIALIZATION:
    
    def initialize(self):
        """Load STT and TTS models."""
        if self._stt_model is not None:
            return  # Already initialized
            
        print("[Voice] Loading STT model "
              f"({self.config.whisper_model})...")
        try:
            from faster_whisper import WhisperModel
            self._stt_model = WhisperModel(
                self.config.whisper_model,
                device="cpu",
                compute_type="int8"
            )
            print("[Voice] ✅ STT ready")
        except Exception as e:
            print(f"[Voice] ❌ STT failed: {e}")
        

    
    # ─────────────────────────────────────────
    # WAKE WORD DETECTION:
    
    def _detect_wake_word(self, 
                           audio_chunk: np.ndarray,
                           text: str) -> tuple[bool, str]:
        """
        Check if wake word is in transcribed text.
        Returns (is_wake_word, remaining_command_text)
        """
        import re
        text_lower = text.lower().strip()
        
        # Remove punctuation for matching
        clean_text = re.sub(r'[^\w\s]', '', text_lower)
        words = clean_text.split()
        
        if not words:
            return False, ""
            
        first_word = words[0]
        
        # Fuzzy matches for "Nova" mishearing, particularly at start of sentence
        variants = [
            "nova", "no", "neva", "nowa",
            "naval", "novak", "november",
            "now", "know", "noah", "over"
        ]
        
        is_wake = first_word in variants or "nova" in text_lower
        
        if is_wake:
            # Reconstruct the rest of the original text
            if first_word in variants:
                # Remove the fuzzy wake word from the start
                pattern = re.compile(r'^[^\w]*' + re.escape(first_word) + r'[^\w]*', re.IGNORECASE)
                remaining = pattern.sub('', text).strip()
            else:
                # Split at "nova" and take everything after
                parts = re.split(r'(?i)nova', text)
                remaining = parts[-1].strip() if parts else ""
                
            return True, remaining
            
        return False, ""
    
    def _is_speech(self, 
                    audio: np.ndarray) -> bool:
        """Simple VAD — check if audio has speech."""
        rms = np.sqrt(np.mean(audio ** 2))
        return rms > self.config.silence_threshold
    
    # ─────────────────────────────────────────
    # RECORDING:
    
    def record_audio(self, 
                     duration: float = None,
                     stop_on_silence: bool = True
                     ) -> Optional[np.ndarray]:
        """
        Record audio from microphone.
        Stops on silence or max duration.
        Returns numpy array of audio data.
        """
        sr = self.config.sample_rate
        max_dur = duration or \
                  self.config.max_record_duration
        chunk_size = int(
            sr * self.config.chunk_duration
        )
        
        frames = []
        silent_chunks = 0
        max_silent = int(
            self.config.silence_duration / 
            self.config.chunk_duration
        )
        
        print("[Voice] 🎤 Recording...")
        
        with sd.InputStream(
            samplerate=sr,
            channels=self.config.channels,
            dtype='float32'
        ) as stream:
            start = time.time()
            while time.time() - start < max_dur:
                audio_chunk, _ = stream.read(
                    chunk_size
                )
                frames.append(audio_chunk.copy())
                
                if stop_on_silence:
                    if self._is_speech(audio_chunk):
                        silent_chunks = 0
                    else:
                        silent_chunks += 1
                    
                    # Stop after silence
                    # (but record at least 1 second)
                    if (silent_chunks >= max_silent and 
                        len(frames) > 
                        int(1.0 / self.config.chunk_duration)):
                        break
        
        if not frames:
            return None
        
        audio = np.concatenate(frames, axis=0)
        return audio.flatten()
    
    def record_short(self, 
                     duration: float = 2.0
                     ) -> Optional[np.ndarray]:
        """Record a short fixed-duration clip."""
        return self.record_audio(
            duration=duration, 
            stop_on_silence=False
        )
    
    # ─────────────────────────────────────────
    # SPEECH TO TEXT:
    
    def transcribe(self, 
                   audio: np.ndarray) -> str:
        """
        Transcribe audio array to text
        using faster-whisper.
        """
        if self._stt_model is None:
            return ""
        
        try:
            # Save to temp wav file
            with tempfile.NamedTemporaryFile(
                suffix='.wav', delete=False
            ) as f:
                tmp_path = f.name
            
            sf.write(
                tmp_path, audio,
                self.config.sample_rate
            )
            
            # Transcribe
            segments, info = self._stt_model.transcribe(
                tmp_path,
                beam_size=5,
                language="en"
            )
            
            text = " ".join(
                seg.text for seg in segments
            ).strip()
            
            # Cleanup
            os.unlink(tmp_path)
            
            print(f"[Voice] Transcribed: '{text}'")
            return text
            
        except Exception as e:
            print(f"[Voice] Transcription failed: {e}")
            return ""
    
    def transcribe_file(self, 
                        path: str) -> str:
        """Transcribe audio file to text."""
        if self._stt_model is None:
            return ""
        try:
            segments, _ = self._stt_model.transcribe(
                path, beam_size=5, language="en"
            )
            return " ".join(
                seg.text for seg in segments
            ).strip()
        except Exception as e:
            return f"Transcription error: {e}"
    
    # ─────────────────────────────────────────
    # TEXT TO SPEECH:
    
    def speak(self, text: str, 
              blocking: bool = True):
        """
        Speak text using Kokoro TTS.
        Falls back to macOS 'say' if Kokoro unavailable.
        """
        if self._speaking:
            return
        
        self._speaking = True
        print(f"[Voice] 🔊 Speaking: {text[:60]}...")
        
        try:
            if not getattr(self, '_kokoro_failed', False):
                self._speak_kokoro(text)
            else:
                self._speak_macos(text)
        finally:
            self._speaking = False
    
    def _speak_kokoro(self, text: str):
        """Speak using Kokoro ONNX."""
        try:
            if self._kokoro is None:
                from kokoro_onnx import Kokoro
                self._kokoro = Kokoro(
                    os.path.expanduser("~/.nova/models/kokoro-v0_19.onnx"),
                    os.path.expanduser("~/.nova/models/voices.bin")
                )
                print("[Voice] ✅ TTS ready")
                
            samples, sr = self._kokoro.create(
                text,
                voice=self.config.tts_voice,
                speed=self.config.tts_speed,
                lang="en-us"
            )
            sd.play(samples, sr)
            sd.wait()
        except Exception as e:
            print(f"[Voice] Kokoro failed: {e}")
            self._kokoro_failed = True
            self._speak_macos(text)
    
    def _speak_macos(self, text: str):
        """Fallback: use macOS say command."""
        # Clean text for shell
        clean = text.replace('"', "'")
        subprocess.run(
            ['say', '-v', 'Samantha', 
             '-r', '175', clean],
            timeout=30
        )
    
    def speak_async(self, text: str):
        """Speak without blocking."""
        thread = threading.Thread(
            target=self.speak,
            args=(text,),
            daemon=True
        )
        thread.start()
    
    # ─────────────────────────────────────────
    # CONTINUOUS LISTENING LOOP:
    
    def start_listening(
            self,
            on_command: Callable[[str], None],
            on_wake: Callable = None):
        """
        Start continuous background listening.
        Calls on_command(text) when command detected
        after wake word.
        """
        self._on_command = on_command
        self._on_wake = on_wake
        self._listening = True
        
        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True
        )
        self._thread.start()
        print(f"[Voice] 👂 Listening for "
              f"'{self.config.wake_word}'...")
    
    def stop_listening(self):
        """Stop the listening loop."""
        self._listening = False
        print("[Voice] Listening stopped")
    
    def _listen_loop(self):
        """
        Main listening loop.
        Runs in background thread.
        Detects wake word then captures command.
        """
        sr = self.config.sample_rate
        chunk = int(sr * self.config.chunk_duration)
        
        while self._listening:
            try:
                # Record short chunk for wake detection
                audio = self.record_short(duration=2.0)
                if audio is None:
                    continue
                
                # Quick transcription for wake word
                if not self._is_speech(audio):
                    continue
                
                text = self.transcribe(audio)
                
                if not text:
                    continue
                
                # Check for wake word
                is_wake, remaining_text = self._detect_wake_word(audio, text)
                if is_wake:
                    print(f"[Voice] 🟢 Wake word detected!")
                    
                    # Notify wake callback
                    if self._on_wake:
                        self._on_wake()
                    
                    # If they already said the command with the wake word (inline)
                    # e.g., "Nova, what's the time" -> remaining_text = "what's the time"
                    if len(remaining_text.split()) > 1:
                        print(f"[Voice] Command inline: '{remaining_text}'")
                        if self._on_command:
                            self._on_command(remaining_text)
                        continue
                        
                    # Otherwise, ask and wait for the command
                    self.speak_async("Yes?")
                    time.sleep(0.8)
                    
                    # Record actual command
                    command_audio = self.record_audio(
                        stop_on_silence=True
                    )
                    
                    if command_audio is not None and \
                       self._is_speech(command_audio):
                        command_text = self.transcribe(
                            command_audio
                        )
                        
                        if command_text:
                            print(f"[Voice] Command: "
                                  f"'{command_text}'")
                            
                            if self._on_command:
                                self._on_command(
                                    command_text
                                )
                    else:
                        self.speak_async(
                            "I didn't catch that. "
                            "Please try again."
                        )
                        
            except Exception as e:
                print(f"[Voice] Listen error: {e}")
                time.sleep(1)
    
    # ─────────────────────────────────────────
    # NOVA VOICE INTEGRATION:
    
    async def process_voice_command(
            self, command: str) -> str:
        """
        Process a voice command through N.O.V.A's
        intent parser and tool router.
        Returns text response to speak.
        """
        try:
            from core.intent_parser import intent_parser
            from core.tool_router import tool_router
            
            intent = await intent_parser.parse(command)
            result = await tool_router.route(intent)
            
            # Shorten response for speaking
            response = result.output
            if len(response) > 200:
                response = response[:197] + "..."
            
            return response
            
        except Exception as e:
            return f"Processing error: {str(e)}"
    
    def handle_voice_command(self, command: str):
        """
        Synchronous wrapper for voice command.
        Runs async processing in new event loop.
        """
        try:
            from core.api_server import main_loop
            import concurrent.futures
            
            if main_loop and main_loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.process_voice_command(command),
                    main_loop
                )
                response = future.result()
            else:
                loop = asyncio.new_event_loop()
                response = loop.run_until_complete(
                    self.process_voice_command(command)
                )
                loop.close()
            
            # Speak the response
            self.speak(response)
            
        except Exception as e:
            self.speak(f"Error: {str(e)[:50]}")

# Singleton
voice_config = VoiceConfig(
    wake_word="nova",
    whisper_model="base",
    tts_voice="af_sky",
    silence_threshold=0.02,
    silence_duration=1.5
)
voice = VoiceModule(voice_config)
