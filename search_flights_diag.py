import subprocess, json

def raw_search(frm, to, date):
    r = subprocess.run(
        ["fli", "flights", frm, to, date, "--format", "json", "--sort", "CHEAPEST"],
        capture_output=True, text=True, timeout=15
    )
    return {
        "returncode": r.returncode,
        "stdout_len": len(r.stdout),
        "stderr": r.stderr[:200],
        "stdout_head": r.stdout[:600],
    }

tests = [
    ("BGY", "OSL", "2026-09-07"),   # outbound - should work
    ("OSL", "BGY", "2026-09-15"),   # return - testing this
    ("BGY", "TIA", "2026-09-07"),   # outbound known-good
    ("TIA", "BGY", "2026-09-15"),   # return of known-good
    ("MXP", "KEF", "2026-09-07"),   # outbound Iceland
    ("KEF", "MXP", "2026-09-15"),   # return Iceland
    ("BGY", "RVN", "2026-09-07"),   # outbound Rovaniemi
    ("RVN", "BGY", "2026-09-15"),   # return Rovaniemi
]

results = {}
for frm, to, date in tests:
    key = f"{frm}->{to} {date}"
    results[key] = raw_search(frm, to, date)
    print(f"{key}: rc={results[key]['returncode']} stdout_len={results[key]['stdout_len']}")

with open("results_diag.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved.")
