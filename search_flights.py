import subprocess, json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Approximate USD->EUR rate (May 2026)
USD_TO_EUR = 0.92

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

DEP_DATE = "2026-09-07"
RET_DATE = "2026-09-15"

def get_legs_info(flight):
    """Extract airline, departure and arrival from outbound/return structure."""
    outbound = flight.get("outbound", {})
    ret = flight.get("return", {})
    out_legs = outbound.get("legs", [])
    ret_legs = ret.get("legs", [])
    airlines = list({
        lg.get("airline", {}).get("name", "")
        for legs in (out_legs, ret_legs)
        for lg in legs
        if lg.get("airline")
    })
    departure = out_legs[0].get("departure_time", "") if out_legs else ""
    arrival = ret_legs[-1].get("arrival_time", "") if ret_legs else ""
    out_stops = outbound.get("stops", 0)
    ret_stops = ret.get("stops", 0)
    return airlines, departure, arrival, out_stops, ret_stops

def search(origin, dest):
    try:
        r = subprocess.run(
            ["fli", "flights", origin, dest, DEP_DATE,
             "--return", RET_DATE,
             "--format", "json", "--sort", "CHEAPEST"],
            capture_output=True, text=True, timeout=12
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        data = json.loads(r.stdout)
        if not (isinstance(data, dict) and data.get("success") and data.get("flights")):
            return None
        flights = data["flights"]
        cheapest = min(flights, key=lambda x: x.get("price") or 999999)
        p_usd = cheapest.get("price")
        if not p_usd:
            return None
        p_eur = round(p_usd * USD_TO_EUR, 0)
        airlines, departure, arrival, out_stops, ret_stops = get_legs_info(cheapest)
        return {
            "origin": origin,
            "destination": dest,
            "price_eur": p_eur,
            "price_usd": p_usd,
            "duration_min": cheapest.get("duration"),
            "outbound_stops": out_stops,
            "return_stops": ret_stops,
            "airlines": airlines,
            "outbound_dep": departure,
            "return_arr": arrival,
        }
    except Exception as e:
        print(f"Error {origin}->{dest}: {e}")
    return None

pairs = [(o, d) for o in ORIGINS for d in DESTINATIONS]
print(f"Searching {len(pairs)} round-trip pairs ({DEP_DATE} -> {RET_DATE}), converting to EUR...")

results = []
with ThreadPoolExecutor(max_workers=50) as ex:
    futures = {ex.submit(search, o, d): (o, d) for o, d in pairs}
    for f in as_completed(futures):
        res = f.result()
        if res:
            results.append(res)
            print(f"  Found: {res['origin']}->{res['destination']} EUR{res['price_eur']}")

seen = {}
for r in sorted(results, key=lambda x: x["price_eur"]):
    key = (r["origin"], r["destination"])
    if key not in seen:
        seen[key] = r

top40 = sorted(seen.values(), key=lambda x: x["price_eur"])[:40]

with open("results.json", "w") as f:
    json.dump({"top40": top40, "total_routes": len(seen),
               "note": "Round-trip prices. USD converted to EUR at 0.92 rate."}, f, indent=2)

print(f"\nDone. {len(seen)} routes found.")
if top40:
    print(f"Cheapest: {top40[0]['origin']}->{top40[0]['destination']} EUR{top40[0]['price_eur']}")
else:
    print("No results found.")
