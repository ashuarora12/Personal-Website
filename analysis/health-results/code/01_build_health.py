"""
01_build_health.py
Builds the datasets for "What Is Behind 'People Receiving Quality Health Services'?
Measurement in the World Bank Group's Health Results".

Inputs : FY25 World Bank Group Scorecard exports (../who-benefits/data/raw/), the validated
         loaders in ../welfare-anchor/code/01_build_dataset.py, and the project text-classification
         output of ../who-benefits (output/dashboard_data.json, output/report_stats.json).
Outputs: data/health_results.csv/.dta      every World Bank project indicator feeding the Scorecard
                                            indicator "people receiving quality HNP services" (Total rows)
         data/health_female.csv/.dta       the female disaggregation rows of the same indicator
         data/aggregates.csv               published WBG/WB/IFC/MIGA totals for the indicator
         data/health_workforce.csv/.dta    1,131 Scorecard projects with health-workforce/jobs/migration flags
Run from the health-results folder:  python3 code/01_build_health.py
"""
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT.parent
RAW = ANALYSIS / "who-benefits" / "data" / "raw"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

spec = importlib.util.spec_from_file_location("wa", ANALYSIS / "welfare-anchor" / "code" / "01_build_dataset.py")
wa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wa)

HEALTH_SUB = "CSC_RES_HEA_SERV"

# ------------------------------------------------------------------ measurement method
# How the project figure becomes "people receiving quality HNP services":
#   direct    : no conversion (factor 1, or no factor and calculated value equals the raw value)
#   adjusted  : a count of people multiplied by a factor (e.g. 0.96 to remove overlap, 0.5 to attribute a share)
#   coverage  : a coverage percentage (or percentage-point change) multiplied by a population base
#   unit      : a count of something other than people (visits, consultations, facilities, cases) converted to people
PEOPLE = (r"\b(people|persons?|person|individuals?|beneficiar\w*|women|girls|men|boys|children|infants|adolescents?|"
          r"mothers|patients?|users?|clients?|population|migrants|students|pupils|households?|members)\b")
SERVICE_UNITS = r"\b(visits?|consultations?|facilit\w+|cases?|referrals?|notifications?)\b"
PCT = r"(^|\b)(percentage|percent|proportion|share|rate)\b|%"


def method(row):
    cf, txt = row.conv_factor, row.indicator_text.lower()
    if row.achieved_m == 0 and (cf == 0 or pd.isna(cf)):
        return "zero"
    if cf == 1 or (pd.isna(cf) and row.calc_equals_raw):
        return "direct"
    if row.unit == "Percentage" or re.search(PCT, txt):
        return "coverage"
    if re.search(SERVICE_UNITS, txt) or not re.search(PEOPLE, txt):
        return "unit"
    return "adjusted"


# ------------------------------------------------------------------ service family
FAMILY = [
    ("vaccination", r"vaccin|immuni[sz]|penta|covid"),
    ("aggregate", r"(people|beneficiar\w*)[^|]{0,40}(health, nutrition|hnp|essential health|health and nutrition|quality health)"
                  r"|direct project beneficiaries"),
    ("outpatient", r"outpatient|consultation|\bvisits?\b"),
    ("infectious", r"\btb\b|tuberculosis|\bhiv\b|malaria"),
    ("ncd_screening", r"\bncds?\b|diabetes|hypertension|cancer|screened for|screening"),
    ("rmnch_fp", r"contracept|family planning|antenatal|\banc\b|pregnan|post-?partum|deliver|birth|breastfe|iron-folate|"
                 r"maternal|reproductive"),
    ("nutrition", r"nutrition|\bdiet\b|micronutrient|stunting"),
    ("facilities", r"facilit"),
]
FAMILY_LABEL = {"vaccination": "Vaccination (incl. COVID-19)", "aggregate": "Aggregate HNP service count",
                "outpatient": "Outpatient visits and consultations", "ncd_screening": "Screening (NCDs, mental health)",
                "rmnch_fp": "Maternal, reproductive health and family planning", "nutrition": "Nutrition services",
                "infectious": "TB and HIV", "facilities": "Health facilities", "other": "Other services"}


def family(txt):
    t = txt.lower()
    for k, pat in FAMILY:
        if re.search(pat, t):
            return k
    return "other"


def num(s):
    return pd.to_numeric(s, errors="coerce")


def build():
    p = wa.load()
    proj = wa.project_covariates(p)
    h = p[p["sub"] == HEALTH_SUB].copy()
    for c in ["Baseline_Value", "Progress_Value", "Target_Value", "Progress_Conversion_Factor", "Target_Conversion_Factor",
              "Progress_Disaggregation_Factor", "Calculated_Baseline_Value", "Calculated_Progress_Value",
              "Calculated_Target_Value", "Achieved_Results", "Expected_Results", "Achieved_Results_IDA",
              "Achieved_Results_IBRD", "Expected_Results_IDA", "Expected_Results_IBRD"]:
        h[c] = num(h[c])
    h["indicator_text"] = h.Project_Indicator.map(wa.clean_text)
    h["unit"] = h.Unit_of_Measure.fillna("Missing")
    h["conv_factor"] = h.Progress_Conversion_Factor
    h["achieved_m"] = h.Achieved_Results.fillna(0) / 1e6
    h["expected_m"] = h.Expected_Results.fillna(0) / 1e6
    h["calc_equals_raw"] = (h.Calculated_Progress_Value.fillna(-1) == h.Progress_Value.fillna(-2))
    h["double_counted"] = (h.Double_Counting_Flag == "Y").astype(int)
    h["raw_progress_zero"] = (h.Progress_Value.fillna(0) == 0).astype(int)
    h["not_reproducible"] = ((h.Demographic_Disaggregation == "Total") & (h.raw_progress_zero == 1)
                             & (h.Achieved_Results > 0)).astype(int)
    span = (h.Closing_Date - h.Approval_Date).dt.days.clip(lower=30)
    h["elapsed"] = ((h.Progress_Date - h.Approval_Date).dt.days / span).clip(0, 1)
    h["progress_ratio"] = (h.Achieved_Results / h.Expected_Results).where(h.Expected_Results > 0)

    T = h[h.Demographic_Disaggregation == "Total"].copy()
    T["method"] = T.apply(method, axis=1)
    T["family"] = T.indicator_text.map(family)
    T["family_label"] = T.family.map(FAMILY_LABEL)
    T["covid"] = T.indicator_text.str.contains(r"(?i)covid").astype(int)
    T["ind_type"] = T.indicator_text.map(wa.classify)
    keep = ["Project_ID", "Project_Indicator_ID", "indicator_text", "unit", "family", "family_label", "method", "covid",
            "ind_type", "Baseline_Value", "Progress_Value", "Target_Value", "conv_factor", "Target_Conversion_Factor",
            "Calculated_Baseline_Value", "Calculated_Progress_Value", "Calculated_Target_Value", "achieved_m", "expected_m",
            "Achieved_Results_IDA", "Achieved_Results_IBRD", "double_counted", "raw_progress_zero", "not_reproducible",
            "elapsed", "progress_ratio", "Progress_Date"]
    T = T[keep].rename(columns={"Project_ID": "project_id", "Project_Indicator_ID": "indicator_id",
                                "Baseline_Value": "baseline_raw", "Progress_Value": "progress_raw", "Target_Value": "target_raw",
                                "Target_Conversion_Factor": "target_conv_factor", "Calculated_Baseline_Value": "baseline_calc",
                                "Calculated_Progress_Value": "progress_calc", "Calculated_Target_Value": "target_calc",
                                "Achieved_Results_IDA": "achieved_ida", "Achieved_Results_IBRD": "achieved_ibrd",
                                "Progress_Date": "progress_date"})
    T = T.merge(proj, on="project_id", how="left").sort_values("achieved_m", ascending=False).reset_index(drop=True)
    T.insert(0, "result_id", np.arange(1, len(T) + 1))
    T["rank_achieved"] = T.achieved_m.rank(ascending=False, method="first").astype(int)

    F = h[h.Demographic_Disaggregation == "Female"].copy()
    F["female_factor"] = F.Progress_Disaggregation_Factor
    F["fixed_share"] = ((F.female_factor > 0) & (F.female_factor < 1)).astype(int)
    F["indicator_text"] = F.Project_Indicator.map(wa.clean_text)
    F = F[["Project_ID", "Project_Indicator_ID", "indicator_text", "female_factor", "fixed_share", "achieved_m", "expected_m",
           "double_counted"]].rename(columns={"Project_ID": "project_id", "Project_Indicator_ID": "indicator_id"})
    F = F.merge(proj, on="project_id", how="left").reset_index(drop=True)
    F.insert(0, "female_id", np.arange(1, len(F) + 1))
    return T, F, proj


def aggregates():
    a = pd.read_excel(RAW / "CSC_RES_HEA_SERV.xlsx", sheet_name="Aggregates")
    a = a[(a.Geography_Code == "ACW") & (a.Disability_Inclusive_Flag == "Total") & a.Sub_Indicator_Code.isna()]
    a = a[["Organization_Code", "Demographic_Disaggregation", "Achieved_Results", "Expected_Results"]].copy()
    a["Achieved_Results"] = num(a.Achieved_Results) / 1e6
    a["Expected_Results"] = num(a.Expected_Results) / 1e6
    im = pd.read_excel(RAW / "CSC_RES_HEA_SERV.xlsx", sheet_name="IFC MIGA Results")
    im = im[im.Disability_Inclusive_Flag == "Total"][["Organization_Code", "Demographic_Disaggregation", "Achieved_Results", "Expected_Results"]]
    im["Achieved_Results"] = num(im.Achieved_Results) / 1e6
    im["Expected_Results"] = num(im.Expected_Results) / 1e6
    im["Organization_Code"] = im.Organization_Code + " (IFC/MIGA sheet)"
    return pd.concat([a, im], ignore_index=True).rename(columns={"Organization_Code": "organization",
                                                                 "Demographic_Disaggregation": "group",
                                                                 "Achieved_Results": "achieved_m",
                                                                 "Expected_Results": "expected_m"})


def health_workforce():
    dash = json.load(open(ANALYSIS / "who-benefits" / "output" / "dashboard_data.json"))
    rows = [{"project_id": x["id"], "country": x["country"], "region": x["region"], "fcv": int(bool(x["fcv"])),
             "dept": x["dept"], "status": x["status"],
             **{f"theme_{k}": int(k in x["themes"]) for k in ["health_workforce", "jobs_skills", "migration",
                                                              "women_econ", "care_economy", "menstrual"]}}
            for x in dash["themes"]["projects"]]
    return pd.DataFrame(rows)


def export(df, name, labels=None):
    df.to_csv(DATA / f"{name}.csv", index=False)
    s = df.copy()
    strcols = []
    for c in s.columns:
        if pd.api.types.is_datetime64_any_dtype(s[c]):
            continue
        if not pd.api.types.is_numeric_dtype(s[c]):
            s[c] = s[c].fillna("").astype(object).astype(str)
            strcols.append(c)
        elif pd.api.types.is_bool_dtype(s[c]):
            s[c] = s[c].astype(int)
    lab = {c: (labels or {}).get(c, wa.LABELS.get(c, c))[:80] for c in s.columns}
    s.to_stata(DATA / f"{name}.dta", write_index=False, version=118, variable_labels=lab,
               convert_strl=[c for c in strcols if s[c].str.len().max() > 240])


LAB = {"family": "Service family (rule-based)", "family_label": "Service family label", "method": "Measurement method",
       "covid": "COVID-19 indicator", "baseline_raw": "Baseline value (project unit)", "progress_raw": "Progress value (project unit)",
       "target_raw": "Target value (project unit)", "conv_factor": "Progress conversion factor", "target_conv_factor": "Target conversion factor",
       "baseline_calc": "Baseline in Scorecard unit", "progress_calc": "Progress in Scorecard unit", "target_calc": "Target in Scorecard unit",
       "achieved_m": "Achieved (million people)", "expected_m": "Expected (million people)", "achieved_ida": "Achieved, IDA share",
       "achieved_ibrd": "Achieved, IBRD share", "raw_progress_zero": "Raw progress value is zero or missing",
       "not_reproducible": "Positive achieved with zero raw progress", "progress_date": "Date of latest progress",
       "rank_achieved": "Rank by achieved", "female_factor": "Female disaggregation factor",
       "fixed_share": "Female figure = total x fixed share", "female_id": "Row identifier"}

if __name__ == "__main__":
    T, F, proj = build()
    export(T, "health_results", LAB)
    export(F, "health_female", LAB)
    aggregates().to_csv(DATA / "aggregates.csv", index=False)
    hw = health_workforce()
    export(hw, "health_workforce", {f"theme_{k}": f"Theme flag: {k}" for k in
                                    ["health_workforce", "jobs_skills", "migration", "women_econ", "care_economy", "menstrual"]})
    nd = T[T.double_counted == 0]
    print("health results", len(T), "projects", T.project_id.nunique(), "| not double counted", len(nd),
          "| positive achieved", int((nd.achieved_m > 0).sum()))
    print("achieved (m)", round(nd.achieved_m.sum(), 3), "by method",
          (nd.groupby("method").achieved_m.sum() / nd.achieved_m.sum()).round(3).to_dict())
    print("by family", (nd.groupby("family").achieved_m.sum() / nd.achieved_m.sum()).round(3).to_dict())
    print("not reproducible", int(nd.not_reproducible.sum()), round(nd.loc[nd.not_reproducible == 1, "achieved_m"].sum(), 3))
    Fn = F[(F.double_counted == 0) & (F.achieved_m > 0)]
    print("female achieved (m)", round(Fn.achieved_m.sum(), 3), "fixed-share share",
          round(Fn.loc[Fn.fixed_share == 1, "achieved_m"].sum() / Fn.achieved_m.sum(), 3))
    print("workforce projects", int(hw.theme_health_workforce.sum()), "of", len(hw))
