import re

MISSPELLINGS = {
    "tomorow": "tomorrow",
    "tomorro": "tomorrow",
    "novemeber": "november",
}

def fix_typos(text: str) -> str:
    lowered = text.lower()
    for bad, good in MISSPELLINGS.items():
        lowered = lowered.replace(bad, good)
    return lowered

def normalize_ordinals(text: str) -> str:
    return re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', text, flags=re.IGNORECASE)

def extract_duration(text: str):
    m = re.search(r"(\d+)\s*(hours|hour|hrs|hr|minutes|minute|mins|min)\b", text, re.IGNORECASE)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2).lower()
    return val * 60 if "hour" in unit or "hr" in unit else val
