import subprocess, json, random
from concurrent.futures import ThreadPoolExecutor, as_completed

USD_TO_EUR = 0.92

ORIGINS = ["BGY", "MXP", "LIN", "VCE", "TSF", "BLQ",
           "VRN", "TRN", "GOA", "TRS", "PMF", "VBS", "BZO", "RMI"]

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

DEP_DATE = "2026-09-07"
RET_DATE = "2026-09-15"

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
        airlines = list({lg.get("airline", {}).get("name", "") for lg in legs if lg.get("airline")})
        return {
            "price_usd": p,
            "price_eur": round(p * USD_TO_EUR, 0),
            "duration_min": cheapest.get("duration"),
            "stops": cheapest.get("stops", 0),
            "airlines": airlines,
            "departure": legs[0].get("departure_time", "") if legs else "",
            "arrival": legs[-1].get("arrival_time", "") if legs else "",
        }
    except Exception:
        return None

# Interlace out/ret tasks so both directions get equal Google quota
out_tasks = [(o, d, DEP_DATE, "out") for o in ORIGINS for d in DESTINATIONS]
ret_tasks = [(d, o, RET_DATE, "ret") for o in ORIGINS for d in DESTINATIONS]
all_tasks = [t for pair in zip(out_tasks, ret_tasks) for t in pair]
random.shuffle(all_tasks)  # further randomise to avoid burst patterns

print(f"Searching {len(all_tasks)} legs interlaced (out+ret), max_workers=30...")

out_prices = {o: {} for o in ORIGINS}
ret_prices = {d: {} for d in DESTINATIONS}
all_results = []

with ThreadPoolExecutor(max_workers=30) as ex:  # 30 instead of 50 to reduce burst
    futures = {ex.submit(search_oneway, frm, to, date): (frm, to, direction)
               for frm, to, date, direction in all_tasks}
    for f in as_completed(futures):
        frm, to, direction = futures[f]
        res = f.result()
        if res:
            all_results.append((frm, to, direction, res))

# Process results sequentially (no concurrency issues)
for frm, to, direction, res in all_results:
    if direction == "out":
        if frm not in out_prices:
            out_prices[frm] = {}
        out_prices[frm][to] = res
    else:
        if frm not in ret_prices:
            ret_prices[frm] = {}
        ret_prices[frm][to] = res

out_count = sum(len(v) for v in out_prices.values())
ret_count = sum(len(v) for v in ret_prices.values())
print(f"Found: {out_count} outbound, {ret_count} return routes")

# Combine: find cheapest open-jaw per destination
best = {}
for dest in DESTINATIONS:
    for orig_out in ORIGINS:
        out_flight = out_prices.get(orig_out, {}).get(dest)
        if not out_flight:
            continue
        for orig_ret in ORIGINS:
            ret_flight = ret_prices.get(dest, {}).get(orig_ret)
            if not ret_flight:
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
                        "price_eur": out_flight["price_eur"],
                        "duration_min": out_flight["duration_min"],
                        "stops": out_flight["stops"],
                        "airlines": out_flight["airlines"],
                        "departure": out_flight["departure"],
                        "arrival": out_flight["arrival"],
                    },
                    "return": {
                        "from": dest, "to": orig_ret,
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
        "out_routes_found": out_count,
        "ret_routes_found": ret_count,
        "note": f"Open-jaw optimized. Out {DEP_DATE}, ret {RET_DATE}. USD->EUR x0.92."
    }, f, indent=2)

print(f"Done. {len(best)} complete itineraries.")
if top40:
    t = top40[0]
    jaw = "open-jaw" if t["open_jaw"] else "round-trip"
    print(f"Cheapest ({jaw}): {t['origin_out']}->{t['destination']}->{t['origin_ret']} EUR{t['total_eur']}")
