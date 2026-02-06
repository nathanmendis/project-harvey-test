import dateparser
import datetime

print(f"Dateparser version: {dateparser.__version__}")
dates = ["next Monday", "Monday", "tomorrow", "2026-05-20"]
for d in dates:
    res = dateparser.parse(d, settings={'PREFER_DATES_FROM': 'future'})
    print(f"'{d}' -> {res}")
