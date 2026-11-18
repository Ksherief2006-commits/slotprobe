"""slotwatch core: poll slots, diff against seen state, match subscribers, write outbox.
Stdlib only, Python 3.9+. Notifications are written to an outbox (dry-run); nothing is sent."""
import json, time, urllib.request
from datetime import datetime

API = "https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=%d&locationId=%s&minimum=1"

def fetch_slots(location_id, limit=50, timeout=15):
    req = urllib.request.Request(API % (limit, location_id), headers={"User-Agent": "slotwatch-poc/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    if not isinstance(data, list):
        raise ValueError("unexpected payload shape")  # schema drift -> fail loudly
    for s in data:
        if "startTimestamp" not in s or "locationId" not in s:
            raise ValueError("slot missing required fields")
    return data

def slot_key(s):
    return "%s|%s" % (s["locationId"], s["startTimestamp"])

def new_slots(slots, seen):
    """Return slots not in `seen` (dict key->first_seen_epoch). Mutates seen."""
    out = []
    for s in slots:
        k = slot_key(s)
        if s.get("active", True) and k not in seen:
            seen[k] = int(time.time()); out.append(s)
    return out

def prune_seen(seen, now=None, max_age=14 * 86400):
    now = now or int(time.time())
    for k in [k for k, t in seen.items() if now - t > max_age]:
        del seen[k]

def matches(sub, slot):
    if str(slot["locationId"]) not in map(str, sub["locations"]):
        return False
    start = datetime.strptime(slot["startTimestamp"], "%Y-%m-%dT%H:%M")
    if "not_before" in sub and start < datetime.strptime(sub["not_before"], "%Y-%m-%d"): return False
    if "not_after" in sub and start > datetime.strptime(sub["not_after"], "%Y-%m-%d"): return False
    return True

def build_messages(subs, slots, max_per_sub=3):
    """One message per subscriber per run (digest), capped, to avoid alert floods."""
    msgs = []
    for sub in subs:
        hit = sorted((s for s in slots if matches(sub, s)), key=lambda s: s["startTimestamp"])
        if hit:
            lines = ["%s (loc %s)" % (s["startTimestamp"], s["locationId"]) for s in hit[:max_per_sub]]
            more = len(hit) - len(lines)
            body = "New slots: " + "; ".join(lines) + ("; +%d more" % more if more > 0 else "")
            msgs.append({"to": sub["id"], "channel": sub.get("channel", "email"), "body": body})
    return msgs

def run_once(subs, state, fetcher=fetch_slots):
    """state = {'seen': {...}, 'errors': {loc: n}}. Per-location failure isolation."""
    state.setdefault("seen", {}); state.setdefault("errors", {})
    prune_seen(state["seen"])
    fresh = []
    for loc in sorted({str(l) for s in subs for l in s["locations"]}):
        try:
            fresh += new_slots(fetcher(loc), state["seen"]); state["errors"][loc] = 0
        except Exception:
            state["errors"][loc] = state["errors"].get(loc, 0) + 1
    health = [l for l, n in state["errors"].items() if n >= 3]  # operator alarm
    return build_messages(subs, fresh), health
