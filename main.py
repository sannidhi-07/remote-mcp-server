from fastmcp import FastMCP
import os
import aiosqlite
import sqlite3
import tempfile
import json

# ===============================
# Configuration
# ===============================

# Use a persistent path if you want data to survive a reboot, 
# otherwise tempfile.gettempdir() works for ephemeral testing.
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

# Path to categories.json relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")

print(f"🚀 Starting Expense Tracker")
print(f"📁 Database path: {DB_PATH}")

# MCP Name: simple, lowercase, no spaces
mcp = FastMCP("expense_tracker")

# ===============================
# Database Initialization (Sync)
# ===============================

def init_db() -> None:
    try:
        # We use standard sqlite3 for the initial table setup
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")  # Critical for concurrent access
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        raise

init_db()

# ===============================
# MCP TOOLS (STRICT TYPES)
# ===============================

@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
) -> dict:
    """
    Add a new expense entry.
    date format: YYYY-MM-DD
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                INSERT INTO expenses(date, amount, category, subcategory, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, amount, category, subcategory, note),
            )
            await db.commit()

            return {
                "status": "success",
                "id": cursor.lastrowid,
                "message": "Expense added successfully"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to add expense: {str(e)}"
        }

@mcp.tool()
async def list_expenses(
    start_date: str,
    end_date: str
) -> list:
    """
    List expenses between start_date and end_date (inclusive).
    Date format: YYYY-MM-DD
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date),
            )

            rows = await cursor.fetchall()
            columns = [col[0] for col in cursor.description]

            return [dict(zip(columns, row)) for row in rows]

    except Exception as e:
        return [{"status": "error", "message": str(e)}]

@mcp.tool()
async def summarize_expenses(
    start_date: str,
    end_date: str,
    category: str = ""
) -> list:
    """
    Summarize expenses grouped by category.
    Date format: YYYY-MM-DD
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            columns = [col[0] for col in cursor.description]

            return [dict(zip(columns, row)) for row in rows]

    except Exception as e:
        return [{"status": "error", "message": str(e)}]

# ===============================
# MCP RESOURCE
# ===============================

@mcp.resource("expense://categories")
def categories() -> str:
    """
    Return available expense categories.
    """
    default_categories = {
        "categories": [
            "Food & Dining", "Transportation", "Shopping", 
            "Entertainment", "Bills & Utilities", "Healthcare", 
            "Travel", "Education", "Business", "Other"
        ]
    }

    try:
        if os.path.exists(CATEGORIES_PATH):
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Resource error: {str(e)}"})

# ===============================
# Run Server
# ===============================

if __name__ == "__main__":
    # SSE is the standard for remote MCP over HTTP
    # Host 0.0.0.0 allows external connections
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8000
    )