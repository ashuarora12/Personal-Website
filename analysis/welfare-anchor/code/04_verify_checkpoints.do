/*==============================================================================
  04_verify_checkpoints.do
  Checks every key number in the paper, using Stata alone.
  Each line prints PASS or FAIL and the value Stata finds next to the value
  reported in the paper. Run 03_analysis.do first if you want the full tables.

  Run from the welfare-anchor folder:   do code/04_verify_checkpoints.do
==============================================================================*/

version 15
clear all
set more off
global nfail = 0
global npass = 0

capture program drop chk
program define chk
    * usage: chk "label" value expected tolerance
    args label value expected tol
    if abs(`value' - `expected') <= `tol' {
        display as result "PASS  " as text %-58s "`label'" "  Stata = " %12.4f `value' "   paper = " %12.4f `expected'
        global npass = $npass + 1
    }
    else {
        display as error  "FAIL  " as text %-58s "`label'" "  Stata = " %12.4f `value' "   paper = " %12.4f `expected'
        global nfail = $nfail + 1
    }
end

* ------------------------------------------------------------------ STEP A: dataset sizes
use "data/results_clean.dta", clear
quietly count
chk "A1 results (rows in results_clean)" r(N) 3617 0
egen pid = group(project_id)
quietly summarize pid
chk "A2 projects" r(max) 1129 0

quietly count if ind_type == "reach"
chk "A3 reach indicators" r(N) 2258 0
quietly count if ind_type == "output"
chk "A4 output indicators" r(N) 569 0
quietly count if ind_type == "outcome"
chk "A5 outcome indicators" r(N) 520 0
quietly count if ind_type == "unclassifiable"
chk "A6 unclassifiable indicators" r(N) 270 0

quietly count if double_counted == 1
chk "A7 masked for double counting" r(N) 485 0
quietly count if judgeable == 1
chk "A8 judgeable (positive target, >=20% elapsed)" r(N) 1809 0
quietly count if judgeable == 1 & ind_type != "unclassifiable"
chk "A9 Test 3 sample" r(N) 1709 0

* ------------------------------------------------------------------ STEP B: Test 1 shares
quietly summarize reach
chk "B1 share reach (62.4%)" r(mean) 0.6243 0.0005
quietly summarize outcome
chk "B2 share outcome (14.4%)" r(mean) 0.1438 0.0005
preserve
    collapse (max) any_out = outcome (mean) sh_reach = reach, by(project_id)
    quietly summarize any_out
    chk "B3 projects with no outcome indicator (79.5%)" 1-r(mean) 0.7954 0.0005
    gen only_reach = sh_reach == 1
    quietly summarize only_reach
    chk "B4 projects with only reach indicators (54.5%)" r(mean) 0.5447 0.0005
restore
quietly summarize outcome if sector == "wash"
chk "B5 WASH outcome share (0%)" r(mean) 0 0.0001

* ------------------------------------------------------------------ STEP C: Test 2 construction
preserve
    keep if double_counted == 0
    quietly count
    chk "C1 results not double counted" r(N) 3132 0
    quietly summarize scaled
    chk "C2 share rescaled (10.2%)" r(mean) 0.1015 0.0005
    quietly summarize zero_baseline
    chk "C3 share zero baseline (90.8%)" r(mean) 0.908 0.0005
    gen double a = max(achieved, 0) if !missing(achieved)
    quietly summarize a
    local tot = r(sum)
    quietly summarize a if scaled == 1
    chk "C4 achieved total from rescaled (29.4%)" r(sum)/`tot' 0.2938 0.0005
    chk "C5 achieved total, millions (802.5)" `tot'/1e6 802.532 0.01
    quietly summarize a if sector == "health"
    local th = r(sum)
    quietly summarize a if sector == "health" & scaled == 1
    chk "C6 health: achieved from rescaled (62.6%)" r(sum)/`th' 0.6259 0.0005
restore

* Worked example: project P144893, health facilities x 10,000
quietly summarize achieved if project_id == "P144893" & strpos(indicator_text, "Health facilities constructed") > 0
chk "C7 P144893 facilities: achieved = 137 x 10,000" r(mean) 1370000 0.5

use "data/gender_pairs.dta", clear
quietly count
chk "C8 pairs with a female figure" r(N) 1734 0
quietly count if pair_status == "fixed_share"
chk "C9 fixed-share female figures" r(N) 387 0
quietly count if pair_status == "informative"
chk "C10 informative female figures" r(N) 235 0
quietly count if pair_status == "no_progress"
chk "C11 no progress yet" r(N) 665 0
quietly summarize fixed_share if sector == "health"
chk "C12 health: fixed-share female (55.1%)" r(mean) 0.5507 0.0005

* ------------------------------------------------------------------ STEP D: Test 3 and key models
use "data/results_clean.dta", clear
egen pid = group(project_id)
keep if judgeable == 1 & ind_type != "unclassifiable"
quietly summarize behind
chk "D1 share behind (56.7%)" r(mean) 0.567 0.0005
gen byte age_bin = 1 if years_since_approval < 3
replace age_bin = 2 if years_since_approval >= 3 & years_since_approval < 5
replace age_bin = 3 if years_since_approval >= 5 & years_since_approval < 7
replace age_bin = 4 if years_since_approval >= 7 & !missing(years_since_approval)
quietly summarize behind if age_bin == 1
chk "D2 behind, <3 years (79.9%)" r(mean) 0.7986 0.0005
quietly summarize behind if age_bin == 4
chk "D3 behind, 7+ years (31.8%)" r(mean) 0.3182 0.0005

* recodes for the regression (same as 03_analysis.do)
gen byte itype = 1 if ind_type == "reach"
replace itype = 2 if ind_type == "output"
replace itype = 3 if ind_type == "outcome"
gen byte sec = 1 if sector == "health"
replace sec = 2 if sector == "wash"
replace sec = 3 if sector == "gender_equality"
replace sec = 4 if sector == "economic_opportunity"
replace sec = 5 if sector == "financial_services"
encode region, gen(reg)
gen byte inc = 1 if income == "LIC"
replace inc = 2 if income == "LMC"
replace inc = 3 if income == "UMC"
replace inc = 4 if income == "HIC"
replace inc = 5 if income == "Unknown"
gen byte instr = 1 if instrument == "IPF"
replace instr = 2 if instrument == "P4R"
replace instr = 3 if instrument == "DPL"
encode dept, gen(dep)
quietly levelsof dep if dept == "HNP", local(hnp)
fvset base `hnp' dep

quietly regress behind i.age_bin, vce(cluster pid)
chk "D4 R-squared, timing only (0.125)" e(r2) 0.1246 0.0005
quietly regress behind i.age_bin i.itype scaled i.sec i.reg fcv i.inc i.instr log_commit i.dep, vce(cluster pid)
chk "D5 R-squared, full model (0.260)" e(r2) 0.260 0.0005
chk "D6 outcome indicator coefficient (+0.133)" _b[3.itype] 0.133 0.0005
chk "D7 outcome indicator clustered SE (0.043)" _se[3.itype] 0.043 0.0015
chk "D8 7+ years coefficient (-0.496)" _b[4.age_bin] -0.496 0.0005
chk "D9 rescaled coefficient (-0.115)" _b[scaled] -0.115 0.0005

* Test 1 headline model (results sample)
use "data/results_clean.dta", clear
egen pid = group(project_id)
gen byte sec = 1 if sector == "health"
replace sec = 2 if sector == "wash"
replace sec = 3 if sector == "gender_equality"
replace sec = 4 if sector == "economic_opportunity"
replace sec = 5 if sector == "financial_services"
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
quietly regress outcome i.sec i.reg fcv i.inc ida i.instr log_commit i.cohort, vce(cluster pid)
chk "E1 Test 1: WASH vs health (-0.237)" _b[2.sec] -0.2375 0.0005
chk "E2 Test 1: financial services vs health (-0.160)" _b[5.sec] -0.1603 0.0005
chk "E3 Test 1: FY25 cohort (+0.057)" _b[5.cohort] 0.0566 0.0005
chk "E4 Test 1: R-squared (0.065)" e(r2) 0.0655 0.0005

display _newline as text "Checks passed: $npass    Checks failed: $nfail"
