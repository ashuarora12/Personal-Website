# Ashu Arora — Personal Website and Data Projects

Source for [ashuarora.com](https://ashuarora.com): a static site plus the reproducible Python pipelines behind its data projects. Every number shown on the site or in the reports is produced by the code in `analysis/`; nothing is typed in by hand.

## Projects

| Project | Live | Report | Source |
|---|---|---|---|
| **Who Benefits? Health, Jobs & Gender in the World Bank Group Portfolio** | [Data story](https://ashuarora.com/who-benefits-flow) | [PDF, 22 pp.](https://ashuarora.com/who-benefits-report.pdf) | [`analysis/who-benefits`](analysis/who-benefits) |
| **What Drives Global Patenting Activity?** | [Dashboard](https://ashuarora.com/patent-dashboard) | [Working paper, 16 pp.](https://ashuarora.com/patent-report.pdf) | [`analysis/wipo-report`](analysis/wipo-report) |
| **Health Economics Data Finder** | [Tool](https://ashuarora.com/data-buff) | [Guide & issue briefs, 12 pp.](https://ashuarora.com/data-finder-guide.pdf) | [`analysis/data-finder`](analysis/data-finder) |

### Who Benefits?
An independent analysis of the World Bank Group's FY25 Corporate Scorecard results (1,131 projects, 125 countries): who is reached, whether projects measure the health workforce and its link to jobs and migration, and whether women are counted and reached as planned.
- **Methods:** rule-based text classification with hand-checked precision (Wilson intervals), a cross-validated early-warning model (grouped CV, cluster-bootstrap AUC, fairness checks), propensity-score matching with regression robustness checks.
- **Data:** World Bank Group Scorecard exports, FY25 cycle.

### What Drives Global Patenting Activity?
An econometric and machine-learning study of resident patent filings: a 141-country cross-section and a 2,201-observation panel (136 countries, 2000–2021).
- **Methods:** log-linear OLS, panel fixed effects with country-clustered SEs, Negative Binomial count model, Gradient Boosting and Random Forest with country-grouped cross-validation, residual ranking of over- and under-performers.
- **Data:** WIPO resident patent applications (World Bank indicator IP.PAT.RESD); Our World in Data country panel.

### Health Economics Data Finder
A guided catalogue of 24 evaluation-ready health datasets for India and global comparisons, tagged by structure, finest geography, research designs, access and comparability traps, with a health-risk hotspot map. 17 of 24 entries are checked against sources; the rest are marked "to verify".
- **Guide:** how to match data to research designs, ten comparability traps, and four short issue briefs.
- **Data:** hand-curated catalogue (`datasets.json`); World Bank Group Scorecard vision indicators for the map and briefs.

## Repository layout

```
ashu-arora-complete-website/   the live site (static HTML, PDFs, assets)
analysis/who-benefits/         pipeline, dashboard builds, report
analysis/wipo-report/          working-paper figures and PDF build
analysis/data-finder/          catalogue, page build, user guide
vercel.json                    clean URLs (/projects -> projects.html)
```

Each `analysis/` folder has its own README with rebuild commands. Builds need Python 3.11 with pandas, numpy, scipy, scikit-learn, statsmodels, matplotlib, playwright and pypdf (pinned in `analysis/who-benefits/requirements.txt`).

## Site pages

Home · [Research](https://ashuarora.com/research) · [Experience](https://ashuarora.com/experience) · [Projects](https://ashuarora.com/projects) · [Consultancy](https://ashuarora.com/consultancy)

© Ashu Arora
