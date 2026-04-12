"""
System Control Tool wrapper for macOS specific commands.
"""
import subprocess
import math
import datetime
import os
import re

def get_running_apps() -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of every process where background only is false'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def open_app(app_name: str) -> str:
    try:
        subprocess.run(["open", "-a", app_name], check=True)
        return f"Opening {app_name}"
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def close_app(app_name: str) -> str:
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{app_name}" to quit'],
            check=True
        )
        return f"Closing {app_name}"
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def lock_mac() -> str:
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'],
            check=True
        )
        return "Mac locked."
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def set_volume(level: int) -> str:
    try:
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {level}"],
            check=True
        )
        return f"Volume set to {level}%"
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def get_volume() -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, check=True
        )
        return f"Current volume: {result.stdout.strip()}%"
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def set_brightness(level: int) -> str:
    try:
        brightness = level / 100
        # This requires specific display tools or third party logic, using as provided.
        subprocess.run(
            ["osascript", "-e", f'tell application "System Events" to set brightness of display 1 to {brightness}'],
            check=True
        )
        return f"Brightness set to {level}%"
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def take_screenshot() -> str:
    try:
        filename = f"/Users/sohamdhande/Docs_Local/NOVA/screenshots/screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        subprocess.run(["screencapture", "-x", filename], check=True)
        return f"Screenshot saved to {filename}"
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def empty_trash() -> str:
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Finder" to empty trash'],
            check=True
        )
        return "Trash emptied."
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"

def sleep_mac() -> str:
    try:
        subprocess.run(["pmset", "sleepnow"], check=True)
        return "Going to sleep."
    except subprocess.SubprocessError as e:
        return f"Failed: {str(e)}"
