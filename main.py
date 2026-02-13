from fastmcp import FastMCP
import json
import os
from datetime import datetime

mcp = FastMCP("dsa_prep")

DATA_FILE = "categories.json"


# ===============================
# Init JSON file
# ===============================

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"problems": [], "notes": {}}, f)


def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ===============================
# TOOL 1 — Add problem
# ===============================

@mcp.tool()
def add_problem(topic: str, difficulty: str, title: str) -> dict:
    data = load_data()

    data["problems"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "topic": topic,
        "difficulty": difficulty,
        "title": title
    })

    save_data(data)

    return {"status": "saved", "title": title}


# ===============================
# TOOL 2 — Generate notes (Claude writes content)
# ===============================

@mcp.tool()
def generate_notes(topic: str) -> dict:
    """
    Claude will generate notes using this instruction
    """

    prompt = f"""
    Create concise DSA notes for {topic}.
    Include:
    - concept
    - patterns
    - complexity
    - common interview questions
    """

    return {"instruction": prompt}


# ===============================
# TOOL 3 — Revision sheet
# ===============================

@mcp.tool()
def revision_sheet(topic: str = "") -> list:
    data = load_data()

    problems = data["problems"]

    if topic:
        problems = [p for p in problems if p["topic"] == topic]

    return problems


# ===============================
# Optional resource
# ===============================

@mcp.resource("dsa://stats")
def stats():
    data = load_data()
    return json.dumps({"total_solved": len(data["problems"])}, indent=2)


# ===============================
# Run server
# ===============================

if __name__ == "__main__":
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=8000
    )
