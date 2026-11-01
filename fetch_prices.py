
#!/usr/bin/env python3
"""
Haalt uurprijzen stroom (en de dagprijs gas) op uit de publieke EnergyZero API
en schrijft data/prices.json voor de statische dashboardpagina.

Bedoeld om elk uur te draaien via GitHub Actions (zie .github/workflows/update-prices.yml).
Gebruikt uitsluitend de Python-standaardbibliotheek; geen pip-installaties nodig.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen
from zoneinfo import ZoneInfo

API = "https://api.energyzero.nl/v1/energyprices"
TZ = ZoneInfo("Europe/Amsterdam")
OUT_PATH = os.path.join("data", "prices.json")


def api_url(start, end, interval, usage_type):
    """Bouw een API-URL; EnergyZero verwacht UTC-timestamps met milliseconden en Z."""
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
    return (
        f"{API}?fromDate={start.astimezone(timezone.utc).strftime(fmt)}"
        f"&tillDate={end.astimezone(timezone.utc).strftime(fmt)}"
        f"&interval={interval}&usageType={usage_type}&inclBtw=true"
    )


def fetch_json(url):
    with urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def day_bounds(day_offset):
    """Midnight (lokale tijd, Europe/Amsterdam) van vandaag + offset."""
    now = datetime.now(TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
    return start, start + timedelta(days=1)


def hourly_prices(day_offset):
    """Uurprijzen stroom voor de gevraagde lokale dag, als lijst dicts."""
    start, end = day_bounds(day_offset)
    url = api_url(start, start + timedelta(days=2), 4, 1)
    payload = fetch_json(url)
    hours = []
    for item in payload.get("Prices", []):
        t = datetime.fromisoformat(item["readingDate"].replace("Z", "+00:00")).astimezone(TZ)
        if start <= t < end:
            hours.append({
                "iso": item["readingDate"],
                "local": t.strftime("%H:%M"),
                "price": item["price"],
            })
    return hours


def gas_price_today():
    """Laatst bekende dagprijs gas voor vandaag, of None."""
    start, end = day_bounds(0)
    url = api_url(start, end, 1, 3)
    try:
        payload = fetch_json(url)
    except Exception:
        return None
    prices = payload.get("Prices", [])
    return prices[-1]["price"] if prices else None


def day_stats(day_offset):
    """Statistieken voor één dag; None als er geen uren beschikbaar zijn."""
    hours = hourly_prices(day_offset)
    if not hours:
        return None
    prices = [h["price"] for h in hours]
    cheapest = min(hours, key=lambda h: h["price"])
    priciest = max(hours, key=lambda h: h["price"])

    # Goedkoopste aaneengesloten blok van 3 uur
    best = None
    for i in range(len(hours) - 2):
        block = hours[i:i + 3]
        total = sum(h["price"] for h in block)
        if best is None or total < best["total"]:
            best = {
                "total": round(total, 4),
                "average": round(total / 3, 4),
                "from": block[0]["local"],
                "till": block[-1]["local"],
            }

    start, _ = day_bounds(day_offset)
    return {
        "date": start.strftime("%Y-%m-%d"),
        "hours": hours,
        "average": round(sum(prices) / len(prices), 4),
        "minimum": cheapest["price"],
        "minimumAt": cheapest["local"],
        "maximum": priciest["price"],
        "maximumAt": priciest["local"],
        "cheapestBlock": best,
    }


def main():
    today = day_stats(0)

    # Morgenprijzen worden doorgaans rond 14:00 uur gepubliceerd;
    # dus vóór die tijd is dit gewoon None en probeert het script het volgende uur weer.
    tomorrow = None
    try:
        tomorrow = day_stats(1)
    except Exception:
        tomorrow = None

    data = {
        "generatedAt": datetime.now(TZ).isoformat(),
        "source": "EnergyZero (uurmarktprijs incl. btw)",
        "electricity": {"today": today, "tomorrow": tomorrow},
        "gas": {"todayPrice": gas_price_today()},
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if today:
        print(f"OK: {len(today['hours'])} uren vandaag, gemiddeld EUR {today['average']}")
    else:
        print("WAARSCHUWING: geen prijzen voor vandaag gevonden")
    print(f" geschreven naar {OUT_PATH}")


if __name__ == "__main__":
    main()
