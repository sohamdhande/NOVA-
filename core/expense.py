
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Constants
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nova_logs.db")
logger = logging.getLogger(__name__)

class ExpenseManager:
    """
    Manages personal expense tracking via SQLite.
    """
    
    VALID_CATEGORIES = {
        "Food", "Transport", "Utilities", "Entertainment", 
        "Shopping", "Health", "Subscriptions", "Other"
    }

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        # Harden concurrency
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                amount REAL,
                category TEXT,
                description TEXT,
                timestamp TEXT
            )
        """)
        self.conn.commit()

    def add_expense(self, amount: float, category: str, description: str, date: str = None) -> Dict[str, Any]:
        """Record a new expense."""
        # Enforce Title Case normalization
        normalized_category = category.strip().title()
        
        if normalized_category not in self.VALID_CATEGORIES:
             # Just warn but allow it for now, or fallback to 'Other'
             # Strict requirement says "Validate category", so let's error or default
             normalized_category = "Other"
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        timestamp = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (date, amount, category, description, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (date, amount, normalized_category, description, timestamp))
        self.conn.commit()
        
        return {
            "status": "success", 
            "message": "Expense added.",
            "data": {
                "date": date,
                "amount": amount,
                "category": normalized_category
            }
        }

    def get_status(self) -> Dict[str, Any]:
        """Check status of expense logging (e.g., did I log today?)."""
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM expenses WHERE date = ?", (today,))
        count = cursor.fetchone()[0]
        
        logging_active = count > 0
        
        # Missing days logic (simple check for previous days with 0 entries?)
        # Let's check last 7 days
        missing_count = 0
        for i in range(1, 8):
            day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            cursor.execute("SELECT COUNT(*) FROM expenses WHERE date = ?", (day,))
            if cursor.fetchone()[0] == 0:
                missing_count += 1
                
        return {
            "today_logged": logging_active,
            "missing_days_count": missing_count,
            "last_7_day_streak": missing_count == 0,
        }

    def get_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate expense report for a date range."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT category, SUM(amount) 
            FROM expenses 
            WHERE date >= ? AND date <= ?
            GROUP BY category
        """, (start_date, end_date))
        
        rows = cursor.fetchall()
        breakdown = {row[0]: row[1] for row in rows}
        
        total = sum(breakdown.values())
        
        # Highest Category
        highest_cat = max(breakdown, key=breakdown.get) if breakdown else None
        
        # Average per day
        # Critical: Must use full calendar range, not just spending days.
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        days = (end - start).days + 1
        avg = total / days if days > 0 else 0
        
        return {
            "total": total,
            "breakdown": breakdown,
            "highest_category": highest_cat,
            "average_per_day": round(avg, 2)
        }
