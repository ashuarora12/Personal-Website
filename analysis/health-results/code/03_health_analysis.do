/*==============================================================================
  03_health_analysis.do
  "What Is Behind 'People Receiving Quality Health Services'? Measurement in
   the World Bank Group's Health Results"  -  Stata replication and checks.

  Reproduces tables 1-9 and checks every headline number against the paper
  (PASS/FAIL lines; the last line reports the totals).
  Built-in commands only; Stata 15 or later.
  Run from the health-results folder:   do code/03_health_analysis.do
==============================================================================*/
version 15
clear all
set more off
capture mkdir "output/stata"
capture log close
log using "output/stata/03_health_analysis.log", replace text

global npass = 0
global nfail = 0
capture program drop chk
program define chk
    args label value expected tol
    if abs(`value' - `expected') <= `tol' {
        display as result "PASS  " as text %-56s "`label'" "  Stata = " %12.4f `value' "   paper = " %12.4f `expected'
        global npass = $npass + 1
    }
    else {
        display as error  "FAIL  " as text %-56s "`label'" "  Stata = " %12.4f `value' "   paper = " %12.4f `expected'
        global nfail = $nfail + 1
    }
end

* ==============================================================================
* Table 1: sample and reconciliation
* ==============================================================================
use "data/health_results.dta", clear
quietly count
chk "T1 health results (non-disaggregated)" r(N) 226 0
egen pid = group(project_id)
quietly summarize pid
chk "T1 projects" r(max) 138 0
quietly count if double_counted == 1
chk "T1 masked for double counting" r(N) 123 0
quietly summarize achieved_m if double_counted == 1
chk "T1 masked results carry zero" r(sum) 0 0.0001

keep if double_counted == 0
quietly summarize achieved_m
local wb = r(sum)
chk "T1 WB project sum = published WB (310.55m)" `wb' 310.552868 0.0001
* published WBG = WB + IFC (68.310599) + MIGA (0.0631)
chk "T1 WBG = WB + IFC + MIGA (378.93m)" `wb'+68.310599+0.0631 378.926567 0.0001
quietly count if achieved_m > 0
chk "T1 results with positive contribution" r(N) 92 0

* ==============================================================================
* Tables 2-3: measurement method and service family
* ==============================================================================
table method, contents(sum achieved_m count achieved_m) format(%9.2f)
foreach m in direct adjusted coverage unit {
    quietly summarize achieved_m if method == "`m'"
    local s_`m' = r(sum) / `wb'
}
chk "T2 share direct (37.4%)"   `s_direct'   0.374148 0.0005
chk "T2 share adjusted (22.8%)" `s_adjusted' 0.228286 0.0005
chk "T2 share coverage (29.2%)" `s_coverage' 0.292298 0.0005
chk "T2 share unit (10.5%)"     `s_unit'     0.105268 0.0005
quietly summarize achieved_m if family == "vaccination"
chk "T3 share vaccination (23.8%)" r(sum)/`wb' 0.237888 0.0005
quietly summarize achieved_m if not_reproducible == 1
chk "T3 not reproducible, million (33.1)" r(sum) 33.108438 0.001

* worked example: P144893, facilities x 10,000
quietly summarize achieved_m if project_id == "P144893" & strpos(indicator_text, "facilities") > 0
chk "Example P144893: 137 facilities x 10,000 = 1.37m" r(sum) 1.37 0.0001

* ==============================================================================
* Table 4: bounds under alternative counting rules
* ==============================================================================
quietly summarize achieved_m if not_reproducible == 0
chk "T4 rule (1) excl. non-reproducible" r(sum) 277.44443 0.001
quietly summarize achieved_m if method != "unit"
chk "T4 rule (2) excl. unit conversions" r(sum) 277.86172 0.001
quietly summarize achieved_m if method != "coverage"
chk "T4 rule (3) excl. coverage conversions" r(sum) 219.778831 0.001
quietly summarize achieved_m if inlist(method, "direct", "adjusted")
chk "T4 rule (4) people counts only" r(sum) 187.087683 0.001
quietly summarize achieved_m if inlist(method, "direct", "adjusted") & not_reproducible == 0
chk "T4 rule (5) rule 4 and reproducible" r(sum) 183.720643 0.001
quietly summarize achieved_m if method == "direct"
chk "T4 rule (6) direct counts only" r(sum) 116.192798 0.001

* ==============================================================================
* Table 5: concentration
* ==============================================================================
preserve
    keep if achieved_m > 0
    gsort -achieved_m
    gen double cum = sum(achieved_m) / `wb'
    chk "T5 top 1 share (12.0%)"  cum[1]  0.119958 0.0005
    chk "T5 top 10 share (59.2%)" cum[10] 0.591615 0.0005
    chk "T5 top 20 share (81.4%)" cum[20] 0.814277 0.0005
    gen double s2 = (achieved_m / `wb')^2
    quietly summarize s2
    chk "T5 Herfindahl index (0.049)" r(sum) 0.048621 0.0005
restore

* ==============================================================================
* Table 6: reported performance by method; portfolio vintage
* ==============================================================================
foreach m in direct unit {
    quietly summarize achieved_m if method == "`m'"
    local a = r(sum)
    quietly summarize expected_m if method == "`m'"
    local r_`m' = `a' / r(sum)
}
chk "T6 achieved/expected, direct (0.80)" `r_direct' 0.801363 0.0005
chk "T6 achieved/expected, unit (1.20)"   `r_unit'   1.195555 0.0005
quietly summarize achieved_m if status == "C"
chk "Vintage: share from closed operations (42.6%)" r(sum)/`wb' 0.426061 0.0005

* ==============================================================================
* Table 7: composition by region and financing (display only)
* ==============================================================================
table region method if achieved_m > 0, contents(sum achieved_m) format(%9.2f)
table ida method if achieved_m > 0, contents(sum achieved_m) format(%9.2f)

* ==============================================================================
* Table 8: women reached
* ==============================================================================
use "data/health_female.dta", clear
keep if double_counted == 0 & achieved_m > 0
quietly summarize achieved_m
local fw = r(sum)
chk "T8 women reached, million (155.35)" `fw' 155.351459 0.001
quietly summarize achieved_m if fixed_share == 1
chk "T8 share from fixed-share figures (59.2%)" r(sum)/`fw' 0.591691 0.0005
quietly summarize female_factor if fixed_share == 1, detail
chk "T8 median female factor (0.508)" r(p50) 0.508219 0.0005

* ==============================================================================
* Table 9: health vs other results areas (all Scorecard results)
* ==============================================================================
capture program drop prep
program define prep
    egen pid = group(project_id)
    gen byte health = sector == "health"
    encode region, gen(reg)
    gen byte inc = 1 if income == "LIC"
    replace inc = 2 if income == "LMC"
    replace inc = 3 if income == "UMC"
    replace inc = 4 if income == "HIC"
    replace inc = 5 if income == "Unknown"
    gen byte instr = 1 if instrument == "IPF"
    replace instr = 2 if instrument == "P4R"
    replace instr = 3 if instrument == "DPL"
    gen byte cohort = 1 if approval_fy <= 2019
    replace cohort = 2 if inrange(approval_fy, 2020, 2021)
    replace cohort = 3 if inrange(approval_fy, 2022, 2023)
    replace cohort = 4 if approval_fy == 2024
    replace cohort = 5 if approval_fy >= 2025 & !missing(approval_fy)
end
global ctl "i.reg fcv i.inc ida i.instr log_commit i.cohort"

use "../welfare-anchor/data/results_clean.dta", clear
prep
regress scaled health $ctl if double_counted == 0, vce(cluster pid)
chk "T9 col 1: health, rescaled (+0.442)" _b[health] 0.441941 0.0005
chk "T9 col 1: clustered SE (0.055)" _se[health] 0.05454 0.0015
regress outcome health $ctl, vce(cluster pid)
chk "T9 col 3: health, outcome indicator (+0.092)" _b[health] 0.09168 0.0005

keep if judgeable == 1 & ind_type != "unclassifiable"
gen byte age_bin = 1 if years_since_approval < 3
replace age_bin = 2 if years_since_approval >= 3 & years_since_approval < 5
replace age_bin = 3 if years_since_approval >= 5 & years_since_approval < 7
replace age_bin = 4 if years_since_approval >= 7 & !missing(years_since_approval)
gen byte outcome_ind = ind_type == "outcome"
regress behind health i.age_bin outcome_ind scaled $ctl, vce(cluster pid)
chk "T9 col 4: health, behind (-0.315)" _b[health] -0.314583 0.0005
chk "T9 col 4: observations" e(N) 1709 0

use "../welfare-anchor/data/gender_pairs.dta", clear
prep
regress fixed_share health $ctl, vce(cluster pid)
chk "T9 col 2: health, fixed-share female (+0.333)" _b[health] 0.33327 0.0005

* ==============================================================================
* Section 9: health workforce
* ==============================================================================
use "data/health_workforce.dta", clear
quietly count
chk "S9 projects in the Scorecard release" r(N) 1131 0
quietly count if theme_health_workforce == 1
chk "S9 projects addressing the health workforce" r(N) 15 0
quietly count if theme_health_workforce == 1 & theme_migration == 1
chk "S9 ... and migration" r(N) 0 0

display _newline as text "Checks passed: $npass    Checks failed: $nfail"
log close
