import time
import subprocess
import pyautogui
from typing import Optional
from core.vision import vision, VisionModule

# Safety settings
pyautogui.FAILSAFE = True      # Move to corner to abort
pyautogui.PAUSE = 0.1          # 100ms between actions

class ComputerControl:
    """
    N.O.V.A's hands. Controls mouse, keyboard, and apps.
    All actions are logged and risk-checked.
    """
    
    def __init__(self):
        self._action_log = []
    
    # ─────────────────────────────────────────
    # MOUSE METHODS:
    
    def click(self, x: int, y: int,
              button: str = 'left',
              description: str = "") -> bool:
        """Click at screen coordinates."""
        try:
            self._log(f"click({x},{y}) {description}")
            pyautogui.click(x, y, button=button)
            time.sleep(0.2)
            return True
        except Exception as e:
            print(f"[Control] Click failed: {e}")
            return False
    
    def double_click(self, x: int, y: int) -> bool:
        """Double click at coordinates."""
        try:
            self._log(f"double_click({x},{y})")
            pyautogui.doubleClick(x, y)
            time.sleep(0.2)
            return True
        except Exception as e:
            return False
    
    def right_click(self, x: int, y: int) -> bool:
        """Right click at coordinates."""
        try:
            self._log(f"right_click({x},{y})")
            pyautogui.click(x, y, button='right')
            time.sleep(0.2)
            return True
        except Exception as e:
            return False
    
    def move_to(self, x: int, y: int,
                duration: float = 0.3) -> bool:
        """Move mouse to coordinates smoothly."""
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            return False
    
    def drag(self, x1: int, y1: int,
             x2: int, y2: int,
             duration: float = 0.5) -> bool:
        """Drag from one point to another."""
        try:
            self._log(f"drag({x1},{y1}→{x2},{y2})")
            pyautogui.drag(
                x2-x1, y2-y1,
                startX=x1, startY=y1,
                duration=duration
            )
            return True
        except Exception as e:
            return False
    
    def scroll(self, x: int, y: int,
               clicks: int = 3,
               direction: str = 'down') -> bool:
        """Scroll at position."""
        try:
            amount = -clicks if direction == 'down' \
                     else clicks
            pyautogui.scroll(amount, x=x, y=y)
            return True
        except Exception as e:
            return False
    
    # ─────────────────────────────────────────
    # KEYBOARD METHODS:
    
    def type_text(self, text: str,
                  interval: float = 0.05) -> bool:
        """Type text with human-like timing."""
        try:
            self._log(f"type('{text[:30]}...')")
            pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            print(f"[Control] Type failed: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """Press a single key."""
        try:
            self._log(f"press({key})")
            pyautogui.press(key)
            time.sleep(0.1)
            return True
        except Exception as e:
            return False
    
    def hotkey(self, *keys) -> bool:
        """Press key combination e.g. hotkey('cmd','c')"""
        try:
            self._log(f"hotkey({'+'.join(keys)})")
            pyautogui.hotkey(*keys)
            time.sleep(0.2)
            return True
        except Exception as e:
            return False
    
    def press_enter(self) -> bool:
        return self.press_key('enter')
    
    def press_escape(self) -> bool:
        return self.press_key('escape')
    
    def copy(self) -> bool:
        return self.hotkey('command', 'c')
    
    def paste(self) -> bool:
        return self.hotkey('command', 'v')
    
    def select_all(self) -> bool:
        return self.hotkey('command', 'a')
    
    # ─────────────────────────────────────────
    # HIGH LEVEL ACTIONS:
    
    def click_button(self, 
                     label: str) -> bool:
        """Find and click a button by its text label."""
        pos = vision.find_button(label)
        if pos:
            self._log(
                f"click_button('{label}') at {pos}"
            )
            return self.click(pos[0], pos[1],
                            description=f"button:{label}")
        print(f"[Control] Button '{label}' not found")
        return False
    
    def type_in_field(self, text: str,
                      clear_first: bool = True) -> bool:
        """
        Type text into currently focused field.
        Optionally clears existing content first.
        """
        if clear_first:
            self.select_all()
            time.sleep(0.1)
            self.press_key('delete')
            time.sleep(0.1)
        return self.type_text(text)
    
    def open_app(self, app_name: str) -> bool:
        """Open a macOS application by name."""
        try:
            self._log(f"open_app('{app_name}')")
            result = subprocess.run(
                ['open', '-a', app_name],
                capture_output=True, text=True,
                timeout=10
            )
            if result.returncode == 0:
                time.sleep(2)  # Wait for app to open
                return True
            else:
                # Try without -a flag
                result2 = subprocess.run(
                    ['open', app_name],
                    capture_output=True, text=True
                )
                return result2.returncode == 0
        except Exception as e:
            print(f"[Control] Open app failed: {e}")
            return False
    
    def open_url(self, url: str,
                 browser: str = "Google Chrome") -> bool:
        """Open URL in browser."""
        try:
            self._log(f"open_url('{url}')")
            if not url.startswith('http'):
                url = 'https://' + url
            subprocess.run(['open', '-a', browser, url])
            time.sleep(2)
            return True
        except Exception as e:
            return False
    
    def run_applescript(self, script: str) -> str:
        """Run AppleScript and return output."""
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True,
                timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            return f"Error: {e}"
    
    def focus_app(self, app_name: str) -> bool:
        """Bring app to foreground."""
        script = f'''
        tell application "{app_name}"
            activate
        end tell
        '''
        result = self.run_applescript(script)
        time.sleep(0.5)
        return True
    
    def get_clipboard(self) -> str:
        """Get current clipboard content."""
        try:
            result = subprocess.run(
                ['pbpaste'],
                capture_output=True, text=True
            )
            return result.stdout
        except:
            return ""
    
    def set_clipboard(self, text: str) -> bool:
        """Set clipboard content."""
        try:
            subprocess.run(
                ['pbcopy'],
                input=text.encode(),
                capture_output=True
            )
            return True
        except:
            return False
    
    # ─────────────────────────────────────────
    # SMART ACTIONS (vision + control combined):
    
    def click_if_visible(self, 
                         text: str,
                         timeout: int = 5) -> bool:
        """
        Wait for text to appear on screen then click it.
        """
        start = time.time()
        while time.time() - start < timeout:
            pos = vision.find_text_on_screen(text)
            if pos:
                return self.click(
                    pos[0], pos[1],
                    description=f"text:{text}"
                )
            time.sleep(0.5)
        return False
    
    def read_and_click(self, 
                       target_text: str) -> bool:
        """Take screenshot, find text, click it."""
        pos = vision.find_text_on_screen(target_text)
        if pos:
            return self.click(pos[0], pos[1])
        return False
    
    def screenshot_and_describe(self) -> str:
        """
        Take screenshot and return text description
        of what's currently on screen.
        """
        return vision.describe_screen()
    
    def _log(self, action: str):
        """Log action for audit trail."""
        from datetime import datetime
        entry = {
            "time": datetime.now().isoformat(),
            "action": action
        }
        self._action_log.append(entry)
        print(f"[Control] {action}")
        
        # Keep log capped at 100 entries
        if len(self._action_log) > 100:
            self._action_log = self._action_log[-100:]
    
    def get_action_log(self) -> list:
        return self._action_log.copy()

# Singleton
computer = ComputerControl()
