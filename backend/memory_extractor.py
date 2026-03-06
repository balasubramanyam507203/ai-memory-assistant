import re
from typing import List

#Simple patterns for MVP.
PREFERENCE_PATTERNS = [
    r"\bmy favorite ([a-zA-Z ]+) is ([^.\n]+)",
    r"\bi like ([^.\n]+)",
    r"\bi love ([^.\n]+)",
    r"\bi prefer ([^.\n]+)",
]

GOAL_PATTERNS = [
    r"\bmy goals is to ([^.\n]+)",
    r"\bi want to ([^.\n]+)",
    r"\bi am trying to ([^.\n]+)",
    r"bi need to ([^.\n]+)",
]

def _clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text[:300]  #Keep memories short for MVP

def extract_memories(message: str) -> List[str]:
    msg = (message or "").strip()
    if not msg:
        return []

    candidates: List[str] = []
    lower = msg.lower()

    # Ignore obvious non-memory chatter
    if lower in {"hi", "hello", "thanks", "thank you", "ok", "okay"}:
        return []

    # Preferences
    for pat in PREFERENCE_PATTERNS:
        m = re.search(pat, msg, flags=re.IGNORECASE)
        if not m:
            continue

        # "my favorite X is Y" has 2 groups
        if "favorite" in pat:
            topic = _clean(m.group(1)) if m.lastindex and m.lastindex >= 1 else ""
            value = _clean(m.group(2)) if m.lastindex and m.lastindex >= 2 else ""
            if topic and value:
                candidates.append(f"Preference: favorite {topic} is {value}")
        else:
            # "I like X" has 1 group
            value = _clean(m.group(1)) if m.lastindex and m.lastindex >= 1 else ""
            if value:
                candidates.append(f"Preference: likes {value}")

    # Goals
    for pat in GOAL_PATTERNS:
        m = re.search(pat, msg, flags=re.IGNORECASE)
        if not m:
            continue
        value = _clean(m.group(1)) if m.lastindex and m.lastindex >= 1 else ""
        if value:
            candidates.append(f"Goal: {value}")

    # Deduplicate (case-insensitive)
    deduped = []
    seen = set()
    for c in candidates:
        key = c.lower()
        if key not in seen:
            deduped.append(c)
            seen.add(key)

    return deduped
            
