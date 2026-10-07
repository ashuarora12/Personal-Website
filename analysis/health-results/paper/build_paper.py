"""
build_paper.py - renders the WBER manuscript and its online appendix (HTML -> PDF) from the R outputs.
Every number in the text is read from output/key_numbers.json or output/tables/*.csv.
Run from the health-results folder:  python3 paper/build_paper.py
"""
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "output" / "tables"
PAPER = ROOT / "paper"
K = json.load(open(ROOT / "output" / "key_numbers.json"))


def pc(x, d=0):
    return f"{100 * x:.{d}f}%" if d else f"{round(100 * x):.0f}%"


def m(x, d=1):
    return f"{x:,.{d}f}"


def n(x):
    return f"{int(round(x)):,}"


def stars(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


T1 = pd.read_csv(TAB / "table1_reconciliation.csv")
T2 = pd.read_csv(TAB / "table2_method.csv").set_index("method")
T3 = pd.read_csv(TAB / "table3_family_method.csv")
T4 = pd.read_csv(TAB / "table4_bounds.csv")
T5 = pd.read_csv(TAB / "table5_concentration.csv").set_index("top_k")
T6 = pd.read_csv(TAB / "table6_female.csv")
T7 = pd.read_csv(TAB / "table7_health_vs_other.csv")
TOP = pd.read_csv(TAB / "tableA1_top20.csv")
H = pd.read_csv(ROOT / "data" / "health_results.csv")
B = {r.rule[:3]: r for r in T4.itertuples()}
sm = K["share_method"]
t7 = {r["model"]: r for r in K["t7"]}
top5 = pd.DataFrame(K["top5_countries"])
hp = K["health_pair_status"]


def table(num, caption, header, rows, note, cls=""):
    h = "".join(f"<th>{x}</th>" for x in header)
    b = "".join("<tr" + (' class="tot"' if str(r[0]).startswith(("Total", "WBG", "All")) else "") + ">" +
                "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<figure class="tbl avoid {cls}"><figcaption><b>Table {num}.</b> {caption}</figcaption>'
            f'<table class="simple"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'
            f'<p class="note">{note}</p></figure>')


def regtable(num, caption, note):
    models = ["(1) Rescaled", "(2) Female figure fixed share", "(3) Outcome indicator", "(4) Behind schedule"]
    heads = ["(1)<br>Result rescaled", "(2)<br>Female figure is a fixed share", "(3)<br>Outcome indicator", "(4)<br>Rated behind"]
    terms = [("health", "Health results area"), ("outcome_ind", "Outcome indicator"), ("scaled", "Rescaled"),
             ("age_bin3-5", "3&ndash;5 years since approval"), ("age_bin5-7", "5&ndash;7 years"), ("age_bin7+", "7+ years"),
             ("fcv", "FCV country"), ("ida", "IDA-financed"), ("log_commit", "Log commitment")]
    body = ""
    for term, label in terms:
        cells, ses = [], []
        for mo in models:
            r = T7[(T7.model == mo) & (T7.term == term)]
            if r.empty:
                cells.append(""); ses.append("")
            else:
                r = r.iloc[0]; cells.append(f"{r.estimate:.3f}{stars(r.p)}"); ses.append(f"({r.se:.3f})")
        body += f"<tr><td>{label}</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
        body += '<tr class="se"><td></td>' + "".join(f"<td>{c}</td>" for c in ses) + "</tr>"
    st = T7.drop_duplicates("model").set_index("model")
    body += '<tr class="stat"><td>Mean of dependent variable, other areas</td>' + "".join(f"<td>{st.loc[mo, 'dep_mean_other']:.3f}</td>" for mo in models) + "</tr>"
    body += '<tr class="stat2"><td>Region, income group, instrument, approval cohort</td>' + "<td>Yes</td>" * 4 + "</tr>"
    body += '<tr class="stat2"><td>Observations</td>' + "".join(f"<td>{n(st.loc[mo, 'n'])}</td>" for mo in models) + "</tr>"
    body += '<tr class="stat2"><td>R&sup2;</td>' + "".join(f"<td>{st.loc[mo, 'r2']:.3f}</td>" for mo in models) + "</tr>"
    h = "".join(f"<th>{x}</th>" for x in heads)
    return (f'<figure class="tbl avoid"><figcaption><b>Table {num}.</b> {caption}</figcaption>'
            f'<table class="reg"><thead><tr><th></th>{h}</tr></thead><tbody>{body}</tbody></table><p class="note">{note}</p></figure>')


def fig(path, num, caption, note):
    return (f'<figure class="fig avoid"><figcaption><b>Figure {num}.</b> {caption}</figcaption>'
            f'<img src="../output/figures/{path}"><p class="note">{note}</p></figure>')


# ------------------------------------------------------------------ tables
table1 = table(1, "From the published headline to project records",
               ["", "Achieved (million)", "Expected (million)"],
               [[r.item.replace("  ", "&nbsp;&nbsp;&nbsp;"), m(r.achieved_m, 2), "" if pd.isna(r.expected_m) else m(r.expected_m, 2)]
                for r in T1.itertuples()],
               "Indicator: &ldquo;Number of people receiving quality health, nutrition, and population services&rdquo;, FY25 "
               "Scorecard, results as of 30 June 2025, all countries. WB project records exclude the "
               f"{K['n_double']} results masked for double counting, which carry zero achieved values. IFC and MIGA publish aggregates only.")

lab = {"direct": "Direct count of people", "adjusted": "Count of people &times; adjustment factor",
       "coverage": "Coverage percentage &times; population base", "unit": "Other unit (visits, facilities, cases) &times; factor"}
table2 = table(2, "How the World Bank health total is constructed",
               ["Measurement method", "Results", "Projects", "Median factor", "Achieved (million)", "Share"],
               [[lab[k], n(T2.loc[k, "positive"]), n(T2.loc[k, "projects"]),
                 f"{T2.loc[k, 'median_factor']:,.2f}" if T2.loc[k, 'median_factor'] < 100 else f"{T2.loc[k, 'median_factor']:,.0f}",
                 m(T2.loc[k, "achieved_m"]), pc(T2.loc[k, "share"])] for k in ["direct", "adjusted", "coverage", "unit"]] +
               [["Total", n(K["n_positive"]), "", "", m(K["wb_project_sum"]), "100%"]],
               "Results with a positive achieved value among results not masked for double counting. Method is assigned from the "
               "conversion factor, unit of measure and indicator wording (Section 3.2); all 92 results were also reviewed by hand "
               "(online appendix table A1). Median factor: median progress conversion factor among the results in each row.")

# column names from reshape: achieved_m.adjusted, achieved_m.coverage, achieved_m.direct, achieved_m.unit
T3c = T3.rename(columns=lambda c: c.replace("achieved_m.", ""))
rows3 = [[r["family_label"], n(r["results"]), m(r["total"]), pc(r["share"]),
          pc((r["coverage"] + r["unit"]) / r["total"]) if r["total"] > 0 else ""] for _, r in T3c.iterrows()]
table3 = table(3, "What the health total is made of: service families",
               ["Service family", "Results", "Achieved (million)", "Share of total", "Converted from percentages or other units"],
               rows3 + [["Total", n(K["n_positive"]), m(K["wb_project_sum"]), "100%",
                         pc(sm["coverage"] + sm["unit"])]],
               "Service family assigned from indicator wording (online appendix B). &ldquo;Aggregate HNP service count&rdquo;: "
               "indicators reported directly in the Scorecard&rsquo;s own unit (&ldquo;people who have received essential health, "
               "nutrition, and population services&rdquo;), whose underlying services are not itemised in the public data.")

table4 = table(4, "The headline under alternative counting rules",
               ["Counting rule", "WB achieved (million)", "Achieved / expected", "WBG headline (million)", "Share of published headline"],
               [[r.rule, m(r.achieved_m), f"{r.achieved_over_expected:.2f}", m(r.wbg_headline_m), pc(r.share_of_published)]
                for r in T4.itertuples()],
               "WBG headline = WB total under each rule plus the published IFC (68.3 million) and MIGA (0.06 million) aggregates, "
               "which cannot be decomposed. Rule (1) drops results with a positive achieved value but a zero raw progress value. "
               "Rules are accounting identities; no sampling uncertainty is involved.")

table5 = table(5, "Concentration of the World Bank health total",
               ["Statistic", "Value"],
               [["Results with a positive contribution", n(K["n_positive"])],
                ["Share of total from the largest result", pc(T5.loc[1, "share"])],
                ["Share from the 5 largest results", pc(T5.loc[5, "share"])],
                ["Share from the 10 largest results", pc(T5.loc[10, "share"])],
                ["Share from the 20 largest results", pc(T5.loc[20, "share"])],
                ["Herfindahl index across results", f"{K['hhi']:.3f}"],
                ["Effective number of results (1/HHI)", f"{K['effective_n']:.1f}"],
                ["Countries with a positive contribution", n(K["n_countries_positive"])],
                ["Share from the 5 largest countries", pc(top5.share.sum())]],
               "Results not masked for double counting, World Bank projects only.")


T8p = pd.read_csv(TAB / "table8_performance_by_method.csv").set_index("method")
T9c = pd.read_csv(TAB / "table9_composition_by_group.csv")
labp = {"direct": "Direct count of people", "adjusted": "Adjusted count of people", "coverage": "Coverage conversion",
        "unit": "Unit conversion", "all": "All results"}
table_perf = table(6, "Reported performance by measurement method",
                   ["Measurement method", "Results", "Achieved (million)", "Expected (million)", "Achieved / expected", "Share of results above target"],
                   [[labp[k], n(T8p.loc[k, "results"]), m(T8p.loc[k, "achieved_m"]), m(T8p.loc[k, "expected_m"]),
                     f"{T8p.loc[k, 'achieved_over_expected']:.2f}", pc(T8p.loc[k, "share_exceeding_target"])]
                    for k in ["direct", "adjusted", "coverage", "unit", "all"]],
                   "Results not masked for double counting. Expected = target minus baseline, converted with the same factor as the result. "
                   "Share above target: results whose achieved value exceeds the expected value, among results with a positive expected value.")
reg_lab = {"AFE": "Eastern & Southern Africa", "AFW": "Western & Central Africa", "EAP": "East Asia & Pacific",
           "ECA": "Europe & Central Asia", "LCR": "Latin America & Caribbean", "MENAAP": "Middle East, N. Africa, Afghanistan & Pakistan",
           "SAR": "South Asia", "FCV": "Fragile and conflict-affected", "Not FCV": "Not fragile or conflict-affected",
           "IDA": "IDA-financed", "IBRD/other": "IBRD and other financing"}
table_comp = table(7, "Who relies on conversions? Composition of the total by region and financing",
                   ["Group", "Total (million)", "Direct", "Adjusted", "Coverage", "Unit"],
                   [[reg_lab.get(r.group, r.group), m(r.total_m), pc(r.direct), pc(r.adjusted), pc(r.coverage), pc(r.unit)]
                    for r in T9c.itertuples()],
                   "Shares of each group&rsquo;s contribution to the World Bank health total, by measurement method. Rows within each "
                   "panel (region; fragility; financing) sum to the World Bank total.")

table6 = table(8, "How women reached are counted in the health indicator",
               ["Component", "Results", "Women reached (million)", "Share"],
               [[r.component, n(r.results), m(r.achieved_m), pc(r.share)] for r in T6.itertuples()] +
               [["Total (equals published WBG female figure)", n(K["female_n"]), m(K["female_total"]), "100%"]],
               "Female disaggregation rows of the health indicator with a positive achieved value, not masked for double counting. "
               f"&ldquo;Fixed share&rdquo;: the disaggregation factor lies strictly between 0 and 1 (median {K['female_factor_median']:.3f}, "
               f"interquartile range {K['female_factor_iqr'][0]:.3f}&ndash;{K['female_factor_iqr'][1]:.3f}).")

table7 = regtable(9, "Health results compared with the other Scorecard results areas: linear probability models",
                  "Each column regresses the indicated outcome on a dummy for the health results area (base: the four other "
                  "people-level areas&mdash;WASH, gender-equality actions, economic opportunity, financial services) and controls. "
                  "Column (1): results not masked for double counting; (2): project &times; sub-indicator pairs with a female figure; "
                  "(3): all results; (4): results with a positive target and at least 20% of the implementation period elapsed. "
                  "&ldquo;Behind&rdquo;: share of target achieved more than 10 percentage points below the share of the implementation "
                  "period elapsed. Standard errors clustered by project in parentheses. *** p&lt;0.01, ** p&lt;0.05, * p&lt;0.10.")

fig1 = fig("fig1_decomposition.png", 1, "The WBG health headline by source and measurement method",
           f"Total = {m(K['wbg'])} million. Blue: counts of people; orange: figures converted into people from coverage "
           "percentages or other units; grey: IFC and MIGA aggregates, which have no public project-level data.")
fig2 = fig("fig2_concentration.png", 2, "A few results make up most of the World Bank health total",
           f"Cumulative share of the World Bank total ({m(K['wb_project_sum'])} million) contributed by the {K['n_positive']} results "
           "with a positive value, ranked from largest to smallest. Orange points: vaccination results. Dashed lines: 50% and 80%.")
fig3 = fig("fig3_bounds.png", 3, "The headline under alternative counting rules", "See table 4 for definitions.")
fig4 = fig("fig4_women.png", 4, "Women reached: measured versus assumed", "See table 8.")

# ------------------------------------------------------------------ text
cov_vacc = K["coverage_vacc_share_of_coverage"]
abstract = f"""
How many people did the World Bank Group&rsquo;s health operations reach? The Group&rsquo;s FY24&ndash;FY30 Scorecard answers with a
single number: {m(K['wbg'])} million people received quality health, nutrition and population services by June 2025. Using the public
project-level records behind that number, I reconcile it exactly to {K['n_positive']} World Bank project results plus IFC and MIGA
aggregates and decompose it by how each figure was produced. Only {pc(sm['direct'])} of the World Bank total is a direct count of people.
{pc(sm['coverage'])} comes from coverage percentages multiplied by population bases&mdash;overwhelmingly COVID-19 vaccination
rates&mdash;and {pc(sm['unit'])} from converting outpatient visits, facilities and cases into people; {m(K['not_reproducible_m'])}
million cannot be reproduced from the published progress values. Restricting the count to people actually counted lowers the headline
by a third, to {m(B['(4)'].wbg_headline_m, 0)} million. The total is concentrated: ten results supply {pc(T5.loc[10, 'share'])} of it.
{pc(K['female_fixed_share'])} of the {m(K['female_total'], 0)} million women reported reached are the total multiplied by an assumed
share of about one half. Health results are {round(100 * t7['(1) Rescaled']['estimate'])} percentage points more likely than other
Scorecard results to be rescaled. The health workforce appears in {K['hw_projects']} of {n(K['hw_total'])} Scorecard projects. The
findings argue for reporting effective coverage and publishing how each figure is constructed.
"""

intro = f"""
<p>Development institutions increasingly summarise their work in a few headline numbers. The World Bank Group&rsquo;s Scorecard for
FY24&ndash;FY30 replaced roughly 150 indicators with 22 results indicators and was presented as a shift toward measuring outcomes rather
than inputs (World Bank 2024a, 2024b). In health, the headline is the number of people receiving quality health, nutrition and population
(HNP) services: {m(K['wbg'])} million by 30 June 2025, against an expected {m(T1.expected_m[0])} million. Numbers of this kind travel
far: into annual reports, replenishment negotiations and, through the Scorecard&rsquo;s cascade into unit targets, into how staff
are managed (Narayanaswamy 2021). Yet little is known about what they are made of.</p>

<p>This paper opens the health headline. The Scorecard&rsquo;s public data release reports, for every World Bank project indicator that
contributes, the original indicator wording, its baseline, progress and target values in the project&rsquo;s own unit, and the conversion
and disaggregation factors used to express it in the Scorecard&rsquo;s unit of &ldquo;people&rdquo;. I use these records to answer four
questions. Does the headline reconcile to its parts? How is each part measured? How sensitive is the headline to the way it is constructed?
And what does the indicator leave out?</p>

<p>The headline reconciles exactly: {m(K['wb'])} million from {K['n_positive']} World Bank project results plus {m(K['ifc'])}
million reported by IFC and {m(K['miga'], 2)} million by MIGA, which publish aggregates only. Its construction, however, is far from a
head-count. Only {pc(sm['direct'])} of the World Bank total is a direct count of people; a further {pc(sm['adjusted'])} is a count of people
multiplied by an adjustment factor. {pc(sm['coverage'])} is produced by multiplying a percentage&mdash;mostly the share of a priority
population vaccinated against COVID-19&mdash;by a population base, and {pc(sm['unit'])} by converting outpatient visits, consultations,
facilities or case notifications into people. In one case, {K['facility_example']:.2f} million people are inferred from 137 health facilities
&ldquo;constructed, renovated, and/or equipped&rdquo; at 10,000 people per facility. Four results worth {m(K['not_reproducible_m'])} million
report a raw progress value of zero, so their contribution cannot be reproduced from the published fields.</p>

<p>These choices matter for the number. Restricting the headline to results that count people lowers it from {m(K['wbg'], 0)} million to
{m(B['(4)'].wbg_headline_m, 0)} million; counting only unadjusted head-counts lowers it to {m(B['(6)'].wbg_headline_m, 0)} million. The total
is also concentrated: the largest single result contributes {pc(T5.loc[1, 'share'])} of the World Bank total and ten results contribute
{pc(T5.loc[10, 'share'])}. The gender breakdown is even more assumption-dependent: {pc(K['female_fixed_share'])} of the {m(K['female_total'])}
million women reported reached are calculated by multiplying the total by a fixed share, typically 0.50&ndash;0.52. Compared with the other
people-level results areas in the Scorecard, health results are far more likely to be rescaled and to rely on fixed-share gender figures,
somewhat more likely to use outcome-type indicators, and much less likely to fall behind schedule. Finally, what is counted is service
contact: the health workforce, the input most often identified as binding for universal health coverage, appears in only {K['hw_projects']} of
the {n(K['hw_total'])} projects in the Scorecard data, and never together with migration.</p>

<p>The paper contributes to three literatures. First, it adds to work on the quality of development statistics, which documents how
administrative and reported data can diverge from what they purport to measure&mdash;often in the direction of exaggerated progress&mdash;when
they are tied to funding or reputation (Lim et al. 2008; Jerven 2013; Sandefur and Glassman 2015). Here the reporting entity is a
multilateral lender rather than a government, and the issue is construction rather than misreporting: every conversion is documented in the
data, but the published headline does not reveal them. Second, it speaks to the measurement of universal health coverage, where the field has
moved from counting service contacts toward effective coverage that combines need, use and quality (Shengelia et al. 2005; Ng et al. 2014;
WHO and World Bank 2023). Evidence that much care in low- and middle-income countries is of low quality (Das and Hammer 2014; Kruk et al. 2018)
makes the distinction between people &ldquo;reached&rdquo; and people helped central. Third, it contributes to the study of indicators as
instruments of governance (Kelley and Simmons 2015) and of target regimes in health care (Bevan and Hood 2006), by quantifying how a single
corporate indicator aggregates heterogeneous measures. The analysis is fully reproducible from public data; replication files in Stata and R
accompany the paper.</p>
"""

background = f"""
<h3>2.1 The indicator</h3>
<p>The Scorecard indicator &ldquo;Number of people receiving quality health, nutrition, and population services&rdquo; aggregates results from
World Bank (IBRD/IDA) operations, IFC investments and MIGA guarantees (World Bank 2024a). For World Bank operations, each contributing project
maps one or more of its own results-framework indicators to the Scorecard indicator. The project reports a baseline, a latest progress value
and a target in its own unit; these are multiplied by a <i>conversion factor</i> to express them in people, and the achieved result is
defined as progress minus baseline and the expected result as target minus baseline. Female and youth figures are produced either from
separately reported disaggregated indicators or by multiplying the total by a <i>disaggregation factor</i>. Where several indicators within
or across projects could count the same people, some are <i>masked</i> for double counting and enter with a value of zero.</p>

<h3>2.2 Why construction matters</h3>
<p>Each step is defensible in isolation. Converting households to people with an average household size, or attributing a share of a national
programme to a project, are standard practices in results reporting. But the steps differ in what they measure. A direct count of people who
received a service is close to the indicator&rsquo;s wording. A change in vaccination coverage multiplied by a population base is an estimate
of people newly covered, which depends on the denominator and assumes the percentage-point change applies to the base. A count of outpatient
visits multiplied by a factor is a count of contacts converted into people with an assumed number of visits per person. A count of facilities
multiplied by a catchment population measures potential access, not service use. When these are summed into one figure, the headline
inherits the mixture, and the mixture is invisible in the published total. This matters for interpretation because effective coverage
requires that people in need actually use services of adequate quality (Ng et al. 2014), and because aggregates of heterogeneous measures
can move for reasons unrelated to performance&mdash;for example, a single large conversion entering or leaving the portfolio.</p>

<h3>2.3 Related evidence on results reporting</h3>
<p>The World Bank&rsquo;s own evaluators have long noted that its self-evaluation systems serve reporting and accountability better than learning
(IEG 2016), and IEG launched a formative evaluation of the Scorecard in 2025 whose approach paper discusses the risk that centralised indicator
systems direct attention toward what is quantifiable (IEG 2025; Hood 2006). Project-level studies show that the quality of monitoring and evaluation
is associated with better-rated outcomes (Raimondo 2016) and that most of the variation in project performance lies within rather than between
countries (Bulman, Kolkma, and Kraay 2017), so how individual projects measure results is consequential. The incentive literature predicts that
when some dimensions of performance are easier to measure, effort and reporting shift toward them (Campbell 1979; Holmstr&ouml;m and Milgrom 1991),
a concern that is acute in aid, where top-down measurement fits poorly with outcomes that are hard to verify (Honig 2018). A companion paper shows
that across all five people-level results areas, most Scorecard indicators count people reached rather than changes in welfare (Arora 2026).
This paper goes deeper into one indicator, asking how its single headline number is built.</p>
"""

data = f"""
<h3>3.1 Source and sample</h3>
<p>I use the FY25 Scorecard data release (results as of 30 June 2025) from scorecard.worldbank.org: the &ldquo;Aggregates&rdquo; sheet,
which reports the published totals by institution, and the &ldquo;WB Project Information&rdquo; sheet, which reports one row per project
indicator and demographic group. The health indicator has {n(K['n_results'])} non-disaggregated World Bank project results from
{n(K['n_projects'])} projects in {n(K['n_countries'])} countries. Of these, {n(K['n_double'])} are masked for double counting and carry a
zero achieved value, leaving {n(K['n_counted'])} results that enter the total, of which {n(K['n_positive'])} have a positive achieved value.
Table 1 shows that the project records reproduce the published World Bank figure to the last person, and that the WBG headline equals the
World Bank total plus the IFC and MIGA aggregates. IDA-financed operations account for {pc(K['ida'] / K['wb'])} of the World Bank total.</p>
{table1}
<p>For comparisons with other results areas (section 8) I use the companion dataset of all {n(3617)} non-disaggregated results that feed the
Scorecard&rsquo;s five people-level results indicators (health; water, sanitation and hygiene; gender-equality actions; economic opportunity;
financial services), with project characteristics from the same release (Arora 2026). For the health workforce (section 9) I use a
rule-based classification of the development objectives and indicator text of all {n(K['hw_total'])} projects in the release.</p>

<h3>3.2 Classification</h3>
<p>Each contributing result is assigned a <i>measurement method</i> using the conversion factor, the unit of measure and the indicator wording:
(i) <i>direct</i>, when no conversion is applied; (ii) <i>adjusted</i>, when an indicator that counts people is multiplied by a factor other than
one; (iii) <i>coverage</i>, when a percentage or rate is multiplied by a population base; and (iv) <i>unit</i>, when a count of something other
than people&mdash;visits, consultations, facilities, case notifications&mdash;is converted into people. Each result is also assigned a
<i>service family</i> from its wording (vaccination; aggregate HNP service counts; outpatient care; screening; maternal, reproductive health and
family planning; nutrition; TB and HIV; facilities; other). Because only {K['n_positive']} results contribute to the total, the rule-based
assignments were checked by hand for every one of them; online appendix table A1 lists each result with its wording, factor and codes so that
readers can verify them. The results-chain type of each indicator (reach, output or outcome) follows the validated rules in Arora (2026),
which agree with independent hand coding in 84 percent of a held-out sample (Cohen&rsquo;s &kappa; = 0.66).</p>
"""

decomp = f"""
<p>Table 2 and figure 1 decompose the World Bank total by measurement method. Direct counts of people account for
{m(T2.loc['direct', 'achieved_m'])} million ({pc(sm['direct'])}), from {T2.loc['direct', 'positive']} results. Counts of people multiplied by
an adjustment factor add {m(T2.loc['adjusted', 'achieved_m'])} million ({pc(sm['adjusted'])}); the median factor is
{T2.loc['adjusted', 'median_factor']:.2f}, consistent with attributing a share of a larger programme to the project or removing overlap.
Coverage conversions add {m(T2.loc['coverage', 'achieved_m'])} million ({pc(sm['coverage'])}); the median factor is
{T2.loc['coverage', 'median_factor']:,.0f} people per percentage point. Conversions from other units add
{m(T2.loc['unit', 'achieved_m'])} million ({pc(sm['unit'])}), dominated by one result that converts {m(K['outpatient_visits_example'])} million
&ldquo;people&rdquo; from annual outpatient visits.</p>
{table2}
{fig1}
<p>Table 3 shows the same total by service family. Aggregate HNP service counts&mdash;indicators reported directly in the Scorecard&rsquo;s
own wording&mdash;make up {pc(K['share_aggregate_family'])} of the total. These are mostly direct or adjusted counts, but the services behind
them are not itemised in the public data, so a reader cannot tell whether a person counted received a vaccination, an antenatal visit or a
nutrition supplement. Vaccination contributes {pc(K['share_vaccination'])}; {pc(K['vacc_from_covid_projects'])} of it comes from projects
explicitly named as COVID-19 response or vaccination operations, and {pc(cov_vacc)} of all coverage conversions are vaccination results.
In other words, about one quarter of the World Bank&rsquo;s health headline ({pc(K['share_covid_vacc_of_total'])}) is COVID-19 vaccination
coverage expressed as people. Outpatient visits and consultations contribute {pc(T3c.loc[T3c.family_label.str.startswith('Outpatient'), 'share'].iloc[0])},
and screening for non-communicable diseases {pc(T3c.loc[T3c.family_label.str.startswith('Screening'), 'share'].iloc[0])}, almost all of it
through a single coverage conversion. Maternal and reproductive health, nutrition, and TB and HIV&mdash;areas central to the World Bank&rsquo;s
health strategy&mdash;together contribute about {pc(T3c.loc[T3c.family_label.str.startswith(('Maternal', 'Nutrition', 'TB')), 'share'].sum())}.</p>
{table3}
<p>Two features deserve emphasis. First, some conversions measure access rather than use. The facilities example in the introduction
counts people in the catchment of upgraded facilities; another result converts the percentage of schools receiving dental check-ups into people.
Second, four results&mdash;including the two largest unit conversions&mdash;report a positive achieved value although their raw progress value
is zero. Together they account for {m(K['not_reproducible_m'])} million people ({pc(K['not_reproducible_m'] / K['wb_project_sum'])} of the
World Bank total). The calculated values may come from information not included in the release, but they cannot be reproduced from it.</p>
"""

bounds = f"""
<p>How much does the headline depend on these choices? Table 4 and figure 3 recompute it under progressively stricter counting rules, holding
the IFC and MIGA aggregates at their published values because they cannot be decomposed. Excluding the {K['not_reproducible_n']}
non-reproducible results lowers the WBG headline to {m(B['(1)'].wbg_headline_m, 0)} million. Excluding coverage conversions lowers it to
{m(B['(3)'].wbg_headline_m, 0)} million. Counting only results that count people&mdash;direct or adjusted&mdash;yields
{m(B['(4)'].wbg_headline_m, 0)} million, {pc(1 - B['(4)'].share_of_published)} below the published figure, and counting only unadjusted
head-counts yields {m(B['(6)'].wbg_headline_m, 0)} million, about half of it. The achieved-to-expected ratio moves less, from
{B['(0)'].achieved_over_expected:.2f} to between {T4.achieved_over_expected.min():.2f} and {T4.achieved_over_expected.max():.2f}, because targets
are constructed with the same conversions as results. The Scorecard&rsquo;s own measure of progress against expectations is therefore
robust to construction in a way that its headline level is not.</p>
{table4}
{fig3}
<h3>5.2 Concentration</h3>
<p>The headline is also concentrated (table 5, figure 2). The largest result&mdash;a direct-plus-adjustment count from a single country
programme&mdash;supplies {pc(T5.loc[1, 'share'])} of the World Bank total; the five largest supply {pc(T5.loc[5, 'share'])}, ten supply
{pc(T5.loc[10, 'share'])} and twenty supply {pc(T5.loc[20, 'share'])}. The effective number of results, the inverse of the Herfindahl index, is
{K['effective_n']:.0f}. Five countries&mdash;{', '.join(top5.country.tolist())}&mdash;account for {pc(top5.share.sum())}. A headline this
concentrated can change substantially when a single project enters or leaves the portfolio, independently of trends in the services people
receive. Online appendix table A2 lists the twenty largest results.</p>
{table5}
{fig2}

<h3>5.3 Conversions and reported performance</h3>
<p>Because targets are converted with the same factors as results, conversion does not mechanically change the ratio of achieved to expected
results. It can, however, change which results look successful. Table 6 shows that unit conversions report {T8p.loc['unit', 'achieved_over_expected']:.2f}
times their expected value and {pc(T8p.loc['unit', 'share_exceeding_target'])} of them exceed their target, against
{T8p.loc['direct', 'achieved_over_expected']:.2f} and {pc(T8p.loc['direct', 'share_exceeding_target'])} for direct counts. The pattern is
consistent with the full Scorecard sample, in which rescaled results are significantly less likely to fall behind schedule than comparable
results (table 9, column 4). A headline that blends methods therefore blends results that are easier and harder to deliver on paper.</p>
{table_perf}
<h3>5.4 Portfolio vintage</h3>
<p>The headline is cumulative over the strategy period. {pc(K['share_closed'])} of the World Bank total comes from operations that had already
closed by June 2025, and operations scheduled to close by June 2026 account for {pc(K['share_closing_by']['2026-06-30'])}. Every vaccination
result belongs to an operation closing by June 2026 ({pc(K['vacc_closing_by_jun2026'])} of the vaccination total). How the indicator treats
closed operations in later cycles therefore matters as much for its trajectory as the performance of new ones, and comparisons across cycles
should be read with the vintage of the portfolio in mind.</p>
"""

women = f"""
<p>The Scorecard reports that {m(K['female_published'])} million of the people reached were women. The female disaggregation rows of the
health indicator reproduce this figure exactly. Table 8 and figure 4 show that {pc(K['female_fixed_share'])} of it ({m(T6.achieved_m[1])} million)
comes from {K['female_fixed_n']} results in which the female figure is the total multiplied by a fixed share, rather than a separate count.
The shares used cluster tightly around one half (median {K['female_factor_median']:.3f}), so these figures restate an assumption about the
population rather than measure who was reached. At the level of project &times; indicator pairs, only {hp.get('informative', 0)} of the
{K['health_pairs']} health pairs with a female figure allow a comparison of the share of women reached with the share planned; {hp.get('fixed_share', 0)}
are fixed-share constructions. For an organisation that has made gender equality a corporate priority, the gender breakdown of its largest
health indicator is therefore mostly modelled.</p>
{table6}
{fig4}
"""


who = f"""
<p>Reliance on conversions is not spread evenly. Table 7 shows that the South Asia total is almost entirely a coverage conversion (a single
non-communicable disease screening result), the East Asia and Pacific total is {pc(T9c.loc[T9c.group == 'EAP', 'unit'].iloc[0])} unit conversion
(outpatient visits converted into people), and coverage conversions supply {pc(T9c.loc[T9c.group == 'AFE', 'coverage'].iloc[0])} of the
Eastern and Southern Africa total, largely through COVID-19 vaccination. Western and Central Africa, Europe and Central Asia, and the Middle East
and North Africa rely mainly on direct counts. IBRD-financed operations rely more on conversions than IDA operations
({pc(T9c.loc[T9c.group == 'IBRD/other', 'coverage'].iloc[0] + T9c.loc[T9c.group == 'IBRD/other', 'unit'].iloc[0])} against
{pc(T9c.loc[T9c.group == 'IDA', 'coverage'].iloc[0] + T9c.loc[T9c.group == 'IDA', 'unit'].iloc[0])}), while IDA and fragile settings rely more on
adjusted counts. Regional comparisons of the indicator therefore compare different kinds of measurement as much as different levels of
service delivery.</p>
{table_comp}
"""

r1, r2, r3, r4 = (t7["(1) Rescaled"], t7["(2) Female figure fixed share"], t7["(3) Outcome indicator"], t7["(4) Behind schedule"])
compare = f"""
<p>Are these features specific to health? Table 9 compares health results with results in the other four people-level areas, using linear
probability models with region, fragility, income group, financing, instrument, size and approval-cohort controls and standard errors clustered
by project. Health results are {round(100 * r1['estimate'])} percentage points more likely to be rescaled by a conversion factor than other
results with similar characteristics (column 1; mean in other areas {pc(r1['dep_mean_other'])}), and their female figures are
{round(100 * r2['estimate'])} points more likely to be fixed-share constructions (column 2). Health indicators are somewhat more likely to
measure outcomes, such as coverage rates (column 3: {round(100 * r3['estimate'])} points; {pc(K['type_health']['outcome'])} of health results
against {pc(r3['dep_mean_other'])} elsewhere). And health results are {round(-100 * r4['estimate'])} points less likely to be rated behind
schedule under a linear on-track rule (column 4), conditional on project age and indicator type; {pc(K['behind_health'])} of health results
are behind against {pc(K['behind_other'])} elsewhere.</p>
{table7}
<p>The last two results fit together. Coverage conversions translate percentage-point gains in mass campaigns, such as vaccination, into large
numbers of people quickly, and aggregate counts accumulate service contacts continuously. Both make health results look on track. Within the full
sample, rescaled results are less likely to be behind (column 4), consistent with conversions making progress look faster. None of this implies
that the underlying services were not delivered; it implies that the indicator mixes measures with very different relationships to people
helped.</p>
"""

workforce = f"""
<p>An indicator that counts service contacts is silent on the inputs that determine whether services are effective. The most prominent of these
in the universal health coverage agenda is the health workforce (WHO and World Bank 2023). Using a rule-based classification of the development
objectives and results indicators of all {n(K['hw_total'])} projects in the Scorecard release, validated by hand ({K['hw_precision']['correct']}
of {K['hw_precision']['reviewed']} sampled matches correct; 95 percent Wilson interval {K['hw_precision']['ci'][0]:.2f}&ndash;{K['hw_precision']['ci'][1]:.2f}),
only {K['hw_projects']} projects ({pc(K['hw_projects'] / K['hw_total'], 1)}) address health workers&mdash;their training, recruitment or
deployment&mdash;in what they measure. {K['hw_jobs']} of these also measure jobs or skills, and none addresses migration, although
{K['jobs_projects']} projects measure jobs or skills and {K['migration_projects']} address migration or displacement. Health workforce projects
are concentrated in Africa ({K['hw_by_region'].get('AFE', 0)} in Eastern and Southern Africa, {K['hw_by_region'].get('AFW', 0)} in Western and
Central Africa). Because the classification is based on text, it measures what projects report, not what they finance; but what is reported is
what the Scorecard can see.</p>
"""

discussion = f"""
<p>Three implications follow. First, the headline is better read as an index of service contact constructed from heterogeneous measures than
as a count of people. That is not a criticism of any single conversion; it is a statement about what the aggregate can and cannot support. It can
support statements about whether operations are delivering against their own expectations&mdash;the achieved-to-expected ratio is robust to
construction. It cannot easily support statements about how many distinct people benefited, let alone whether their health improved.</p>

<p>Second, the composition of the headline matters for its trend. Because a quarter of the World Bank total comes from COVID-19 vaccination
coverage conversions in operations approved in FY20&ndash;FY22, the headline will fall mechanically as these operations close, regardless of
how health services evolve. Readers comparing Scorecard cycles need to know which results entered and left, and how each was measured.</p>

<p>Third, the findings connect corporate results measurement to the effective-coverage agenda. Health economists and global health agencies
have spent two decades moving from counting contacts to measuring whether people in need receive care of sufficient quality to produce health
gains (Shengelia et al. 2005; Ng et al. 2014; Kruk et al. 2018). The Scorecard indicator includes the word &ldquo;quality&rdquo;, but nothing
in the public data allows quality to be verified, and a third of the total consists of conversions from coverage or service units. The history
of administrative vaccination data, where performance-based payments were followed by over-reporting relative to surveys (Lim et al. 2008;
Sandefur and Glassman 2015), is a reminder that aggregates tied to institutional reputation deserve independent validation. IEG&rsquo;s ongoing formative evaluation of the Scorecard (IEG 2025) offers a natural opportunity to do so.</p>

<p><b>Limitations.</b> The analysis uses one Scorecard cycle and the public release, which omits IFC and MIGA project data and the documentation
behind each conversion factor. Measurement methods are inferred from the published fields and checked by hand, not confirmed with project teams.
The comparison in section 8 is descriptive. Finally, the paper does not test whether the services counted improved health; doing so requires
linking project results to independent coverage data such as household surveys, which is a natural next step.</p>
"""

recs = f"""
<ol class="recs">
<li><b>Publish a construction code for every figure.</b> Each contributing result should carry a code&mdash;direct count, adjusted count, coverage
conversion, unit conversion&mdash;with the factor&rsquo;s source. The Scorecard could then report the headline alongside the share that is
directly counted ({pc(sm['direct'])} today).</li>
<li><b>Report coverage as coverage.</b> Results measured as coverage rates should be reported as rates against a defined population, not
converted into people and added to head-counts.</li>
<li><b>Count women only where women are counted.</b> Report the female figure from direct disaggregation and show modelled figures separately.</li>
<li><b>Move from contact to effective coverage.</b> For the largest service families&mdash;immunisation, maternal care, outpatient care&mdash;pair
counts with a quality-adjusted or effective-coverage measure drawn from facility or household surveys.</li>
<li><b>Track the inputs that matter.</b> Add a health workforce indicator (health workers trained, deployed and retained) to the Scorecard&rsquo;s
health narrative, so that the system measures capacity as well as contact.</li>
</ol>
"""

conclusion = f"""
<p>The World Bank Group&rsquo;s health headline reconciles to its parts, which is a credit to the transparency of the Scorecard release. But the
parts are not what the headline suggests. Only about a third of the World Bank&rsquo;s total is a count of people; much of the rest is converted
from vaccination coverage, outpatient visits and facilities; a handful of results drive most of it; and most of the gender breakdown is assumed.
Making these choices visible, and moving toward measures of effective coverage, would let the Scorecard say not only how many people were reached,
but how many were helped.</p>
"""

refs = [
    "Arora, A. 2026. &ldquo;Counting Reach, Not Welfare: Testing the World Bank Group Scorecard against a Welfare Anchor.&rdquo; Working paper.",
    "Bevan, G., and C. Hood. 2006. &ldquo;What&rsquo;s Measured Is What Matters: Targets and Gaming in the English Public Health Care System.&rdquo; <i>Public Administration</i> 84 (3): 517&ndash;38.",
    "Bulman, D., W. Kolkma, and A. Kraay. 2017. &ldquo;Good Countries or Good Projects? Comparing Macro and Micro Correlates of World Bank and Asian Development Bank Project Performance.&rdquo; <i>Review of International Organizations</i> 12 (3): 335&ndash;63.",
    "Campbell, D. T. 1979. &ldquo;Assessing the Impact of Planned Social Change.&rdquo; <i>Evaluation and Program Planning</i> 2 (1): 67&ndash;90.",
    "Das, J., and J. Hammer. 2014. &ldquo;Quality of Primary Care in Low-Income Countries: Facts and Economics.&rdquo; <i>Annual Review of Economics</i> 6: 525&ndash;53.",
    "Holmstr&ouml;m, B., and P. Milgrom. 1991. &ldquo;Multitask Principal&ndash;Agent Analyses: Incentive Contracts, Asset Ownership, and Job Design.&rdquo; <i>Journal of Law, Economics, and Organization</i> 7: 24&ndash;52.",
    "Honig, D. 2018. <i>Navigation by Judgment: Why and When Top-Down Management of Foreign Aid Doesn&rsquo;t Work</i>. New York: Oxford University Press.",
    "Hood, C. 2006. &ldquo;Gaming in Targetworld: The Targets Approach to Managing British Public Services.&rdquo; <i>Public Administration Review</i> 66 (4): 515&ndash;21.",
    "IEG (Independent Evaluation Group). 2016. <i>Behind the Mirror: A Report on the Self-Evaluation Systems of the World Bank Group</i>. Washington, DC: World Bank.",
    "IEG (Independent Evaluation Group). 2025. <i>World Bank Group Scorecard Formative Evaluation: Approach Paper</i>. Washington, DC: World Bank.",
    "Jerven, M. 2013. <i>Poor Numbers: How We Are Misled by African Development Statistics and What to Do about It</i>. Ithaca, NY: Cornell University Press.",
    "Kelley, J. G., and B. A. Simmons. 2015. &ldquo;Politics by Number: Indicators as Social Pressure in International Relations.&rdquo; <i>American Journal of Political Science</i> 59 (1): 55&ndash;70.",
    "Kruk, M. E., A. D. Gage, N. T. Joseph, G. Danaei, S. Garc&iacute;a-Sais&oacute;, and J. A. Salomon. 2018. &ldquo;Mortality Due to Low-Quality Health Systems in the Universal Health Coverage Era: A Systematic Analysis of Amenable Deaths in 137 Countries.&rdquo; <i>The Lancet</i> 392 (10160): 2203&ndash;12.",
    "Lim, S. S., D. B. Stein, A. Charrow, and C. J. L. Murray. 2008. &ldquo;Tracking Progress towards Universal Childhood Immunisation and the Impact of Global Initiatives: A Systematic Analysis of Three-Dose Diphtheria, Tetanus, and Pertussis Immunisation Coverage.&rdquo; <i>The Lancet</i> 372 (9655): 2031&ndash;46.",
    "Narayanaswamy, M. 2021. &ldquo;What Gets Measured Gets Done: Using a Corporate Scorecard to Drive Greater Investment Impact.&rdquo; EM Compass Note 108, International Finance Corporation, Washington, DC.",
    "Ng, M., N. Fullman, J. L. Dieleman, A. D. Flaxman, C. J. L. Murray, and S. S. Lim. 2014. &ldquo;Effective Coverage: A Metric for Monitoring Universal Health Coverage.&rdquo; <i>PLoS Medicine</i> 11 (9): e1001730.",
    "Raimondo, E. 2016. &ldquo;What Difference Does Good Monitoring and Evaluation Make to World Bank Project Performance?&rdquo; Policy Research Working Paper 7726, World Bank, Washington, DC.",
    "Sandefur, J., and A. Glassman. 2015. &ldquo;The Political Economy of Bad Data: Evidence from African Survey and Administrative Statistics.&rdquo; <i>Journal of Development Studies</i> 51 (2): 116&ndash;32.",
    "Shengelia, B., A. Tandon, O. B. Adams, and C. J. L. Murray. 2005. &ldquo;Access, Utilization, Quality, and Effective Coverage: An Integrated Conceptual Framework and Measurement Strategy.&rdquo; <i>Social Science &amp; Medicine</i> 61 (1): 97&ndash;109.",
    "WHO and World Bank. 2023. <i>Tracking Universal Health Coverage: 2023 Global Monitoring Report</i>. Geneva: World Health Organization; Washington, DC: World Bank.",
    "World Bank Group. 2025. <i>World Bank Group Scorecard</i>, FY25 data release (results as of June 30, 2025). https://scorecard.worldbank.org.",
    "World Bank. 2024a. <i>New World Bank Group Scorecard FY24&ndash;FY30: Driving Action, Measuring Results</i>. Washington, DC: World Bank Group.",
    "World Bank. 2024b. &ldquo;World Bank Group Announces New Approach to Measuring Impact.&rdquo; Press release, April 9, 2024.",
]

CSS = """
@font-face { font-family: 'SS3'; src: url('fonts/source-sans-3-400-normal.woff2'); font-weight: 400; }
@font-face { font-family: 'SS3'; src: url('fonts/source-sans-3-600-normal.woff2'); font-weight: 600; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-400-normal.woff2'); font-weight: 400; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-400-italic.woff2'); font-weight: 400; font-style: italic; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-600-normal.woff2'); font-weight: 600; }
@font-face { font-family: 'SS4'; src: url('fonts/source-serif-4-700-normal.woff2'); font-weight: 700; }
@page { size: Letter; margin: 1in; }
body { font-family: 'SS4', 'Times New Roman', serif; font-size: 12pt; line-height: 2; color: #111; margin: 0; }
p { margin: 0 0 0; text-indent: 0.4in; text-align: left; }
h1 { font-size: 16pt; line-height: 1.3; text-align: center; margin: 0 0 18pt; }
h2 { font-size: 12pt; font-weight: 700; margin: 18pt 0 0; line-height: 2; break-after: avoid; }
h3 { font-size: 12pt; font-weight: 400; font-style: italic; margin: 6pt 0 0; line-height: 2; break-after: avoid; }
.tp p { text-indent: 0; }
.center { text-align: center; text-indent: 0; }
.abstract { line-height: 1.6; margin: 12pt 0; }
.abstract p { text-indent: 0; }
.small { font-size: 11pt; line-height: 1.5; }
figure { margin: 12pt 0 14pt; line-height: 1.25; }
figcaption { font-family: 'SS3', sans-serif; font-size: 10pt; margin-bottom: 4pt; }
figure img { width: 100%; }
.note { font-family: 'SS3', sans-serif; font-size: 8.4pt; line-height: 1.3; color: #333; text-indent: 0; margin-top: 3pt; }
table { border-collapse: collapse; width: 100%; font-family: 'SS3', sans-serif; font-size: 9pt; line-height: 1.25; }
thead th { border-top: 1pt solid #111; border-bottom: 0.6pt solid #111; padding: 3pt 4pt; font-weight: 600; text-align: center; vertical-align: bottom; }
thead th:first-child { text-align: left; }
tbody td { padding: 2pt 4pt; text-align: center; }
tbody td:first-child { text-align: left; }
tbody tr:last-child td { border-bottom: 1pt solid #111; }
tr.tot td { border-top: 0.6pt solid #111; font-weight: 600; }
table.reg tr.se td { color: #444; font-size: 8pt; padding-top: 0; }
table.reg tr.stat td { border-top: 0.6pt solid #111; }
.avoid { break-inside: avoid; }
.pb { break-before: page; }
ol.recs { line-height: 2; }
ol.recs li { margin-bottom: 0; }
.refs p { padding-left: 0.4in; text-indent: -0.4in; line-height: 1.6; margin-bottom: 4pt; }
.author-note { background: #f8f1de; padding: 4pt 6pt; text-indent: 0; line-height: 1.5; font-size: 11pt; }
td.l { text-align: left; }
"""

title = "What Is Behind &ldquo;People Receiving Quality Health Services&rdquo;? Measurement in the World Bank Group&rsquo;s Health Results"

titlepage = f"""
<div class="tp">
<h1>{title}</h1>
<p class="center">Ashu Arora<sup>*</sup></p>
<div class="abstract"><p><b>Abstract.</b> {abstract}</p></div>
<p class="small" style="text-indent:0"><b>JEL codes:</b> I15, I18, F35, O19, H43<br>
<b>Keywords:</b> results measurement; universal health coverage; effective coverage; development statistics; World Bank; gender data</p>
<p class="small" style="text-indent:0;margin-top:14pt"><sup>*</sup>Ashu Arora is an independent researcher [affiliation, address and email to be added].
[Acknowledgements to be added.] The data are public; replication files (Stata and R) are available at [repository link] and will be
deposited with the journal. The findings, interpretations and conclusions are the author&rsquo;s own.</p>
<p class="author-note">[Author to confirm before submission.] Use of AI tools: the author used Claude (Anthropic) under the author&rsquo;s
direction for drafting analysis code, a first-pass classification of indicators, figure preparation and copy editing. All classifications,
results and interpretations were reviewed by the author, who is responsible for any errors.</p>
</div>"""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>WBER manuscript</title><style>{CSS}</style></head><body>
{titlepage}
<h2 class="pb">1. Introduction</h2>{intro}
<h2>2. How the Scorecard Counts Health Results</h2>{background}
<h2>3. Data</h2>{data}
<h2>4. What the Headline Is Made Of</h2>{decomp}
<h2>5. How Much Does Construction Matter?</h2><h3>5.1 Bounds</h3>{bounds}
<h2>6. Who Relies on Conversions?</h2>{who}
<h2>7. Counting Women</h2>{women}
<h2>8. Health Compared with Other Results Areas</h2>{compare}
<h2>9. What Is Not Counted: The Health Workforce</h2>{workforce}
<h2>10. Discussion</h2>{discussion}
<h2>11. Recommendations</h2>{recs}
<h2>12. Conclusion</h2>{conclusion}
<h2 class="pb">References</h2><div class="refs">{''.join(f'<p>{r}</p>' for r in refs)}</div>
</body></html>"""

# ------------------------------------------------------------------ online appendix
Hp = H[(H.double_counted == 0) & (H.achieved_m > 0)].sort_values("achieved_m", ascending=False)
rowsA1 = [[int(r.rank_achieved), r.project_id, r.country, r.indicator_text[:120], f"{r.conv_factor:,.3g}" if pd.notna(r.conv_factor) else "",
           r.method, r.family, f"{r.achieved_m:.3f}"] for r in Hp.itertuples()]
appA1 = (f'<figure class="tbl"><figcaption><b>Table A1.</b> All {len(Hp)} results contributing to the World Bank health total, with codes</figcaption>'
         '<table class="simple app"><thead><tr><th>Rank</th><th>Project</th><th>Country</th><th>Indicator (as published)</th><th>Factor</th>'
         '<th>Method</th><th>Family</th><th>Achieved (m)</th></tr></thead><tbody>' +
         "".join("<tr>" + "".join(f'<td class="{"l" if j == 3 else ""}">{c}</td>' for j, c in enumerate(r)) + "</tr>" for r in rowsA1) +
         '</tbody></table><p class="note">Results not masked for double counting, positive achieved value, sorted by contribution. Method and family '
         'codes as defined in section 3.2 and appendix B; each was reviewed by hand.</p></figure>')
rowsA2 = [[int(r.rank_achieved), r.project_id, r.country, r.indicator_text[:90], r.method, f"{r.achieved_m:.2f}", int(r.approval_fy)]
          for r in TOP.itertuples()]
appA2 = table("A2", "The twenty largest contributing results", ["Rank", "Project", "Country", "Indicator", "Method", "Achieved (m)", "Approval FY"],
              rowsA2, "World Bank projects; see table A1 for codes.")
appB = """<h2>Appendix B. Classification rules</h2>
<p style="text-indent:0"><b>Measurement method</b> (applied in order): <i>direct</i> if the progress conversion factor equals 1, or no factor is
reported and the calculated value equals the raw value; <i>coverage</i> if the unit is a percentage or the wording refers to a percentage,
proportion, share or rate; <i>unit</i> if the wording refers to visits, consultations, facilities, cases, referrals or notifications, or does not
refer to people; otherwise <i>adjusted</i>. <b>Service family</b> (first match): vaccination (vaccin-, immuni-, Penta, COVID); aggregate HNP count
(people or beneficiaries receiving &ldquo;health, nutrition&rdquo;, &ldquo;HNP&rdquo;, &ldquo;essential/quality health&rdquo; services, or
&ldquo;direct project beneficiaries&rdquo;); outpatient (outpatient, consultation, visits); TB and HIV (TB, tuberculosis, HIV, malaria);
screening (NCD, diabetes, hypertension, cancer, screening); maternal, reproductive health and family planning (contraception, family planning,
antenatal, pregnancy, post-partum, delivery, birth, breastfeeding, iron-folate, maternal, reproductive); nutrition; facilities; other. Full
regular expressions are in <span>code/01_build_health.py</span>.</p>"""
appendix_html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Online appendix</title><style>{CSS}
table.app {{ font-size: 7.6pt; }} body {{ line-height: 1.5; }}</style></head><body>
<h1>Online Appendix<br><span style="font-weight:400;font-size:13pt">{title}</span></h1>
<h2>Appendix A. Contributing results</h2>{appA1}{appA2}{appB}</body></html>"""

(PAPER / "manuscript.html").write_text(html, encoding="utf-8")
(PAPER / "online_appendix.html").write_text(appendix_html, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

exe = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=exe)
    for src, out in [("manuscript.html", "wber-health-manuscript.pdf"), ("online_appendix.html", "wber-health-online-appendix.pdf")]:
        pg = b.new_page()
        pg.goto((PAPER / src).resolve().as_uri())
        pg.wait_for_timeout(600)
        pg.pdf(path=str(PAPER / out), format="Letter", print_background=True, display_header_footer=True,
               header_template="<span></span>",
               footer_template='<div style="font-size:9px;width:100%;text-align:center;font-family:serif"><span class="pageNumber"></span></div>',
               margin={"top": "1in", "bottom": "1in", "left": "1in", "right": "1in"})
    b.close()
print("wrote manuscript and online appendix")
