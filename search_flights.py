import subprocess, json
from concurrent.futures import ThreadPoolExecutor, as_completed

ORIGINS = [
    "BGY", "MXP", "LIN", "VCE", "TSF", "BLQ",
    "VRN", "TRN", "GOA", "TRS", "PMF", "VBS", "BZO", "RMI",
]

DESTINATIONS = [
    # Iceland
    "KEF", "AEY", "EGS", "IFJ",
    # Faroe
    "FAE",
    # Norway
    "OSL", "BGO", "TRD", "SVG", "HAU", "BOO", "EVE", "TOS",
    "ALF", "LKL", "KKN", "HFT", "VDS", "MQN", "RRS", "SOG",
    "LKN", "SVJ", "ANX", "LYR",
    # Greenland
    "GOH", "SFJ", "JAV", "UAK", "CNP",
    # Sweden
    "ARN", "GOT", "UME", "SDL", "OSD", "LLA", "KRN", "GEV", "HMV", "VBY",
    # Finland
    "HEL", "OUL", "RVN", "KAO", "IVL", "KTT", "ENF", "JOE", "KAJ", "MHQ",
    # Denmark
    "CPH",
    # Baltics
    "TLL", "RIX", "VNO",
    # Scotland & British Isles
    "EDI", "GLA", "INV", "WIC", "KOI", "LSI", "SYY", "BEB", "ILY", "TRE",
    "SNN", "CFN",
    # Atlantic islands
    "FNC", "PDL", "TER", "HOR", "SMA",
    # Morocco
    "CMN", "RAK", "FEZ", "TNG", "AGA",
    # Turkey
    "IST", "TZX", "VAN", "ERZ",
    # China
    "PEK", "PVG", "CAN", "CTU", "KMG", "LJG", "URC", "XNN", "LXA",
    # Japan
    "NRT", "HND", "KIX", "CTS", "FUK", "AKJ", "KUH", "WKJ", "ISG",
    # Central Asia & Caucasus
    "FRU", "OSS", "TAS", "SKD", "UGC", "NCU", "DYU", "LEN",
    "ALA", "ASB", "GYD", "EVN", "LWN", "TBS", "KUT", "BUS",
    # India Himalayan
    "IXL", "SXR",
    # Nepal, Bhutan, Mongolia
    "KTM", "PBH", "ULN",
    # SE Asia
    "CMB", "RGN", "DPS", "MDC", "BPN", "REP", "LPQ",
    # Patagonia & South America
    "USH", "FTE", "BRC", "PUQ", "PMC", "IQT", "CUZ", "LPB",
    # New Zealand
    "AKL", "CHC", "ZQN", "WLG", "DUD", "ROT",
    # Australia
    "HBA",
    # Canada & Alaska
    "YVR", "YYC", "YXY", "YZF", "YFB", "ANC",
    # Balkans
    "TIA", "TGD", "SKP",
    # East Africa
    "ADD", "NBO", "JRO", "EBB", "ZNZ", "MBA", "LAU",
    # Southern Africa
    "WDH", "CPT", "VFA", "LVI", "MUB", "KGL",
    # Indian Ocean
    "TNR", "RUN", "MRU",
]

DATE = "2026-09-07"

def search(origin, dest):
    try:
        r = subprocess.run(
            ["fli", "flights", origin, dest, DATE, "--format", "json", "--sort", "CHEAPEST"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        data = json.loads(r.stdout)
        # fli returns a dict: {"success": true, "flights": [...], ...}
        if not (isinstance(data, dict) and data.get("success") and data.get("flights")):
            return None
        flights = data["flights"]
        cheapest = min(flights, key=lambda x: x.get("price") or 999999)
        p = cheapest.get("price")
        if not p:
            return None
        legs = cheapest.get("legs", [])
        airlines = list({
            lg.get("airline", {}).get("name", "")
            for lg in legs if lg.get("airline")
        })
        return {
            "origin": origin,
            "destination": dest,
            "price": p,
            "currency": cheapest.get("currency", "USD"),
            "duration_min": cheapest.get("duration"),
            "stops": cheapest.get("stops", 0),
            "airlines": airlines,
            "departure": legs[0].get("departure_time", "") if legs else "",
            "arrival": legs[-1].get("arrival_time", "") if legs else "",
        }
    except Exception as e:
        print(f"Error {origin}->{dest}: {e}")
    return None

pairs = [(o, d) for o in ORIGINS for d in DESTINATIONS]
print(f"Searching {len(pairs)} pairs ({len(ORIGINS)} origins x {len(DESTINATIONS)} destinations)...")

results = []
with ThreadPoolExecutor(max_workers=50) as ex:
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
    print("No results found.")
