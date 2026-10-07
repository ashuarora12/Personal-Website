"""
build_paper.py  -  renders the working paper (HTML -> PDF) from the R outputs.
Every number in the text is read from output/key_numbers.json or output/tables/*.csv,
so re-running code/02_analysis.R and then this script keeps text and results in sync.

Run from the welfare-anchor folder:  python3 paper/build_paper.py
"""
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
TAB = OUT / "tables"
PAPER = ROOT / "paper"
K = json.load(open(OUT / "key_numbers.json"))
VAL = {r["type"]: r for r in K["validation"]}


def pc(x, d=0):
    return f"{100 * x:.{d}f}%"


def pp(x, d=1):
    return f"{100 * x:.{d}f}"


def n(x):
    return f"{int(round(x)):,}"


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def coef(df, model, term, scale=1.0, d=3):
    r = df[(df.model == model) & (df.term == term)]
    if r.empty:
        return None
    r = r.iloc[0]
    return r.estimate * scale, r.se * scale, r.p


def cell(df, model, term, d=3):
    c = coef(df, model, term)
    if c is None:
        return "", ""
    b, s, p = c
    return f"{b:.{d}f}{stars(p)}", f"({s:.{d}f})"


def regtable(df, models, headers, rows, stats, caption, note, num):
    """rows: list of (term, label) or ('__group__', label)."""
    h = "".join(f"<th>{x}</th>" for x in headers)
    body = ""
    for term, label in rows:
        if term == "__group__":
            body += f'<tr class="grp"><td colspan="{len(models) + 1}">{label}</td></tr>'
            continue
        cells = [cell(df, m, term) for m in models]
        if all(c[0] == "" for c in cells):
            continue
        body += f"<tr><td>{label}</td>" + "".join(f"<td>{c[0]}</td>" for c in cells) + "</tr>"
        body += '<tr class="se"><td></td>' + "".join(f"<td>{c[1]}</td>" for c in cells) + "</tr>"
    for label, vals in stats:
        body += f'<tr class="stat"><td>{label}</td>' + "".join(f"<td>{v}</td>" for v in vals) + "</tr>"
    return (f'<figure class="tbl avoid"><figcaption><b>Table {num}.</b> {caption}</figcaption>'
            f'<table class="reg"><thead><tr><th></th>{h}</tr></thead><tbody>{body}</tbody></table>'
            f'<p class="note">{note}</p></figure>')


def simpletable(header, rows, caption, note, num, cls=""):
    h = "".join(f"<th>{x}</th>" for x in header)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<figure class="tbl avoid {cls}"><figcaption><b>Table {num}.</b> {caption}</figcaption>'
            f'<table class="simple"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'
            f'<p class="note">{note}</p></figure>')


def fig(path, num, caption, note):
    return (f'<figure class="fig avoid"><figcaption><b>Figure {num}.</b> {caption}</figcaption>'
            f'<img src="../output/figures/{path}"><p class="note">{note}</p></figure>')


SECTOR = {"health": "Health, nutrition & population", "wash": "Water, sanitation & hygiene",
          "gender_equality": "Gender equality actions", "economic_opportunity": "Economic opportunity",
          "financial_services": "Financial services", "all": "All results areas"}
SECTOR_TERMS = [("sectorwash", "WASH"), ("sectorgender_equality", "Gender equality actions"),
                ("sectoreconomic_opportunity", "Economic opportunity"), ("sectorfinancial_services", "Financial services")]
COHORT_TERMS = [("cohortFY20-21", "Approved FY20-21"), ("cohortFY22-23", "Approved FY22-23"),
                ("cohortFY24", "Approved FY24"), ("cohortFY25 (post-Scorecard)", "Approved FY25 (new Scorecard)")]

# ------------------------------------------------------------------ data for tables
T1 = pd.read_csv(TAB / "table1_projects.csv").set_index("variable")
T2 = pd.read_csv(TAB / "table2_type_by_sector.csv").set_index("sector")
T4 = pd.read_csv(TAB / "table4_test1_outcome_models.csv"); S4 = pd.read_csv(TAB / "table4_stats.csv")
AME = pd.read_csv(TAB / "table4_logit_ame.csv").set_index("term").ame
T5 = pd.read_csv(TAB / "table5_construction_by_sector.csv").set_index("sector")
T6 = pd.read_csv(TAB / "table6_test2_models.csv"); S6 = pd.read_csv(TAB / "table6_stats.csv")
T7 = pd.read_csv(TAB / "table7_test3_models.csv"); S7 = pd.read_csv(TAB / "table7_stats.csv")
T8 = pd.read_csv(TAB / "table8_robustness.csv")
A1 = pd.read_csv(TAB / "tableA1_manual_subsample.csv")
G = pd.read_csv(ROOT / "data" / "gender_pairs.csv")
R = pd.read_csv(ROOT / "data" / "results_clean.csv")

m3 = "(3) LPM + dept FE"
b_wash = coef(T4, "(2) LPM + controls", "sectorwash")
b_fin = coef(T4, "(2) LPM + controls", "sectorfinancial_services")
b_gen = coef(T4, "(2) LPM + controls", "sectorgender_equality")
b_fy25 = coef(T4, "(2) LPM + controls", "cohortFY25 (post-Scorecard)")
b_fy25_fe = coef(T4, m3, "cohortFY25 (post-Scorecard)")
fs = K["fixed_share_by_sector"]
b_fs24 = coef(T6, "(1) Fixed-share female figure, LPM", "cohortFY24")
b_fs25 = coef(T6, "(1) Fixed-share female figure, LPM", "cohortFY25 (post-Scorecard)")
b_sc_pct = coef(T6, "(3) Rescaled result, LPM", "pct_unit")
b_sc_fy25 = coef(T6, "(3) Rescaled result, LPM", "cohortFY25 (post-Scorecard)")
b_out = coef(T7, "(5) LPM behind: + dept FE", "ind_typeoutcome")
b_out4 = coef(T7, "(4) LPM behind: + controls", "ind_typeoutcome")
b_scal = coef(T7, "(5) LPM behind: + dept FE", "scaled")
b_age7 = coef(T7, "(5) LPM behind: + dept FE", "age_bin7+ yrs")
b_fl_out = coef(T7, "(1) Fractional logit: progress", "ind_typeoutcome")
b_fl_sc = coef(T7, "(1) Fractional logit: progress", "scaled")
rob_out = T8[T8.term == "ind_typeoutcome"]
gs = K["gender_status"]
n_pairs = K["n_pairs"]
ach_tot = T5.loc["all", "achieved_total_m"]
n_countries_only = R.loc[~R.country.str.contains("Africa$", regex=True), "country"].nunique()
pred = K["pred_progress_at_half"]
behind_age = K["behind_by_age"]
bt = K["behind_by_type"]

# ------------------------------------------------------------------ tables
table_flow = simpletable(
    ["Step", "Records", "Projects"],
    [["Project-indicator records in the FY25 Scorecard exports (four results files)", "10,893", "1,131"],
     ["&nbsp;&nbsp;of which disaggregation rows (female, youth)", "7,276", ""],
     ["Results: total (non-disaggregated) project indicators &mdash; <i>Tests 1&ndash;2</i>", n(K["n_results"]), n(K["n_projects"])],
     ["&nbsp;&nbsp;not masked for double counting", n((R.double_counted == 0).sum()), n(R.loc[R.double_counted == 0, "project_id"].nunique())],
     ["&nbsp;&nbsp;with positive target, dates, and &ge;20% of implementation period elapsed", n(R.judgeable.sum()), n(R.loc[R.judgeable == 1, "project_id"].nunique())],
     ["&nbsp;&nbsp;excluding unclassifiable indicators &mdash; <i>Test 3</i>", n(K["t3_n"]), n(K["t3_projects"])],
     ["Project &times; Scorecard sub-indicator pairs with a female figure &mdash; <i>Test 2 (gender)</i>", n(n_pairs), n(G.project_id.nunique())]],
    "Construction of the analysis samples",
    "Source: World Bank Group Scorecard, FY25 cycle (results as of 30 June 2025), sheet &ldquo;WB Project Information&rdquo; "
    "of the health, WASH, gender and financial-services results files. Rows that appear in two files are counted once.", 1)

table_desc = simpletable(
    ["Variable (project level, N = " + n(K["n_projects"]) + ")", "Mean", "SD", "Min", "Max"],
    [[lbl, f'{T1.loc[v, "mean"]:.2f}', f'{T1.loc[v, "sd"]:.2f}', f'{T1.loc[v, "min"]:.2f}', f'{T1.loc[v, "max"]:.2f}']
     for v, lbl in [("fcv", "Fragile and conflict-affected (FCV) country"), ("ldc", "Least developed country"),
                    ("ida", "IDA-financed"), ("active", "Active (not closed) at cutoff"),
                    ("commitment_musd", "Net commitment (US$ million)"), ("years_since_approval", "Years since approval"),
                    ("planned_years", "Planned duration (years)"), ("post_scorecard", "Approved FY25 (after new Scorecard)")]],
    "Project characteristics", "Commitment is the net commitment recorded in the Scorecard export. "
    "Regional distribution of projects: " + ", ".join(f"{k} {v}" for k, v in K["region_counts"].items()) + ".", 2)

rows = []
for s in ["health", "wash", "gender_equality", "economic_opportunity", "financial_services", "all"]:
    r = T2.loc[s]
    rows.append([SECTOR[s], n(r.n), pc(r.reach), pc(r.output), pc(r.outcome), pc(r.unclassifiable)])
table_types = simpletable(["Scorecard results area", "Results", "Reach", "Output", "Outcome", "Unclassifiable"], rows,
                          "What the Scorecard counts: results-chain type of contributing project indicators",
                          "Rule-based classification of the indicator wording (Appendix A). Shares are row percentages.", 3)

vrows = []
for t in ["reach", "output", "outcome"]:
    v = VAL[t]
    vrows.append([t.capitalize(), f'{v["precision"]:.2f} [{v["prec_lo"]:.2f}, {v["prec_hi"]:.2f}]',
                  f'{v["recall"]:.2f} [{v["rec_lo"]:.2f}, {v["rec_hi"]:.2f}]', pc(v["rule_share_all"], 1),
                  f'{pc(v["manual_share_400"], 1)} [{pc(v["manual_lo"], 1)}, {pc(v["manual_hi"], 1)}]'])
table_val = simpletable(["Type", "Precision (test set)", "Recall (test set)", "Rule-based share, all results",
                         "Hand-coded share (n = 400)"], vrows,
                        "Validation of the indicator classification",
                        f"Held-out test set of 200 randomly drawn results coded by hand without sight of the rule labels; "
                        f"overall agreement {pc(K['val_test_accuracy'], 1)}, Cohen&rsquo;s &kappa; = {K['val_test_kappa']:.2f}. "
                        "A separate development set of 200 results was used to refine the rules and is not used for these "
                        "statistics. The last column pools both hand-coded sets. 95% Wilson intervals in brackets.", 4)

table4 = regtable(
    T4, ["(1) LPM sector+cohort", "(2) LPM + controls", m3], ["(1)", "(2)", "(3)"],
    [("__group__", "Results area (base: health, nutrition &amp; population)")] + SECTOR_TERMS +
    [("__group__", "Approval cohort (base: FY19 or earlier)")] + COHORT_TERMS +
    [("__group__", "Project characteristics")] + [("fcv", "FCV country"), ("ida", "IDA-financed"), ("log_commit", "Log commitment")],
    [("Region, income group, instrument", ["", "Yes", "Yes"]), ("Lead department fixed effects", ["", "", "Yes"]),
     ("Observations (results)", [n(x) for x in S4.n[:3]]), ("Clusters (projects)", [n(K["t1_clusters"])] * 3),
     ("R&sup2;", [f"{x:.3f}" for x in S4.r2[:3]])],
    "Test 1 &mdash; Which results are outcome indicators? Linear probability models",
    "Dependent variable = 1 if the project indicator measures a welfare outcome. Standard errors clustered by project in parentheses. "
    "*** p&lt;0.01, ** p&lt;0.05, * p&lt;0.10. A logit version gives the same pattern (average marginal effects in the text); "
    "no WASH result is an outcome indicator, so WASH is perfectly predicted in the logit.", 5)

crows = []
for s in ["health", "wash", "gender_equality", "economic_opportunity", "financial_services", "all"]:
    r = T5.loc[s]
    fsh = G.fixed_share.mean() if s == "all" else fs[s]
    crows.append([SECTOR[s], n(r.results), pc(r.share_zero_baseline), pc(r.share_scaled), pc(r.achieved_from_scaled),
                  pc(fsh)])
table5 = simpletable(["Scorecard results area", "Results", "Zero baseline", "Rescaled", "Share of reported total from rescaled results",
                      "Female figure = fixed share of total"], crows,
                     "Test 2 &mdash; How Scorecard figures are constructed",
                     f"Results not masked for double counting (N = {n(T5.loc['all', 'results'])}). &ldquo;Rescaled&rdquo;: the project "
                     "figure is multiplied by a conversion factor (positive and different from 1) to express it in the Scorecard unit. "
                     f"Last column: project &times; sub-indicator pairs with a female figure (N = {n(n_pairs)}).", 6)

table6 = regtable(
    T6, ["(1) Fixed-share female figure, LPM", "(3) Rescaled result, LPM"], ["(1) Female figure is a fixed share", "(2) Result is rescaled"],
    [("__group__", "Results area (base: health, nutrition &amp; population)")] + SECTOR_TERMS +
    [("__group__", "Indicator")] + [("pct_unit", "Unit is a percentage"), ("ind_typeoutput", "Output indicator"),
                                     ("ind_typeoutcome", "Outcome indicator")] +
    [("__group__", "Approval cohort (base: FY19 or earlier)")] + COHORT_TERMS +
    [("__group__", "Project characteristics")] + [("fcv", "FCV country"), ("ida", "IDA-financed"), ("log_commit", "Log commitment")],
    [("Region, income group, instrument", ["Yes", "Yes"]), ("Observations", [n(S6.n[0]), n(S6.n[2])]),
     ("R&sup2;", [f"{S6.r2[0]:.3f}", f"{S6.r2[2]:.3f}"])],
    "Test 2 &mdash; Which figures are constructed rather than measured? Linear probability models",
    "Column (1): project &times; Scorecard sub-indicator pairs with a female figure. Column (2): results not masked for double "
    "counting. Standard errors clustered by project. *** p&lt;0.01, ** p&lt;0.05, * p&lt;0.10.", 7)

table7 = regtable(
    T7, ["(1) Fractional logit: progress", "(2) LPM behind: timing only", "(3) LPM behind: + design",
         "(4) LPM behind: + controls", "(5) LPM behind: + dept FE"],
    ["(1) Progress<br><span class='sub'>frac. logit</span>", "(2) Behind", "(3) Behind", "(4) Behind", "(5) Behind"],
    [("__group__", "Timing")] + [("elapsed", "Share of period elapsed"), ("elapsed2", "Share elapsed, squared"),
                                ("age_bin3-5 yrs", "3&ndash;5 years since approval"), ("age_bin5-7 yrs", "5&ndash;7 years"),
                                ("age_bin7+ yrs", "7+ years")] +
    [("__group__", "What is measured (base: reach indicator)")] + [("ind_typeoutput", "Output indicator"), ("ind_typeoutcome", "Outcome indicator"),
                                                                 ("scaled", "Rescaled figure")] +
    [("__group__", "Results area (base: health, nutrition &amp; population)")] + SECTOR_TERMS +
    [("__group__", "Project characteristics")] + [("fcv", "FCV country"), ("log_commit", "Log commitment")],
    [("Region, income group, instrument", ["Yes", "", "", "Yes", "Yes"]), ("Lead department fixed effects", ["", "", "", "", "Yes"]),
     ("Observations (results)", [n(x) for x in S7.n]), ("Clusters (projects)", [n(K["t3_projects"])] * 5),
     ("R&sup2;", ["&ndash;"] + [f"{x:.3f}" for x in S7.r2[1:]])],
    "Test 3 &mdash; Progress and the &ldquo;behind&rdquo; judgement",
    "Column (1): fractional logit (Papke and Wooldridge 1996) of the share of target achieved (capped at 1), coefficients in log-odds. "
    "Columns (2)&ndash;(5): linear probability models; &ldquo;behind&rdquo; = share of target achieved below share of implementation "
    "period elapsed minus 10 percentage points. Base age category: under 3 years. Standard errors clustered by project. "
    "*** p&lt;0.01, ** p&lt;0.05, * p&lt;0.10.", 8)

rrows = []
for mname in ["Threshold 0 pp", "Threshold 20 pp", "Active projects only", "Excluding rescaled results",
              "Clustered by country", "Logit (log-odds)"]:
    o = T8[(T8.model == mname) & (T8.term == "ind_typeoutcome")].iloc[0]
    a = T8[(T8.model == mname) & (T8.term == "age_bin7+ yrs")].iloc[0]
    nn = {"Threshold 0 pp": K["rob_n"][0], "Threshold 20 pp": K["rob_n"][1], "Active projects only": K["rob_n"][2],
          "Excluding rescaled results": K["rob_n"][3]}.get(mname, K["t3_n"])
    rrows.append([mname, f"{o.estimate:.3f}{stars(o.p)} ({o.se:.3f})", f"{a.estimate:.3f}{stars(a.p)} ({a.se:.3f})", n(nn)])
o5 = coef(T7, "(5) LPM behind: + dept FE", "ind_typeoutcome"); a5 = coef(T7, "(5) LPM behind: + dept FE", "age_bin7+ yrs")
rrows.insert(0, ["Baseline (Table 8, column 5)", f"{o5[0]:.3f}{stars(o5[2])} ({o5[1]:.3f})", f"{a5[0]:.3f}{stars(a5[2])} ({a5[1]:.3f})", n(K["t3_n"])])
table8 = simpletable(["Specification", "Outcome indicator", "7+ years since approval", "N"], rrows,
                     "Robustness of the Test 3 results",
                     "Each row re-estimates column (5) of Table 8 with one change. Thresholds redefine &ldquo;behind&rdquo; as progress below "
                     "elapsed share (0 pp) or elapsed share minus 20 pp. The logit omits department fixed effects. Clustered standard errors "
                     "in parentheses. *** p&lt;0.01, ** p&lt;0.05, * p&lt;0.10.", 9)

tA1 = regtable(A1, ["LPM, hand-coded subsample"], ["Outcome (hand-coded)"],
               SECTOR_TERMS + COHORT_TERMS,
               [("Observations", [n(K["manual_sub_n"])])],
               "Test 1 re-estimated on the 400 hand-coded results",
               "Dependent variable = 1 if the hand coder classified the indicator as an outcome. Standard errors clustered by project.", "A1")

# ------------------------------------------------------------------ figures
fig1 = fig("fig1_indicator_types.png", 1, "What the Scorecard counts, by results area",
           f"Share of the {n(K['n_results'])} project indicators feeding each Scorecard results area, by results-chain type. "
           "Source: author&rsquo;s classification of FY25 Scorecard project records.")
fig2 = fig("fig2_constructed.png", 2, "Constructed figures in the Scorecard, by results area",
           "Left: share of the reported achieved total that comes from project figures multiplied by a conversion factor. "
           "Right: share of project &times; sub-indicator pairs whose female figure is the total multiplied by a fixed share.")
fig3 = fig("fig3_delivery_curve.png", 3, "Results accumulate along a curve, not a straight line",
           "Lines: average predicted share of target achieved from the fractional logit in Table 8, column (1), evaluated over the "
           "estimation sample. Dots: binned means (size proportional to the number of results). Dashed line: the linear benchmark "
           "implied by comparing cumulative progress with elapsed time.")
fig4 = fig("fig4_behind_by_age.png", 4, "Share of results rated &ldquo;behind&rdquo; falls steeply with project age",
           f"N = {n(K['t3_n'])} results in {n(K['t3_projects'])} projects. Error bars: 95% Wilson intervals.")

# ------------------------------------------------------------------ text
abstract = f"""
The World Bank Group&rsquo;s FY24&ndash;FY30 Scorecard was presented as a shift from counting inputs to measuring outcomes. This paper
tests that claim against a welfare anchor, extending the welfare-economics criterion that Gonz&aacute;lez (2026) proposes for private
sector development to the Scorecard&rsquo;s people-level results. Using the public project-level records behind the FY25 Scorecard
({n(K['n_results'])} results from {n(K['n_projects'])} projects in {n_countries_only} countries), I apply three tests. <b>Welfare relevance:</b>
{pc(K['share_type']['reach'])} of contributing project indicators count people or firms reached and only {pc(K['share_type']['outcome'])}
measure a change in welfare ({pc(VAL['outcome']['manual_share_400'])} in a hand-coded sample); {pc(K['projects_no_outcome'])} of projects
report no outcome indicator at all, and projects approved after the new Scorecard are not significantly more outcome-oriented. <b>Measurement integrity:</b>
{pc(K['zero_baseline'])} of results start from a zero baseline, {pc(K['achieved_from_scaled'])} of the reported achieved total
({pc(T5.loc['health', 'achieved_from_scaled'])} in health) comes from figures rescaled by conversion factors, and only
{pc(K['informative_share'])} of female figures can show whether women were reached as planned. <b>Progress judgement:</b> under a linear
on-track rule, {pc(K['behind_rate'])} of results look &ldquo;behind&rdquo;, falling from {pc(behind_age['<3 yrs'])} in projects under three
years old to {pc(behind_age['7+ yrs'])} after seven; and outcome indicators are {pp(b_out[0], 0)} percentage points more likely to be rated behind
than reach indicators with the same age, sector and country characteristics. A results system built this way rewards counting reach and
penalises measuring welfare. I propose five changes that would anchor the Scorecard in welfare without adding reporting burden.
"""

intro = f"""
<p>In April 2024 the World Bank Group (WBG) replaced its corporate scorecard of roughly 150 indicators with a new Scorecard of 22 results
indicators for FY24&ndash;FY30. Management described the change as a milestone in the Group&rsquo;s efforts &ldquo;to focus on outcomes,
rather than inputs&rdquo; (World Bank 2024b), and the Scorecard now serves as both a communication device and a management tool that
cascades into unit-level targets (World Bank 2024a). Its headline numbers&mdash;hundreds of millions of people receiving health services,
water, financial services or gender-equality actions&mdash;have become the Group&rsquo;s main public account of what its lending achieves.</p>

<p>Whether those numbers measure welfare is a question with a long history inside the institution. The Independent Evaluation Group (IEG)
has repeatedly found the Bank Group&rsquo;s self-evaluation systems geared to results reporting and upward accountability rather than learning
(IEG 2016), and in November 2025 it launched a formative evaluation of the Scorecard itself, whose approach paper draws on the literature on
gaming in centralised performance systems (IEG 2025; see also Hood 2006). From outside, Gonz&aacute;lez (2026) argues that the Bank&rsquo;s
private sector work has been reorganised repeatedly because it lacks a fixed objective, and proposes a welfare-economics &ldquo;anchor&rdquo;:
an operation qualifies only if it addresses a binding market failure, acts on that failure, and changes outcomes that would not otherwise occur.</p>

<p>This paper applies the same discipline to the measurement side. If the Scorecard is anchored in welfare, three things should be true of
the results it aggregates. First, they should measure changes in people&rsquo;s welfare, not only how many people a project touched
(<i>welfare relevance</i>). Second, the reported figures should be measured rather than constructed from conversion factors, assumed shares
and zero baselines (<i>measurement integrity</i>). Third, the way progress is judged should reflect performance rather than the passage of time,
and should not penalise teams that choose to measure welfare (<i>progress judgement</i>).</p>

<p>I test each condition with the public project-level records that underlie the FY25 Scorecard: {n(K['n_results'])} project indicators
(&ldquo;results&rdquo;) from {n(K['n_projects'])} IDA- and IBRD-financed projects in {n_countries_only} countries, feeding five people-level
results areas (health, nutrition and population; water, sanitation and hygiene; gender-equality actions; economic opportunity; and
financial services). Each indicator is classified by its position in the results chain&mdash;reach, output or outcome&mdash;using transparent
rules validated against a held-out hand-coded sample (&kappa; = {K['val_test_kappa']:.2f}). The econometrics is deliberately simple:
linear probability models, a fractional logit, and logit checks, all with standard errors clustered by project.</p>

<p>The results are consistent across the three tests. Most of what the Scorecard counts is reach: {pc(K['share_type']['reach'])} of
contributing indicators count people or firms served, and {pc(K['projects_no_outcome'])} of projects feed it no outcome indicator at all.
A large share of the reported totals is constructed: {pc(K['achieved_from_scaled'])} of the achieved total comes from rescaled figures,
and more than half of female figures in health and WASH are the total multiplied by an assumed share. And a linear on-track rule mostly
measures project age, while rating outcome indicators as behind {pp(b_out[0], 0)} percentage points more often than comparable reach
indicators&mdash;a direct, if unintended, penalty on measuring welfare.</p>

<p>The paper contributes in three ways. It provides a systematic, reproducible audit of the Scorecard&rsquo;s project-level evidence,
complementing IEG&rsquo;s ongoing formative evaluation. It extends the welfare-anchor argument from what the Bank finances to how it counts.
And it converts the familiar warning that &ldquo;what gets measured gets done&rdquo; (Narayanaswamy 2021) into specific, testable
quantities that management could track. Data and code in R and Stata are released with the paper.</p>
"""

background = f"""
<h3>2.1 The Scorecard and its project-level evidence</h3>
<p>The WBG adopted a corporate scorecard in 2011, extended it to IFC and MIGA in 2014 and revised it in 2017 and 2020 (IEG 2025). The
FY24&ndash;FY30 Scorecard reduced the indicator set to a short list of WBG results indicators alongside vision and client-context indicators
(World Bank 2024a). Each people-level results indicator is an aggregate of project indicators: every active or recently closed project that
contributes reports a baseline, a target and a latest progress value, and these are converted into the Scorecard&rsquo;s unit (usually
&ldquo;people&rdquo;) and summed. The public data release reports, for each contributing project indicator, the original wording, the
baseline, progress and target values, the conversion and disaggregation factors applied, and a flag for results masked to avoid double counting.
These records are what make the tests in this paper possible.</p>

<h3>2.2 Performance measurement and its distortions</h3>
<p>A large literature warns that quantitative targets change behaviour in ways that can undermine their purpose. Campbell (1979) observed that
the more a quantitative indicator is used for decisions, the more it is subject to corruption pressures. Hood (2006) and Bevan and Hood (2006)
document ratchet, threshold and output-distortion effects in the British &ldquo;targets regime&rdquo;. In principal&ndash;agent terms,
Holmstr&ouml;m and Milgrom (1991) show that when some dimensions of a task are easier to measure than others, strong incentives on the measurable
dimension pull effort away from the rest. In aid, Natsios (2010) describes how compliance-driven measurement crowds out the most transformational
work, and Honig (2018) shows that tight top-down measurement performs worst precisely where outcomes are hardest to verify. Andrews, Pritchett and
Woolcock (2013) and Pritchett, Samji and Hammer (2013) argue for monitoring that supports learning about what works rather than reporting
compliance.</p>

<h3>2.3 What predicts World Bank project performance</h3>
<p>Studies of the Bank&rsquo;s own project ratings find that project-level factors explain much more of the variation in outcomes than country
characteristics (Denizer, Kaufmann and Kraay 2013; Bulman, Kolkma and Kraay 2017), that preparation matters (Kilby 2015), and that projects with
better monitoring and evaluation are rated more highly (Raimondo 2016). IEG&rsquo;s annual <i>Results and Performance of the World Bank Group</i>
reports identify improving results monitoring as one of the main levers for better outcomes (IEG 2024). This literature uses ex-post ratings of
closed projects; the present paper looks instead at the indicators that the Scorecard aggregates while projects are under way.</p>

<h3>2.4 From a welfare anchor for operations to a welfare anchor for results</h3>
<p>Gonz&aacute;lez (2026) shows that each wave of private sector development doctrine redefined success&mdash;privatisation transactions,
reforms achieved, capital mobilised, accounts opened&mdash;and that &ldquo;a structural remedy cannot resolve an analytical problem&rdquo;.
His remedy is a test any operation must pass before public money is committed. The analogue for results is a test that any reported result
should pass before it is counted as evidence of development impact. Appendix B maps his three hurdles onto the three tests used here.</p>
"""

data_sec = f"""
<p><b>Source.</b> The data are the FY25 Scorecard exports published at scorecard.worldbank.org, with results as of 30 June 2025. I use the
project-level sheet of the four files that cover the people-level results areas: health, nutrition and population services; water, sanitation
and hygiene; gender-equality and economic-opportunity actions; and financial services. Each record is a project indicator mapped to a Scorecard
sub-indicator, with project characteristics (region, country, lead department, lending instrument, financing source, commitment, approval and
closing dates, FCV and LDC flags, income group).</p>

<p><b>Unit of analysis.</b> A <i>result</i> is one non-disaggregated project indicator contributing to one Scorecard sub-indicator. Female and youth
rows are disaggregations of these results and are used only in the gender test, where the unit is a project &times; sub-indicator pair. Table 1
shows how the samples are built; Table 2 describes the projects.</p>
{table_flow}
{table_desc}

<p><b>Key variables.</b> <i>Indicator type</i> is the results-chain classification described in Section 4.1. <i>Rescaled</i> equals one when the
progress conversion factor is positive and different from one, i.e. the project&rsquo;s own figure is multiplied to express it in the Scorecard
unit (for example, sewer connections multiplied by household size, or a vaccination percentage multiplied by a population). <i>Zero baseline</i>
equals one when the calculated baseline value is zero. <i>Fixed-share female figure</i> follows the export&rsquo;s disaggregation factor: when the
factor lies strictly between zero and one, the female figure is the total multiplied by an assumed share rather than a separate count.
<i>Behind</i> applies a linear on-track rule: a result is behind if the share of its target achieved is more than 10 percentage points below the
share of the implementation period elapsed (approval to closing). The rule is not an official WBG rating; it formalises the benchmark implicit
whenever cumulative progress is compared with elapsed time, and alternative thresholds are reported.</p>

<p><b>Dataset release.</b> The clean files <span class="mono">results_clean</span>, <span class="mono">gender_pairs</span> and
<span class="mono">projects_clean</span> are released in CSV and Stata (.dta) formats with variable labels, together with the Python build
script that produces them from the raw exports, an R script and a Stata do-file that reproduce every table and figure.</p>
"""

methods = f"""
<h3>4.1 Classifying what each indicator measures</h3>
<p>Each indicator&rsquo;s wording is classified into one of four types using ordered, transparent rules (Appendix A):
<b>outcome</b>&mdash;a change in a condition or behaviour of people or firms (income, employment, sales, health status, adoption of a practice,
service-use rates); <b>output</b>&mdash;something the project produces or does (people trained or certified, works built, loans issued, plans adopted);
<b>reach</b>&mdash;a count of people, households or firms who receive, access or benefit from project goods or services; and
<b>unclassifiable</b>&mdash;breakdown labels such as &ldquo;of which women&rdquo; or a country name. To guard against tuning the rules to the
data used to evaluate them, I drew two independent random samples of 200 results. The first (development set) was used to refine the rules;
the second (test set) was coded by hand without sight of the rule labels and is used only for evaluation. On the test set the rules agree with
the hand coding in {pc(K['val_test_accuracy'], 1)} of cases (&kappa; = {K['val_test_kappa']:.2f}, &ldquo;substantial&rdquo; agreement; Cohen 1960).
Reach is identified with high precision and recall; outcome labels are rarely wrong (precision {VAL['outcome']['precision']:.2f}) but some outcomes
are missed (recall {VAL['outcome']['recall']:.2f}). The rule-based share of outcome indicators should therefore be read as a lower bound, and I report
the hand-coded share alongside it (Table 4).</p>

<h3>4.2 Test 1: welfare relevance</h3>
<p>I estimate linear probability models (LPM) of the form</p>
<p class="eq">Outcome<sub>ip</sub> = &alpha; + &Sigma;<sub>s</sub> &beta;<sub>s</sub> Area<sub>s,ip</sub> + &Sigma;<sub>c</sub> &delta;<sub>c</sub> Cohort<sub>c,p</sub> + X&prime;<sub>p</sub>&gamma; + &mu;<sub>d(p)</sub> + &epsilon;<sub>ip</sub></p>
<p>where <i>i</i> indexes results and <i>p</i> projects, <i>Area</i> are Scorecard results areas, <i>Cohort</i> are approval-year groups (the FY25
cohort, approved after the new Scorecard was adopted, is of particular interest), <i>X</i> contains region, FCV status, income group, IDA
financing, lending instrument and log commitment, and &mu; are lead-department fixed effects. The LPM coefficients are directly interpretable
as percentage-point differences; logit average marginal effects are reported as a check.</p>

<h3>4.3 Test 2: measurement integrity</h3>
<p>I first document the prevalence of zero baselines, rescaled figures and fixed-share female figures, and the share of the reported achieved
total that comes from rescaled figures. I then estimate the same LPM with <i>Rescaled<sub>ip</sub></i> and, at the pair level,
<i>FixedShare<sub>jp</sub></i> as dependent variables, adding indicator type and a percentage-unit dummy in the rescaling model.</p>

<h3>4.4 Test 3: progress judgement</h3>
<p>Two questions matter: how does progress accumulate over a project&rsquo;s life, and what does the linear on-track rule actually pick up?
For the first, I estimate a fractional logit (Papke and Wooldridge 1996) for the share of target achieved, <i>y</i><sub>ip</sub> &isin; [0, 1]:</p>
<p class="eq">E[y<sub>ip</sub> | &middot;] = &Lambda;( &theta;<sub>1</sub>E<sub>ip</sub> + &theta;<sub>2</sub>E<sup>2</sup><sub>ip</sub> + &lambda;<sub>1</sub>Output<sub>ip</sub> + &lambda;<sub>2</sub>Outcome<sub>ip</sub> + &kappa;Rescaled<sub>ip</sub> + Area&prime;&beta; + X&prime;<sub>p</sub>&gamma; )</p>
<p>where <i>E</i> is the share of the implementation period elapsed and &Lambda; is the logistic function. If progress were linear, the predicted curve
would track the 45-degree line. For the second, I estimate LPMs of <i>Behind<sub>ip</sub></i> on project-age bins alone and then add indicator type,
rescaling, results area, project characteristics and department fixed effects. Comparing the R&sup2; of the timing-only model with the full model
shows how much of the explainable variation in &ldquo;behind&rdquo; is about time; the coefficient on <i>Outcome</i> shows whether the rule penalises
welfare measurement holding age constant.</p>

<p><b>Inference.</b> Results within a project share design, team and context, so all standard errors are clustered by project (Cameron and Miller
2015); clustering by country is reported as a robustness check. The analysis is descriptive and associational: the tests ask whether the
Scorecard&rsquo;s evidence has the properties a welfare-anchored system would need, not what causes project success.</p>
"""

v_out = VAL["outcome"]
results1 = f"""
<h3>5.1 Test 1: the Scorecard mostly counts reach</h3>
<p>Figure 1 and Table 3 show the composition of the evidence. Across all five results areas, {pc(K['share_type']['reach'])} of contributing
indicators count people or firms reached, {pc(K['share_type']['output'])} are outputs, and {pc(K['share_type']['outcome'])} measure a welfare
outcome. The hand-coded samples give a very similar picture: {pc(VAL['reach']['manual_share_400'])} reach and {pc(v_out['manual_share_400'])}
outcome (95% CI {pc(v_out['manual_lo'])}&ndash;{pc(v_out['manual_hi'])}). Water, sanitation and hygiene results contain essentially no outcome
indicators&mdash;every result counts people provided with a service&mdash;while economic opportunity and health have the highest outcome shares,
reflecting indicators such as jobs created, sales or income gains, and vaccination or service-coverage rates.</p>
{fig1}
{table_types}
{table_val}
<p>At the project level, {pc(K['projects_no_outcome'])} of the {n(K['n_projects'])} projects contribute no outcome indicator to the Scorecard,
and {pc(K['projects_only_reach'])} contribute only reach indicators. For most projects, then, the Scorecard can say how many people were
touched but not whether anything changed for them.</p>

<p>Table 5 shows that these differences are systematic. Relative to health, WASH results are {pp(-b_wash[0])} percentage points less likely
to be outcome indicators, financial-services results {pp(-b_fin[0])} points less likely, and gender-equality actions {pp(-b_gen[0])} points less
likely, holding region, fragility, income group, financing, instrument and size constant. Project characteristics other than the results area
explain little. Logit average marginal effects are almost identical (for example {pp(AME['financial_services'])} points for financial services).
Importantly, there is no sign that the new Scorecard shifted design toward welfare measurement: projects approved in FY25, after its adoption,
are {pp(b_fy25[0])} points more likely to use outcome indicators than pre-FY20 projects (p = {b_fy25[2]:.2f}), and the difference falls to
{pp(b_fy25_fe[0])} points (p = {b_fy25_fe[2]:.2f}) with department fixed effects. The hand-coded subsample tells the same story (Appendix Table A1).</p>
{table4}
"""

results2 = f"""
<h3>5.2 Test 2: much of the reported total is constructed</h3>
<p>Three features of the data show how far the Scorecard&rsquo;s numbers are built rather than measured (Table 6, Figure 2). First, {pc(K['zero_baseline'])}
of results start from a zero baseline, so they record cumulative contact with the project rather than change against a counterfactual or starting
level. Second, {pc(K['share_scaled'])} of results are rescaled by a conversion factor, but these account for {pc(K['achieved_from_scaled'])} of the
{n(ach_tot)} million achieved &ldquo;units&rdquo; reported across the five areas. In health the figure is {pc(T5.loc['health', 'achieved_from_scaled'])}:
most of the reported number of people receiving health services is derived by multiplying project indicators&mdash;often coverage percentages&mdash;by
population or household factors. Among indicators measured in percentages, {pc(K['pct_unit_scaled'])} are converted into counts of people in this way.
Third, {pc(K['double_counted_share'])} of results are masked to avoid double counting, a sensible correction that also signals how much overlap the
aggregation must manage.</p>
{fig2}
{table5}
<p>Gender disaggregation shows the same pattern more sharply. Of {n(n_pairs)} project &times; sub-indicator pairs with a female figure,
{n(gs['fixed_share'])} ({pc(gs['fixed_share'] / n_pairs)}) are fixed-share constructions, {n(gs['no_progress'])} report no progress yet, {n(gs['women_only'])}
concern women-only interventions and {n(gs['identical_share'])} report an identical planned and achieved share. Only {n(gs['informative'])}
({pc(K['informative_share'])}) can show whether women were reached in the proportion planned. Fixed-share figures dominate in health ({pc(fs['health'])})
and WASH ({pc(fs['wash'])}), the two areas where the Scorecard reports the largest numbers of women reached.</p>

<p>Table 7 shows that the construction of figures is mainly a property of the results area rather than of the country or project. There is one
encouraging trend: projects approved in FY24 and FY25 are {pp(-b_fs24[0])} and {pp(-b_fs25[0])} percentage points less likely than pre-FY20 projects
to report fixed-share female figures, and FY25 projects are {pp(-b_sc_fy25[0])} points less likely to be rescaled. Percentage-unit indicators are
{pp(b_sc_pct[0])} points more likely to be rescaled, as expected.</p>
{table6}
"""

results3 = f"""
<h3>5.3 Test 3: a linear on-track rule measures time and penalises welfare measurement</h3>
<p>Under the linear rule, {pc(K['behind_rate'])} of the {n(K['t3_n'])} judgeable results are behind schedule. Figure 4 shows that this share falls from
{pc(behind_age['<3 yrs'])} for projects less than three years old to {pc(behind_age['3-5 yrs'])}, {pc(behind_age['5-7 yrs'])} and {pc(behind_age['7+ yrs'])}
in successive age groups. Age bins alone explain an R&sup2; of {K['r2_timing']:.3f}, {pc(K['r2_timing_share'])} of the {K['r2_full']:.3f} explained by
the full model with design, project characteristics and department fixed effects (Table 8).</p>
{fig4}
<p>The reason is visible in Figure 3. Progress does not accumulate in a straight line: the fractional logit implies that a typical reach result
has achieved about {pc(pred['reach'])} of its target at the midpoint of implementation, not 50%, and an outcome result about {pc(pred['outcome'])}.
Results follow an S-shaped path in which early years are spent on procurement, works and institutional set-up. A benchmark that expects
proportional progress will therefore flag most young projects as failing, whatever their eventual performance.</p>
{fig3}
<p>The most consequential finding is the coefficient on outcome indicators. Holding project age, rescaling, results area, region, fragility,
income group, instrument, size and lead department constant, outcome indicators are {pp(b_out[0])} percentage points more likely to be rated behind
than reach indicators (Table 8, column 5; {pp(b_out4[0])} points without department fixed effects). In the fractional logit their progress is
significantly lower ({b_fl_out[0]:.2f} log-odds). Outcomes come later in the results chain, so a time-proportional rule systematically
makes them look worse. Rescaled figures move the other way: they are {pp(-b_scal[0])} points less likely to be behind, and their progress is
higher ({b_fl_sc[0]:.2f} log-odds), consistent with constructed numbers flattering performance. Combined with the Scorecard&rsquo;s role in cascading
targets, this creates exactly the multitask incentive that Holmstr&ouml;m and Milgrom (1991) describe: teams that choose to measure welfare are
penalised on the dimension that is monitored.</p>
{table7}

<h3>5.4 Robustness</h3>
<p>Table 9 shows that the two central Test 3 results hold across alternative definitions and samples. The outcome-indicator penalty ranges from
{pp(rob_out.estimate.min())} to {pp(rob_out[rob_out.model != 'Logit (log-odds)'].estimate.max())} percentage points across thresholds of 0 and
20 points, active projects only, excluding rescaled results, and clustering by country, and is significant in every specification; the logit
gives the same sign and significance. The age gradient is large and precise in all specifications. For Test 1, re-estimating on the 400 hand-coded
results (Appendix Table A1) reproduces the WASH gap and the absence of a post-Scorecard shift. Misclassification of a binary dependent variable
biases LPM coefficients toward zero when it is unrelated to the regressors (Hausman, Abrevaya and Scott-Morton 1998), so the Test 1 differences are,
if anything, understated.</p>
{table8}
"""

discussion = f"""
<p>Taken together, the three tests suggest that the Scorecard is anchored in reach rather than welfare. That is partly by design: aggregating
outcomes across heterogeneous projects is hard, and counts of people served are additive in a way that income gains or mortality reductions are
not. The 2024 reform recognised this tension and moved some indicators from access toward use (World Bank 2024b). But the project-level evidence
shows how far there is still to go. The numbers that headline the Group&rsquo;s annual reporting are dominated by cumulative counts from zero
baselines; a substantial part of them is produced by conversion factors and assumed shares; and the implicit standard for judging progress rewards
counting reach early and penalises measuring welfare.</p>

<p>Three caveats shape the interpretation. First, reach is not worthless: in WASH, for instance, connecting people to safely managed water is
itself close to a welfare outcome, and the Scorecard&rsquo;s vision indicators track country-level welfare separately. The point is that the
<i>results</i> layer, the part attributable to WBG operations, rarely measures change. Second, conversion factors are often reasonable
(household size is a sensible way to turn connections into people), but they are undocumented in the public release, so readers cannot tell which
totals are counted and which are modelled. Third, the &ldquo;behind&rdquo; finding concerns a linear rule that any reader of cumulative progress data
implicitly applies; it is not a claim about how WBG managers formally rate projects. The concern is that the same benchmark shapes how teams, managers
and the Board read the Scorecard.</p>

<p>The findings complement those of the project-performance literature. That literature shows that good monitoring and evaluation is associated
with better project outcomes (Raimondo 2016) and that most variation in performance is within countries (Bulman, Kolkma and Kraay 2017). Here too,
the results area and indicator choice&mdash;design decisions made by teams&mdash;explain far more than country characteristics. This means the
problem is fixable through the rules that govern what projects report.</p>
"""

recs = f"""
<p>Five changes would anchor the Scorecard in welfare without adding new reporting burdens.</p>
<ol class="recs">
<li><b>Publish an outcome-coverage ratio for each results area.</b> Alongside each people-level total, report the share of contributing projects that
also report at least one outcome indicator for the same beneficiaries (currently {pc(1 - K['projects_no_outcome'])} of projects overall and none in WASH).
Setting a rising floor for this ratio would reward teams for measuring change without redesigning the Scorecard.</li>
<li><b>Flag how every number was built.</b> Add a method code to each contributing figure&mdash;measured, rescaled, fixed-share disaggregation, zero
baseline&mdash;and publish totals with and without constructed components. In health, where {pc(T5.loc['health', 'achieved_from_scaled'])} of the
achieved total is rescaled, this single change would materially alter how the headline is read.</li>
<li><b>Count women only when women are counted.</b> Report the number of women reached only from directly measured disaggregations, and show
estimated figures separately. With {pc(K['informative_share'])} of female figures currently able to show whether women were reached as planned,
the gender headline mostly restates assumptions.</li>
<li><b>Replace linear benchmarks with empirical trajectories.</b> Judge progress against curves estimated from closed projects, by results area and
indicator type, rather than against elapsed time. The fractional-logit approach used here is one simple way to do this; it would remove most
of the spurious &ldquo;behind&rdquo; ratings for young projects.</li>
<li><b>Remove the penalty on outcome indicators.</b> When the Scorecard cascades into unit targets, assess outcome indicators against later milestones
or give them separate weight, so that choosing to measure welfare does not make a team look worse. IEG&rsquo;s formative evaluation is well placed to
test whether this penalty affects indicator choice in practice.</li>
</ol>
<p>For researchers and evaluators, the most valuable single step would be for the WBG to publish earlier Scorecard cycles in the same format.
That would allow trajectories, rather than snapshots, to be analysed, and would make it possible to test whether the 2024 reform changed reporting
behaviour.</p>
"""

limits = f"""
<p>The analysis uses one Scorecard cycle and is therefore cross-sectional; it cannot follow individual results over time or link them to
ex-post ratings. The indicator classification is rule-based and imperfect, although validated on a held-out sample and conservative for outcomes.
Some fields&mdash;notably conversion factors of zero or missing&mdash;are not documented in the public release, and I treat only explicit factors
different from one as rescaling. Results masked for double counting are excluded from Tests 2 and 3. The &ldquo;behind&rdquo; rule is an analytical
construct. Finally, the associations reported here are not causal estimates of the effect of indicator choice on project success; they describe the
properties of the evidence that the Scorecard aggregates.</p>
"""

conclusion = f"""
<p>The FY24&ndash;FY30 Scorecard set out to measure outcomes rather than inputs. Its own project-level evidence shows that it mostly measures reach:
most contributing indicators count people served, a large share of reported totals is constructed from conversion factors and assumed shares, and
the implicit standard for judging progress mostly reflects time while penalising the indicators that measure welfare. None of this requires a new
Scorecard. It requires the existing one to be anchored: to report how much of each number is measured, to show whether anything changed for the
people counted, and to judge progress against realistic trajectories. Those changes would let the Scorecard do what its designers intended&mdash;tell
the Group&rsquo;s shareholders and the public whether lives are improving, not just how many were reached.</p>
"""

appendix = f"""
<h3>Appendix A. Classification rules</h3>
<p>Indicator wording is lower-cased and stripped of ID prefixes and numbering. Rules are applied in order; the first match determines the type.</p>
<table class="simple small"><thead><tr><th>Order</th><th>Type</th><th>Rule (abbreviated; full regular expressions in <span class="mono">code/01_build_dataset.py</span>)</th></tr></thead><tbody>
<tr><td>1</td><td>Unclassifiable</td><td>Breakdown labels (&ldquo;of which&hellip;&rdquo;, &ldquo;female&rdquo;, &ldquo;regional&rdquo;) or fewer than four characters</td></tr>
<tr><td>2</td><td>Reach</td><td>Scorecard template wording &ldquo;benefiting from actions to&hellip;&rdquo;</td></tr>
<tr><td>3</td><td>Outcome</td><td>Income, earnings, sales, profits; mortality, stunting, prevalence; learning; employment status; new firms; people or firms adopting a practice; vaccinated; rates, proportions and shares; &ldquo;increase/reduction in&rdquo; (not &ldquo;in the number of&rdquo;)</td></tr>
<tr><td>4</td><td>Output</td><td>Trained, training, certified, apprenticeship, courses</td></tr>
<tr><td>5</td><td>Outcome</td><td>Jobs, employment (after training rules)</td></tr>
<tr><td>6</td><td>Reach</td><td>A person/household/firm noun followed by receiving, provided with, access, benefiting, using, enrolled, reached, supported, covered, served, participating</td></tr>
<tr><td>7</td><td>Output</td><td>Issued, disbursed, loans; constructed, rehabilitated, installed; prepared, approved, established; systems, plans, policies, registries</td></tr>
<tr><td>8</td><td>Reach</td><td>Any remaining person/household/firm noun</td></tr>
</tbody></table>

<h3>Appendix B. Mapping the welfare anchor to results</h3>
<table class="simple small"><thead><tr><th>Gonz&aacute;lez (2026) hurdle for operations</th><th>Test for reported results (this paper)</th><th>Evidence used</th></tr></thead><tbody>
<tr><td>Justification: a binding market failure is diagnosed</td><td>Welfare relevance: the result measures a change in welfare</td><td>Indicator wording; results-chain type</td></tr>
<tr><td>Effectiveness: the instrument acts on the distortion</td><td>Measurement integrity: the figure is measured, not constructed</td><td>Baselines, conversion and disaggregation factors</td></tr>
<tr><td>Additionality: outcomes would not occur otherwise</td><td>Progress judgement: ratings reflect performance, not time</td><td>Progress, targets, dates</td></tr>
</tbody></table>
{tA1}

<h3>Data and code availability</h3>
<p>All data are public WBG Scorecard exports. The replication package contains the clean datasets (CSV and .dta), the Python build script, the R
script and the Stata do-file, the hand-coded validation samples, and this paper&rsquo;s build script: [repository link].</p>

<h3>Use of AI tools</h3>
<p class="author-note">[Author to confirm before circulation.] The author used Claude (Anthropic) under the author&rsquo;s direction for drafting
analysis code, a first-pass coding of the validation samples, figure preparation and copy editing. All coding decisions, results and
interpretations were reviewed by the author, who is responsible for any remaining errors.</p>
"""

refs = [
    "Andrews, M., Pritchett, L., and Woolcock, M. (2013). Escaping capability traps through problem driven iterative adaptation (PDIA). <i>World Development</i>, 51, 234&ndash;244.",
    "Bevan, G., and Hood, C. (2006). What&rsquo;s measured is what matters: Targets and gaming in the English public health care system. <i>Public Administration</i>, 84(3), 517&ndash;538.",
    "Bulman, D., Kolkma, W., and Kraay, A. (2017). Good countries or good projects? Comparing macro and micro correlates of World Bank and Asian Development Bank project performance. <i>Review of International Organizations</i>, 12(3), 335&ndash;363.",
    "Cameron, A. C., and Miller, D. L. (2015). A practitioner&rsquo;s guide to cluster-robust inference. <i>Journal of Human Resources</i>, 50(2), 317&ndash;372.",
    "Campbell, D. T. (1979). Assessing the impact of planned social change. <i>Evaluation and Program Planning</i>, 2(1), 67&ndash;90.",
    "Cohen, J. (1960). A coefficient of agreement for nominal scales. <i>Educational and Psychological Measurement</i>, 20(1), 37&ndash;46.",
    "Denizer, C., Kaufmann, D., and Kraay, A. (2013). Good countries or good projects? Macro and micro correlates of World Bank project performance. <i>Journal of Development Economics</i>, 105, 288&ndash;302.",
    "Gonz&aacute;lez, &Aacute;. S. (2026). <i>The World Bank Cannot Stop Reorganizing Its Private Sector Work: The Missing Welfare Anchor</i>. CGD Policy Paper 402. Washington, DC: Center for Global Development.",
    "Hausman, J. A., Abrevaya, J., and Scott-Morton, F. M. (1998). Misclassification of the dependent variable in a discrete-response setting. <i>Journal of Econometrics</i>, 87(2), 239&ndash;269.",
    "Holmstr&ouml;m, B., and Milgrom, P. (1991). Multitask principal&ndash;agent analyses: Incentive contracts, asset ownership, and job design. <i>Journal of Law, Economics, and Organization</i>, 7, 24&ndash;52.",
    "Honig, D. (2018). <i>Navigation by Judgment: Why and When Top-Down Management of Foreign Aid Doesn&rsquo;t Work</i>. New York: Oxford University Press.",
    "Hood, C. (2006). Gaming in Targetworld: The targets approach to managing British public services. <i>Public Administration Review</i>, 66(4), 515&ndash;521.",
    "IEG (Independent Evaluation Group) (2016). <i>Behind the Mirror: A Report on the Self-Evaluation Systems of the World Bank Group</i>. Washington, DC: World Bank.",
    "IEG (2024). <i>Results and Performance of the World Bank Group 2024</i>. Washington, DC: World Bank.",
    "IEG (2025). <i>World Bank Group Scorecard Formative Evaluation: Approach Paper</i>. Washington, DC: World Bank, November.",
    "Kilby, C. (2015). Assessing the impact of World Bank preparation on project outcomes. <i>Journal of Development Economics</i>, 115, 111&ndash;123.",
    "Narayanaswamy, M. (2021). <i>What Gets Measured Gets Done: Using a Corporate Scorecard to Drive Greater Investment Impact</i>. EM Compass Note 108. Washington, DC: International Finance Corporation.",
    "Natsios, A. (2010). <i>The Clash of the Counter-bureaucracy and Development</i>. CGD Essay. Washington, DC: Center for Global Development.",
    "Papke, L. E., and Wooldridge, J. M. (1996). Econometric methods for fractional response variables with an application to 401(k) plan participation rates. <i>Journal of Applied Econometrics</i>, 11(6), 619&ndash;632.",
    "Pritchett, L., Samji, S., and Hammer, J. (2013). <i>It&rsquo;s All About MeE: Using Structured Experiential Learning (&ldquo;e&rdquo;) to Crawl the Design Space</i>. CGD Working Paper 322. Washington, DC: Center for Global Development.",
    "Raimondo, E. (2016). <i>What Difference Does Good Monitoring and Evaluation Make to World Bank Project Performance?</i> Policy Research Working Paper 7726. Washington, DC: World Bank.",
    "Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. <i>Journal of the American Statistical Association</i>, 22(158), 209&ndash;212.",
    "World Bank (2024a). <i>New World Bank Group Scorecard FY24&ndash;FY30: Driving Action, Measuring Results</i>. Washington, DC: World Bank Group.",
    "World Bank (2024b). &ldquo;World Bank Group Announces New Approach to Measuring Impact.&rdquo; Press release, April 9, 2024.",
    "World Bank Group (2025). <i>World Bank Group Scorecard</i>, FY25 data release (results as of June 30, 2025). scorecard.worldbank.org.",
]

CSS = """
@font-face { font-family: 'SS3'; src: url('fonts/source-sans-3-400-normal.woff2'); font-weight: 400; }
@font-face { font-family: 'SS3'; src: url('fonts/source-sans-3-600-normal.woff2'); font-weight: 600; }
@font-face { font-family: 'SS3'; src: url('fonts/source-sans-3-700-normal.woff2'); font-weight: 700; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-400-normal.woff2'); font-weight: 400; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-400-italic.woff2'); font-weight: 400; font-style: italic; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-600-normal.woff2'); font-weight: 600; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-700-normal.woff2'); font-weight: 700; }
@font-face { font-family: 'Mono'; src: url('fonts/ibm-plex-mono-400-normal.woff2'); font-weight: 400; }
@page { size: A4; margin: 22mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'SS4', Georgia, serif; font-size: 10.6pt; line-height: 1.5; color: #16212e; margin: 0; }
p { margin: 0 0 7pt; text-align: justify; hyphens: auto; }
h1 { font-size: 19pt; line-height: 1.2; margin: 0 0 6pt; font-weight: 700; }
h2 { font-family: 'SS3', sans-serif; font-size: 13pt; margin: 18pt 0 6pt; font-weight: 700; color: #0f2a44; break-after: avoid; }
h3 { font-family: 'SS3', sans-serif; font-size: 11pt; margin: 12pt 0 4pt; font-weight: 600; color: #0f2a44; break-after: avoid; }
.wp { font-family: 'SS3'; font-size: 8.5pt; letter-spacing: .08em; text-transform: uppercase; color: #0e7c74; margin-bottom: 14pt; }
.author { font-family: 'SS3'; font-size: 11pt; margin: 6pt 0 2pt; }
.aff { font-family: 'SS3'; font-size: 9pt; color: #465264; margin-bottom: 14pt; }
.abstract { border-top: 0.8pt solid #16212e; border-bottom: 0.8pt solid #16212e; padding: 8pt 0; margin: 10pt 0 8pt; font-size: 10pt; }
.abstract p { margin: 0; }
.kw { font-family: 'SS3'; font-size: 8.8pt; color: #465264; }
.mono { font-family: 'Mono', monospace; font-size: 8.6pt; }
.eq { text-align: center; margin: 6pt 0 9pt; font-style: italic; }
figure { margin: 10pt 0 12pt; }
figcaption { font-family: 'SS3'; font-size: 9.4pt; margin-bottom: 5pt; }
figure img { width: 100%; }
.note { font-family: 'SS3'; font-size: 8pt; color: #465264; line-height: 1.35; margin-top: 4pt; text-align: left; }
table { border-collapse: collapse; width: 100%; font-family: 'SS3', sans-serif; font-size: 8.6pt; }
thead th { border-top: 0.9pt solid #16212e; border-bottom: 0.6pt solid #16212e; padding: 3pt 4pt; font-weight: 600; text-align: center; vertical-align: bottom; }
thead th:first-child { text-align: left; }
tbody td { padding: 1.6pt 4pt; text-align: center; }
tbody td:first-child { text-align: left; }
tbody tr:last-child td { border-bottom: 0.9pt solid #16212e; }
table.reg tr.se td { color: #465264; font-size: 7.8pt; padding-top: 0; }
table.reg tr.grp td { font-style: italic; color: #0e7c74; padding-top: 4pt; }
table.reg tr.stat:first-of-type td { border-top: 0.6pt solid #16212e; }
table.reg tr.stat td { padding-top: 2pt; }
table.simple td { border-bottom: 0.3pt solid #dfe3e8; padding: 3pt 4pt; }
table.small { font-size: 8.2pt; }
table.small td { text-align: left; }
.sub { font-weight: 400; font-size: 7.6pt; color: #465264; }
.avoid { break-inside: avoid; }
.pb { break-before: page; }
ol.recs li { margin-bottom: 6pt; text-align: justify; }
.refs p { padding-left: 18pt; text-indent: -18pt; text-align: left; font-size: 9.4pt; margin-bottom: 4pt; }
.author-note { background: #f8f1de; padding: 6pt 8pt; font-size: 9.4pt; }
"""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Counting Reach, Not Welfare</title><style>{CSS}</style></head><body>
<div class="wp">Working paper &middot; Draft for comment &middot; October 2026</div>
<h1>Counting Reach, Not Welfare: Testing the World Bank Group Scorecard Against a Welfare Anchor</h1>
<div class="author">Ashu Arora</div>
<div class="aff">Independent researcher [affiliation and contact to be added]</div>
<div class="abstract"><p><b>Abstract.</b> {abstract}</p></div>
<p class="kw"><b>Keywords:</b> results measurement; World Bank; corporate scorecard; performance indicators; gender data; development effectiveness.
<b>JEL:</b> F35, O19, H43, C25.</p>
<h2>1. Introduction</h2>{intro}
<h2>2. Background and related literature</h2>{background}
<h2>3. Data</h2>{data_sec}
<h2>4. Methods</h2>{methods}
<h2>5. Results</h2>{results1}{results2}{results3}
<h2>6. Discussion</h2>{discussion}
<h2>7. Recommendations</h2>{recs}
<h2>8. Limitations</h2>{limits}
<h2>9. Conclusion</h2>{conclusion}
<h2 class="pb">References</h2><div class="refs">{''.join(f'<p>{r}</p>' for r in refs)}</div>
<h2 class="pb">Appendix</h2>{appendix}
</body></html>"""

(PAPER / "paper.html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

exe = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=exe)
    pg = b.new_page()
    pg.goto((PAPER / "paper.html").resolve().as_uri())
    pg.wait_for_timeout(800)
    pg.pdf(path=str(PAPER / "counting-reach-not-welfare.pdf"), format="A4", print_background=True,
           display_header_footer=True, header_template="<span></span>",
           footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#7a8494;font-family:sans-serif">'
                           '<span class="pageNumber"></span></div>',
           margin={"top": "22mm", "bottom": "22mm", "left": "22mm", "right": "22mm"})
    b.close()
print("wrote paper/paper.html and paper/counting-reach-not-welfare.pdf")
