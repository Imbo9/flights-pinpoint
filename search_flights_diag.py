import subprocess, json

ORIGIN = "MXP"
DATE = "2026-09-07"
tests = [
    ("MXP", "OSL"),  # common route, should exist
    ("MXP", "KEF"),  # Iceland
    ("BGY", "TLL"),  # Bergamo -> Tallinn
]

diag = {}
for origin, dest in tests:
    r = subprocess.run(
        ["fli", "flights", origin, dest, DATE, "--format", "json", "--sort", "CHEAPEST"],
        capture_output=True, text=True, timeout=15
    )
    diag[f"{origin}->{dest}"] = {
        "returncode": r.returncode,
        "stdout_raw": r.stdout[:2000],
        "stderr_raw": r.stderr[:500],
    }
    print(f"=== {origin}->{dest} rc={r.returncode} ===")
    print("STDOUT:", r.stdout[:500] or "(empty)")
    print("STDERR:", r.stderr[:200] or "(empty)")

# Also test without --format json
r2 = subprocess.run(
    ["fli", "flights", "MXP", "OSL", DATE],
    capture_output=True, text=True, timeout=15
)
diag["MXP->OSL_no_json"] = {
    "returncode": r2.returncode,
    "stdout_raw": r2.stdout[:2000],
    "stderr_raw": r2.stderr[:500],
}
print("=== MXP->OSL (no --format json) ===")
print("STDOUT:", r2.stdout[:500] or "(empty)")
print("STDERR:", r2.stderr[:200] or "(empty)")

# Test fli --version
rv = subprocess.run(["fli", "--version"], capture_output=True, text=True)
diag["fli_version"] = rv.stdout.strip() or rv.stderr.strip()
print("fli version:", diag["fli_version"])

with open("results_diag.json", "w") as f:
    json.dump(diag, f, indent=2)
print("Saved results_diag.json")
