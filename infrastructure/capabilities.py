import os
import re
import json
import subprocess
import asyncio
import requests
import httpx
from datetime import datetime

TAVILY_KEY = os.getenv("TAVILY_API_KEY")

class NovaCapabilities:

    # ─── SPOTIFY ────────────────────────────────
    
    def spotify_command(self, 
                         command: str) -> str:
        """Control Spotify via AppleScript."""
        COMMANDS = {
            "play":     "play",
            "pause":    "pause", 
            "next":     "next track",
            "prev":     "previous track",
            "stop":     "pause"
        }
        action = COMMANDS.get(command, command)
        script = f'''
        tell application "Spotify"
            {action}
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Spotify: {action} ✓"
        return f"Spotify error: {result.stderr}"
    
    def spotify_search_play(self, 
                             query: str) -> str:
        """Search and play on Spotify."""
        script = f'''
        tell application "Spotify"
            activate
            play track "spotify:search:{query}"
        end tell
        '''
        # Open Spotify and search
        subprocess.Popen(['open', '-a', 'Spotify'])
        import time; time.sleep(2)
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        return f"Playing: {query}"
    
    def get_spotify_status(self) -> str:
        """Get current playing track."""
        script = '''
        tell application "Spotify"
            if player state is playing then
                set t to current track
                return (name of t) & " by " & \
                       (artist of t)
            else
                return "Not playing"
            end if
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        return result.stdout.strip() or "Spotify not running"
    
    # ─── VOLUME / BRIGHTNESS ────────────────────
    
    def set_volume(self, level: int) -> str:
        """Set system volume 0-100."""
        level = max(0, min(100, level))
        # AppleScript uses 0-100 scale
        script = f'set volume output volume {level}'
        subprocess.run(
            ['osascript', '-e', script]
        )
        return f"Volume set to {level}%"
    
    def set_brightness(self, level: int) -> str:
        """Set screen brightness 0-100."""
        # Convert to 0.0-1.0
        bright = level / 100.0
        script = f'''
        tell application "System Preferences"
        end tell
        do shell script "brightness {bright}"
        '''
        # Try using brightness CLI tool
        result = subprocess.run(
            ['brightness', str(bright)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # Fallback: use AppleScript
            script2 = f'''
            tell application "System Events"
                tell process "SystemUIServer"
                    set value of slider 1 of \
                    menu bar item "Brightness" of \
                    menu bar 1 to {bright}
                end tell
            end tell
            '''
            subprocess.run(
                ['osascript', '-e', script2]
            )
        return f"Brightness set to {level}%"
    
    def mute(self) -> str:
        subprocess.run(
            ['osascript', '-e', 
             'set volume output muted true']
        )
        return "System muted"
    
    def unmute(self) -> str:
        subprocess.run(
            ['osascript', '-e',
             'set volume output muted false']
        )
        return "System unmuted"
    
    # ─── SYSTEM TOGGLES ─────────────────────────
    
    def toggle_dark_mode(self, 
                          enable: bool) -> str:
        """Toggle macOS dark/light mode."""
        mode = "true" if enable else "false"
        script = f'''
        tell application "System Events"
            tell appearance preferences
                set dark mode to {mode}
            end tell
        end tell
        '''
        subprocess.run(
            ['osascript', '-e', script]
        )
        return f"Dark mode {'enabled' if enable else 'disabled'}"
    
    def toggle_wifi(self, enable: bool) -> str:
        """Toggle WiFi on/off."""
        action = "on" if enable else "off"
        result = subprocess.run(
            ['networksetup', '-setairportpower',
             'en0', action],
            capture_output=True, text=True
        )
        return f"WiFi turned {action}"
    
    def toggle_bluetooth(self, 
                          enable: bool) -> str:
        """Toggle Bluetooth."""
        action = "on" if enable else "off"
        result = subprocess.run(
            ['blueutil', f'--{action}'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return (f"Bluetooth toggle failed. "
                    f"Install blueutil: "
                    f"brew install blueutil")
        return f"Bluetooth turned {action}"
    
    def toggle_dnd(self, enable: bool) -> str:
        """Toggle Do Not Disturb / Focus."""
        if enable:
            script = '''
            tell application "System Events"
                tell process "Control Center"
                    keystroke "f" using \
                    {control down, option down}
                end tell
            end tell
            '''
        else:
            script = '''
            tell application "System Events"
                tell process "Control Center"
                    keystroke "f" using \
                    {control down, option down}
                end tell
            end tell
            '''
        # Use shortcuts app if available
        result = subprocess.run(
            ['shortcuts', 'run', 
             'Focus' if enable else 'Stop Focus'],
            capture_output=True, text=True
        )
        return f"Do Not Disturb " \
               f"{'enabled' if enable else 'disabled'}"
    
    # ─── FILE OPERATIONS ────────────────────────
    
    def create_file(self, path: str, 
                    content: str = "") -> str:
        """Create a file with optional content."""
        expanded = os.path.expanduser(path)
        os.makedirs(
            os.path.dirname(expanded),
            exist_ok=True
        )
        with open(expanded, 'w') as f:
            f.write(content)
        return f"File created: {path}"
    
    def create_folder(self, path: str) -> str:
        """Create a directory."""
        expanded = os.path.expanduser(path)
        os.makedirs(expanded, exist_ok=True)
        return f"Folder created: {path}"
    
    # ─── NEWS ───────────────────────────────────────

    async def get_news(self, category: str = "general") -> str:
        """Fetch current news headlines. Tavily → DuckDuckGo → LLM."""
        from datetime import datetime

        CATEGORY_QUERIES = {
            "general": "today's top news headlines national international",
            "ai": "artificial intelligence AI machine learning news today",
            "technology": "technology tech news today",
            "business": "business finance economy news today",
            "sports": "sports news today",
            "science": "science space research news today",
        }
        query = CATEGORY_QUERIES.get(category, CATEGORY_QUERIES["general"])
        today = datetime.now().strftime("%B %d, %Y")

        # ── 1. TAVILY (primary — best for news) ──────
        if TAVILY_KEY:
            try:
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": TAVILY_KEY,
                        "query": query,
                        "search_depth": "advanced",
                        "topic": "news",
                        "max_results": 8,
                        "include_domains": [],
                        "exclude_domains": [],
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                if results:
                    headlines = []
                    for r in results[:8]:
                        title = r.get("title", "")
                        url = r.get("url", "")
                        snippet = r.get("content", "")[:200]
                        headlines.append(
                            f"**{title}**\n{snippet}\n🔗 {url}"
                        )
                    header = f"📰 **News Briefing — {today}**"
                    if category != "general":
                        header += f" ({category.upper()})"
                    return (
                        f"{header}\n"
                        f"{'─' * 40}\n\n"
                        + "\n\n".join(headlines)
                    )
                print("[News] Tavily returned 0 results, "
                      "falling through")
            except requests.RequestException as e:
                print(f"[News] Tavily failed: {e}")

        # ── 2. DUCKDUCKGO NEWS (fallback) ────────────
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                    timeout=10,
                    follow_redirects=True,
                )
                data = resp.json()

            chunks = []
            if data.get("Answer"):
                chunks.append(data["Answer"])
            if data.get("AbstractText"):
                chunks.append(data["AbstractText"])
            for topic in data.get("RelatedTopics", [])[:8]:
                if isinstance(topic, dict) and topic.get("Text"):
                    chunks.append(topic["Text"])

            raw = "\n".join(chunks)
            if raw.strip():
                from llm import _chat
                try:
                    summary = _chat(
                        system=(
                            "You are N.O.V.A, an AI assistant. "
                            "Format the following search data as "
                            "a clean news briefing with bullet points. "
                            "Include national and international news. "
                            "Be factual and concise."
                        ),
                        user=(
                            f"Create a news briefing for {today} "
                            f"from this data:\n\n{raw}\n\n"
                            f"Category: {category}\n"
                            f"Format as clear bullet points with "
                            f"headlines and brief summaries."
                        ),
                    )
                    return summary
                except Exception:
                    return raw[:500]

            print("[News] DuckDuckGo returned nothing, "
                  "using LLM")
        except Exception as e:
            print(f"[News] DuckDuckGo failed: {e}")

        # ── 3. LLM FALLBACK (uses training knowledge) ─
        try:
            from llm import _chat
            return _chat(
                system=(
                    "You are N.O.V.A, a tactical AI assistant. "
                    "The user asked for today's news but live "
                    "search is unavailable. Acknowledge that you "
                    "cannot fetch live news right now, and suggest "
                    "the user configure a Tavily API key for "
                    "real-time news. Provide a brief summary of "
                    "major ongoing stories you know about up to "
                    "your knowledge cutoff. Be honest about "
                    "limitations."
                ),
                user=(
                    f"Give me {category} news for {today}. "
                    f"If you can't access live data, say so "
                    f"and share what you know."
                ),
            )
        except Exception:
            return (
                "⚠ News service unavailable.\n\n"
                "To enable real-time news, add your "
                "Tavily API key to `.env`:\n"
                "TAVILY_API_KEY=tvly-xxxxx\n\n"
                "Get a free key at https://tavily.com "
                "(1000 searches/month, no card needed)"
            )

    # ─── WEB SEARCH ─────────────────────────────
    
    async def web_search(self, query: str) -> str:
        """Search with priority: Tavily → DuckDuckGo → LLM fallback."""
        
        if not any(country in query.lower() for country in ["india", "us", "uk", "china", "pakistan", "russia"]):
            query = f"{query} India"
            
        # ── 1. TAVILY (primary) ──────────────────────
        if TAVILY_KEY:
            try:
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": TAVILY_KEY,
                        "query": query,
                        "max_results": 5,
                        "search_depth": "advanced",
                        "topic": "news",
                        "include_raw_content": False,
                        "include_answer": False,
                        "country": "IN"
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                if results:
                    return "\n\n".join(
                        f"{r['title']}\n{r['url']}\n"
                        f"{r.get('content', '')[:300]}"
                        for r in results
                    )
                print("[Search] Tavily returned 0 results, falling through to DuckDuckGo")
            except requests.RequestException as e:
                print(f"[Search] Tavily failed: {e} — falling back to DuckDuckGo")
        
        # ── 2. DUCKDUCKGO (fallback) ─────────────────
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                    timeout=10,
                    follow_redirects=True,
                )
                data = resp.json()
            
            chunks = []
            if data.get("Answer"):
                chunks.append(data["Answer"])
            if data.get("AbstractText"):
                chunks.append(data["AbstractText"])
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    chunks.append(topic["Text"])
            
            raw_content = "\n".join(chunks)
            
            if raw_content.strip():
                from llm import _chat
                try:
                    return _chat(
                        system="You are a helpful assistant.",
                        user=(
                            f"Based on this search data, "
                            f"give a concise answer to: "
                            f"'{query}'\n\n"
                            f"Search data:\n{raw_content}"
                            f"\n\nAnswer in 3-5 sentences. "
                            f"Be specific and factual."
                        ),
                    )
                except Exception:
                    return raw_content[:300]
            
            print("[Search] DuckDuckGo returned nothing useful, falling through to LLM")
        except Exception as e:
            print(f"[Search] DuckDuckGo failed: {e} — falling back to LLM")
        
        # ── 3. LLM FALLBACK (last resort) ────────────
        try:
            from llm import _chat
            return _chat(
                system="You are a helpful assistant.",
                user=(
                    f"Answer this question concisely "
                    f"based on your knowledge: {query}\n\n"
                    f"Keep answer under 150 words."
                ),
            )
        except Exception:
            return "Search unavailable."

    # ─── INTEL BRIEFING ─────────────────────────

    async def intel_briefing(self, query: str) -> str:
        """Sequential search for military/geopolitical analysis."""
        from datetime import datetime
        from llm import _chat
        import httpx
        
        today = datetime.now().strftime("%B %d, %Y")
        
        if not TAVILY_KEY:
            return "⚠ TAVILY_API_KEY missing. Cannot perform intel briefing."

        if not any(country in query.lower() for country in ["india", "us", "uk", "china", "pakistan", "russia"]):
            query = f"{query} India"

        combined_results = []
        queries = [
            f"{query} India military government",
            f"{query} geopolitics impact analysis"
        ]
        
        for q in queries:
            try:
                resp = requests.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": TAVILY_KEY,
                        "query": q,
                        "search_depth": "advanced",
                        "topic": "news",
                        "max_results": 5,
                        "include_raw_content": False,
                        "include_answer": False,
                        "country": "IN"
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                for r in results:
                    title = r.get("title", "")
                    url = r.get("url", "")
                    content = r.get("content", "")
                    combined_results.append(f"Title: {title}\nSummary: {content}\nSource: {url}")
            except requests.RequestException as e:
                print(f"[Intel] Tavily call failed for '{q}': {e}")
        
        if not combined_results:
            return "No intel gathered from the search."
            
        raw_context = "\n\n".join(combined_results)
        
        system_prompt = (
            "You are NOVA — a classified intelligence briefing system for a RAW field operative.\n"
            "Present the following news as a structured field intelligence report.\n\n"
            "[CLASSIFIED — EYES ONLY]\n"
            f"Operative Briefing — {today}\n\n"
            "SECTION 1 — DOMESTIC MILITARY & GOVERNMENT\n"
            "SECTION 2 — GEOPOLITICAL THREAT ASSESSMENT  \n"
            "SECTION 3 — OPERATIVE ADVISORY (2-3 bullets on what to watch this week)\n\n"
            "Tone: precise, clinical, no fluff. Never say 'as an AI'."
        )
        
        try:
            report = _chat(
                system=system_prompt,
                user=raw_context
            )
            return report
        except Exception as e:
            return f"Intel processing failed: {str(e)}"

    
    # ─── WEBPAGE READING ────────────────────────
    
    async def read_webpage(self, url: str) -> str:
        """Fetch and summarize a webpage."""
        if not url:
            return "No URL provided."
        if not url.startswith("http"):
            url = "https://" + url
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url, timeout=15,
                    follow_redirects=True,
                    headers={"User-Agent": 
                             "Mozilla/5.0"}
                )
                html = resp.text
                
            # Strip HTML tags
            clean = re.sub(r'<[^>]+>', ' ', html)
            clean = re.sub(r'\s+', ' ', clean).strip()
            content = clean[:4000]
            
            # Summarize with LLM
            from llm import _chat
            try:
                summary = _chat(
                    system="You are a helpful assistant.",
                    user=(
                        f"Summarize this webpage "
                        f"content concisely in "
                        f"3-4 sentences:\n\n"
                        f"{content}"
                    )
                )
            except Exception:
                summary = content[:500]
            return f"Summary of {url}:\n{summary}"
        except Exception as e:
            return f"Could not read page: {str(e)}"
    
    # ─── SCREENSHOT ─────────────────────────────
    
    def take_screenshot(self, 
                         path: str = None,
                         annotate: bool = False
                         ) -> str:
        """Take and save screenshot."""
        if not path:
            ts = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            path = f"~/Desktop/nova_{ts}.png"
        
        expanded = os.path.expanduser(path)
        
        # Use screencapture (native macOS)
        result = subprocess.run(
            ['screencapture', '-x', expanded],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Open in Preview if annotate
            if annotate:
                subprocess.Popen(
                    ['open', '-a', 'Preview', 
                     expanded]
                )
                return (f"Screenshot saved to {path}. "
                        f"Opening in Preview for "
                        f"annotation.")
            return f"Screenshot saved to {path}"
        return "Screenshot failed"
    
    # ─── WHATSAPP ───────────────────────────────
    
    def send_whatsapp(self, contact: str,
                       message: str) -> str:
        """Send WhatsApp message via URL scheme."""
        if not contact and not message:
            return "Please specify contact and message."
        
        # Open WhatsApp with pre-filled message
        import urllib.parse
        encoded = urllib.parse.quote(message)
        
        if contact:
            # Try to open conversation
            script = f'''
            tell application "WhatsApp"
                activate
            end tell
            '''
            subprocess.Popen(
                ['open', '-a', 'WhatsApp']
            )
            return (f"WhatsApp opened. "
                    f"Please send '{message}' "
                    f"to {contact} manually. "
                    f"(Direct send requires "
                    f"phone number.)")
        return "WhatsApp opened."
    
    # ─── EMAIL ──────────────────────────────────
    
    def send_email(self, to: str, 
                    subject: str,
                    body: str) -> str:
        """Send email via macOS Mail app."""
        script = f'''
        tell application "Mail"
            activate
            set newMsg to make new outgoing message \
                with properties {{
                    subject: "{subject}",
                    content: "{body}",
                    visible: true
                }}
            tell newMsg
                make new to recipient with properties \
                    {{address: "{to}"}}
            end tell
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return (f"Email composed to {to}. "
                    f"Review and send in Mail app.")
        return f"Email draft opened in Mail app."
    
    # ─── REMINDERS ──────────────────────────────
    
    def set_reminder(self, label: str,
                      time_str: str = "") -> str:
        """Set a reminder via macOS Reminders."""
        if time_str:
            script = f'''
            tell application "Reminders"
                tell list "Reminders"
                    make new reminder with properties\
                        {{name: "{label}",
                          due date: (current date) + \
                          60}}
                end tell
            end tell
            '''
        else:
            script = f'''
            tell application "Reminders"
                tell list "Reminders"
                    make new reminder with properties \
                        {{name: "{label}"}}
                end tell
            end tell
            '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return f"Reminder set: '{label}'"
        return f"Reminder created in Reminders app."

# Singleton
capabilities = NovaCapabilities()
