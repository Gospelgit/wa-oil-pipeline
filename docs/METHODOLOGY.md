# Methodology

## 1. Why these sources

**JODI** is the only free source with monthly, country-level data across the whole oil chain: crude production and trade, refinery intake, fuel output, demand and trade. National agencies report to it, and Nigeria's figures match NUPRC's exactly (1,505 kb/d in July 2026). **FRED** republishes the US EIA's Brent price with a stable download link. **Baker Hughes** has the only long, free, country-level rig count.

## 2. Getting JODI without clicking

JODI's Table Viewer exports one table at a time, by hand. The pipeline uses the bulk files instead (`world_primary_csv.zip` and `world_secondary_csv.zip`), which hold every country and series. The primary file is about 290 MB unzipped. It's read in chunks of 500,000 rows and filtered to our countries and the codes in `pipeline/config.py`.

**Validation.** Before the pipeline was built, 45,917 values were exported by hand from the Table Viewer. The bulk-file extract matched every one of them (largest difference 0.005, rounding). The hand exports are kept in `data/reference/` and checked on every run.

**Codes used.** Primary table: `CRUDEOIL` with `INDPROD` (production), `TOTIMPSB` (imports), `TOTEXPSB` (exports), `REFINOBS` (refinery intake), all in `KBD`, and `CLOSTLV` (closing stocks) in `KBBL`. Stocks must use KBBL because JODI marks stocks in KBD as not applicable. Secondary table: `GASOLINE`, `GASDIES` and `TOTPRODS` with `REFGROUT`, `TOTDEMO`, `TOTIMPSB` and `TOTEXPSB`, in `KBD`. JODI's "-" (not reported) and "x" (confidential) both become empty, never zero.

## 3. Rig counts and the Saudi break

Baker Hughes' current report starts in January 2024. Older months (2013 to 2023) come from its archive file. The two overlap from January 2024 to July 2025 and match exactly for every country except Saudi Arabia. In January 2024 Baker Hughes started counting Saudi "operating" rigs instead of "active" rigs, without restating the archive. Its January 2024 count was 46 oil rigs under the old method and 182 under the new. The pipeline keeps both versions for the overlap. For modelling, the new counts are scaled down by the average new/old ratio in the overlap, so the Saudi series stays on one basis.

## 4. Quality checks

The run stops if a country is missing, if the newest production month is more than 4 months old, if any flow is negative, or if under 90% of the reference values are still present (a sign the source format changed).

Unusual jumps use a robust z-score on back-to-back monthly changes:

    score = (change − median change) / (1.4826 × MAD)

The MAD (median absolute deviation) times 1.4826 estimates the normal spread without being thrown off by the outliers we're looking for. The spread is floored at the 25th percentile spread for that product and flow, so near-flat series don't flag tiny wobbles. A score above 5 in the last 6 months is flagged. Jumps are reported, never corrected: many are real events. For example, Saudi production fell 23% in August 2026 during the Hormuz disruption. Others look like reporting errors, such as US total products output jumping 29% in September 2026 while US demand didn't move.

## 5. Strait of Hormuz status

**Signal: Kuwait.** Kuwait has no pipeline around the strait, so every barrel it exports by sea passes through Hormuz. Its crude exports against their pre-war level (the average from September 2025 to February 2026) measure whether the strait is working.

**Why not Saudi Arabia.** About 5.5 of Saudi Arabia's 6.3 mb/d of crude exports in 2025 went through the strait, but its 7 mb/d East-West pipeline to Yanbu on the Red Sea lets it keep exporting when the strait is shut. In April 2026, with the strait effectively closed, Saudi exports were still 57% of pre-war while Kuwait's were 3%. Saudi Arabia was the first choice of signal and was replaced for this reason. It's still shown on the card as context. Iraq, Qatar and the UAE would also work, but they don't report crude exports to JODI.

| Kuwait's exports vs pre-war | Status |
| --- | --- |
| Under 60% | Closed |
| 60% to 90% | Restricted |
| 90% or more for 2 months in a row | Open |

Kuwait's exports fell to 3% in April and 2% in May 2026, then recovered to 75% in June and 77% in September (Restricted). Saudi exports bottomed at 49% in May. Because JODI runs about two months behind, `config/hormuz_status.json` can override the status by hand. While the status isn't "open", the Kuwaiti and Saudi forecasts carry a warning.

## 6. Forecasting crude production

**Target:** monthly crude production, 1 to 12 months ahead.

**Models tested:**
- **Naive:** the last month carried forward.
- **Mean3:** the average of the last 3 months carried forward, which smooths out one-off outages.
- **Damped Holt:** exponential smoothing with a trend that flattens out, fitted on the last 10 years.
- **Blend:** the average of mean3 and damped Holt.
- **Drivers:** mean3 adjusted by the past 12 months' change in Brent and oil rigs. A regression pooled across countries, refitted at each test point using only past data.

**Backtest.** Rolling origins every 3 months from December 2015 to September 2025. At each origin the models see only data up to that month. A country is included when it has 24 unbroken months before the origin. Origins up to September 2022 were used to choose the model, and later origins were kept back as an unseen test.

| Average absolute % error, months 1 to 12 | Selection | Test |
| --- | --- | --- |
| Blend | **7.77** | 6.73 |
| Damped Holt | 7.81 | **6.61** |
| Naive | 8.07 | 6.94 |
| Mean3 | 8.27 | 6.98 |
| Drivers | 9.15 | 7.09 |

The test errors rose after Kuwait was added (about 5.3% before), because Kuwait's exports and output collapsed in spring 2026 when the strait shut. No model trained on past months could foresee that.

**Choice:** the blend, which won the selection period by a hair. It is effectively tied with damped Holt.

**Brent and rigs didn't help.** The drivers model came last in both periods. Its fitted effects were tiny: a doubling of Brent over a year moved production by about 2 to 3%, and the rig effect was close to zero. Over 12 months, output depends far more on its own recent level, plus policy (OPEC+ quotas), disruption and field timing, than on prices or drilling. Rigs may matter over longer horizons, which this data can't test yet.

**Ranges.** The 80% range comes from the blend's own backtest errors: the 10th to 90th percentile of % error at each horizon, for each country with at least 25 backtest points, otherwise pooled across countries. Ranges only widen with horizon.

**Not forecast:** countries whose latest data is 3 or more months behind the newest (Angola, Iran, Russia), and Libya, which has too little recent history.

**Test error by country (blend):** US 1.7%, Canada 3.2%, Algeria 4.4%, Norway 4.7%, Nigeria 7.0%, Venezuela 7.8%, Saudi Arabia 8.4%, Kuwait 15.6% (the Hormuz closure). The less stable the country, the harder it is to forecast.

## 7. Limitations

- JODI is reported by governments and is sometimes revised. The pipeline records revisions against the reference copy.
- Stock definitions differ by country, so compare changes in stocks, not levels.
- Canada has no products data in JODI. Brazil's products data stops in December 2022. Venezuela reports zero product demand from 2025, which is almost certainly missing reporting.
- Baker Hughes' site returns 403 Forbidden to automated requests from GitHub's servers, so the monthly report is downloaded by hand and uploaded to `data/manual/rigs/`. Uploading it starts a run. If no new report arrives, the pipeline keeps the previous rig data and shows a reminder once it is more than 2 months behind. Rigs aren't a forecast input, so a late upload never affects the forecast.
