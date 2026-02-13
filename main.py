from fastmcp import FastMCP
import os
import aiosqlite
import sqlite3
import logging
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DSAPrepPro")

# PRODUCTION FIX: Use a writable directory for the database.
# Ensures the server works even if the deployment root is read-only.
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(TEMP_DIR, "dsa_prep_prod.db"))

# Initialize FastMCP Server object
mcp = FastMCP("DSA_Prep_Pro")

# --- Database Schema Setup ---
def init_db() -> None:
    """Initializes the SQLite schema with high-concurrency settings (WAL mode)."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # WAL mode is critical for remote/production servers to prevent locking
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Problems Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS problems(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    solve_date DATE DEFAULT CURRENT_DATE
                )
            """)
            
            # Revision Notes Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info(f"✅ DSA Database initialized at: {DB_PATH}")
    except Exception as e:
        logger.error(f"❌ DB Init Failed: {e}")
        raise

# Ensure DB is ready on startup
init_db()

# --- MCP Tools (Foundry Optimized) ---

@mcp.tool()
async def add_problem(title: str, topic: str, difficulty: str) -> Dict[str, Any]:
    """
    Logs a solved DSA problem into the tracking system.
    
    Args:
        title: The name of the problem (e.g., 'Two Sum').
        topic: The data structure or algorithm category (e.g., 'Arrays').
        difficulty: The complexity level ('Easy', 'Medium', 'Hard').
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO problems (title, topic, difficulty) VALUES (?, ?, ?)",
                (title, topic, difficulty.capitalize())
            )
            await db.commit()
            return {"status": "success", "id": cursor.lastrowid, "message": f"Logged {title}"}
    except Exception as e:
        logger.error(f"Add Problem Error: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def get_revision_sheet(topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves a list of solved problems, optionally filtered by topic.
    
    Args:
        topic: Optional filter for a specific category (e.g., 'Graphs').
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if topic:
                query = "SELECT * FROM problems WHERE topic LIKE ? ORDER BY solve_date DESC"
                params = (f"%{topic}%",)
            else:
                query = "SELECT * FROM problems ORDER BY solve_date DESC"
                params = ()

            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()
                return {"problems": [dict(row) for row in rows]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def get_progress_stats() -> Dict[str, Any]:
    """
    Calculates preparation analytics including difficulty breakdown and daily averages.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Get Difficulty Counts
            async with db.execute("SELECT difficulty, COUNT(*) as count FROM problems GROUP BY difficulty") as cur:
                difficulty_data = {row["difficulty"]: row["count"] for row in await cur.fetchall()}
            
            # Get Total and Today's Count
            today = datetime.now().strftime("%Y-%m-%d")
            async with db.execute("SELECT COUNT(*) as total, SUM(CASE WHEN solve_date = ? THEN 1 ELSE 0 END) as today FROM problems", (today,)) as cur:
                counts = await cur.fetchone()
                
            return {
                "total_solved": counts["total"] or 0,
                "solved_today": counts["today"] or 0,
                "breakdown": difficulty_data
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def save_revision_note(topic: str, content: str) -> Dict[str, str]:
    """
    Saves or updates key learning notes for a specific DSA topic.
    
    Args:
        topic: The category title (e.g., 'Recursion Tips').
        content: The actual study notes or patterns to remember.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO notes (topic, content, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(topic) DO UPDATE SET 
                    content=excluded.content, 
                    updated_at=excluded.updated_at
            """, (topic, content))
            await db.commit()
            return {"status": "success", "message": f"Notes updated for {topic}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Entry Point ---
if __name__ == "__main__":
    # Use environment port for cloud providers (Railway, Render, etc.)
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="sse", host="0.0.0.0", port=port)