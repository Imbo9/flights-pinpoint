import subprocess, json
from concurrent.futures import ThreadPoolExecutor, as_completed

ORIGINS = ["MXP"]
DESTINATIONS = ["OSL", "KEF"]
DATE = "2026-09-07"

def search(origin, dest):
    try:
        r = subprocess.run(
            ["fli", "flights", origin, dest, DATE, "--format", "json", "--sort", "CHEAPEST"],
            capture_output=True, text=True, timeout=10
        )
        print(f"[{origin}->{dest}] rc={r.returncode} stdout={r.stdout[:200]} stderr={r.stderr[:100]}")
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            if isinstance(data, list) and data:
                cheapest = min(data, key=lambda x: x.get('price') or 999999)
                p = cheapest.get('price')
                if p:
                    legs = cheapest.get('legs', [])
                    return {
                        'origin': origin, 'destination': dest,
                        'price': p, 'currency': cheapest.get('currency', 'EUR'),
                        'duration_min': cheapest.get('duration'),
                        'stops': cheapest.get('stops', 0),
                        'airlines': list({lg.get('airline','') for lg in legs if lg.get('airline')}),
                        'departure': legs[0].get('departure_datetime','') if legs else '',
                        'arrival': legs[-1].get('arrival_datetime','') if legs else '',
                    }
    except Exception as e:
        print(f"Error {origin}->{dest}: {e}")
    return None

pairs = [(o, d) for o in ORIGINS for d in DESTINATIONS]
results = [r for r in (search(o, d) for o, d in pairs) if r]

with open('results_test.json', 'w') as f:
    json.dump({'top20': results, 'total_routes': len(results)}, f, indent=2)

print(f"Done. {len(results)} routes found.")
for r in results:
    print(f"  {r['origin']}->{r['destination']} {r['currency']}{r['price']}")
