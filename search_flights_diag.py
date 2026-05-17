import subprocess, json

# Test round-trip raw structure and currency flag
for extra in [[], ["--currency", "EUR"]]:
    label = "EUR" if extra else "USD_default"
    r = subprocess.run(
        ["fli", "flights", "BGY", "TIA", "2026-09-07", "--return", "2026-09-15",
         "--format", "json", "--sort", "CHEAPEST"] + extra,
        capture_output=True, text=True, timeout=20
    )
    print(f"\n=== Round-trip BGY->TIA ({label}) rc={r.returncode} ===")
    if r.stdout.strip():
        data = json.loads(r.stdout)
        # Print top-level keys
        print("Top keys:", list(data.keys()))
        flights = data.get("flights", [])
        if flights:
            f0 = flights[0]
            print("First flight keys:", list(f0.keys()))
            print("price:", f0.get("price"))
            print("currency:", f0.get("currency"))
            print("stops:", f0.get("stops"))
            print("duration:", f0.get("duration"))
            print("legs count:", len(f0.get("legs", [])))
            legs = f0.get("legs", [])
            if legs:
                print("First leg keys:", list(legs[0].keys()))
                print("First leg:", json.dumps(legs[0], indent=2)[:400])
            # Check for other keys that might contain segments
            for k, v in f0.items():
                if k not in ("price", "currency", "stops", "duration", "legs"):
                    print(f"  other key '{k}':", str(v)[:200])
    print("stderr:", r.stderr[:100] or "(none)")

with open("results_diag.json", "w") as f:
    json.dump({"done": True}, f)
