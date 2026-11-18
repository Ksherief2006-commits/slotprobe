"""Poll each location once, append CSV rows. No notifications. Exit 0 always (failures are data)."""
import csv, json, os, sys, time, urllib.error
from datetime import datetime, timezone
from core import fetch_slots

FIELDS = ["utc_time", "location_id", "http_status", "latency_ms", "slots_returned", "earliest_slot", "error"]

def probe_one(loc, fetcher=fetch_slots):
    t0 = time.time(); row = {"location_id": loc, "http_status": 200, "slots_returned": 0, "earliest_slot": "", "error": ""}
    try:
        slots = fetcher(loc)
        row["slots_returned"] = len(slots)
        if slots: row["earliest_slot"] = min(s["startTimestamp"] for s in slots)
    except urllib.error.HTTPError as e:
        row["http_status"] = e.code; row["error"] = "HTTPError"
    except Exception as e:
        row["http_status"] = 0; row["error"] = type(e).__name__
    row["latency_ms"] = int((time.time() - t0) * 1000)
    row["utc_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return row

def main(loc_path, csv_path, fetcher=fetch_slots):
    locs = json.load(open(loc_path)); new = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new: w.writeheader()
        for loc in locs:
            w.writerow(probe_one(loc, fetcher)); time.sleep(1)  # be polite: 1 req/sec
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
