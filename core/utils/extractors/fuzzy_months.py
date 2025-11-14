import re, difflib

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]
MONTH_ABB = {m[:3]: m for m in MONTHS}

def fuzzy_fix_months(text: str) -> str:
    t = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    t = re.sub(r'([A-Za-z])(\d)', r'\1 \2', t)

    tokens = t.split()
    output = []

    for tok in tokens:
        cleaned = re.sub(r'[^A-Za-z]', '', tok).lower()
        if not cleaned:
            output.append(tok)
            continue

        if 2 <= len(cleaned) <= 6:
            abb = cleaned[:3]
            if abb in MONTH_ABB:
                output.append(MONTH_ABB[abb])
                continue

            match = difflib.get_close_matches(cleaned, MONTHS, n=1, cutoff=0.6)
            if match:
                output.append(match[0])
                continue

        output.append(tok)

    return " ".join(output)
