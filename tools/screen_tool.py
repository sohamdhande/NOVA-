import os
import re
import time
import json
import threading
import pyautogui
import mss
import google.generativeai as genai
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

SCREEN_MEMORY = {}  # stores last screen context
PASSIVE_MODE = False
_passive_thread = None

# Ensure screenshots directory exists
os.makedirs("/Users/sohamdhande/Docs_Local/NOVA/screenshots", exist_ok=True)

def capture_screen() -> str:
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"/Users/sohamdhande/Docs_Local/NOVA/screenshots/screen_{timestamp}.png"
        with mss.mss() as sct:
            sct.shot(output=filepath)
        return filepath
    except Exception as e:
        return f"Failed: {str(e)}"

def analyze_screen() -> dict:
    try:
        filepath = capture_screen()
        if filepath.startswith("Failed"):
            return {"error": filepath}
            
        img = Image.open(filepath)
        prompt = (
            "Analyze this screenshot and return ONLY a JSON object with:\n"
            "{\n"
            "  'app': 'current foreground app name',\n"
            "  'task': 'what the user appears to be doing in one sentence',\n"
            "  'page_type': 'type of content (code/browser/terminal/document/etc)',\n"
            "  'visible_text': 'key text visible on screen (max 200 chars)',\n"
            "  'ui_elements': ['list of interactive elements visible'],\n"
            "  'errors': ['any error messages visible'],\n"
            "  'suggestions': ['1-2 actionable suggestions based on screen context']\n"
            "}\n"
            "Return ONLY valid JSON. No explanation."
        )
        response = model.generate_content([prompt, img])
        
        # Parse JSON from response
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model response")
        data = json.loads(match.group())
        
        SCREEN_MEMORY['last'] = {
            'timestamp': time.time(),
            'context': data
        }
        return data
    except Exception as e:
        return {"error": f"Failed: {str(e)}"}

def get_screen_context() -> str:
    data = analyze_screen()
    if "error" in data:
        return data["error"]
        
    return (
        f"🖥️ Screen Context\n"
        f"App: {data.get('app')}\n"
        f"Task: {data.get('task')}\n"
        f"Type: {data.get('page_type')}\n"
        f"Visible: {data.get('visible_text')}\n"
        f"Elements: {data.get('ui_elements')}\n"
        f"Errors: {data.get('errors')}\n"
        f"Suggestions: {data.get('suggestions')}"
    )

def ask_about_screen(question: str) -> str:
    try:
        filepath = capture_screen()
        if filepath.startswith("Failed"):
            return filepath
            
        img = Image.open(filepath)
        prompt = (
            "You are NOVA analyzing the user's screen.\n"
            "Answer based strictly on what you see.\n"
            f"User question: {question}"
        )
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"Failed: {str(e)}"

def fix_screen_error() -> str:
    try:
        data = analyze_screen()
        if "error" in data:
            return data["error"]
            
        errors = data.get("errors", [])
        if not errors or (isinstance(errors, list) and len(errors) > 0 and str(errors[0]).lower() in ["none", ""]):
            return "No errors detected on screen."
            
        filepath = capture_screen()
        img = Image.open(filepath)
        prompt = (
            f"The user has this error on their screen: {errors}\n"
            "Provide a specific fix. Be concise. Max 5 lines."
        )
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"Failed: {str(e)}"

def click_element(element_description: str) -> str:
    try:
        # call to populate context but we actually need the coords directly from a fresh gemini call
        analyze_screen() 
        filepath = capture_screen()
        img = Image.open(filepath)
        prompt = (
            f"In this screenshot, find the element matching: {element_description}\n"
            "Return ONLY a JSON: {'x': pixel_x, 'y': pixel_y, 'found': true/false}"
        )
        response = model.generate_content([prompt, img])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model response")
        coords = json.loads(match.group())
        
        if coords.get("found", False):
            # Scale coordinates down by half for retina displays because mss captures at 2x 
            # while pyautogui clicks at 1x points.
            pyautogui.click(coords["x"] // 2, coords["y"] // 2)
            return f"Clicked {element_description}"
        else:
            return "Element not found"
    except Exception as e:
        return f"Failed: {str(e)}"

def type_text(text: str) -> str:
    try:
        pyautogui.typewrite(text, interval=0.05)
        return f"Typed: {text}"
    except Exception as e:
        return f"Failed: {str(e)}"

def scroll(direction: str = "down", amount: int = 3) -> str:
    try:
        if direction == "down":
            pyautogui.scroll(-amount * 100)
        elif direction == "up":
            pyautogui.scroll(amount * 100)
        return f"Scrolled {direction}"
    except Exception as e:
        return f"Failed: {str(e)}"

def _passive_loop(interval: int):
    global PASSIVE_MODE
    while PASSIVE_MODE:
        try:
            analyze_screen()
        except:
            pass
        time.sleep(interval)

def start_passive_mode(interval: int = 30) -> str:
    global PASSIVE_MODE, _passive_thread
    if PASSIVE_MODE:
        return "Passive screen monitoring is already running."
        
    PASSIVE_MODE = True
    _passive_thread = threading.Thread(target=_passive_loop, args=(interval,), daemon=True)
    _passive_thread.start()
    return "Passive screen monitoring started."

def stop_passive_mode() -> str:
    global PASSIVE_MODE
    PASSIVE_MODE = False
    return "Passive monitoring stopped."
