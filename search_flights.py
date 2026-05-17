import subprocess, json
from concurrent.futures import ThreadPoolExecutor, as_completed

# All commercial airports in North Italy (Bologna northwards)
ORIGINS = [
    "BGY",  # Milan Bergamo Orio al Serio
    "MXP",  # Milan Malpensa
    "LIN",  # Milan Linate
    "VCE",  # Venice Marco Polo
    "TSF",  # Venice Treviso
    "BLQ",  # Bologna
    "VRN",  # Verona
    "TRN",  # Turin
    "GOA",  # Genoa
    "TRS",  # Trieste
    "PMF",  # Parma
    "VBS",  # Brescia Montichiari
    "BZO",  # Bolzano
    "RMI",  # Rimini
]
DESTINATIONS = [
    "KEF", "FAE",
    "OSL", "BGO", "TRD", "TOS", "SVG", "BOO", "EVE", "LYR",
    "ARN", "GOT", "UME", "LLA", "KRN",
    "HEL", "OUL", "RVN", "KAO", "IVL",
    "CPH", "GOH",
    "EDI", "GLA", "INV", "SNN",
    "FNC", "PDL", "TER", "HOR", "SMA",
    "CMN", "RAK", "FEZ", "TNG", "AGA",
    "PEK", "PVG", "CAN", "CTU", "KMG", "URC",
    "NRT", "HND", "KIX", "CTS", "FUK",
    "FRU", "TAS", "DYU", "ALA", "GYD", "EVN", "TBS",
    "KTM", "PBH", "ULN",
    "USH", "PUQ", "PMC",
    "AKL", "CHC", "ZQN",
    "YVR", "YYC", "ANC",
    "TIA", "TGD", "SKP",
    "ADD", "NBO", "JRO", "EBB",
]
DATE = "2026-09-07"

def search(origin, dest):
    try:
        r = subprocess.run(
            ["fli", "flights", origin, dest, DATE, "--format", "json", "--sort", "CHEAPEST"],
            capture_output=True, text=True, timeout=25
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            if isinstance(data, list) and data:
                cheapest = min(data, key=lambda x: x.get("price") or 999999)
                p = cheapest.get("price")
                if p:
                    legs = cheapest.get("legs", [])
                    return {
                        "origin": origin,
                        "destination": dest,
                        "price": p,
                        "currency": cheapest.get("currency", "EUR"),
                        "duration_min": cheapest.get("duration"),
                        "stops": cheapest.get("stops", 0),
                        "airlines": list({lg.get("airline", "") for lg in legs if lg.get("airline")}),
                        "departure": legs[0].get("departure_datetime", "") if legs else "",
                        "arrival": legs[-1].get("arrival_datetime", "") if legs else "",
                    }
    except Exception as e:
        print(f"Error {origin}->{dest}: {e}")
    return None

pairs = [(o, d) for o in ORIGINS for d in DESTINATIONS]
results = []

print(f"Searching {len(pairs)} origin-destination pairs ({len(ORIGINS)} origins x {len(DESTINATIONS)} destinations)...")

with ThreadPoolExecutor(max_workers=30) as ex:
    futures = {ex.submit(search, o, d): (o, d) for o, d in pairs}
    for f in as_completed(futures):
        res = f.result()
        if res:
            results.append(res)
            print(f"  Found: {res['origin']}->{res['destination']} {res['currency']}{res['price']}")

seen = {}
for r in sorted(results, key=lambda x: x["price"]):
    key = (r["origin"], r["destination"])
    if key not in seen:
        seen[key] = r

top20 = sorted(seen.values(), key=lambda x: x["price"])[:20]

with open("results.json", "w") as f:
    json.dump({"top20": top20, "total_routes": len(seen)}, f, indent=2)

print(f"\nDone. {len(seen)} routes found.")
if top20:
    print(f"Cheapest: {top20[0]['origin']}->{top20[0]['destination']} {top20[0]['currency']}{top20[0]['price']}")
else:
    print("No results found - Google may be blocking GitHub runner IPs.")
