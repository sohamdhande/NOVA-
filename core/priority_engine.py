from datetime import datetime, timedelta, timezone
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class PriorityEngine:
    """
    Deterministic Priority Engine for NOVA tasks.
    
    Computes dynamic priority scores based on:
    - Deadlines (Overdue, Today, 48h, 7d)
    - Task Age
    - Goal Weight
    
    Sorting Order:
    1. Score (Highest first)
    2. Deadline (Earliest first)
    3. Creation Time (Oldest first)
    """
    
    def __init__(self):
        pass

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string to timezone-aware datetime object."""
        if not date_str:
            return None
        
        try:
            # Handle ISO format
            # Notion dates are usually YYYY-MM-DD or ISO 8601 with timezone
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Basic date, assume start of day local time or handle as date
                dt = datetime.fromisoformat(date_str)
            
            # Ensure timezone awareness (assume local system time if naive)
            if dt.tzinfo is None:
                dt = dt.astimezone()
                
            return dt
        except ValueError:
            logger.warning(f"Failed to parse datetime: {date_str}")
            return None

    def _get_goal_weight(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> int:
        """
        Retrieve goal weight based on operational mode or task context.
        """
        if context and "goal_weight" in context:
            return context["goal_weight"]
            
        # Default fallback
        return 1

    def calculate_score(self, task: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Compute priority score and breakdown for a single task.
        
        Args:
            task: Task data
            context: Runtime context (e.g. current mode, global weights)
            
        Returns:
            Dict containing 'score', 'breakdown', and sort keys.
        """
        score = 0
        breakdown = []
        
        # Ensure we use system-aware time consistent with the user's environment
        now = datetime.now().astimezone()
        
        # 1. Deadline Scoring
        due_date_str = task.get("due_date")
        due_date = self._parse_datetime(due_date_str)
        
        if due_date:
            # Normalize to date for logic if needed, but exact time precision is better for Overdue
            # Requirement: "Overdue task -> +50"
            # Requirement: "Due today -> +30"
            # Requirement: "Due within 48 hours -> +20"
            # Requirement: "Due within 7 days -> +10"
            
            time_diff = due_date - now
            
            if due_date < now:
                # Overdue
                points = 50
                score += points
                breakdown.append(f"Overdue (+{points})")
            elif due_date.date() == now.date():
                # Due today (future time)
                points = 30
                score += points
                breakdown.append(f"Due today (+{points})")
            elif time_diff <= timedelta(hours=48):
                 # Within 48 hours
                points = 20
                score += points
                breakdown.append(f"Due within 48h (+{points})")
            elif time_diff <= timedelta(days=7):
                # Within 7 days
                points = 10
                score += points
                breakdown.append(f"Due within 7d (+{points})")
            else:
                # Future > 7 days - No points specified for >7d
                pass
        else:
            # No deadline -> +5
            points = 5
            score += points
            breakdown.append(f"No deadline (+{points})")

        # 2. Task Age Scoring
        # Add min(task_age_days, 10)
        created_time_str = task.get("created_time")
        created_time = self._parse_datetime(created_time_str)
        
        if created_time:
            age_delta = now - created_time
            age_days = max(0, age_delta.days) # Ensure no negative age
            
            age_points = min(age_days, 10)
            score += age_points
            if age_points > 0:
                breakdown.append(f"Age {age_days}d (+{age_points})")
        
        # 3. Goal Weight Scoring
        # Add goal_weight × 10
        goal_weight = self._get_goal_weight(task, context)
        weight_points = goal_weight * 10
        score += weight_points
        breakdown.append(f"Goal weight {goal_weight} (+{weight_points})")
        
        # Sort helpers
        # Sort Deadline: if none, push to end (max date)
        # We use a timezone-aware max date to match 'due_date' which is aware
        sort_deadline = due_date if due_date else datetime.max.replace(tzinfo=timezone.utc)
        
        # Sort Created: if none, push to start (min date) - actually, if unknown, treat as 'new' (now)
        # to avoid it jumping to top of 'oldest' list.
        sort_created = created_time if created_time else now

        return {
            "score": score,
            "breakdown": breakdown,
            "sort_deadline": sort_deadline, 
            "sort_created": sort_created
        }

    def process_tasks(self, tasks: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Process, score, and sort a list of tasks.
        
        Args:
            tasks: List of task dicts
            context: Optional context for scoring (e.g. mode weights)
        
        Requirements:
        - Only include tasks with status = ACTIVE
        - Exclude completed and cancelled tasks
        - Sort: Score (desc) -> Deadline (asc) -> Oldest (asc)
        """
        processed_tasks = []
        
        # Define statuses to exclude
        EXCLUDED_STATUSES = {"done", "completed", "cancelled", "archived", "deleted"}
        
        for task in tasks:
            # Status Filter
            status = str(task.get("status", "")).lower()
            if status in EXCLUDED_STATUSES:
                continue
            
            # Calculate Score
            scoring = self.calculate_score(task, context)
            
            # Enrich task with scoring data
            # Create a new dict to avoid mutating original if needed, or just update
            enriched_task = task.copy()
            enriched_task["computed_score"] = scoring["score"]
            enriched_task["breakdown"] = scoring["breakdown"]
            
            # Store sort keys internally
            enriched_task["_sort_deadline"] = scoring["sort_deadline"]
            enriched_task["_sort_created"] = scoring["sort_created"]
            
            processed_tasks.append(enriched_task)
            
        # Sorting Order:
        # 1. Highest score first (reverse=True)
        # 2. Earliest deadline (normal)
        # 3. Oldest task (created time) (normal)
        
        # Python's sort is stable. We can sort in reverse order of priority.
        # Primary key: Score (Desc)
        # Secondary key: Deadline (Asc)
        # Tertiary key: Created (Asc)
        
        # To do this in one pass with a tuple:
        # (-score, deadline, created)
        # Since deadline and created are datetimes, they support comparison.
        
        processed_tasks.sort(key=lambda t: (
            -t["computed_score"],       # Descending Score
            t["_sort_deadline"],        # Ascending Deadline (Earliest first)
            t["_sort_created"]          # Ascending Created (Oldest first)
        ))
        
        # Clean up internal sort keys
        for t in processed_tasks:
            t.pop("_sort_deadline", None)
            t.pop("_sort_created", None)
            
        return processed_tasks
