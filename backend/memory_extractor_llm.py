import json
from typing import List, Dict


ALLOWED_ACTIONS = {"add", "update"}
ALLOWED_CATEGORIES = {"preference", "goal", "constraint"}


def build_memory_extraction_prompt(user_message: str) -> List[Dict[str, str]]:
    system = (
        "You are a memory extraction engine.\n"
        "Return ONLY valid JSON. No markdown. No explanations.\n"
        "Output must be a JSON array.\n"
        "Each item must be an object with EXACTLY these keys: action, category, text.\n"
        "action must be one of: add, update.\n"
        "category must be one of: preference, goal, constraint.\n\n"
        "Use action=update when the user corrects/changes a previously stated memory.\n\n"
        "Examples:\n"
        "User: 'Remember: my favorite framework is React.'\n"
        "Output: [{\"action\":\"add\",\"category\":\"preference\",\"text\":\"Favorite framework is React\"}]\n\n"
        "User: 'Actually my favorite framework is Next.js now.'\n"
        "Output: [{\"action\":\"update\",\"category\":\"preference\",\"text\":\"Favorite framework is Next.js\"}]\n\n"
        "Rules:\n"
        "- Only store stable long-term facts.\n"
        "- Do NOT store sensitive data (passwords, API keys, addresses, banking, medical info).\n"
        "- If nothing should be stored, output [].\n"
        "- Keep text short (max 120 chars).\n"
    )

    user = f"User message:\n{user_message}\n\nExtract memories now."

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_memory_json(text: str) -> List[Dict[str, str]]:
    text = (text or "").strip()
    data = json.loads(text)

    if not isinstance(data, list):
        return []

    cleaned: List[Dict[str, str]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        action = str(item.get("action", "")).strip().lower()
        category = str(item.get("category", "")).strip().lower()
        mem_text = str(item.get("text", "")).strip()

        if action not in ALLOWED_ACTIONS:
            continue
        if category not in ALLOWED_CATEGORIES:
            continue
        if not mem_text:
            continue

        if len(mem_text) > 120:
            mem_text = mem_text[:120].rstrip()

        cleaned.append({"action": action, "category": category, "text": mem_text})

    # de-dupe
    seen = set()
    out = []
    for x in cleaned:
        key = (x["action"], x["category"], x["text"].lower())
        if key not in seen:
            out.append(x)
            seen.add(key)

    return out