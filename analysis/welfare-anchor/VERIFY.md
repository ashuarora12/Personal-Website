# Verification guide: checking every step of "Counting Reach, Not Welfare"

This guide takes you from the raw World Bank files to every number in the paper. Each step tells you what to run or open, what you should see, and what to do if it differs. Work through the steps in order, ticking each box as you go. It takes about half a day; most of that time is Step 3, re-coding the validation sample.

**Folder:** `analysis/welfare-anchor/`, called "the project folder" below. Run every command from the project folder.

---

## Step 0. Set up the tools (once)

| Tool | Used for | Install |
|---|---|---|
| Stata 15 or later | `.dta` files, `03_analysis.do`, `04_verify_checkpoints.do` | your licence |
| R 4.x | `02_analysis.R` | `install.packages(c("sandwich","lmtest","ggplot2","jsonlite","scales","haven"))` |
| Python 3.10+ | building the dataset, rebuilding the paper | `pip install pandas numpy openpyxl pyreadstat statsmodels beautifulsoup4 pillow playwright` |
| Excel | spot-checking raw rows by hand | |

You only need Python if you want to rebuild the datasets or the paper. To verify the results in Stata, the `.dta` files are enough.

---

## Step 1. Check the raw data (the World Bank files)

**Where:** `analysis/who-benefits/data/raw/`. These are the Scorecard exports from scorecard.worldbank.org, FY25 cycle, with results as of 30 June 2025.

- [ ] **1a. The four results files are present.** You should see `CSC_RES_HEA_SERV.xlsx` (health), `CSC_RES_WAT_SAN_HYG_TOT.xlsx` (WASH), `CSC_RES_GEN_EQU_BENE.xlsx` (gender and economic opportunity) and `CSC_RES_FIN_SERV_WOM.xlsx` (financial services).
- [ ] **1b. Row counts.** Open the sheet **"WB Project Information"** in each file. It should have **665** rows (health), **1,133** (WASH), **8,279** (gender) and **816** (financial services), which adds up to **10,893** records from **1,131** projects. This matches the first row of Table 1 in the paper.
- [ ] **1c. Read the "Dictionary" sheet.** Its definitions are the ones the paper relies on:
  - `Achieved_Results` = progress − baseline.
  - `Expected_Results` = target − baseline.
  - `Progress_Conversion_Factor` converts the project's unit into the Scorecard unit.
  - `Progress_Disaggregation_Factor` is used "to report on youth and female beneficiaries".
  - `Double_Counting_Flag` marks results that are "masked due to considerations of double counting".
- [ ] **1d. Work through two examples by hand.** These are the examples used in the paper.

  **Example A: health facilities become people (project P144893).** In `CSC_RES_HEA_SERV.xlsx`, sheet "WB Project Information", go to **Excel row 293**, or filter `Project_ID` = P144893 and `Demographic_Disaggregation` = Total. The indicator is "Health facilities constructed, renovated, and/or equipped (number)". You should see:
  - `Baseline_Value` 0, `Progress_Value` 137, `Target_Value` 119, `Progress_Conversion_Factor` 10000.
  - `Achieved_Results` = (137 − 0) × 10,000 = **1,370,000** and `Expected_Results` = 119 × 10,000 = **1,190,000**. ✔
  - Approval 4 Mar 2015, closing 30 Jun 2024, progress date 25 Jun 2024. So elapsed = 3,401 / 3,406 days = 0.9985, and the progress ratio = 1.37 m / 1.19 m = 1.151. That is above 0.9985 − 0.10, so the result is **not behind**. ✔

  **Example B: a percentage becomes people (project P128442, cervical-cancer screening).** You should see:
  - Baseline 8.5, progress 9.7, conversion factor 5,055.05.
  - `Achieved_Results` = (9.7 − 8.5) × 5,055.05 = **6,066.06**. ✔

If any number here differs, you have a different download of the Scorecard. Stop and re-download the FY25 files, because every later step depends on these.

---

## Step 2. Build the clean datasets (Python), or check the ones provided

**Run:** `python3 code/01_build_dataset.py`

- [ ] **2a. Console output.** You should see:
  ```
  results 3617 projects 1129
  {'reach': 2258, 'output': 569, 'outcome': 520, 'unclassifiable': 270}
  judgeable 1809 behind 0.563
  scaled 0.112 zero_baseline 0.919
  gender pairs 1734 {'no_progress': 665, 'fixed_share': 387, 'women_only': 349, 'informative': 235, 'identical_share': 91, 'inconsistent': 7}
  ```
  The line `behind 0.563` covers all judgeable results, *including* unclassifiable ones. The paper's 56.7% excludes unclassifiable results, so both numbers are correct. Likewise, `scaled 0.112` and `zero_baseline 0.919` include double-counted rows, while the paper's 10.2% and 90.8% exclude them.
- [ ] **2b. What the script does.** Read `code/01_build_dataset.py` from top to bottom. It is about 300 lines with comments. The decisions to check are:
  1. Only `Demographic_Disaggregation == "Total"` rows become "results". Female and youth rows are breakdowns of these.
  2. A result is `scaled` when the conversion factor is above 0 and not equal to 1. Zero or missing factors are *not* counted as scaled, which is the conservative choice.
  3. A female figure is a `fixed_share` when its disaggregation factor is strictly between 0 and 1.
  4. `behind` = 1 when progress ratio < elapsed − 0.10. A result is `judgeable` only if it has a positive target, is not double counted, and at least 20% of its implementation period has elapsed.
  5. The `ind_type` rules are listed in Appendix A of the paper.
- [ ] **2c. Open the clean data in Stata.**
  ```stata
  use data/results_clean.dta, clear
  describe            // 47 variables, each with a label
  count               // 3,617
  tab ind_type        // reach 2,258 | output 569 | outcome 520 | unclassifiable 270
  list project_id indicator_text conv_factor achieved expected behind if project_id=="P144893", clean
  ```
  The last line should show the facilities example from Step 1, with achieved = 1,370,000.

---

## Step 3. Verify the indicator classification (the most important step)

The classification of each indicator as **reach / output / outcome** drives Test 1, so it must be your own judgement.

- [ ] **3a. Re-code the test sample yourself.**
  1. Open `validation/test_sample_coded.csv` in Excel. **Hide the `rule_type` and `manual_type` columns first** so you are not influenced by them.
  2. For each of the 200 rows, read `indicator_text` and write your own code in a new column `my_type` using these definitions:
     - **outcome**: a change in a condition or behaviour of people or firms. Examples: income, jobs obtained, sales, health status, adopting a practice, coverage *rates*.
     - **output**: something the project produces or does. Examples: people trained or certified, facilities built, loans issued, plans adopted.
     - **reach**: a count of people, households or firms who receive, access or benefit from something.
     - **unclassifiable**: a label only, such as "Of which women" or a country name.
  3. Unhide the columns and compare `my_type` with `manual_type`, which is the first-pass coding. Where you disagree, your code wins: copy `my_type` into `manual_type`.
- [ ] **3b. Re-score the classifier:** run `python3 code/00_validation_scores.py validation/test_sample_coded.csv`. Currently it reports accuracy 0.835, κ 0.661, outcome precision 0.895 and recall 0.567. Your numbers will change slightly if you changed codes.
- [ ] **3c. Do the same for the development sample**, `validation/dev_sample_coded.csv`. It is used for the pooled hand-coded share and Appendix Table A1.
- [ ] **3d. Re-run the R script and rebuild the paper** (Step 5 and Step 7). Table 4, the κ in the text and Appendix Table A1 update automatically.
- [ ] **3e. Optional but valuable:** ask a colleague to code the same 200 test rows, and report agreement between the two coders (Cohen's κ) in a footnote.

---

## Step 4. Verify the results in Stata

- [ ] **4a. Run the automatic checkpoints:** `do code/04_verify_checkpoints.do`
  - It runs **39 checks**, covering dataset sizes, every headline percentage, the worked example, and the key regression coefficients, standard errors and R² values.
  - Each check prints a line such as `PASS  D6 outcome indicator coefficient (+0.133)   Stata = 0.1330   paper = 0.1330`.
  - The last line should read **`Checks passed: 39    Checks failed: 0`**.
  - If anything fails, note its code (A1–E4) and go to the matching step in the table below.

  | Code | Checks | Paper location |
  |---|---|---|
  | A1–A9 | sample sizes | Table 1 |
  | B1–B5 | what the Scorecard counts | Abstract, Section 5.1, Table 3 |
  | C1–C12 | constructed figures and gender audit | Section 5.2, Table 6 |
  | D1–D9 | "behind" shares and the Test 3 model | Section 5.3, Table 8 |
  | E1–E4 | Test 1 model | Section 5.1, Table 5 |

- [ ] **4b. Run the full analysis:** `do code/03_analysis.do`. The log is saved to `output/stata/03_analysis.log`. Compare the output with the paper as follows:

  | Paper table | Stata output to look at | Should match |
  |---|---|---|
  | Table 3 (types by area) | `tab sec itype, row nofreq` | row percentages |
  | Table 5 (Test 1) | `estimates table t1_m1 t1_m2 t1_m3` | coefficients to 3 decimals; standard errors to 3 decimals |
  | Table 6 (construction) | `tabstat scaled zero_baseline share_from_scaled, by(sec)` and `tabstat fixed_share, by(sec)` | shares |
  | Table 7 (Test 2 models) | `estimates table t2_m1 t2_m3` | coefficients |
  | Table 8 (Test 3) | `fracreg` output and `estimates table t3_m2 … t3_m5` | coefficients; R² |
  | Table 9 (robustness) | `estimates table r_t0 r_t20 r_active r_noscaled r_country` | outcome and "7+ years" rows |

  **Expected differences, which are not errors:**
  - Linear (regress) models should match R exactly.
  - In the **logit and fractional logit**, Stata and R apply slightly different small-sample corrections to clustered standard errors. Expect the standard errors to differ in the 3rd decimal place; the coefficients should match.
  - In the Test 1 **logit**, Stata reports that WASH "predicts failure perfectly" and drops it. That is expected, because no WASH result is an outcome indicator.

---

## Step 5. Verify the results in R (optional second check)

- [ ] Run `Rscript code/02_analysis.R`. It rewrites `output/tables/*.csv`, `output/figures/*.png` and `output/key_numbers.json`.
- [ ] Open `output/key_numbers.json`. Every number quoted in the paper's text comes from this file. For example:
  - `share_type.reach` = 0.6243 is the "62%" in the abstract.
  - `behind_by_age` gives the 80% / 68% / 47% / 32% figures.
- [ ] If you changed the validation codes in Step 3, the R script picks up the new codes automatically.

---

## Step 6. Check the text against the tables

For each number in the paper, its source file in `output/tables/` is:

| Section of paper | Source |
|---|---|
| Abstract and Introduction | `output/key_numbers.json` |
| Table 1 | `data/*` row counts (Step 2) |
| Table 2 | `table1_projects.csv` |
| Table 3 | `table2_type_by_sector.csv` |
| Table 4 | `table3_validation.csv` |
| Table 5 | `table4_test1_outcome_models.csv`, `table4_stats.csv` |
| Logit AMEs in 5.1 | `table4_logit_ame.csv` |
| Table 6 | `table5_construction_by_sector.csv` |
| Table 7 | `table6_test2_models.csv`, `table6_stats.csv` |
| Table 8 | `table7_test3_models.csv`, `table7_stats.csv` |
| Table 9 | `table8_robustness.csv` |
| Figure 3 | `fig3_predicted_curve.csv` |
| Appendix Table A1 | `tableA1_manual_subsample.csv` |

The paper's file numbering is off by one from the CSV numbering because the paper adds a sample-construction table, which becomes Table 1.

---

## Step 7. Check citations and quotations

- [ ] Open each reference and confirm that the claim attributed to it. The ones to read closely are:
  - **IEG (2025)**, the Scorecard formative evaluation approach paper (November 2025). It is described as citing the literature on gaming in performance systems.
  - **IEG (2016)**, *Behind the Mirror*: self-evaluation geared to reporting and accountability rather than learning.
  - **IEG (2024)**, RAP 2024: improving results monitoring is one of four levers.
  - **World Bank (2024b)**, the press release of 9 April 2024. Check the exact wording of "to focus on outcomes, rather than inputs".
  - **González (2026)**, CGD Policy Paper 402. Check the exact wording of "a structural remedy cannot resolve an analytical problem".
- [ ] Fill in the placeholders: affiliation and contact on page 1, the repository link, and the "Use of AI tools" statement in the appendix.

---

## Step 8. Rebuild the paper after any change

```bash
Rscript code/02_analysis.R            # tables, figures, key numbers
python3 paper/build_paper.py          # paper.html + PDF
python3 paper/html_to_blocks.py       # structured text for Word
node paper/build_docx.js              # Word file (needs: npm install docx)
```

You can also edit the Word file (`paper/counting-reach-not-welfare.docx`) directly, for example to apply a journal template. If you do, make sure any number you change still matches the outputs.

---

## Quick reference: headline numbers

| Number in paper | Value | Verified by |
|---|---|---|
| Results / projects / countries | 3,617 / 1,129 / 124 (+2 regional) | A1, A2 |
| Share reach / outcome | 62.4% / 14.4% | B1, B2 |
| Projects with no outcome indicator | 79.5% | B3 |
| Zero baseline | 90.8% | C3 |
| Achieved total from rescaled figures (all / health) | 29.4% / 62.6% | C4, C6 |
| Female figures informative | 235 of 1,734 (13.6%) | C10 |
| Share "behind" (all / <3 yrs / 7+ yrs) | 56.7% / 79.9% / 31.8% | D1–D3 |
| Outcome-indicator penalty | +13.3 pp (SE 0.043) | D6, D7 |
| WASH vs health, outcome probability | −23.7 pp | E1 |
