
import re
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

import logging

logger = logging.getLogger(__name__)

# Default timezone if none provided in reference (Execution System Local)
# In production, this might come from configuration.
DEFAULT_TZ = ZoneInfo("Asia/Kolkata") 

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}

def parse_natural_date(phrase: str, reference_datetime: datetime = None, duration_minutes: int = 60):
    """
    Deterministically parse a natural language date phrase into ISO 8601 timestamps.
    
    Args:
        phrase (str): The natural language phrase (e.g., "tomorrow at 3pm").
        reference_datetime (datetime, optional): The anchor time for relative dates. 
                                                 Defaults to datetime.now(DEFAULT_TZ).
        duration_minutes (int): Duration of the event in minutes. Default 60.

    Returns:
        tuple: (start_iso_string, end_iso_string)

    Raises:
        ValueError: If phrase cannot be parsed or results in a past time.
    """
    if not phrase:
        raise ValueError("Empty date phrase.")

    phrase = phrase.lower().strip()
    
    # 1. Establish Reference Time
    if reference_datetime is None:
        reference_datetime = datetime.now(DEFAULT_TZ)
    
    if reference_datetime.tzinfo is None:
        # If naive, assume default TZ
        reference_datetime = reference_datetime.replace(tzinfo=DEFAULT_TZ)

    # Normalize reference to start of day for some calculations
    today_start = reference_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    
    target_date = None
    target_time_hour = 9  # Default 9 AM
    target_time_minute = 0
    is_relative_time_found = False

    # --- 2. Date Extraction Strategy ---
    
    # A. "Tomorrow" / "Today"
    if "tomorrow" in phrase:
        target_date = today_start + timedelta(days=1)
    elif "today" in phrase:
        target_date = today_start
    
    # B. "Next [Weekday]"
    elif "next" in phrase:
        for day_name, day_idx in WEEKDAYS.items():
            if day_name in phrase:
                current_weekday = reference_datetime.weekday()
                # Calculate days ahead: (target - current + 7) % 7
                # If 0 (same day), add 7 to ensure it's "next" week, not today.
                # However, "next Monday" usually means the one in the next week, ie. 7 days later?
                # Standard convention: 
                # If today is Monday, "next Monday" is +7 days.
                # If today is Sunday, "next Monday" is +1 day.
                # WAIT: "Next Monday" is ambiguous. 
                # Strict interpretation: "Next occurrence of Monday".
                # But widely, "Next Monday" often implies "Monday of next week".
                # Let's use strict "next occurrence that isn't today".
                
                days_ahead = (day_idx - current_weekday + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                
                target_date = today_start + timedelta(days=days_ahead)
                break
    
    # C. Implicit "[Weekday]" (e.g. "Friday at 5pm")
    # If no "next", assume the immediate coming weekday
    else:
        for day_name, day_idx in WEEKDAYS.items():
            if day_name in phrase:
                current_weekday = reference_datetime.weekday()
                days_ahead = (day_idx - current_weekday + 7) % 7
                # If today is Friday and user says "Friday at 5pm":
                # If 5pm is in future -> Today
                # If 5pm is in past -> Next week? Or Error?
                # Let's optimistically set date to today + days_ahead, 
                # and logic below will handle past times if on same day.
                target_date = today_start + timedelta(days=days_ahead)
                break

    # --- 3. Time Extraction Strategy ---
    # Patterns: "at 3pm", "at 10:30am", "at 15:00", "3pm", "10am" (if explicit date found)
    
    # Regex for "at HH(:MM)am/pm" or just "HH(:MM)am/pm"
    # We search specifically often preceded by "at" or just ending the string
    time_match = re.search(r"(\b at\s+)?(\d{1,2})(:(\d{2}))?\s*(am|pm)", phrase)
    if not time_match:
        # Try 24hr format "at 15:00"
        time_match = re.search(r"\b at\s+(\d{1,2})(:(\d{2}))", phrase)

    if time_match:
        groups = time_match.groups()
        # Handle the variable groups depending on which regex matched
        if groups[-1] in ('am', 'pm'):
            # 12-hour regex
            # groups: (prefix, hour, :min_group, min, ampm)
            hour_str = groups[1]
            min_str = groups[3]
            meridiem = groups[4]
            
            hour = int(hour_str)
            minute = int(min_str) if min_str else 0
            
            if meridiem == "pm" and hour != 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
        else:
            # 24-hour regex
            # groups: hour, :min_group, min
            hour_str = groups[0]
            min_str = groups[2]
            
            hour = int(hour_str)
            minute = int(min_str) if min_str else 0
            
        target_time_hour = hour
        target_time_minute = minute
        is_relative_time_found = True

    # --- 4. Relative Offset Strategy ("in X hours") ---
    # This overrides explicit date/time if present
    # Matches "in 2 hours", "meeting in 2 hours", etc.
    relative_match = re.search(r"\bin\s+(\d+)\s+(hour|minute)s?", phrase)
    if relative_match:
        val = int(relative_match.group(1))
        unit = relative_match.group(2)
        
        target_start = reference_datetime
        if "hour" in unit:
             target_start += timedelta(hours=val)
        else:
             target_start += timedelta(minutes=val)
             
        target_start = target_start.replace(second=0, microsecond=0)
        target_end = target_start + timedelta(minutes=duration_minutes)
        return target_start.isoformat(), target_end.isoformat()

    # --- 5. Validating & Assembling ---
    
    if not target_date and not is_relative_time_found:
        # Fallback: If just "at 5pm" was said without date?
        # Requires context. Assuming 'today' if future, else 'tomorrow'.
        if time_match:
             target_date = today_start
        else:
             # No date, no relative match.
             raise ValueError(f"Could not understand date phrase: '{phrase}'")

    # Combine date and time
    candidate_start = target_date.replace(hour=target_time_hour, minute=target_time_minute)

    # Smart correction for "Friday at 5pm" if today is Friday 6pm
    # Or "at 5pm" if today is 6pm
    if candidate_start < reference_datetime:
        # If the phrase was just a weekday "Friday" and we mapped it to Today, but it's passed
        # Move to next week (+7 days)
        # OR if it was "at 5pm" (implied today), move to tomorrow (+1 day)
        
        if "tomorrow" in phrase or "next" in phrase:
            # Explicitly requested a future date that turned out to be past? Impossible unless ref time is weird.
            # E.g. "Tomorrow at 8am" when ref is Tomorrow 9am? Unlikely.
            pass 
        elif "today" in phrase:
             # User said "today" but it's passed.
             raise ValueError(f"Requested time {candidate_start.strftime('%H:%M')} is in the past.")
        else:
            # Ambiguous implicit date. Move forward.
            # If explicit weekday was used ("Friday"), move 7 days
            found_weekday = False
            for day in WEEKDAYS:
                if day in phrase:
                    candidate_start += timedelta(days=7)
                    found_weekday = True
                    break
            
            # If no weekday (just "at 5pm"), move 1 day
            if not found_weekday:
                candidate_start += timedelta(days=1)

    # Final Past Check (Strict)
    if candidate_start < reference_datetime:
         raise ValueError(f"Resulting time {candidate_start} is in the past relative to {reference_datetime}.")

    target_end = candidate_start + timedelta(minutes=duration_minutes)
    
    return candidate_start.isoformat(), target_end.isoformat()
