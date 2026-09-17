"""COROS -> data/ synchronization.

Pulls all key datasets from the COROS MCP server and saves them into
data/ with real newlines. Run any time:  python coros_sync.py
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
AUTH = os.path.join(HERE, "..", "data")
os.makedirs(AUTH, exist_ok=True)

tokens = json.load(open(os.path.join(HERE, "coros-auth.json"), encoding="utf-8"))
HDRS = {"Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"}
SID = [0]


def rpc(method, params):
    SID[0] += 1
    body = json.dumps({"jsonrpc": "2.0", "id": SID[0], "method": method,
                       "params": params}).encode()
    req = urllib.request.Request("https://mcp.coros.com/mcp", data=body, headers=HDRS)
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode()
        for line in raw.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:])
        return json.loads(raw)


def call(tool, args):
    res = rpc("tools/call", {"name": tool, "arguments": args})
    txt = res["result"]["content"][0]["text"]
    return txt.replace(chr(92) + "n", chr(10))  # server sends escaped newlines


def save(name, txt):
    path = os.path.join(AUTH, name + ".txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    return path


rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "zcode-sync", "version": "1.0"}})

CALLS = {
    "daily_health":      ("queryDailyHealthData", {"days": 14}),
    "resting_hr":        ("queryRestingHeartRate", {"days": 14}),
    "sleep_hrv":         ("querySleepHrv", {"days": 7}),
    "stress":            ("queryStressLevel", {"days": 14}),
    "avg_hr":            ("queryAvgHeartRate", {"days": 14}),
    "fitness_assessment": ("queryFitnessAssessmentOverview", {}),
    "training_load":     ("queryTrainingLoadAssessment", {}),
    "recovery":          ("queryRecoveryStatus", {}),
    "training_schedule": ("queryTrainingSchedule", {}),
}

saved = []
for name, (tool, args) in CALLS.items():
    try:
        saved.append(save(name, call(tool, args)))
        print(f"ok   {name}")
    except Exception as e:
        print(f"ERR  {name}: {str(e)[:80]}")

# sport records in 2-month chunks to dodge the 20-records cap
all_lines, seen = [], set()
y, m = 2024, 12
while (y, m) <= (2026, 9):
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    start, end = f"{y}{m:02d}01", f"{ny}{nm:02d}01"
    try:
        t = call("querySportRecords", {"startDate": start, "endDate": end})
        all_lines.append(t)
        for lbl in t.split("LabelId: ")[1:]:
            seen.add(lbl.split()[0])
    except Exception as e:
        print(f"ERR  sport {start}: {str(e)[:60]}")
    y, m = ny, nm

full = chr(10).join(all_lines)
save("sport_records_full", full)
print(f"ok   sport_records_full ({len(seen)} unique sessions)")
print(f"\nSynced {len(saved) + 1} files into data/")
