/*==============================================================================
  03_analysis.do
  "Counting Reach, Not Welfare: Testing the World Bank Group Scorecard
   Against a Welfare Anchor"

  Stata replication of code/02_analysis.R (same samples, same specifications).
  Requires Stata 15 or later. Only built-in commands are used (regress, logit,
  fracreg, margins, estimates table); esttab is optional (ssc install estout).

  Run from the welfare-anchor folder:   do code/03_analysis.do
==============================================================================*/

version 15
clear all
set more off
capture log close
capture mkdir "output"
capture mkdir "output/stata"
log using "output/stata/03_analysis.log", replace text

* ------------------------------------------------------------------------------
* 0. Common recodes (program applied to each dataset)
*    Base categories match the R script: health, AFE, LIC, IPF, HNP, FY19-or-earlier
* ------------------------------------------------------------------------------
capture program drop recode_common
program define recode_common
    * project identifier for clustering
    egen pid = group(project_id)
    egen cid = group(country)

    * results area (sector) -- base = health
    capture confirm variable sector
    if !_rc {
        gen byte sec = .
        replace sec = 1 if sector == "health"
        replace sec = 2 if sector == "wash"
        replace sec = 3 if sector == "gender_equality"
        replace sec = 4 if sector == "economic_opportunity"
        replace sec = 5 if sector == "financial_services"
        label define sec 1 "Health" 2 "WASH" 3 "Gender equality" ///
                         4 "Economic opportunity" 5 "Financial services", replace
        label values sec sec
    }

    * region -- base = AFE (alphabetical encode puts AFE first)
    encode region, gen(reg)

    * income group -- base = LIC
    gen byte inc = .
    replace inc = 1 if income == "LIC"
    replace inc = 2 if income == "LMC"
    replace inc = 3 if income == "UMC"
    replace inc = 4 if income == "HIC"
    replace inc = 5 if income == "Unknown"
    label define inc 1 "LIC" 2 "LMC" 3 "UMC" 4 "HIC" 5 "Unknown", replace
    label values inc inc

    * lending instrument -- base = IPF
    gen byte instr = 1 if instrument == "IPF"
    replace instr = 2 if instrument == "P4R"
    replace instr = 3 if instrument == "DPL"
    label define instr 1 "IPF" 2 "PforR" 3 "DPF", replace
    label values instr instr

    * lead global department -- base = HNP
    encode dept, gen(dep)
    quietly levelsof dep if dept == "HNP", local(hnp)
    fvset base `hnp' dep

    * approval cohort -- base = FY19 or earlier
    gen byte cohort = 1 if approval_fy <= 2019
    replace cohort = 2 if inrange(approval_fy, 2020, 2021)
    replace cohort = 3 if inrange(approval_fy, 2022, 2023)
    replace cohort = 4 if approval_fy == 2024
    replace cohort = 5 if approval_fy >= 2025 & !missing(approval_fy)
    label define cohort 1 "FY19 or earlier" 2 "FY20-21" 3 "FY22-23" 4 "FY24" ///
                        5 "FY25 (post-Scorecard)", replace
    label values cohort cohort
end

* ==============================================================================
* TEST 1. Welfare relevance: what do Scorecard results measure?
* ==============================================================================
use "data/results_clean.dta", clear
recode_common

gen byte itype = 1 if ind_type == "reach"
replace itype = 2 if ind_type == "output"
replace itype = 3 if ind_type == "outcome"
replace itype = 4 if ind_type == "unclassifiable"
label define itype 1 "Reach" 2 "Output" 3 "Outcome" 4 "Unclassifiable", replace
label values itype itype

* Table 2: composition by results area
tab sec itype, row nofreq
tab itype

* Projects that feed no outcome indicator into the Scorecard
preserve
    collapse (max) any_outcome = outcome (mean) share_reach = reach, by(project_id)
    gen byte only_reach = share_reach == 1
    summarize any_outcome only_reach
restore

* Table 4: outcome indicator ~ design characteristics (clustered by project)
global ctrl "i.reg fcv i.inc ida i.instr log_commit"

regress outcome i.sec i.cohort, vce(cluster pid)
estimates store t1_m1
regress outcome i.sec $ctrl i.cohort, vce(cluster pid)
estimates store t1_m2
regress outcome i.sec $ctrl i.cohort i.dep, vce(cluster pid)
estimates store t1_m3
* Note: no WASH result is an outcome indicator, so logit drops WASH (perfect prediction)
logit outcome i.sec $ctrl i.cohort, vce(cluster pid)
estimates store t1_m4
margins, dydx(sec cohort)

estimates table t1_m1 t1_m2 t1_m3, keep(i.sec i.cohort fcv ida log_commit) ///
    b(%9.3f) se(%9.3f) stats(N r2) title("Table 4. Outcome indicator (LPM)")

* ==============================================================================
* TEST 2. Measurement integrity: measured or constructed figures?
* ==============================================================================

* (a) Rescaled results, among results not masked for double counting
preserve
    keep if double_counted == 0
    summarize scaled zero_baseline pct_unit
    * share of the reported achieved total that comes from rescaled indicators
    gen double ach_pos = max(achieved, 0) if !missing(achieved)
    egen double tot_all = total(ach_pos)
    egen double tot_scaled = total(ach_pos * scaled)
    display "Share of achieved total from rescaled indicators: " %6.3f tot_scaled[1] / tot_all[1]
    bysort sec: egen double s_all = total(ach_pos)
    bysort sec: egen double s_sc = total(ach_pos * scaled)
    gen double share_from_scaled = s_sc / s_all
    tabstat scaled zero_baseline share_from_scaled, by(sec) stat(mean) format(%6.3f)

    regress scaled i.sec pct_unit i.itype $ctrl i.cohort, vce(cluster pid)
    estimates store t2_m3
restore

* (b) Fixed-share female figures (project x Scorecard sub-indicator pairs)
use "data/gender_pairs.dta", clear
recode_common
tab pair_status
tabstat fixed_share, by(sec) stat(mean n) format(%6.3f)

regress fixed_share i.sec $ctrl i.cohort, vce(cluster pid)
estimates store t2_m1
logit fixed_share i.sec $ctrl i.cohort, vce(cluster pid)
estimates store t2_m2
margins, dydx(sec cohort)

estimates table t2_m1 t2_m3, keep(i.sec i.cohort fcv ida log_commit) ///
    b(%9.3f) se(%9.3f) stats(N r2) title("Table 6. Constructed figures (LPM)")

* ==============================================================================
* TEST 3. Progress judgement: does "behind" measure performance or time?
* ==============================================================================
use "data/results_clean.dta", clear
recode_common
keep if judgeable == 1 & ind_type != "unclassifiable"

gen byte itype = 1 if ind_type == "reach"
replace itype = 2 if ind_type == "output"
replace itype = 3 if ind_type == "outcome"
label define itype 1 "Reach" 2 "Output" 3 "Outcome", replace
label values itype itype

gen byte age_bin = 1 if years_since_approval < 3
replace age_bin = 2 if years_since_approval >= 3 & years_since_approval < 5
replace age_bin = 3 if years_since_approval >= 5 & years_since_approval < 7
replace age_bin = 4 if years_since_approval >= 7 & !missing(years_since_approval)
label define age_bin 1 "<3 yrs" 2 "3-5 yrs" 3 "5-7 yrs" 4 "7+ yrs", replace
label values age_bin age_bin

summarize behind
tabstat behind, by(age_bin) stat(mean n) format(%6.3f)
tabstat behind progress_frac, by(itype) stat(mean p50 n) format(%6.3f)

* (1) Fractional logit of progress (Papke & Wooldridge 1996)
fracreg logit progress_frac c.elapsed##c.elapsed i.itype scaled i.sec i.reg fcv ///
    i.inc i.instr log_commit, vce(cluster pid)
estimates store t3_m1
margins itype, at(elapsed = (0.25 0.5 0.75 1))

* (2)-(5) Linear probability models of "behind"
regress behind i.age_bin, vce(cluster pid)
estimates store t3_m2
regress behind i.age_bin i.itype scaled i.sec, vce(cluster pid)
estimates store t3_m3
regress behind i.age_bin i.itype scaled i.sec i.reg fcv i.inc i.instr log_commit, vce(cluster pid)
estimates store t3_m4
regress behind i.age_bin i.itype scaled i.sec i.reg fcv i.inc i.instr log_commit i.dep, vce(cluster pid)
estimates store t3_m5

estimates table t3_m2 t3_m3 t3_m4 t3_m5, keep(i.age_bin i.itype scaled fcv log_commit) ///
    b(%9.3f) se(%9.3f) stats(N r2) title("Table 7. Behind schedule (LPM)")

* Robustness (Table 8)
global full "i.age_bin i.itype scaled i.sec i.reg fcv i.inc i.instr log_commit i.dep"
regress behind_t0  $full, vce(cluster pid)
estimates store r_t0
regress behind_t20 $full, vce(cluster pid)
estimates store r_t20
regress behind $full if active == 1, vce(cluster pid)
estimates store r_active
regress behind i.age_bin i.itype i.sec i.reg fcv i.inc i.instr log_commit i.dep ///
    if scaled == 0, vce(cluster pid)
estimates store r_noscaled
regress behind $full, vce(cluster cid)
estimates store r_country
logit behind i.age_bin i.itype scaled i.sec i.reg fcv i.inc i.instr log_commit, vce(cluster pid)
estimates store r_logit

estimates table r_t0 r_t20 r_active r_noscaled r_country, keep(i.age_bin i.itype) ///
    b(%9.3f) se(%9.3f) stats(N) title("Table 8. Robustness")

* Optional: publication tables with esttab (ssc install estout)
* esttab t1_m1 t1_m2 t1_m3 using "output/stata/table4.rtf", se b(3) se(3) ///
*     keep(*.sec *.cohort) star(* 0.10 ** 0.05 *** 0.01) replace

log close
