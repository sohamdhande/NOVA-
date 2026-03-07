# Quick test to verify vision + control work:

import asyncio
import sys
sys.path.insert(0, '/Users/sohamdhande/Docs_Local/NOVA')

from core.vision import vision
from core.computer_control import computer

def test_vision():
    print("\n=== N.O.V.A Vision Test ===\n")
    
    # Test 1: Screenshot
    print("Test 1: Capturing screenshot...")
    img = vision.capture()
    print(f"  ✅ Screenshot: {img.size[0]}x{img.size[1]}")
    
    # Test 2: Active app
    print("Test 2: Getting active app...")
    app = vision.get_active_app()
    print(f"  ✅ Active app: {app}")
    
    # Test 3: Screen state
    print("Test 3: Full screen state...")
    state = vision.get_screen_state(save=True)
    print(f"  ✅ App: {state.active_app}")
    print(f"  ✅ Window: {state.active_window}")
    print(f"  ✅ Mouse: {state.mouse_position}")
    print(f"  ✅ Screenshot saved: {state.screenshot_path}")
    print(f"  ✅ Text preview: "
          f"{state.screen_text[:100]}...")
    
    # Test 4: Screen description
    print("Test 4: Screen description...")
    desc = vision.describe_screen()
    print(f"  ✅ Description generated")
    print(f"  {desc[:200]}")
    
    # Test 5: Clipboard
    print("Test 5: Clipboard...")
    computer.set_clipboard("N.O.V.A test")
    content = computer.get_clipboard()
    if "N.O.V.A test" in content:
        print(f"  ✅ Clipboard: read/write working")
    else:
        print(f"  ❌ Clipboard: failed")
    
    print("\n=== Vision Test Complete ===\n")

if __name__ == "__main__":
    test_vision()
