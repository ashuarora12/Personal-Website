# Counting Reach, Not Welfare — replication package

Working paper: *Counting Reach, Not Welfare: Testing the World Bank Group Scorecard Against a Welfare Anchor* (Ashu Arora, draft, October 2026).
PDF: [`paper/counting-reach-not-welfare.pdf`](paper/counting-reach-not-welfare.pdf)

The paper tests whether the people-level results behind the World Bank Group's FY25 Scorecard measure welfare. It has three tests:

1. **Welfare relevance.** Do the results measure changes in welfare, or only how many people or firms were reached?
2. **Measurement integrity.** Are the reported figures measured, or constructed from conversion factors, fixed shares and zero baselines?
3. **Progress judgement.** Does a linear on-track rule measure performance, or time? And does it penalise outcome indicators?

## Folder layout

```
code/01_build_dataset.py     raw Scorecard exports -> clean datasets (CSV + Stata .dta) and validation samples
code/00_validation_scores.py precision / recall / kappa of the indicator classifier
code/02_analysis.R           all tables, figures and key numbers (base R + sandwich/lmtest, ggplot2)
code/03_analysis.do          the same models in Stata (built-in commands only)
data/results_clean.*         3,617 results (project indicators), 1,129 projects        <- Tests 1-3
data/gender_pairs.*          1,734 project x sub-indicator pairs with a female figure  <- Test 2 (gender)
data/projects_clean.*        1,129 projects
validation/                  hand-coded development (200) and held-out test (200) samples
output/tables/*.csv          every table in the paper
output/figures/*.png         every figure in the paper
output/key_numbers.json      every number quoted in the text
paper/build_paper.py         builds paper.html and the PDF from the outputs above
```

The raw exports are read from `../who-benefits/data/raw/` (FY25 cycle, from scorecard.worldbank.org).

## How to reproduce

Run these from this folder:

```bash
python3 code/01_build_dataset.py      # needs pandas, numpy, openpyxl
Rscript code/02_analysis.R            # needs sandwich, lmtest, ggplot2, jsonlite, scales
python3 paper/build_paper.py          # needs pandas, playwright (Chromium)
```

To run the same models in Stata (version 15 or later), open Stata in this folder and type `do code/03_analysis.do`. The log is written to `output/stata/`.

**Checks already done.** The `.dta` files were read back with R `haven` and Python. An independent re-estimation of Table 5, column 2 and Table 8, column 4 in Python (statsmodels) reproduces the R coefficients and clustered standard errors exactly. **The Stata do-file has not been run, because Stata was not available.** Run it once and compare its output with `output/tables/`. Expect small differences only in the logit and fractional-logit standard errors, because small-sample corrections differ between programs.

## Codebook (main variables, `results_clean`)

| Variable | Meaning |
|---|---|
| `ind_type` | results-chain type of the indicator wording: reach / output / outcome / unclassifiable (rules in Appendix A) |
| `outcome`, `reach` | 0/1 dummies from `ind_type` |
| `scaled` | 1 if the progress conversion factor is above 0 and not equal to 1, meaning the figure was rescaled into the Scorecard unit |
| `zero_baseline` | 1 if the calculated baseline equals 0 |
| `double_counted` | 1 if the result is masked for double counting |
| `achieved`, `expected` | progress minus baseline; target minus baseline |
| `elapsed` | share of the approval-to-closing period elapsed at the progress date |
| `progress_frac` | achieved / expected, capped at 1 |
| `behind` | 1 if `progress_ratio < elapsed - 0.10` (`behind_t0`, `behind_t20`: alternative thresholds) |
| `judgeable` | in the Test 3 sample (positive target, not double counted, elapsed ≥ 0.2) |
| `sector` | Scorecard results area |
| `region`, `income`, `fcv`, `ida`, `instrument`, `dept`, `log_commit`, `approval_fy`, `years_since_approval` | project characteristics |

In `gender_pairs`, the variable `pair_status` takes the values fixed_share / no_progress / women_only / identical_share / inconsistent / informative. `gap_pp` is the achieved minus the planned women's share, in percentage points.

## Before you circulate the paper: author checklist

1. **Re-code the validation samples yourself.** `validation/dev_sample_coded.csv` and `validation/test_sample_coded.csv` hold a first-pass coding done with Claude, not by you. Review the `manual_type` column of the test file without looking at `rule_type`, change any codes you disagree with, then re-run `python3 code/00_validation_scores.py` and the R script. The paper's κ and precision/recall figures update automatically. Ideally, have a second person code the test set as well, and report agreement between the two coders.
2. **Run the Stata do-file** and confirm that it matches the R output.
3. **Check the two direct quotations against the originals.** These are the April 2024 press release ("to focus on outcomes, rather than inputs") and González (2026) ("a structural remedy cannot resolve an analytical problem").
4. **Check the reference list.** Every reference was checked to exist. Still open the IEG 2025 approach paper and RAP 2024, because the paper paraphrases them.
5. **Fill in the placeholders:** your affiliation and contact details on page 1, the repository link, and the AI-use statement in the appendix.
6. **Keep the framing of "behind".** It is the author's linear on-track rule, not an official WBG rating, and the paper says so. Keep that caveat in any blog or pitch version.
