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
    # --- Iceland ---
    "KEF",  # Reykjavik (main)
    "AEY",  # Akureyri (north Iceland)
    "EGS",  # Egilsstadir (east Iceland)
    "IFJ",  # Isafjordur (Westfjords, very remote)

    # --- Faroe Islands ---
    "FAE",

    # --- Norway mainland ---
    "OSL", "BGO", "TRD", "SVG", "HAU",
    "BOO",  # Bodo (gateway to Lofoten)
    "EVE",  # Harstad/Narvik
    "TOS",  # Tromso
    "ALF",  # Alta (Northern Lights)
    "LKL",  # Lakselv (Finnmark)
    "KKN",  # Kirkenes (extreme north, Russian border)
    "HFT",  # Hammerfest
    "VDS",  # Vardo (easternmost Norway)
    "MQN",  # Mo i Rana
    "RRS",  # Roros (UNESCO mining town)
    "SOG",  # Sogndal (Sognefjord)
    # --- Lofoten & Vesteralen ---
    "LKN",  # Leknes (Lofoten Islands)
    "SVJ",  # Svolvaer (Lofoten)
    "ANX",  # Andenes (whale watching)
    # --- Svalbard ---
    "LYR",  # Longyearbyen (Svalbard)

    # --- Greenland ---
    "GOH",  # Nuuk
    "SFJ",  # Kangerlussuaq
    "JAV",  # Ilulissat (iceberg UNESCO)
    "UAK",  # Narsarsuaq (south Greenland)
    "CNP",  # Neerlerit Inaat (east Greenland)

    # --- Sweden ---
    "ARN", "GOT",
    "UME",  # Umea
    "SDL",  # Sundsvall
    "OSD",  # Are/Ostersund (mountain wilderness)
    "LLA",  # Lulea
    "KRN",  # Kiruna (Swedish Lapland)
    "GEV",  # Gallivare (Lapland)
    "HMV",  # Hemavan (mountain, bear country)
    "VBY",  # Visby (Gotland island)

    # --- Finland ---
    "HEL", "OUL",
    "RVN",  # Rovaniemi (Santa/Lapland)
    "KAO",  # Kuusamo (Oulanka NP)
    "IVL",  # Ivalo (northernmost Finland)
    "KTT",  # Kittila (Lapland ski & wilderness)
    "ENF",  # Enontekio (northernmost Finland)
    "JOE",  # Joensuu (Karelia)
    "KAJ",  # Kajaani
    "MHQ",  # Mariehamn (Aland Islands)

    # --- Denmark + Greenland ---
    "CPH",

    # --- Baltics ---
    "TLL",  # Tallinn (Estonia)
    "RIX",  # Riga (Latvia)
    "VNO",  # Vilnius (Lithuania)

    # --- Scotland & remote British Isles ---
    "EDI", "GLA", "INV",
    "WIC",  # Wick (Caithness, far north Scotland)
    "KOI",  # Kirkwall (Orkney Islands)
    "LSI",  # Lerwick/Sumburgh (Shetland Islands)
    "SYY",  # Stornoway (Outer Hebrides)
    "BEB",  # Benbecula (Outer Hebrides)
    "ILY",  # Islay (whisky island)
    "TRE",  # Tiree (remote Atlantic island)
    "SNN",  # Shannon (Ireland)
    "CFN",  # Donegal (Wild Atlantic Way)

    # --- Atlantic Islands ---
    "FNC", "PDL", "TER", "HOR", "SMA",

    # --- Morocco ---
    "CMN", "RAK", "FEZ", "TNG", "AGA",

    # --- Turkey (nature & remote) ---
    "IST",  # Istanbul
    "TZX",  # Trabzon (Black Sea, Kackar mountains)
    "VAN",  # Van (Lake Van, east Turkey)
    "ERZ",  # Erzurum (east Anatolia)

    # --- China ---
    "PEK", "PVG", "CAN", "CTU",
    "KMG",  # Kunming (Yunnan gateway)
    "LJG",  # Lijiang (Yunnan, Jade Dragon Snow Mountain)
    "URC",  # Urumqi (Xinjiang/Silk Road)
    "XNN",  # Xining (Qinghai, Tibetan plateau)
    "LXA",  # Lhasa (Tibet)

    # --- Japan ---
    "NRT", "HND", "KIX",
    "CTS",  # Sapporo (Hokkaido)
    "FUK",  # Fukuoka
    "AKJ",  # Asahikawa (Hokkaido, Daisetsuzan NP)
    "KUH",  # Kushiro (Hokkaido, Akan NP, cranes)
    "WKJ",  # Wakkanai (northernmost Japan)
    "ISG",  # Ishigaki (Okinawa chain, coral reefs)

    # --- Central Asia & Caucasus ---
    "FRU",  # Bishkek (Kyrgyzstan)
    "OSS",  # Osh (southern Kyrgyzstan, Pamir gateway)
    "TAS",  # Tashkent (Uzbekistan)
    "SKD",  # Samarkand (Silk Road)
    "UGC",  # Urgench (gateway to Khiva/Khorezm)
    "NCU",  # Nukus (Karakalpakstan, Aral Sea)
    "DYU",  # Dushanbe (Tajikistan)
    "LEN",  # Khujand (northern Tajikistan)
    "ALA",  # Almaty (Kazakhstan)
    "ASB",  # Ashgabat (Turkmenistan)
    "GYD",  # Baku (Azerbaijan)
    "EVN",  # Yerevan (Armenia)
    "LWN",  # Gyumri (Armenia)
    "TBS",  # Tbilisi (Georgia)
    "KUT",  # Kutaisi (Georgia, Ryanair hub)
    "BUS",  # Batumi (Georgia, Black Sea)

    # --- India (Himalayan / remote) ---
    "IXL",  # Leh (Ladakh, world's highest airport)
    "SXR",  # Srinagar (Kashmir)

    # --- Nepal, Bhutan, Mongolia ---
    "KTM", "PBH", "ULN",

    # --- South & Southeast Asia ---
    "CMB",  # Colombo (Sri Lanka)
    "RGN",  # Yangon (Myanmar)
    "DPS",  # Bali (Indonesia)
    "MDC",  # Manado (North Sulawesi, diving)
    "BPN",  # Balikpapan (Borneo, orangutans)
    "REP",  # Siem Reap (Cambodia, Angkor Wat)
    "LPQ",  # Luang Prabang (Laos)

    # --- Patagonia & South America wild ---
    "USH",  # Ushuaia (southernmost city)
    "FTE",  # El Calafate (Perito Moreno glacier)
    "BRC",  # Bariloche (Argentine lake district)
    "PUQ",  # Punta Arenas (Chilean Patagonia)
    "PMC",  # Puerto Montt (lakes & volcanoes)
    "IQT",  # Iquitos (Amazon, Peru, no roads)
    "CUZ",  # Cusco (Machu Picchu gateway)
    "LPB",  # La Paz (Bolivia, highest capital)

    # --- New Zealand ---
    "AKL", "CHC", "ZQN",
    "WLG",  # Wellington
    "DUD",  # Dunedin (gateway to Fiordland)
    "ROT",  # Rotorua (geothermal)

    # --- Australia remote ---
    "HBA",  # Hobart (Tasmania wilderness)

    # --- Canada wilderness & Arctic ---
    "YVR", "YYC",
    "YXY",  # Whitehorse (Yukon)
    "YZF",  # Yellowknife (Northwest Territories, Northern Lights)
    "YFB",  # Iqaluit (Nunavut, Arctic)

    # --- Alaska ---
    "ANC",

    # --- Balkans wild nature ---
    "TIA", "TGD", "SKP",

    # --- East Africa ---
    "ADD", "NBO", "JRO", "EBB",
    "ZNZ",  # Zanzibar
    "MBA",  # Mombasa
    "LAU",  # Lamu (Kenya island archipelago)

    # --- Southern & Central Africa ---
    "WDH",  # Windhoek (Namibia, Namib desert)
    "CPT",  # Cape Town
    "VFA",  # Victoria Falls (Zimbabwe)
    "LVI",  # Livingstone (Zambia, Victoria Falls)
    "MUB",  # Maun (Botswana, Okavango Delta)
    "KGL",  # Kigali (Rwanda, gorilla trekking)

    # --- Indian Ocean islands ---
    "TNR",  # Antananarivo (Madagascar)
    "RUN",  # Saint-Denis (Reunion)
    "MRU",  # Mauritius
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

print(f"Searching {len(pairs)} pairs ({len(ORIGINS)} origins x {len(DESTINATIONS)} destinations)...")

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
    print("No results found - Google may be blocking GitHub runner IPs.")
