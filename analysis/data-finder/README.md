# Health Economics Data Finder

Source for `/data-buff` (`ashu-arora-complete-website/data-buff.html`).

```bash
python3 build.py   # datasets.json + Scorecard vision data + world map -> data-buff.html
```

- `datasets.json` is the hand-curated catalogue. Each entry has `status` (`checked` or `to_verify`) and, when checked, an `evidence` link to the source used, plus `checked_on` at the top of the file. New entries must carry a source link before they are marked `checked`.
- The hotspot map uses World Bank Group Scorecard vision indicators from `../who-benefits/data/raw/`: food and nutrition insecurity, basic hygiene, sanitation and drinking water (shown as the share without access), and poverty at $3.00 a day. Only the latest country-year from 2015 onward is shown; nothing is estimated or filled in.
- Country outlines are taken from the patent dashboard's map (Natural Earth via world-atlas), rounded to whole pixels.
- `template.html` keeps the original Data Buff design system; the build only embeds data.
