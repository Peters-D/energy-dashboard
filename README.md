# Energieprijs-vandaag (Energy Dashboard NL)

Dynamisch energiedashboard met uurprijzen stroom voor Nederland (incl. btw),
op basis van de publieke EnergyZero API.

## Hoe het werkt

- `index.html` — de dashboardpagina (statisch, geen dependencies).
- `fetch_prices.py` — haalt elk uur de prijzen op en schrijft `data/prices.json`.
- `.github/workflows/update-prices.yml` — draait het Python-script elk uur via GitHub Actions
  en commit het bijgewerkte JSON terug naar deze repository.
- `data/prices.json` — gegenereerde prijzendata (wordt door de workflow bijgewerkt).

De pagina leest `data/prices.json`; valt dat weg, dan haalt hij live de EnergyZero API aan.

## Lokaal draaien

```bash
python fetch_prices.py   # schrijft data/prices.json (alleen standaardbibliotheek)
```

En open `index.html` in een browser.

## Hosten

Zet GitHub Pages aan via Settings → Pages → branch `main`, map `/ (root)`.
Site: https://peters-d.github.io/energy-dashboard/
