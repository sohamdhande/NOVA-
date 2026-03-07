import sys
sys.path.insert(
    0, '/Users/sohamdhande/Docs_Local/NOVA'
)

def test_voice():
    print("\n=== N.O.V.A Voice Test ===\n")
    
    from core.voice import voice
    
    # Test 1: Initialize
    print("Test 1: Initializing voice...")
    voice.initialize()
    print("  ✅ Voice initialized")
    
    # Test 2: TTS
    print("\nTest 2: Testing TTS...")
    print("  Speaking test message...")
    voice.speak(
        "N.O.V.A voice system online. "
        "All systems nominal."
    )
    print("  ✅ TTS working")
    
    # Test 3: Short recording + STT
    print("\nTest 3: Recording 3 seconds of audio...")
    print("  Please say something...")
    audio = voice.record_short(duration=3.0)
    if audio is not None:
        print(f"  ✅ Recorded {len(audio)} samples")
        text = voice.transcribe(audio)
        print(f"  ✅ Transcribed: '{text}'")
    else:
        print("  ❌ Recording failed")
    
    # Test 4: Wake word detection
    print("\nTest 4: Wake word check...")
    import numpy as np
    dummy_audio = np.zeros(16000)
    result = voice._detect_wake_word(
        dummy_audio, "hey nova what time is it"
    )
    print(f"  ✅ Wake word detected: {result}")
    
    print("\n=== Voice Test Complete ===\n")
    print("To test full voice loop:")
    print("  voice.start_listening(")
    print("    on_command=lambda t: print(t)")
    print("  )")

if __name__ == "__main__":
    test_voice()
