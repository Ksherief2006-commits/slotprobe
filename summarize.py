"""Day-7 report for kill criteria 1 and 3, from the CSV. Usage: python3 summarize.py data.csv"""
import csv, statistics, sys
from collections import defaultdict

def summarize(path, low=5):
    rows = list(csv.DictReader(open(path)))
    ok = [r for r in rows if r["http_status"] == "200"]
    pct = 100.0 * len(ok) / len(rows) if rows else 0.0
    days_blocked = defaultdict(lambda: [0, 0])  # day -> [ok, total]
    for r in rows:
        d = r["utc_time"][:10]; days_blocked[d][1] += 1; days_blocked[d][0] += r["http_status"] == "200"
    dead_days = sorted(d for d, (o, t) in days_blocked.items() if o == 0)
    per_loc = defaultdict(lambda: defaultdict(list))
    for r in ok: per_loc[r["location_id"]][r["utc_time"][:10]].append(int(r["slots_returned"]))
    scarce = []
    for loc, days in per_loc.items():
        scarce_days = sum(1 for v in days.values() if statistics.median(v) < low)
        if days and scarce_days > len(days) / 2: scarce.append(loc)
    return {"runs": len(rows), "pct_200": round(pct, 1), "fully_blocked_days": dead_days,
            "scarce_locations": sorted(scarce),
            "criterion1_pass": pct >= 95, "criterion3_pass": len(scarce) >= 3}

if __name__ == "__main__":
    print(summarize(sys.argv[1]))
