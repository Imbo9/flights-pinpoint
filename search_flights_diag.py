import subprocess, json

results = {}

for extra, label in [([],"no_currency"), (["--currency","EUR"],"with_EUR")]:
    r = subprocess.run(
        ["fli", "flights", "BGY", "TIA", "2026-09-07",
         "--return", "2026-09-15",
         "--format", "json", "--sort", "CHEAPEST"] + extra,
        capture_output=True, text=True, timeout=20
    )
    entry = {"returncode": r.returncode, "stderr": r.stderr[:300]}
    if r.stdout.strip():
        try:
            data = json.loads(r.stdout)
            flights = data.get("flights", [])
            entry["top_level_keys"] = list(data.keys())
            entry["flight_count"] = len(flights)
            if flights:
                f0 = flights[0]
                entry["first_flight_keys"] = list(f0.keys())
                entry["price"] = f0.get("price")
                entry["currency"] = f0.get("currency")
                entry["stops"] = f0.get("stops")
                entry["duration"] = f0.get("duration")
                legs = f0.get("legs", [])
                entry["legs_count"] = len(legs)
                if legs:
                    entry["first_leg"] = legs[0]
                    entry["last_leg"] = legs[-1]
                # capture all non-standard keys
                entry["other_keys"] = {
                    k: str(v)[:300] for k, v in f0.items()
                    if k not in ("price","currency","stops","duration","legs")
                }
        except Exception as e:
            entry["parse_error"] = str(e)
            entry["raw"] = r.stdout[:1000]
    else:
        entry["stdout_empty"] = True
    results[label] = entry

with open("results_diag.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved.")
