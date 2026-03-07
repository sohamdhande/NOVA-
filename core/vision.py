import os
import time
import base64
import subprocess
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import pyautogui
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io

@dataclass
class ScreenState:
    timestamp: datetime
    screenshot_path: str
    width: int
    height: int
    active_app: str
    active_window: str
    screen_text: str           # OCR text from full screen
    focused_text: str          # OCR text from center region
    mouse_position: tuple
    base64_image: str          # for sending to LLM

@dataclass  
class ScreenRegion:
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    confidence: float = 0.0

class VisionModule:
    """
    N.O.V.A's eyes. Captures and understands screen state.
    """
    
    SCREENSHOT_DIR = os.path.expanduser(
        "~/.nova/screenshots"
    )
    
    def __init__(self):
        os.makedirs(self.SCREENSHOT_DIR, exist_ok=True)
        self._last_screenshot: Optional[Image.Image] = None
        self._last_state: Optional[ScreenState] = None
    
    # ─────────────────────────────────────────
    # SCREEN CAPTURE METHODS:
    
    def capture(self) -> Image.Image:
        """Take a full screenshot. Returns PIL Image."""
        screenshot = pyautogui.screenshot()
        self._last_screenshot = screenshot
        return screenshot
    
    def capture_region(self, x: int, y: int, 
                       width: int, 
                       height: int) -> Image.Image:
        """Capture a specific screen region."""
        screenshot = pyautogui.screenshot(
            region=(x, y, width, height)
        )
        return screenshot
    
    def capture_active_window(self) -> Image.Image:
        """
        Capture only the currently active window
        using AppleScript to get window bounds.
        """
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                tell frontApp
                    set win to front window
                    set {x, y} to position of win
                    set {w, h} to size of win
                end tell
                return {appName, x, y, w, h}
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 5:
                    app = parts[0]
                    x, y, w, h = int(parts[1]), \
                        int(parts[2]), int(parts[3]), \
                        int(parts[4])
                    return self.capture_region(x, y, w, h)
        except Exception as e:
            print(f"[Vision] Window capture failed: {e}")
        
        return self.capture()
    
    def save_screenshot(self, 
                        img: Image.Image,
                        label: str = "") -> str:
        """Save screenshot to disk, return path."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"{ts}_{label}.png" if label \
                else f"{ts}.png"
        path = os.path.join(self.SCREENSHOT_DIR, fname)
        img.save(path)
        return path
    
    # ─────────────────────────────────────────
    # OCR METHODS:
    
    def read_text(self, img: Image.Image) -> str:
        """
        Extract all text from image using Tesseract OCR.
        Returns cleaned text string.
        """
        try:
            # Preprocess for better OCR accuracy
            enhanced = self._preprocess_for_ocr(img)
            text = pytesseract.image_to_string(
                enhanced,
                config='--psm 3 --oem 3'
            )
            return text.strip()
        except Exception as e:
            print(f"[Vision] OCR failed: {e}")
            return ""
    
    def read_region_text(self, x: int, y: int,
                         width: int, 
                         height: int) -> str:
        """Read text from a specific screen region."""
        region_img = self.capture_region(
            x, y, width, height
        )
        return self.read_text(region_img)
    
    def find_text_on_screen(self, 
                            target: str) -> Optional[tuple]:
        """
        Find where specific text appears on screen.
        Returns (x, y) center position or None.
        """
        try:
            img = self.capture()
            data = pytesseract.image_to_data(
                self._preprocess_for_ocr(img),
                output_type=pytesseract.Output.DICT
            )
            target_lower = target.lower()
            for i, word in enumerate(data['text']):
                if target_lower in word.lower() and \
                   int(data['conf'][i]) > 60:
                    x = data['left'][i] + \
                        data['width'][i] // 2
                    y = data['top'][i] + \
                        data['height'][i] // 2
                    return (x, y)
        except Exception as e:
            print(f"[Vision] Text find failed: {e}")
        return None
    
    def _preprocess_for_ocr(self, 
                             img: Image.Image) -> Image.Image:
        """Enhance image for better OCR results."""
        # Convert to grayscale
        gray = img.convert('L')
        # Increase contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.0)
        # Scale up for better OCR
        w, h = enhanced.size
        scaled = enhanced.resize(
            (w * 2, h * 2), 
            Image.LANCZOS
        )
        return scaled
    
    # ─────────────────────────────────────────
    # SCREEN STATE METHODS:
    
    def get_active_app(self) -> str:
        """Get name of currently active application."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                return name of frontApp
            end tell
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True,
                timeout=3
            )
            return result.stdout.strip()
        except:
            return "Unknown"
    
    def get_active_window_title(self) -> str:
        """Get title of currently active window."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                tell frontApp
                    if exists front window then
                        return name of front window
                    end if
                end tell
            end tell
            return ""
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True,
                timeout=3
            )
            return result.stdout.strip()
        except:
            return ""
    
    def get_screen_state(self, 
                         save: bool = False) -> ScreenState:
        """
        Full screen state snapshot.
        Captures screenshot + reads text + gets app info.
        """
        img = self.capture()
        
        # Get screen dimensions
        w, h = img.size
        
        # Get active app
        active_app = self.get_active_app()
        active_window = self.get_active_window_title()
        
        # OCR full screen (sample regions for speed)
        # Read center 60% of screen — most relevant
        cx, cy = w // 2, h // 2
        center_region = self.capture_region(
            cx - w//3, cy - h//3,
            (w//3) * 2, (h//3) * 2
        )
        focused_text = self.read_text(center_region)
        
        # Quick full screen OCR (lower res for speed)
        small = img.resize((w//3, h//3), Image.LANCZOS)
        screen_text = self.read_text(small)
        
        # Save if requested
        path = ""
        if save:
            path = self.save_screenshot(
                img, f"state_{active_app}"
            )
        
        # Base64 encode for LLM vision (thumbnail)
        thumb = img.resize((800, 500), Image.LANCZOS)
        buffer = io.BytesIO()
        thumb.save(buffer, format='PNG')
        b64 = base64.b64encode(
            buffer.getvalue()
        ).decode()
        
        state = ScreenState(
            timestamp=datetime.now(),
            screenshot_path=path,
            width=w,
            height=h,
            active_app=active_app,
            active_window=active_window,
            screen_text=screen_text,
            focused_text=focused_text,
            mouse_position=pyautogui.position(),
            base64_image=b64
        )
        
        self._last_state = state
        return state
    
    # ─────────────────────────────────────────
    # VISUAL SEARCH METHODS:
    
    def find_button(self, 
                    label: str) -> Optional[tuple]:
        """
        Find a button or UI element by its label text.
        Returns (x, y) to click or None.
        """
        return self.find_text_on_screen(label)
    
    def find_input_field(self) -> Optional[tuple]:
        """
        Find the focused/active input field on screen.
        Returns approximate (x, y) center.
        Uses AppleScript for accuracy.
        """
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                tell frontApp
                    set textFields to every text field whose focused is true
                    if (count textFields) > 0 then
                        set tf to first item of textFields
                        set {x, y} to position of tf
                        set {w, h} to size of tf
                        return {x + w/2, y + h/2}
                    end if
                end tell
            end tell
            return ""
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True,
                timeout=3
            )
            if result.stdout.strip():
                parts = result.stdout.strip().split(', ')
                if len(parts) == 2:
                    return (int(float(parts[0])),
                            int(float(parts[1])))
        except Exception as e:
            print(f"[Vision] Input find failed: {e}")
        return None
    
    def describe_screen(self) -> str:
        """
        Generate a text description of current screen
        for the LLM to understand context.
        """
        state = self.get_screen_state()
        
        description = f"""
SCREEN STATE at {state.timestamp.strftime('%H:%M:%S')}
Active App: {state.active_app}
Window: {state.active_window}
Screen Size: {state.width}x{state.height}
Mouse at: {state.mouse_position}

VISIBLE TEXT (sample):
{state.focused_text[:500] if state.focused_text else 'No text detected'}
        """.strip()
        
        return description
    
    def wait_for_text(self, target: str,
                      timeout: int = 10) -> bool:
        """
        Wait until specific text appears on screen.
        Returns True if found, False if timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.find_text_on_screen(target):
                return True
            time.sleep(0.5)
        return False

# Singleton
vision = VisionModule()
