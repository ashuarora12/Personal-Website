# What Is Behind "People Receiving Quality Health Services"? — WBER submission package

Manuscript prepared for *The World Bank Economic Review*.

| File | What it is |
|---|---|
| `paper/wber-health-manuscript.docx` / `.pdf` | Manuscript: title page, abstract (195 words), JEL codes, double-spaced body, 9 tables, 4 figures |
| `paper/wber-health-online-appendix.docx` / `.pdf` | Online appendix: all 92 contributing results with their codes, the top 20, and the classification rules |
| `paper/cover-letter.md` | Draft cover letter to the editors |
| `data/health_results.*` | 226 health-indicator project results (CSV and Stata .dta), with raw values, factors, method and family codes |
| `data/health_female.*` | Female disaggregation rows of the same indicator |
| `data/aggregates.csv` | Published WBG / WB / IDA / IBRD / IFC / MIGA totals |
| `data/health_workforce.*` | 1,131 Scorecard projects with health-workforce, jobs and migration flags |
| `code/01_build_health.py` | Raw Scorecard exports → datasets above |
| `code/02_health_analysis.R` | Every table, figure and number (`output/`) |
| `code/03_health_analysis.do` | Stata replication with **39 PASS/FAIL checks** of the paper's numbers |

Comparisons with the other results areas (Table 9) use `../welfare-anchor/data/`. The raw exports are in `../who-benefits/data/raw/`.

## Reproduce

```bash
python3 code/01_build_health.py
Rscript code/02_health_analysis.R
python3 paper/build_paper.py                                   # PDF manuscript + appendix
python3 paper/html_to_blocks.py manuscript.html blocks_manuscript.json && node paper/build_docx.js blocks_manuscript.json wber-health-manuscript.docx
python3 paper/html_to_blocks.py online_appendix.html blocks_appendix.json && node paper/build_docx.js blocks_appendix.json wber-health-online-appendix.docx
```

To check every number in Stata, run `do code/03_health_analysis.do` from this folder. The last line should read `Checks passed: 39  Checks failed: 0`. Stata was not available when the package was built; every check value was confirmed independently in Python from the same `.dta` files.

## Verify, step by step

1. **Reconciliation.** In `CSC_RES_HEA_SERV.xlsx`, sheet **Aggregates**, the WBG total is 378,926,567. The **IFC MIGA Results** sheet gives IFC = 68,310,599 and MIGA = 63,100. The sum of `Achieved_Results` over the **Total** rows of "WB Project Information" is 310,552,868. Check that 310,552,868 + 68,310,599 + 63,100 = 378,926,567 (Table 1).
2. **Method codes.** Open the online appendix table A1, or `data/health_results.csv` filtered to `double_counted == 0` and `achieved_m > 0`. For each of the 92 rows, confirm the `method` code from the indicator wording and `conv_factor`, using these definitions:
   - **direct**: factor = 1;
   - **coverage**: a percentage multiplied by a population base;
   - **unit**: visits, facilities or cases converted into people;
   - **adjusted**: a count of people multiplied by a factor other than 1.

   This review is the author's responsibility before submission. The paper states that every one of the 92 results was reviewed by hand.
3. **Worked example.** Health file, project P144893, *Total* row: 137 facilities × 10,000 = 1,370,000 people.
4. **Bounds (Table 4).** Sum `achieved_m` under each rule; the Stata checks T4 do this.
5. **Women (Table 8).** In the Female rows (`data/health_female`), 59.2% of the 155.35 million comes from rows whose disaggregation factor lies between 0 and 1.
6. **Regressions (Table 9).** Run `code/03_health_analysis.do`; checks T9 compare the coefficients with the paper.

## Before submission: author checklist

- [ ] Do the method and family review of the 92 results (step 2 above).
- [ ] Run the Stata do-file and confirm 39 PASS.
- [ ] Fill in the title-page placeholders: affiliation, address, email, acknowledgements, repository link.
- [ ] Decide on the AI-use statement (title-page footnote) according to OUP's current policy.
- [ ] Re-check WBER's current author guidelines (length limit, abstract length, reference style, figure format) on the journal website. These were taken from search results, because the guidelines page could not be opened from the build environment.
- [ ] Deposit the replication package (WBER requires public data and code as a condition of publication).
