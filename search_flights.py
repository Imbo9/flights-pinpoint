import subprocess, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product

USD_TO_EUR = 0.92

ORIGINS = [
    "BGY", "MXP", "LIN", "VCE", "TSF", "BLQ",
    "VRN", "TRN", "GOA", "TRS", "PMF", "VBS", "BZO", "RMI",
]

DESTINATIONS = [
    "KEF", "AEY", "EGS", "IFJ", "FAE",
    "OSL", "BGO", "TRD", "SVG", "HAU", "BOO", "EVE", "TOS",
    "ALF", "LKL", "KKN", "HFT", "VDS", "MQN", "RRS", "SOG",
    "LKN", "SVJ", "ANX", "LYR",
    "GOH", "SFJ", "JAV", "UAK", "CNP",
    "ARN", "GOT", "UME", "SDL", "OSD", "LLA", "KRN", "GEV", "HMV", "VBY",
    "HEL", "OUL", "RVN", "KAO", "IVL", "KTT", "ENF", "JOE", "KAJ", "MHQ",
    "CPH",
    "TLL", "RIX", "VNO",
    "EDI", "GLA", "INV", "WIC", "KOI", "LSI", "SYY", "BEB", "ILY", "TRE",
    "SNN", "CFN",
    "FNC", "PDL", "TER", "HOR", "SMA",
    "CMN", "RAK", "FEZ", "TNG", "AGA",
    "IST", "TZX", "VAN", "ERZ",
    "PEK", "PVG", "CAN", "CTU", "KMG", "LJG", "URC", "XNN", "LXA",
    "NRT", "HND", "KIX", "CTS", "FUK", "AKJ", "KUH", "WKJ", "ISG",
    "FRU", "OSS", "TAS", "SKD", "UGC", "NCU", "DYU", "LEN",
    "ALA", "ASB", "GYD", "EVN", "LWN", "TBS", "KUT", "BUS",
    "IXL", "SXR",
    "KTM", "PBH", "ULN",
    "CMB", "RGN", "DPS", "MDC", "BPN", "REP", "LPQ",
    "USH", "FTE", "BRC", "PUQ", "PMC", "IQT", "CUZ", "LPB",
    "AKL", "CHC", "ZQN", "WLG", "DUD", "ROT",
    "HBA",
    "YVR", "YYC", "YXY", "YZF", "YFB", "ANC",
    "TIA", "TGD", "SKP",
    "ADD", "NBO", "JRO", "EBB", "ZNZ", "MBA", "LAU",
    "WDH", "CPT", "VFA", "LVI", "MUB", "KGL",
    "TNR", "RUN", "MRU",
]

DEP_DATE = "2026-09-07"  # outbound
RET_DATE = "2026-09-15"  # return

def search_oneway(origin, dest, date):
    try:
        r = subprocess.run(
            ["fli", "flights", origin, dest, date,
             "--format", "json", "--sort", "CHEAPEST"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0 or not r.stdout.strip():
            return None
        data = json.loads(r.stdout)
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
            "price_usd": p,
            "price_eur": round(p * USD_TO_EUR, 0),
            "duration_min": cheapest.get("duration"),
            "stops": cheapest.get("stops", 0),
            "airlines": airlines,
            "departure": legs[0].get("departure_time", "") if legs else "",
            "arrival": legs[-1].get("arrival_time", "") if legs else "",
        }
    except Exception as e:
        return None

# Build all search tasks: outbound (IT->DEST) and return (DEST->IT)
out_tasks  = [(o, d, DEP_DATE, "out")  for o in ORIGINS for d in DESTINATIONS]
ret_tasks  = [(d, o, RET_DATE, "ret")  for o in ORIGINS for d in DESTINATIONS]
all_tasks  = out_tasks + ret_tasks

print(f"Searching {len(all_tasks)} one-way legs "
      f"({len(ORIGINS)} origins x {len(DESTINATIONS)} dests x 2 directions)...")

# out_prices[origin][dest] = flight_info
# ret_prices[dest][origin] = flight_info  (dest->origin on return date)
out_prices = {o: {} for o in ORIGINS}
ret_prices = {d: {} for d in DESTINATIONS}

with ThreadPoolExecutor(max_workers=50) as ex:
    futures = {
        ex.submit(search_oneway, frm, to, date): (frm, to, direction)
        for frm, to, date, direction in all_tasks
    }
    for f in as_completed(futures):
        frm, to, direction = futures[f]
        res = f.result()
        if res:
            if direction == "out":
                out_prices[frm][to] = res
                print(f"  OUT {frm}->{to} EUR{res['price_eur']}")
            else:
                # frm=dest, to=origin
                if frm not in ret_prices:
                    ret_prices[frm] = {}
                ret_prices[frm][to] = res
                print(f"  RET {frm}->{to} EUR{res['price_eur']}")

# Find cheapest open-jaw per destination:
# for each dest, try all (origin_out, origin_ret) combinations
best = {}  # dest -> best combo

for dest in DESTINATIONS:
    for orig_out, orig_ret in product(ORIGINS, ORIGINS):
        out_flight = out_prices.get(orig_out, {}).get(dest)
        ret_flight = ret_prices.get(dest, {}).get(orig_ret)
        if not out_flight or not ret_flight:
            continue
        total_eur = out_flight["price_eur"] + ret_flight["price_eur"]
        if dest not in best or total_eur < best[dest]["total_eur"]:
            best[dest] = {
                "destination": dest,
                "origin_out": orig_out,
                "origin_ret": orig_ret,
                "open_jaw": orig_out != orig_ret,
                "total_eur": total_eur,
                "outbound": {
                    "from": orig_out, "to": dest,
                    "date": DEP_DATE,
                    "price_eur": out_flight["price_eur"],
                    "duration_min": out_flight["duration_min"],
                    "stops": out_flight["stops"],
                    "airlines": out_flight["airlines"],
                    "departure": out_flight["departure"],
                    "arrival": out_flight["arrival"],
                },
                "return": {
                    "from": dest, "to": orig_ret,
                    "date": RET_DATE,
                    "price_eur": ret_flight["price_eur"],
                    "duration_min": ret_flight["duration_min"],
                    "stops": ret_flight["stops"],
                    "airlines": ret_flight["airlines"],
                    "departure": ret_flight["departure"],
                    "arrival": ret_flight["arrival"],
                },
            }

top40 = sorted(best.values(), key=lambda x: x["total_eur"])[:40]

with open("results.json", "w") as f:
    json.dump({
        "top40": top40,
        "total_destinations": len(best),
        "note": f"Open-jaw optimized. Outbound {DEP_DATE}, return {RET_DATE}. USD->EUR x0.92."
    }, f, indent=2)

print(f"\nDone. {len(best)} destinations with complete itineraries.")
if top40:
    t = top40[0]
    jaw = f"{t['origin_out']}->" if t['open_jaw'] else ""
    print(f"Cheapest: {jaw}{t['destination']}->{t['origin_ret']} EUR{t['total_eur']}")
else:
    print("No complete itineraries found.")
