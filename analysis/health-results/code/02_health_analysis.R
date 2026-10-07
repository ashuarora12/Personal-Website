# =====================================================================================
# 02_health_analysis.R
# "What Is Behind 'People Receiving Quality Health Services'? Measurement in the
#  World Bank Group's Health Results"  - all tables, figures and numbers in the paper.
# Base R + sandwich/lmtest (clustered SEs), ggplot2, jsonlite.
# Run from the health-results folder:  Rscript code/02_health_analysis.R
# Stata replication: code/03_health_analysis.do
# =====================================================================================
suppressPackageStartupMessages({ library(sandwich); library(lmtest); library(ggplot2); library(jsonlite) })
dir.create("output/tables", recursive = TRUE, showWarnings = FALSE)
dir.create("output/figures", recursive = TRUE, showWarnings = FALSE)

H  <- read.csv("data/health_results.csv", stringsAsFactors = FALSE)
FE <- read.csv("data/health_female.csv", stringsAsFactors = FALSE)
AG <- read.csv("data/aggregates.csv", stringsAsFactors = FALSE)
HW <- read.csv("data/health_workforce.csv", stringsAsFactors = FALSE)
R  <- read.csv("../welfare-anchor/data/results_clean.csv", stringsAsFactors = FALSE)   # all five results areas
GP <- read.csv("../welfare-anchor/data/gender_pairs.csv", stringsAsFactors = FALSE)
RS <- fromJSON("../who-benefits/output/report_stats.json")
K <- list()
agg <- function(org, grp = "Total") AG$achieved_m[AG$organization == org & AG$group == grp][1]
aggE <- function(org, grp = "Total") AG$expected_m[AG$organization == org & AG$group == grp][1]

# =====================================================================================
# 1. Sample and reconciliation with the published headline
# =====================================================================================
N <- H[H$double_counted == 0, ]                 # results that enter the total
P <- N[N$achieved_m > 0, ]
K$n_results <- nrow(H); K$n_projects <- length(unique(H$project_id)); K$n_double <- sum(H$double_counted)
K$n_counted <- nrow(N); K$n_positive <- nrow(P); K$n_countries <- length(unique(H$country))
K$wbg <- agg("WBG"); K$wb <- agg("WB"); K$ifc <- agg("IFC"); K$miga <- agg("MIGA")
K$ida <- agg("IDA"); K$ibrd <- agg("IBRD")
K$wb_project_sum <- sum(N$achieved_m); K$wb_expected <- aggE("WB")
K$reconciliation_gap <- K$wbg - (K$wb_project_sum + K$ifc + K$miga)
K$double_counted_achieved <- sum(H$achieved_m[H$double_counted == 1])
T1 <- data.frame(
  item = c("WBG headline (published)", "  World Bank (IBRD/IDA) projects", "    sum of project records in this paper",
           "      of which IDA-financed", "      of which IBRD-financed", "      of which other (trust funds)",
           "  IFC (aggregate only)", "  MIGA (aggregate only)", "Reconciliation gap"),
  achieved_m = c(K$wbg, K$wb, K$wb_project_sum, K$ida, K$ibrd, K$wb - K$ida - K$ibrd, K$ifc, K$miga, K$reconciliation_gap),
  expected_m = c(aggE("WBG"), aggE("WB"), sum(N$expected_m), aggE("IDA"), aggE("IBRD"), aggE("WB") - aggE("IDA") - aggE("IBRD"),
                 aggE("IFC"), aggE("MIGA"), NA))
write.csv(T1, "output/tables/table1_reconciliation.csv", row.names = FALSE)

# =====================================================================================
# 2. Decomposition by measurement method and service family
# =====================================================================================
meth <- c("direct", "adjusted", "coverage", "unit")
T2 <- do.call(rbind, lapply(meth, function(m) {
  d <- N[N$method == m, ]
  data.frame(method = m, results = nrow(d), positive = sum(d$achieved_m > 0), projects = length(unique(d$project_id)),
             achieved_m = sum(d$achieved_m), share = sum(d$achieved_m) / sum(N$achieved_m),
             median_factor = median(d$conv_factor[d$achieved_m > 0], na.rm = TRUE))
}))
write.csv(T2, "output/tables/table2_method.csv", row.names = FALSE)
K$share_method <- as.list(setNames(T2$share, T2$method))
fam <- aggregate(achieved_m ~ family_label + method, data = N, FUN = sum)
famw <- reshape(fam, idvar = "family_label", timevar = "method", direction = "wide")
famw[is.na(famw)] <- 0
famw$total <- rowSums(famw[, -1]); famw$share <- famw$total / sum(famw$total)
famw$results <- as.vector(table(factor(P$family_label, levels = famw$family_label)))
famw <- famw[order(-famw$total), ]
write.csv(famw, "output/tables/table3_family_method.csv", row.names = FALSE)
K$share_vaccination <- sum(N$achieved_m[N$family == "vaccination"]) / sum(N$achieved_m)
K$share_covid <- sum(N$achieved_m[N$covid == 1]) / sum(N$achieved_m)
covid_proj <- grepl("covid", N$project_name, ignore.case = TRUE)
K$share_covid_projects <- sum(N$achieved_m[covid_proj]) / sum(N$achieved_m)
K$vacc_from_covid_projects <- sum(N$achieved_m[covid_proj & N$family == "vaccination"]) / sum(N$achieved_m[N$family == "vaccination"])
K$share_covid_vacc_of_total <- sum(N$achieved_m[covid_proj & N$family == "vaccination"]) / sum(N$achieved_m)
K$share_aggregate_family <- sum(N$achieved_m[N$family == "aggregate"]) / sum(N$achieved_m)
K$not_reproducible_n <- sum(N$not_reproducible); K$not_reproducible_m <- sum(N$achieved_m[N$not_reproducible == 1])
K$coverage_vacc_share_of_coverage <- sum(N$achieved_m[N$method == "coverage" & N$family == "vaccination"]) /
  sum(N$achieved_m[N$method == "coverage"])
K$facility_example <- N$achieved_m[grepl("Health facilities constructed", N$indicator_text)][1]
K$outpatient_visits_example <- N$achieved_m[N$rank_achieved == 2]

# =====================================================================================
# 3. Bounds: the headline under alternative counting rules
# =====================================================================================
rule <- function(label, keep) {
  d <- N[keep, ]
  a <- sum(d$achieved_m); e <- sum(d$expected_m)
  data.frame(rule = label, achieved_m = a, expected_m = e, achieved_over_expected = a / e,
             wbg_headline_m = a + K$ifc + K$miga, share_of_published = (a + K$ifc + K$miga) / K$wbg)
}
T4 <- rbind(
  rule("(0) As published", rep(TRUE, nrow(N))),
  rule("(1) Excluding figures not reproducible from raw progress", N$not_reproducible == 0),
  rule("(2) Excluding unit-to-people conversions", N$method != "unit"),
  rule("(3) Excluding coverage-to-people conversions", N$method != "coverage"),
  rule("(4) People counts only (direct + adjusted)", N$method %in% c("direct", "adjusted")),
  rule("(5) Rule (4) and reproducible", N$method %in% c("direct", "adjusted") & N$not_reproducible == 0),
  rule("(6) Direct counts only (lower bound)", N$method == "direct"))
write.csv(T4, "output/tables/table4_bounds.csv", row.names = FALSE)
K$bounds <- T4

# =====================================================================================
# 4. Concentration and influence
# =====================================================================================
Ps <- P[order(-P$achieved_m), ]
cum <- cumsum(Ps$achieved_m) / sum(Ps$achieved_m)
T5 <- data.frame(top_k = c(1, 5, 10, 20, 46), share = cum[c(1, 5, 10, 20, 46)])
hhi <- sum((Ps$achieved_m / sum(Ps$achieved_m))^2)
K$top_shares <- T5; K$hhi <- hhi; K$effective_n <- 1 / hhi
cty <- aggregate(achieved_m ~ country, data = P, FUN = sum); cty <- cty[order(-cty$achieved_m), ]
cty$share <- cty$achieved_m / sum(cty$achieved_m)
K$top5_countries <- head(cty, 5); K$n_countries_positive <- nrow(cty)
write.csv(T5, "output/tables/table5_concentration.csv", row.names = FALSE)
write.csv(cty, "output/tables/table5b_countries.csv", row.names = FALSE)
write.csv(Ps[1:20, c("rank_achieved", "project_id", "country", "indicator_text", "method", "family", "conv_factor",
                     "achieved_m", "approval_fy")], "output/tables/tableA1_top20.csv", row.names = FALSE)


# =====================================================================================
# 4b. Reported performance by method, portfolio vintage, and who relies on conversions
# =====================================================================================
T8 <- do.call(rbind, lapply(meth, function(mm) {
  d <- N[N$method == mm, ]
  data.frame(method = mm, results = nrow(d), achieved_m = sum(d$achieved_m), expected_m = sum(d$expected_m),
             achieved_over_expected = sum(d$achieved_m) / sum(d$expected_m),
             share_exceeding_target = mean(d$progress_ratio > 1, na.rm = TRUE))
}))
T8 <- rbind(T8, data.frame(method = "all", results = nrow(N), achieved_m = sum(N$achieved_m), expected_m = sum(N$expected_m),
                           achieved_over_expected = sum(N$achieved_m) / sum(N$expected_m),
                           share_exceeding_target = mean(N$progress_ratio > 1, na.rm = TRUE)))
write.csv(T8, "output/tables/table8_performance_by_method.csv", row.names = FALSE)
K$perf <- T8
N$closing_d <- as.Date(N$closing)
K$share_closed <- sum(N$achieved_m[N$status == "C"]) / sum(N$achieved_m)
K$share_closing_by <- as.list(sapply(c("2025-12-31", "2026-06-30", "2027-06-30"), function(d)
  sum(N$achieved_m[N$closing_d <= as.Date(d)], na.rm = TRUE) / sum(N$achieved_m)))
K$vacc_closing_by_jun2026 <- sum(N$achieved_m[N$family == "vaccination" & N$closing_d <= as.Date("2026-06-30")], na.rm = TRUE) /
  sum(N$achieved_m[N$family == "vaccination"])
comp <- function(var) {
  t <- tapply(P$achieved_m, list(P[[var]], factor(P$method, levels = meth)), sum); t[is.na(t)] <- 0
  out <- data.frame(group = rownames(t), t / rowSums(t), total_m = rowSums(t), row.names = NULL); out$by <- var; out
}
T9 <- rbind(comp("region"), transform(comp("fcv"), group = ifelse(group == "1", "FCV", "Not FCV")),
            transform(comp("ida"), group = ifelse(group == "1", "IDA", "IBRD/other")))
write.csv(T9, "output/tables/table9_composition_by_group.csv", row.names = FALSE)

# =====================================================================================
# 5. Women reached
# =====================================================================================
Fn <- FE[FE$double_counted == 0 & FE$achieved_m > 0, ]
K$female_total <- sum(Fn$achieved_m); K$female_published <- agg("WBG", "Female")
K$female_fixed_share <- sum(Fn$achieved_m[Fn$fixed_share == 1]) / sum(Fn$achieved_m)
K$female_fixed_n <- sum(Fn$fixed_share); K$female_n <- nrow(Fn)
K$female_factor_median <- median(Fn$female_factor[Fn$fixed_share == 1])
K$female_factor_iqr <- quantile(Fn$female_factor[Fn$fixed_share == 1], c(.25, .75))
G <- GP[GP$sector == "health", ]
K$health_pairs <- nrow(G); K$health_pair_status <- as.list(table(G$pair_status))
T6 <- data.frame(component = c("Female figure measured directly", "Female figure = total x fixed share"),
                 achieved_m = c(sum(Fn$achieved_m[Fn$fixed_share == 0]), sum(Fn$achieved_m[Fn$fixed_share == 1])),
                 results = c(sum(Fn$fixed_share == 0), sum(Fn$fixed_share == 1)))
T6$share <- T6$achieved_m / sum(T6$achieved_m)
write.csv(T6, "output/tables/table6_female.csv", row.names = FALSE)

# =====================================================================================
# 6. Health versus the other results areas (all Scorecard results), clustered by project
# =====================================================================================
recode <- function(d) {
  d$health <- as.integer(d$sector == "health")
  d$region <- relevel(factor(d$region), ref = "AFE"); d$income <- relevel(factor(d$income), ref = "LIC")
  d$instrument <- relevel(factor(d$instrument), ref = "IPF")
  d$cohort <- cut(d$approval_fy, c(-Inf, 2019, 2021, 2023, 2024, Inf),
                  labels = c("FY19 or earlier", "FY20-21", "FY22-23", "FY24", "FY25"))
  d
}
R <- recode(R); GP <- recode(GP)
ctl <- "region + fcv + income + ida + instrument + log_commit + cohort"
Rn <- R[R$double_counted == 0, ]
D <- R[R$judgeable == 1 & R$ind_type != "unclassifiable", ]
D$age_bin <- cut(D$years_since_approval, c(-Inf, 3, 5, 7, Inf), labels = c("<3", "3-5", "5-7", "7+"))
D$outcome_ind <- as.integer(D$ind_type == "outcome")
mods <- list(
  "(1) Rescaled" = lm(as.formula(paste("scaled ~ health +", ctl)), data = Rn),
  "(2) Female figure fixed share" = lm(as.formula(paste("fixed_share ~ health +", ctl)), data = GP),
  "(3) Outcome indicator" = lm(as.formula(paste("outcome ~ health +", ctl)), data = R),
  "(4) Behind schedule" = lm(as.formula(paste("behind ~ health + age_bin + outcome_ind + scaled +", ctl)), data = D))
T7 <- do.call(rbind, lapply(names(mods), function(n) {
  m <- mods[[n]]; ct <- coeftest(m, vcov. = vcovCL(m, cluster = ~project_id, type = "HC1"))
  data.frame(model = n, term = rownames(ct), estimate = ct[, 1], se = ct[, 2], p = ct[, 4],
             n = nobs(m), r2 = summary(m)$r.squared, dep_mean = mean(model.frame(m)[[1]]),
             dep_mean_other = mean(model.frame(m)[[1]][model.frame(m)$health == 0]), row.names = NULL)
}))
write.csv(T7, "output/tables/table7_health_vs_other.csv", row.names = FALSE)
K$t7 <- T7[T7$term == "health", c("model", "estimate", "se", "p", "n", "dep_mean_other")]
K$behind_health <- mean(D$behind[D$health == 1]); K$behind_other <- mean(D$behind[D$health == 0])
K$type_health <- as.list(prop.table(table(R$ind_type[R$health == 1])))

# =====================================================================================
# 7. What is not counted: the health workforce
# =====================================================================================
K$hw_projects <- sum(HW$theme_health_workforce); K$hw_total <- nrow(HW)
K$hw_jobs <- sum(HW$theme_health_workforce & HW$theme_jobs_skills)
K$hw_migration <- sum(HW$theme_health_workforce & HW$theme_migration)
K$hw_by_region <- as.list(table(HW$region[HW$theme_health_workforce == 1]))
K$jobs_projects <- sum(HW$theme_jobs_skills); K$migration_projects <- sum(HW$theme_migration)
K$hw_precision <- RS$precision$health_workforce
write.csv(data.frame(theme = c("health_workforce", "jobs_skills", "migration", "hw_and_jobs", "hw_and_migration"),
                     projects = c(K$hw_projects, K$jobs_projects, K$migration_projects, K$hw_jobs, K$hw_migration)),
          "output/tables/table8_workforce.csv", row.names = FALSE)

# =====================================================================================
# Figures
# =====================================================================================
ink <- "#0b0b0b"; ink2 <- "#52514e"; grid_c <- "#e6e5e1"; blue <- "#2a78d6"; orange <- "#eb6834"; aqua <- "#1baf7a"; grey <- "#b9b8b2"
theme_paper <- theme_minimal(base_size = 10) +
  theme(text = element_text(colour = ink), axis.text = element_text(colour = ink2),
        panel.grid.major = element_line(colour = grid_c, linewidth = 0.3), panel.grid.minor = element_blank(),
        legend.position = "top", legend.justification = "left", legend.title = element_blank(),
        plot.margin = margin(5, 14, 5, 5))

# Figure 1: the headline by source and measurement method
f1 <- data.frame(part = c("IFC (aggregate, no project data)", "MIGA (aggregate)", "WB: direct people counts",
                          "WB: adjusted people counts", "WB: coverage % converted to people", "WB: other units converted to people"),
                 m = c(K$ifc, K$miga, T2$achieved_m[T2$method == "direct"], T2$achieved_m[T2$method == "adjusted"],
                       T2$achieved_m[T2$method == "coverage"], T2$achieved_m[T2$method == "unit"]),
                 kind = c("Not observable", "Not observable", "Counted", "Counted", "Converted", "Converted"))
f1$part <- factor(f1$part, levels = rev(f1$part))
g1 <- ggplot(f1, aes(m, part, fill = kind)) + geom_col(width = 0.62) +
  geom_text(aes(label = sprintf("%.1f m", m)), hjust = -0.12, size = 3.1, colour = ink) +
  scale_fill_manual(values = c("Not observable" = grey, "Counted" = blue, "Converted" = orange), breaks = c("Counted", "Converted", "Not observable")) +
  scale_x_continuous(limits = c(0, 140), expand = c(0, 0)) + labs(x = "Million 'people receiving quality HNP services'", y = NULL) +
  theme_paper
ggsave("output/figures/fig1_decomposition.png", g1, width = 6.5, height = 3.2, dpi = 300, bg = "white")

# Figure 2: concentration curve
f2 <- data.frame(rank = seq_along(cum), cum = cum, vacc = Ps$family == "vaccination")
g2 <- ggplot(f2, aes(rank, cum)) + geom_line(colour = blue, linewidth = 0.9) +
  geom_point(aes(colour = vacc), size = 1.6) +
  scale_colour_manual(values = c(`FALSE` = blue, `TRUE` = orange), labels = c("Other results", "Vaccination results")) +
  geom_hline(yintercept = c(0.5, 0.8), linetype = "dashed", colour = ink2, linewidth = 0.3) +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1.01)) +
  labs(x = "Project results ranked by contribution", y = "Cumulative share of the WB health total") + theme_paper
ggsave("output/figures/fig2_concentration.png", g2, width = 6.5, height = 3.3, dpi = 300, bg = "white")

# Figure 3: bounds
f3 <- T4; f3$rule <- factor(f3$rule, levels = rev(f3$rule))
g3 <- ggplot(f3, aes(wbg_headline_m, rule)) +
  geom_segment(aes(x = 0, xend = wbg_headline_m, yend = rule), colour = grid_c, linewidth = 2.2) +
  geom_point(colour = blue, size = 3) +
  geom_text(aes(label = sprintf("%.0f m", wbg_headline_m)), hjust = -0.35, size = 3.1, colour = ink) +
  scale_x_continuous(limits = c(0, 470), expand = c(0, 0)) +
  labs(x = "WBG health headline, million people", y = NULL) + theme_paper
ggsave("output/figures/fig3_bounds.png", g3, width = 6.5, height = 3.2, dpi = 300, bg = "white")

# Figure 4: women reached
f4 <- data.frame(part = factor(T6$component, levels = T6$component), m = T6$achieved_m)
g4 <- ggplot(f4, aes(m, part)) + geom_col(width = 0.5, fill = c(blue, orange)) +
  geom_text(aes(label = sprintf("%.1f m (%.0f%%)", m, 100 * m / sum(m))), hjust = -0.1, size = 3.2, colour = ink) +
  scale_x_continuous(limits = c(0, 125), expand = c(0, 0)) + labs(x = "Million women reported reached", y = NULL) + theme_paper
ggsave("output/figures/fig4_women.png", g4, width = 6.5, height = 1.9, dpi = 300, bg = "white")

write_json(K, "output/key_numbers.json", auto_unbox = TRUE, digits = 6, pretty = TRUE)
cat("Done.\n")
