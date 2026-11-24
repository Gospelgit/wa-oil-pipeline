# Handover: Nigeria Oil Value Chain Dashboard page for gospelbassey.com

## Goal

Add a second live dashboard page to the portfolio site, next to the existing West Africa Industry Dashboard. It shows Nigeria's crude oil and refined fuel against 11 other producers, grouped by region, with a 12-month production forecast. The data comes from an automated pipeline that refreshes every month. The page only **reads** JSON files from GitHub, so it needs no backend or database.

Keep the rest of the site as it is. Reuse the same colours, fonts, card style, chart style, loading skeleton and error state as the West Africa Industry Dashboard, so the two pages look like a pair.

## 1. Where it goes on the site

1. **New page at `/projects/oil-value-chain`**, with the site's normal header and footer.
2. **Featured card, second in "Featured Projects"**, right after the West Africa Industry card, styled the same way:
   - Title: **Nigeria Oil Value Chain Pipeline**
   - Badge: **LIVE · Updated monthly** with the pulsing dot, as on the other live card
   - Description: *An automated pipeline that compares Nigeria's crude oil and refined fuel with 11 producers across five regions, and forecasts crude production a year ahead.*
   - Tags: Data Engineering, Python, Forecasting, GitHub Actions, Energy
   - Buttons: **Open Dashboard** (to the new page) and **View Code** (https://github.com/Gospelgit/wa-oil-pipeline)
   - Live figure on the card: "Nigeria: {forecast} kb/d forecast for {month}", read from forecast.json (Nigeria's last forecast row)
3. **Navigation: turn "Live Data" into a small dropdown** with two items: "West Africa Industry" (the existing page) and "Nigeria Oil Value Chain" (the new page). On mobile, show both as items under "Live Data".
4. **Announcement strip** below the hero buttons: change it to *New: Nigeria Oil Value Chain Dashboard →*, linking to the new page.

## 2. Data source

All data is in public JSON files on GitHub. Fetch them in the browser when the page loads. Never copy the data into the site's code, because it changes every month.

**Base URL:**
```
https://raw.githubusercontent.com/Gospelgit/wa-oil-pipeline/main/public_data/
```

Fetch these files at the same time (`Promise.all`): `meta.json`, `crude.json`, `products.json`, `nigeria_fuel.json`, `peers.json`, `forecast.json`, `backtest.json`, `hormuz_status.json`, `quality.json`, `brent.json`, `rigs.json`. Show a loading skeleton while waiting, and a friendly error with a "Try again" button if any request fails.

**Series format.** Time series are arrays of `[month, value]` pairs, with month as `"YYYY-MM"`. Missing months are simply absent. **Never draw a line across a missing month, and never treat a gap as zero.**

Units: kb/d means thousand barrels per day. Show numbers with thousands separators, e.g. "1,500 kb/d".

### meta.json
| Field | Meaning |
| --- | --- |
| generated_at | When the pipeline last ran (ISO date-time, UTC) |
| newest_month | Newest month of JODI data, e.g. "2026-09" |
| countries | List of {name, short_name, iso2, region}. Use `short_name` for labels ("Iran", "Russia", "United States") |
| sources | Source descriptions for the footer |

Regions are: Africa, Middle East, Europe, North America, South America.

### crude.json
`series[country][flow]` = `[[month, value], ...]` from 2005. Flows: "Production", "Exports", "Imports", "Refinery intake" (all kb/d) and "Closing stocks" (thousand barrels). Country keys are the full `name` from meta.json.

### products.json
`series[country]["{product} | {flow}"]` = `[[month, value], ...]`. Products: "Motor and aviation gasoline" (label it "Petrol"), "Gas/diesel oil" (label "Diesel"), "Total oil products" (label "All fuels"). Flows: "Refinery output", "Demand", "Imports", "Exports". Canada has no products data.

### nigeria_fuel.json
One row per year from 2015: `year`, `refinery_output`, `demand`, `imports`, `exports` (kb/d, total oil products), `self_sufficiency_pct` (output ÷ demand × 100), `net_exports` (exports − imports; negative means Nigeria imports more than it exports). The latest year is the year so far.

### peers.json
One row per country: `country`, `short_name`, `region`, `latest_month`, `latest_kbd`, `avg_2010_kbd`, `change_since_2010_pct`, `peak_kbd`, `peak_month`, `pct_of_peak`, `typical_monthly_swing_pct`, `export_share_pct` and `refined_at_home_pct` (for `share_basis_year`), `fuel_self_sufficiency_pct` and `net_product_exports_kbd` (for `fuel_basis_year`), `oil_rigs`, `kbd_per_rig`. Any of these can be null: show "No data", not 0.

### forecast.json
- `countries[country]`: `history` (last 36 months, `[month, value]`), `forecast` (12 rows of `[month, forecast, low_80, high_80]`), `test_error_pct` (average % error in testing), and `warning` (a string or null).
- `skipped`: list of `{country, reason}` for countries not forecast.

### backtest.json
`models`: rows of {model, selection, test}, the average % error of each model in two test periods. `chosen_model` is "blend". `blend_test_error_by_country`: {country: % error}.

### hormuz_status.json
| Field | Meaning |
| --- | --- |
| status | "closed", "restricted" or "open" |
| decided_by | "data" or "manual override" |
| latest_month, latest_pct_of_prewar | e.g. "2026-09", 76.5: Saudi exports as a % of their pre-war level |
| lowest_month, lowest_pct_of_prewar | The low point, e.g. "2026-05", 48.8 |
| override | null, or {status, as_of, note, source} when set by hand |
| monthly_pct_of_prewar | [{month, pct}] from Sep 2025 |
| rules | The thresholds: closed below 60%, open from 90% for 2 months |

### quality.json
`newest_month`, `revised_since_reference` (count), `stopped_reporting` ([{country, last_month}]), `unusual_jumps` (rows with country, product, flow, month, value, change_pct, score), `rig_warning` (string or null; set when the rig data is behind and needs a new upload).

### brent.json and rigs.json
`brent.series` = `[[month, US$ per barrel], ...]`. `rigs.series[country]` = `[[month, oil rigs], ...]`, plus a `note` about Saudi Arabia's count change in January 2024 (show it under any rig chart that includes Saudi Arabia).

## 3. Page layout, top to bottom

### 3.1 Header and status bar
- Title: **Nigeria Oil Value Chain Dashboard**
- Subtitle: *Nigeria's crude oil and refined fuel compared with 11 producers across five regions, from JODI, FRED and Baker Hughes. Refreshed automatically every month.*
- LIVE badge, as on the featured card.
- Status pills: "Data refreshed: {generated_at as e.g. 22 Dec 2026}", "Latest data: {newest_month as e.g. Sep 2026}", and "✓ Data checks passed".
- Links: **View Code** and **Methodology** (https://github.com/Gospelgit/wa-oil-pipeline/blob/main/docs/METHODOLOGY.md).

### 3.2 Key findings (four cards, numbers read from the data)
1. **Nigeria now makes more fuel than it uses.** "{self_sufficiency_pct}% of its fuel demand in {year}, up from {2023 value}% in 2023." From nigeria_fuel.json (latest year and 2023).
2. **Nigeria is now a net fuel exporter.** "Net product exports: {net_exports} kb/d in {year}, against {2023 value} kb/d in 2023." From nigeria_fuel.json.
3. **Output is {pct_of_peak}% of its peak.** "{latest_kbd} kb/d in {latest_month}, against {peak_kbd} kb/d in {peak_month}." From peers.json (Nigeria).
4. **The least stable producer of the 12.** "Output typically moves {typical_monthly_swing_pct}% a month." Then name the next highest country and its value. From peers.json.

### 3.3 Strait of Hormuz status card
A compact card near the top, beside or below the key findings:
- A small simple map graphic of the strait (Iran to the north, UAE and Oman to the south, the narrow channel between). Show the channel's state visually:
  - **closed:** red, with a solid barrier across the channel
  - **restricted:** amber, with a dashed or partial barrier
  - **open:** green, with no barrier and an arrow passing through
- A status pill with the word as well as the colour (Closed / Restricted / Open).
- Two small figures: "Saudi exports vs pre-war: {latest_pct_of_prewar}% ({latest_month})" and "Lowest: {lowest_pct_of_prewar}% ({lowest_month})".
- A small sparkline of `monthly_pct_of_prewar`, with dashed lines at 60% and 90%.
- If `decided_by` is "manual override", show "Updated by hand on {override.as_of}: {override.note}" with a link to `override.source`.
- Footnote: "Saudi Arabia ships most of its oil through the strait, so its exports show whether the strait is working. JODI data runs about two months behind."

### 3.4 Nigeria against the world, by region
- A table built from peers.json, **grouped by region** with a region heading row, in this order: Africa, Middle East, Europe, North America, South America. Nigeria is always the first row of Africa and is highlighted.
- Columns: Country, Output now (kb/d), % of peak, Change since 2010, Monthly swing, Exported, Refined at home, Fuel self-sufficiency, kb/d per rig.
- Show the month next to "Output now" for countries whose `latest_month` is old (Angola, Iran, Russia), with a small "stopped reporting" label.
- Above the table, a metric selector and a horizontal bar chart of the selected metric for all 12 countries, coloured by region, with Nigeria highlighted. Default metric: **% of peak**.
- On phones, the table scrolls sideways with the Country column fixed.

### 3.5 Crude oil explorer
- Dropdowns: country (default Nigeria) and flow (default Production).
- Line chart from 2005. Gaps are breaks in the line.
- Toggle: **"Compare with"** a second country (optional), drawn in a second colour.
- Mark any month listed in `quality.unusual_jumps` for that country and flow with a small marker. The tooltip shows the change and says "Unusual change: may be a real event or a reporting error".

### 3.6 Nigeria's fuel turnaround
- A chart from nigeria_fuel.json (2015 onwards): bars for refinery output, a line for demand.
- A second small chart: imports and exports as bars, with the net value as a line crossing zero. Add the label "Net exporter" above zero and "Net importer" below.
- A product selector (Petrol, Diesel, All fuels) that switches both charts to monthly data from products.json (Nigeria), from 2019.
- One sentence: *"Since 2024 Nigeria has started refining far more of its own crude, and in March 2026 it began exporting more fuel than it imports."*

### 3.7 Production forecast
- Country dropdown (default Nigeria), from forecast.json's countries.
- Chart: `history` as a solid line, then the forecast as a dashed line with a shaded band between `low_80` and `high_80`, labelled "Forecast (80% range)". Start the dashed line from the last real value so they join. Use a style that can't be mistaken for real data.
- Under the chart: "Average error in testing: {test_error_pct}%".
- If `warning` isn't null, show it in an amber notice box above the chart, with a link to the Hormuz card.
- Below, a list "Not forecast" from `skipped`, with the reasons.
- A small table from backtest.json: model, error in the selection period, error in the test period, with the chosen model highlighted. One sentence: *"Five methods were tested on months they hadn't seen. Adding oil prices and rig counts made 12-month forecasts worse, so the chosen model uses each country's recent production only."*

### 3.8 Prices and drilling (context)
- Brent price line from brent.json, with a shaded area from March 2026 labelled "Hormuz disruption".
- Oil rigs line chart from rigs.json, with a country selector (default Nigeria). Show the Saudi note under the chart when Saudi Arabia is selected.

### 3.9 Data quality and how it works
- Small cards: "Countries no longer reporting" (from `stopped_reporting`), "Values revised since last check", and "Unusual recent changes" (top 5 from `unusual_jumps`). If `rig_warning` isn't null, show it as an amber notice.
- Flow graphic: **JODI + FRED + Baker Hughes → filter and check → Hormuz status, peers, forecast → JSON → this page**
- Text: *"A GitHub Actions workflow runs on the 22nd of every month, after JODI's update. It skips the run if no source has changed. Otherwise it downloads JODI's full database, keeps 12 countries, checks the data, rebuilds the forecast and publishes the files this page reads."*

## 4. Technical notes

- Same stack and chart library as the West Africa Industry Dashboard.
- Fetch once per page load. Parse `[month, value]` pairs into objects in `useMemo`.
- Region colours: one colour per region, used the same way in every chart and table.
- Page title: "Nigeria Oil Value Chain Dashboard | Gospel Bassey", with the subtitle as the meta description.
- Accessibility: every chart has a text title, and statuses and flags use words or icons as well as colour.

## 5. Please don't

- Don't hard-code any numbers. Every figure in the key findings and the Hormuz card comes from the JSON files.
- Don't fill in, smooth or join across missing months.
- Don't draw forecasts in the same style as real data.
- Don't change the West Africa Industry page, apart from the shared navigation dropdown.

## 6. Done when

- [ ] The new featured card is second in Featured Projects, with the LIVE badge, live Nigeria figure and both buttons working
- [ ] "Live Data" is a dropdown with both dashboards, on desktop and mobile
- [ ] All 11 files load, with loading and error states
- [ ] The Hormuz card shows "Restricted" with 76.5% for 2026-09, and switches state if `status` changes
- [ ] The peers table is grouped by region with Nigeria first and highlighted
- [ ] Nigeria's forecast chart shows the dashed forecast and shaded range after Aug 2026
- [ ] Choosing Saudi Arabia in the forecast shows the amber warning
- [ ] Choosing Libya and Production in the explorer shows a gap from 2014 to 2026, not a line
- [ ] The page works and looks right on a phone
