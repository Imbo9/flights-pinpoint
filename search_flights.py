import subprocess, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product

USD_TO_EUR = 0.92

ORIGINS = ["BGY", "MXP", "LIN", "VCE", "TSF", "BLQ",
           "VRN", "TRN", "GOA", "TRS", "PMF", "VBS", "BZO", "RMI"]

DESTINATIONS = [
    "KEF", "FAE", "OSL", "TOS", "BGO", "ARN", "HEL", "CPH",
    "TLL", "RIX", "VNO", "EDI", "GLA", "RAK", "FEZ", "CMN",
    "RVN", "TIA", "TBS", "GYD", "EVN", "KUT",
    "NRT", "HND", "KIX", "FNC", "PDL", "CMB", "KTM",
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
    except Exception as e:
        return None

# Tasks: (from, to, date, direction)
out_tasks = [(o, d, DEP_DATE, "out") for o in ORIGINS for d in DESTINATIONS]
ret_tasks = [(d, o, RET_DATE, "ret") for o in ORIGINS for d in DESTINATIONS]
all_tasks = out_tasks + ret_tasks

print(f"Searching {len(all_tasks)} legs ({len(ORIGINS)}x{len(DESTINATIONS)}x2)...")

out_prices = {o: {} for o in ORIGINS}      # out_prices[it_origin][dest]
ret_prices = {d: {} for d in DESTINATIONS} # ret_prices[dest][it_origin]

with ThreadPoolExecutor(max_workers=50) as ex:
    futures = {}
    for frm, to, date, direction in all_tasks:
        fut = ex.submit(search_oneway, frm, to, date)
        futures[fut] = (frm, to, direction)

    for f in as_completed(futures):
        frm, to, direction = futures[f]
        res = f.result()
        if res:
            if direction == "out":
                out_prices[frm][to] = res
            else:  # ret: frm=dest, to=it_origin
                ret_prices[frm][to] = res

# Count what we found
out_count = sum(len(v) for v in out_prices.values())
ret_count = sum(len(v) for v in ret_prices.values())
print(f"Found: {out_count} outbound routes, {ret_count} return routes")

# Sample what we have
out_sample = [(o, d, v["price_eur"]) for o, dests in out_prices.items() for d, v in dests.items()][:5]
ret_sample = [(d, o, v["price_eur"]) for d, origs in ret_prices.items() for o, v in origs.items()][:5]
print("Out sample:", out_sample)
print("Ret sample:", ret_sample)

# Combine open-jaw
best = {}
for dest in DESTINATIONS:
    for orig_out in ORIGINS:
        out_flight = out_prices[orig_out].get(dest)
        if not out_flight:
            continue
        for orig_ret in ORIGINS:
            ret_flight = ret_prices[dest].get(orig_ret)
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
                    "outbound": {"from": orig_out, "to": dest,
                                 "price_eur": out_flight["price_eur"],
                                 "duration_min": out_flight["duration_min"],
                                 "stops": out_flight["stops"],
                                 "airlines": out_flight["airlines"],
                                 "departure": out_flight["departure"],
                                 "arrival": out_flight["arrival"]},
                    "return": {"from": dest, "to": orig_ret,
                               "price_eur": ret_flight["price_eur"],
                               "duration_min": ret_flight["duration_min"],
                               "stops": ret_flight["stops"],
                               "airlines": ret_flight["airlines"],
                               "departure": ret_flight["departure"],
                               "arrival": ret_flight["arrival"]},
                }

top40 = sorted(best.values(), key=lambda x: x["total_eur"])[:40]

with open("results.json", "w") as f:
    json.dump({
        "top40": top40,
        "total_destinations": len(best),
        "out_routes_found": out_count,
        "ret_routes_found": ret_count,
        "note": f"Open-jaw. Outbound {DEP_DATE}, return {RET_DATE}. USD->EUR x0.92."
    }, f, indent=2)

print(f"Done. {len(best)} complete itineraries found.")
if top40:
    t = top40[0]
    print(f"Cheapest: {t['origin_out']}->{t['destination']}->{t['origin_ret']} EUR{t['total_eur']}")
