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
    # Iceland & Faroe
    "KEF", "FAE",

    # Norway (mainland + extreme north)
    "OSL", "BGO", "TRD", "TOS", "SVG", "BOO", "EVE", "LYR",
    "KKN",  # Kirkenes (extreme north, Norwegian-Russian border)
    "LKL",  # Lakselv (Finnmark)
    "ALF",  # Alta (gateway to Northern Lights)
    "HAU",  # Haugesund

    # Sweden
    "ARN", "GOT", "UME", "LLA", "KRN",
    "SDL",  # Sundsvall
    "OSD",  # Åre/Östersund (Swedish mountain wilderness)

    # Finland
    "HEL", "OUL", "RVN", "KAO", "IVL",
    "KTT",  # Kittilä (Lapland ski & wilderness)
    "ENF",  # Enontekiö (northernmost Finland)

    # Denmark + Greenland
    "CPH",
    "GOH",  # Nuuk, Greenland
    "SFJ",  # Kangerlussuaq, Greenland
    "JAV",  # Ilulissat (icefjord UNESCO)

    # Baltics (NEW)
    "TLL",  # Tallinn, Estonia
    "RIX",  # Riga, Latvia
    "VNO",  # Vilnius, Lithuania

    # Scotland & remote British Isles
    "EDI", "GLA", "INV",
    "KOI",  # Kirkwall, Orkney Islands
    "LSI",  # Lerwick/Sumburgh, Shetland Islands
    "SYY",  # Stornoway, Outer Hebrides
    "SNN",  # Shannon, Ireland

    # Atlantic islands
    "FNC", "PDL", "TER", "HOR", "SMA",

    # Morocco
    "CMN", "RAK", "FEZ", "TNG", "AGA",

    # China
    "PEK", "PVG", "CAN", "CTU", "KMG", "URC",

    # Japan
    "NRT", "HND", "KIX", "CTS", "FUK",

    # Central Asia & Caucasus
    "FRU",  # Bishkek, Kyrgyzstan
    "OSS",  # Osh, Kyrgyzstan (gateway to Pamir/southern Kyrgyzstan)
    "TAS",  # Tashkent, Uzbekistan
    "SKD",  # Samarkand, Uzbekistan
    "DYU",  # Dushanbe, Tajikistan
    "ALA",  # Almaty, Kazakhstan
    "ASB",  # Ashgabat, Turkmenistan
    "GYD",  # Baku, Azerbaijan
    "EVN",  # Yerevan, Armenia
    "TBS",  # Tbilisi, Georgia

    # Nepal, Bhutan, Mongolia
    "KTM", "PBH", "ULN",

    # South & Southeast Asia
    "CMB",  # Colombo, Sri Lanka
    "RGN",  # Yangon, Myanmar
    "DPS",  # Bali, Indonesia

    # Patagonia & South America wild
    "USH", "PUQ", "PMC",
    "CUZ",  # Cusco, Peru (Machu Picchu, Andes)
    "LPB",  # La Paz, Bolivia (world's highest capital)

    # New Zealand
    "AKL", "CHC", "ZQN",

    # Oceania
    "HBA",  # Hobart, Tasmania (wilderness, Antarctic gateway)

    # Canada & Alaska
    "YVR", "YYC", "ANC",
    "YXY",  # Whitehorse, Yukon (wilderness)

    # Balkans wild nature
    "TIA", "TGD", "SKP",

    # East Africa
    "ADD", "NBO", "JRO", "EBB",

    # Southern & Central Africa
    "WDH",  # Windhoek, Namibia (Namib desert, Etosha)
    "CPT",  # Cape Town, South Africa
    "VFA",  # Victoria Falls, Zimbabwe
    "KGL",  # Kigali, Rwanda (gorilla trekking gateway)
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
