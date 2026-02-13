from fastmcp import FastMCP
import json
import os
from datetime import datetime

mcp = FastMCP("dsa_prep")

DATA_FILE = "dsa_data.json"


# ===============================
# Safe Load / Save
# ===============================

def load_data():
    file_path = os.path.abspath(DATA_FILE)

    if not os.path.exists(file_path):
        return {"problems": [], "notes": {}}

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except:
        return {"problems": [], "notes": {}}

    data.setdefault("problems", [])
    data.setdefault("notes", {})
    return data


def save_data(data):
    with open(os.path.abspath(DATA_FILE), "w") as f:
        json.dump(data, f, indent=2)


# ===============================
# TOOL 1 — Add problem
# ===============================

@mcp.tool()
def add_problem(topic: str, difficulty: str, title: str) -> dict:
    """Log solved problem"""

    data = load_data()

    data["problems"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "topic": topic,
        "difficulty": difficulty.capitalize(),
        "title": title
    })

    save_data(data)

    return {"status": "saved"}


# ===============================
# TOOL 2 — Revision sheet
# ===============================

@mcp.tool()
def revision_sheet(topic: str = "") -> list:
    """Show problems (all or topic wise)"""

    data = load_data()

    if topic:
        return [p for p in data["problems"] if p["topic"].lower() == topic.lower()]

    return data["problems"]


# ===============================
# TOOL 3 — Progress stats (ALL metrics)
# ===============================

@mcp.tool()
def progress_stats() -> dict:
    """Return complete analytics"""

    data = load_data()
    problems = data["problems"]

    total = len(problems)

    today = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(p["date"] == today for p in problems)

    difficulty = {"Easy": 0, "Medium": 0, "Hard": 0}
    for p in problems:
        difficulty[p["difficulty"]] += 1

    unique_days = len({p["date"] for p in problems}) or 1
    avg_per_day = round(total / unique_days, 2)

    return {
        "total_solved": total,
        "today": today_count,
        "difficulty_breakdown": difficulty,
        "avg_per_day": avg_per_day
    }


# ===============================
# Run server
# ===============================

if __name__ == "__main__":
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8000
    )
