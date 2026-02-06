import dateparser
import datetime

print(f"Dateparser version: {dateparser.__version__}")
dates = ["next Monday", "Monday", "tomorrow", "in 2 days"]
for d in dates:
    res = dateparser.parse(d, settings={'PREFER_DATES_FROM': 'future'}, languages=['en'])
    print(f"'{d}' -> {res}")
