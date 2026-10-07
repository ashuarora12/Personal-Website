"""
01_build_dataset.py
Builds the clean analysis datasets for
"Counting Reach, Not Welfare: Testing the World Bank Group Scorecard Against a Welfare Anchor".

Input : World Bank Group Corporate Scorecard exports, FY25 cycle (results as of 30 June 2025),
        sheet "WB Project Information" of each CSC_RES_*.xlsx file
        (stored in ../../who-benefits/data/raw/, downloaded from scorecard.worldbank.org).
Output: data/results_clean.csv / .dta   one row per project indicator ("result") feeding the Scorecard
        data/gender_pairs.csv / .dta    one row per project x Scorecard sub-indicator with a female figure
        data/projects_clean.csv / .dta  one row per project
        validation/indicator_validation_sample.csv  random sample for manual coding

Run from the welfare-anchor folder:  python3 code/01_build_dataset.py
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "who-benefits" / "data" / "raw"
DATA = ROOT / "data"
VAL = ROOT / "validation"
CUTOFF = pd.Timestamp("2025-06-30")
SCORECARD_LAUNCH = pd.Timestamp("2024-07-01")  # FY25 start; FY24-FY30 Scorecard presented April 2024

FILES = {
    "HEALTH": "CSC_RES_HEA_SERV.xlsx",
    "WASH": "CSC_RES_WAT_SAN_HYG_TOT.xlsx",
    "GENDER": "CSC_RES_GEN_EQU_BENE.xlsx",
    "FIN": "CSC_RES_FIN_SERV_WOM.xlsx",
}
SECTOR = {  # Scorecard sub-indicator -> short sector label
    "CSC_RES_HEA_SERV": "health",
    "CSC_RES_WAT_SAN_HYG": "wash",
    "CSC_RES_WAT_SAN_SAFE": "wash",
    "CSC_RES_GEN_EQU": "gender_equality",
    "CSC_RES_BENE_ENAB_ECO_OPP": "economic_opportunity",
    "CSC_RES_FIN_SERV": "financial_services",
    "CSC_RES_FIN_SERV_WOM_CUS": "financial_services",
}

# ------------------------------------------------------------------ indicator classification
# Results-chain coding of each project indicator's text (after stripping the ID prefix):
#   outcome = a change in a condition or behaviour of people (income, jobs, health status,
#             learning, service-use rates, yields);
#   output  = something the project produces or does (people trained, works built, loans
#             issued, plans adopted);
#   reach   = a count of people / households / firms who receive, access or benefit from
#             project goods or services.
# Rules are applied in that order. Indicators whose text is only a breakdown label
# ("Of which women", a country name) are coded "unclassifiable".
NOUN = (r"(people|persons?|individuals?|beneficiar\w*|households?|families|farmers|students|pupils|learners|women|girls|"
        r"men|boys|youth|adolescents?|adults|users?|clients?|customers?|patients?|children|infants|mothers|members|"
        r"population|residents|refugees|workers|teachers|staff|entrepreneurs|firms?|enterprises?|m?smes?|msmes|"
        r"businesses|companies|cooperatives|producers|communities|recipients|owners|actors|startups?|agribusinesses)")
# A. welfare outcomes: change in income, jobs, health status, behaviour (adoption, use rates), firm creation
OUTCOME = [
    r"(?<!low )(?<!low-)(?<!middle )\b(incomes?(?![- ](generating|support|areas|countr|groups?))|earnings?|wages?|salar(y|ies)|sales|profits?|revenues?)\b",
    r"\b(mortality|deaths?|stunting|wasting|an(a)?emi\w*|malnutrition|prevalence|incidence|survival)\b",
    r"\b(learning outcomes?|test scores?|proficien\w*|literacy)\b",
    r"\b(consumption|food (in)?security|travel time|time (saved|spent))\b",
    r"\b(self-)?employed\b", r"\bemployment (rate|status|outcomes?)\b", r"\bgig work\b",
    r"\bnew (firms?|businesses|enterprises|agribusinesses|companies|startups?|m?smes?)\b",
    NOUN + r"[^.;]{0,40}\badopt(ed|ing|ion)\b",
    r"\b(fully )?vaccinated\b", r"\brepresentation of women\b", r"\bland rights\b",
    r"\b(making|receiving) digital payments\b",
    r"^(the )?(percentage|proportion|share|rate|ratio) of\b",
    r"\b(increase|reduction|decrease|improvement|rise|decline) in (?!the number|number)",
]
# B. training and certification: outputs even when they count people
TRAINING = [r"\btrain(ed|ing|ees?)\b", r"\bcertif\w*", r"\bapprentice\w*", r"\b(courses?|curricul\w*)\b"]
# C. jobs (after training, so "trained in ... jobs" stays an output)
JOBS = [r"\bjobs?\b(?![- ](fair|portal|cent))", r"\b(employment|placed in work)\b"]
# D. reach: beneficiaries receiving / accessing / using project goods or services
REACH = [
    NOUN + r"[^.;]{0,60}\b(receiv\w*|provided with|access\w*|benefit\w*|using|use of|enrol\w*|reached|supported|"
    r"covered|served|participat\w*|assisted|with (improved |new )?access|granted|financed|accepted)",
    r"\b(beneficiar\w*|recipients)\b", r"\benrol(l)?ment\b", r"\b(deliveries|visits|consultations|cases)\b",
]
# E. outputs: things the project produces or does
OUTPUT = [
    r"\b(issued|disbursed|sub-?loans?|number of loans|loans (to|issued|disbursed|facilitated))\b",
    r"\b(construct\w*|buil[td]|rehabilitat\w*|reconstruct\w*|upgrad\w*|install\w*|refurbish\w*|renovat\w*)\b",
    r"\b(prepared|validated|appointed|deployed|recruited|established|adopted|approved|developed|launched|operational|enacted)\b",
    r"\b(registr(y|ies)|systems?|plans?|polic(y|ies)|laws?|regulations?|reforms?|strategies|documents?|profiles?|technologies)\b",
    r"\b(km|kilomet\w*|hectares?|facilities|classrooms|connections)\b",
]
BREAKDOWN = re.compile(r"^(of which|o/w|of these)\b|^(female|male|women|men|youth|girls|boys|regional|national|total)"
                       r"( ?[-–(].{0,25})?$")


def clean_text(s):
    s = re.sub(r"^IN\d+[^:]*:\s*", "", str(s)).strip()
    return re.sub(r"\s+", " ", s)


def _any(pats, t):
    return any(re.search(p, t) for p in pats)


def classify(text):
    """Results-chain type of a project indicator: outcome / output / reach / unclassifiable."""
    t = text.lower()
    t = re.sub(r"^(pdo|iri?|dli|ir)[- #]*\d*[a-z]?[:.)]?\s*|^\d+(\.\d+)*[a-z]?[.)]?\s+", "", t)
    if len(t) < 4 or BREAKDOWN.match(t):
        return "unclassifiable"
    if re.search(r"benefit\w* from actions to", t):  # Scorecard reach wording
        return "reach"
    if _any(OUTCOME, t):
        return "outcome"
    if _any(TRAINING, t):
        return "output"
    if _any(JOBS, t):
        return "outcome"
    if _any(REACH, t):
        return "reach"
    if _any(OUTPUT, t):
        return "output"
    if re.search(r"\b" + NOUN + r"\b", t):
        return "reach"
    return "unclassifiable"


def num(s):
    return pd.to_numeric(s, errors="coerce")


# ------------------------------------------------------------------ load
def load():
    frames = []
    for k, f in FILES.items():
        d = pd.read_excel(RAW / f, sheet_name="WB Project Information")
        d["source_file"] = k
        frames.append(d)
    p = pd.concat(frames, ignore_index=True)
    p["sub"] = p.sub_indicator_code.fillna(p.indicator_code)
    p = p.drop_duplicates(subset=[c for c in p.columns if c != "source_file"])  # same row in two exports
    for c in ["Approval_Date", "Closing_Date", "Progress_Date", "Baseline_Date", "Target_Date"]:
        p[c] = pd.to_datetime(p[c], errors="coerce")
    return p


def project_covariates(p):
    g = p.groupby("Project_ID").agg(
        project_name=("Project_Name", "first"), country=("CountryEconomy_Name", "first"),
        country_code=("CountryEconomy_Code", "first"), region=("WB_Region", "first"),
        dept=("Global_Department", "first"), status=("Project_Status", "first"),
        instrument=("Lending_Instrument", "first"), financier=("Agreement_Type", "first"),
        commitment=("Net_Commitment_Total", "first"), approval=("Approval_Date", "first"),
        closing=("Closing_Date", "first"), fcv=("FCV_Flag", "first"), ldc=("LDC_Flag", "first"),
        sids=("SIDS_Flag", "first"), income=("Income_Group", "first"),
        disability_incl=("Disability_Inclusive_Flag", "first")).reset_index()
    g = g.rename(columns={"Project_ID": "project_id"})
    g["fcv"] = (g.fcv == "Y").astype(int)
    g["ldc"] = (g.ldc == "Y").astype(int)
    g["sids"] = (g.sids == "Y").astype(int)
    g["disability_incl"] = (g.disability_incl == "Yes").astype(int)
    g["active"] = (g.status == "A").astype(int)
    g["ida"] = (g.financier == "IDA").astype(int)
    g["income"] = g.income.fillna("Unknown")
    g["commitment_musd"] = num(g.commitment) / 1e6
    g["log_commit"] = np.log(g.commitment_musd.clip(lower=0.1))
    g["approval_fy"] = g.approval.dt.year + (g.approval.dt.month >= 7).astype(int)
    g["years_since_approval"] = (CUTOFF - g.approval).dt.days / 365.25
    g["post_scorecard"] = (g.approval >= SCORECARD_LAUNCH).astype(int)
    g["planned_years"] = (g.closing - g.approval).dt.days / 365.25
    # small departments pooled so fixed effects are estimable
    big = g.dept.value_counts()
    g["dept"] = g.dept.where(g.dept.map(big) >= 20, "OTHER")
    return g.drop(columns=["commitment"])


# ------------------------------------------------------------------ results dataset
def results(p, proj):
    t = p[p.Demographic_Disaggregation == "Total"].copy()
    t["indicator_text"] = t.Project_Indicator.map(clean_text)
    t["ind_type"] = t.indicator_text.map(classify)
    t["sector"] = t["sub"].map(SECTOR)
    t["unit"] = t.Unit_of_Measure.fillna("Missing")
    t["pct_unit"] = (t.unit == "Percentage").astype(int)
    cf = num(t.Progress_Conversion_Factor)
    t["conv_factor"] = cf
    t["scaled"] = ((cf > 0) & (cf != 1)).astype(int)  # figure rescaled into the Scorecard unit
    t["zero_baseline"] = (num(t.Calculated_Baseline_Value).fillna(0) == 0).astype(int)
    t["double_counted"] = (t.Double_Counting_Flag == "Y").astype(int)
    t["achieved"] = num(t.Achieved_Results)
    t["expected"] = num(t.Expected_Results)
    span = (t.Closing_Date - t.Approval_Date).dt.days.clip(lower=30)
    t["elapsed"] = ((t.Progress_Date - t.Approval_Date).dt.days / span).clip(0, 1)
    t["progress_ratio"] = (t.achieved / t.expected).where(t.expected > 0)
    t["progress_frac"] = t.progress_ratio.clip(0, 1)
    # Scorecard-style judgement: share of target delivered below share of time elapsed (10-pt tolerance)
    for thr, name in [(0.10, "behind"), (0.0, "behind_t0"), (0.20, "behind_t20")]:
        t[name] = np.where(t.progress_ratio.notna() & t.elapsed.notna(),
                           (t.progress_ratio < t.elapsed - thr).astype(float), np.nan)
    t["judgeable"] = ((t.expected > 0) & (t.double_counted == 0) & (t.elapsed >= 0.2)
                      & t.progress_ratio.notna()).astype(int)
    keep = ["Project_ID", "Project_Indicator_ID", "sub", "sector", "indicator_text", "ind_type", "unit", "pct_unit",
            "conv_factor", "scaled", "zero_baseline", "double_counted", "achieved", "expected", "elapsed",
            "progress_ratio", "progress_frac", "behind", "behind_t0", "behind_t20", "judgeable"]
    r = t[keep].rename(columns={"Project_ID": "project_id", "Project_Indicator_ID": "indicator_id",
                                "sub": "scorecard_sub"})
    r = r.merge(proj, on="project_id", how="left")
    r["outcome"] = (r.ind_type == "outcome").astype(int)
    r["reach"] = (r.ind_type == "reach").astype(int)
    r = r.sort_values(["project_id", "scorecard_sub", "indicator_text"]).reset_index(drop=True)
    r.insert(0, "result_id", np.arange(1, len(r) + 1))
    return r


# ------------------------------------------------------------------ gender pairs (follows who-benefits/pipeline.py)
def gender_pairs(p, proj):
    q = p[p.Double_Counting_Flag == "N"].copy()
    q["A"], q["E"] = num(q.Achieved_Results), num(q.Expected_Results)
    f = num(q.Progress_Disaggregation_Factor)
    q["fixed_share"] = (f > 0) & (f < 1)
    F = q[q.Demographic_Disaggregation == "Female"].groupby(["Project_ID", "sub"]).agg(
        AF=("A", "sum"), EF=("E", "sum"), fixed_share=("fixed_share", "max"))
    T = q[q.Demographic_Disaggregation == "Total"].groupby(["Project_ID", "sub"]).agg(AT=("A", "sum"), ET=("E", "sum"))
    m = F.join(T, how="inner").reset_index()
    m["pair_status"] = "informative"
    m.loc[m.fixed_share, "pair_status"] = "fixed_share"
    nop = ~m.fixed_share & ((m.AT <= 0) | (m.ET <= 0))
    m.loc[nop, "pair_status"] = "no_progress"
    ok = m.pair_status == "informative"
    sa = (m.AF / m.AT).where(ok)
    se = (m.EF / m.ET).where(ok)
    bad = ok & ((sa > 1.05) | (se > 1.05) | (m.AF < 0))
    m.loc[bad, "pair_status"] = "inconsistent"
    ok = m.pair_status == "informative"
    women_only = ok & (sa > 0.995) & (se > 0.995)
    m.loc[women_only, "pair_status"] = "women_only"
    ok = m.pair_status == "informative"
    identical = ok & ((sa - se).abs() < 1e-3)
    m.loc[identical, "pair_status"] = "identical_share"
    m["share_women_achieved"] = sa.where(m.pair_status == "informative")
    m["share_women_planned"] = se.where(m.pair_status == "informative")
    m["gap_pp"] = 100 * (m.share_women_achieved - m.share_women_planned)
    m["fixed_share"] = m.fixed_share.astype(int)
    m["informative"] = (m.pair_status == "informative").astype(int)
    m = m.rename(columns={"Project_ID": "project_id", "sub": "scorecard_sub"})
    m["sector"] = m.scorecard_sub.map(SECTOR)
    m = m.drop(columns=["AF", "EF", "AT", "ET"]).merge(proj, on="project_id", how="left")
    m.insert(0, "pair_id", np.arange(1, len(m) + 1))
    return m


def project_level(r, proj):
    g = r.groupby("project_id").agg(
        n_results=("result_id", "size"), share_outcome=("outcome", "mean"), share_reach=("reach", "mean"),
        share_scaled=("scaled", "mean"), share_zero_baseline=("zero_baseline", "mean"),
        any_outcome=("outcome", "max")).reset_index()
    return proj.merge(g, on="project_id", how="inner")


# ------------------------------------------------------------------ export
LABELS = {
    "result_id": "Row identifier", "project_id": "World Bank project ID", "indicator_id": "Project indicator ID (Scorecard)",
    "scorecard_sub": "Scorecard results sub-indicator", "sector": "Scorecard results area",
    "indicator_text": "Project indicator wording (ID prefix removed)", "ind_type": "Results-chain type (rule-based)",
    "unit": "Unit of measure", "pct_unit": "Unit is a percentage", "conv_factor": "Progress conversion factor",
    "scaled": "Rescaled by conversion factor (>0, not 1)", "zero_baseline": "Baseline value is zero",
    "double_counted": "Masked for double counting", "achieved": "Achieved result (progress - baseline)",
    "expected": "Expected result (target - baseline)", "elapsed": "Share of implementation period elapsed",
    "progress_ratio": "Achieved / expected", "progress_frac": "Achieved / expected, capped at 1",
    "behind": "Behind: progress < elapsed - 0.10", "behind_t0": "Behind: progress < elapsed",
    "behind_t20": "Behind: progress < elapsed - 0.20", "judgeable": "In delivery sample",
    "outcome": "Outcome indicator", "reach": "Reach indicator", "project_name": "Project name",
    "country": "Country/economy", "country_code": "Country code", "region": "World Bank region",
    "dept": "Lead global department", "status": "Project status (A/C)", "instrument": "Lending instrument",
    "financier": "Agreement type", "approval": "Approval date", "closing": "Closing date", "fcv": "FCV country",
    "ldc": "Least developed country", "sids": "Small island developing state", "income": "Income group",
    "disability_incl": "Disability-inclusive design", "active": "Project active", "ida": "IDA-financed",
    "commitment_musd": "Net commitment, US$ million", "log_commit": "Log net commitment (US$ m)",
    "approval_fy": "Approval fiscal year", "years_since_approval": "Years since approval (to 30 Jun 2025)",
    "post_scorecard": "Approved FY25 or later", "planned_years": "Planned duration, years",
    "pair_id": "Pair identifier", "fixed_share": "Female figure = total x fixed share",
    "pair_status": "Female-figure audit category", "informative": "Female figure informative",
    "share_women_achieved": "Women's share of achieved", "share_women_planned": "Women's share of expected",
    "gap_pp": "Achieved minus planned women's share (pp)", "n_results": "Number of results",
    "share_outcome": "Share of outcome indicators", "share_reach": "Share of reach indicators",
    "share_scaled": "Share rescaled", "share_zero_baseline": "Share with zero baseline", "any_outcome": "Has any outcome indicator",
}


def export(df, name):
    df.to_csv(DATA / f"{name}.csv", index=False)
    s = df.copy()
    strcols = []
    for c in s.columns:
        if pd.api.types.is_datetime64_any_dtype(s[c]):
            continue
        if not pd.api.types.is_numeric_dtype(s[c]):
            s[c] = s[c].fillna("").astype(object).astype(str)
            strcols.append(c)
    labels = {c: LABELS.get(c, c)[:80] for c in s.columns}
    s.to_stata(DATA / f"{name}.dta", write_index=False, version=118, variable_labels=labels,
               convert_strl=[c for c in strcols if s[c].str.len().max() > 240])


def main():
    p = load()
    proj = project_covariates(p)
    r = results(p, proj)
    gp = gender_pairs(p, proj)
    pl = project_level(r, proj)
    for df, name in [(r, "results_clean"), (gp, "gender_pairs"), (pl, "projects_clean")]:
        export(df, name)
    # validation sample: 200 random classifiable-or-not results, fixed seed
    # validation: a development sample (used to refine the rules) and a held-out test sample
    cols = ["result_id", "project_id", "scorecard_sub", "unit", "indicator_text", "ind_type"]
    dev = r.sample(200, random_state=20251007)
    test = r.drop(dev.index).sample(200, random_state=20251008)
    for df, name in [(dev, "dev_sample_rules"), (test, "test_sample_rules")]:
        df[cols].rename(columns={"ind_type": "rule_type"}).to_csv(VAL / f"{name}.csv", index=False)
    print("results", len(r), "projects", r.project_id.nunique())
    print(r.ind_type.value_counts().to_dict())
    print("judgeable", int(r.judgeable.sum()), "behind", round(r.loc[r.judgeable == 1, "behind"].mean(), 3))
    print("scaled", round(r.scaled.mean(), 3), "zero_baseline", round(r.zero_baseline.mean(), 3))
    print("gender pairs", len(gp), gp.pair_status.value_counts().to_dict())


if __name__ == "__main__":
    main()
