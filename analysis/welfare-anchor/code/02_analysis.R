# =====================================================================================
# 02_analysis.R
# "Counting Reach, Not Welfare: Testing the World Bank Group Scorecard Against a Welfare Anchor"
#
# Reproduces every table, figure and number in the paper from data/*.csv.
# Uses base R plus sandwich/lmtest (cluster-robust SEs), ggplot2 and jsonlite.
#   install.packages(c("sandwich", "lmtest", "ggplot2", "jsonlite", "haven"))
# Run from the welfare-anchor folder:  Rscript code/02_analysis.R
# The Stata do-file code/03_analysis.do estimates the same models.
# =====================================================================================

suppressPackageStartupMessages({
  library(sandwich); library(lmtest); library(ggplot2); library(jsonlite)
})
dir.create("output/tables", recursive = TRUE, showWarnings = FALSE)
dir.create("output/figures", recursive = TRUE, showWarnings = FALSE)
set.seed(20251007)

R <- read.csv("data/results_clean.csv", stringsAsFactors = FALSE)
G <- read.csv("data/gender_pairs.csv", stringsAsFactors = FALSE)
P <- read.csv("data/projects_clean.csv", stringsAsFactors = FALSE)
K <- list()  # key numbers cited in the text

# ---------------------------------------------------------------- common recodes
recode <- function(d) {
  if ("sector" %in% names(d))
    d$sector <- factor(d$sector, levels = c("health", "wash", "gender_equality",
                                            "economic_opportunity", "financial_services"))
  d$region <- relevel(factor(d$region), ref = "AFE")
  d$income <- relevel(factor(d$income), ref = "LIC")
  d$instrument <- relevel(factor(d$instrument), ref = "IPF")
  d$dept <- relevel(factor(d$dept), ref = "HNP")
  d$cohort <- cut(d$approval_fy, c(-Inf, 2019, 2021, 2023, 2024, Inf),
                  labels = c("FY19 or earlier", "FY20-21", "FY22-23", "FY24", "FY25 (post-Scorecard)"))
  d
}
R <- recode(R); G <- recode(G); P <- recode(P)
R$ind_type <- factor(R$ind_type, levels = c("reach", "output", "outcome", "unclassifiable"))

# cluster-robust coefficient table (clustered by project unless stated)
ctab <- function(m, cluster = ~project_id, data = NULL, keep = NULL, label = "") {
  V <- vcovCL(m, cluster = cluster, type = "HC1")
  ct <- coeftest(m, vcov. = V)
  out <- data.frame(model = label, term = rownames(ct), estimate = ct[, 1], se = ct[, 2],
                    p = ct[, 4], row.names = NULL)
  if (!is.null(keep)) out <- out[grepl(keep, out$term), ]
  out
}
fit_stats <- function(m, label) {
  data.frame(model = label, n = nobs(m),
             r2 = if (inherits(m, "lm") && !inherits(m, "glm")) summary(m)$r.squared else NA,
             clusters = length(unique(model.frame(m)$`(cluster)`)))
}
wilson <- function(x, n, z = 1.96) {
  p <- x / n; d <- 1 + z^2 / n; c <- (p + z^2 / (2 * n)) / d
  h <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / d
  c(lo = c - h, hi = c + h)
}
pct <- function(x, k = 1) round(100 * x, k)

# =====================================================================================
# Table 1. Sample
# =====================================================================================
K$n_results <- nrow(R); K$n_projects <- length(unique(R$project_id))
K$n_countries <- length(unique(R$country)); K$n_pairs <- nrow(G)
desc_vars <- c("fcv", "ldc", "ida", "active", "commitment_musd", "years_since_approval",
               "planned_years", "post_scorecard")
T1 <- data.frame(variable = desc_vars,
                 mean = sapply(P[desc_vars], function(x) mean(x, na.rm = TRUE)),
                 sd = sapply(P[desc_vars], function(x) sd(x, na.rm = TRUE)),
                 min = sapply(P[desc_vars], function(x) min(x, na.rm = TRUE)),
                 max = sapply(P[desc_vars], function(x) max(x, na.rm = TRUE)),
                 n = sapply(P[desc_vars], function(x) sum(!is.na(x))))
write.csv(T1, "output/tables/table1_projects.csv", row.names = FALSE)
K$region_counts <- as.list(table(P$region))
K$results_by_sector <- as.list(table(R$sector))

# =====================================================================================
# Test 1. Welfare relevance: what do Scorecard results measure?
# =====================================================================================
T2 <- as.data.frame.matrix(prop.table(table(R$sector, R$ind_type), 1))
T2$n <- as.vector(table(R$sector))
all <- prop.table(table(R$ind_type)); T2 <- rbind(T2, all = c(as.vector(all), nrow(R)))
T2$sector <- rownames(T2)
write.csv(T2, "output/tables/table2_type_by_sector.csv", row.names = FALSE)
K$share_type <- as.list(round(all, 4))

# Hand-coded validation samples (development and held-out test)
val <- rbind(transform(read.csv("validation/dev_sample_coded.csv"), set = "development"),
             transform(read.csv("validation/test_sample_coded.csv"), set = "test"))
vt <- val[val$set == "test", ]
acc <- mean(vt$rule_type == vt$manual_type)
cats <- union(vt$rule_type, vt$manual_type)
pe <- sum(sapply(cats, function(c) mean(vt$rule_type == c) * mean(vt$manual_type == c)))
K$val_test_accuracy <- round(acc, 3); K$val_test_kappa <- round((acc - pe) / (1 - pe), 3)
VAL <- do.call(rbind, lapply(c("reach", "output", "outcome"), function(c) {
  tp <- sum(vt$rule_type == c & vt$manual_type == c); np <- sum(vt$rule_type == c); nt <- sum(vt$manual_type == c)
  pr <- wilson(tp, np); rc <- wilson(tp, nt)
  m_all <- sum(val$manual_type == c); sh <- wilson(m_all, nrow(val))
  data.frame(type = c, precision = tp / np, prec_lo = pr[1], prec_hi = pr[2], recall = tp / nt,
             rec_lo = rc[1], rec_hi = rc[2], manual_share_400 = m_all / nrow(val),
             manual_lo = sh[1], manual_hi = sh[2], rule_share_all = mean(R$ind_type == c))
}))
write.csv(VAL, "output/tables/table3_validation.csv", row.names = FALSE)
K$validation <- VAL

# Project level: how many projects report no outcome indicator to the Scorecard?
K$projects_no_outcome <- round(mean(P$any_outcome == 0), 4)
K$projects_only_reach <- round(mean(P$share_reach == 1), 4)

# Model 1: LPM of outcome indicator on design characteristics, clustered by project
f1 <- outcome ~ sector + region + fcv + income + ida + instrument + log_commit + cohort
m1a <- lm(outcome ~ sector + cohort, data = R)
m1b <- lm(f1, data = R)
m1c <- lm(update(f1, . ~ . + dept), data = R)
m1d <- glm(f1, data = R, family = binomial)
# average marginal effects for the logit (finite difference for factors/binaries)
ame <- function(m, var, levels_to = NULL, data) {
  base <- data; out <- c()
  if (is.null(levels_to)) {  # binary or continuous (+1 unit / 0->1)
    d0 <- base; d1 <- base
    if (all(base[[var]] %in% c(0, 1))) { d0[[var]] <- 0; d1[[var]] <- 1 } else { d1[[var]] <- d1[[var]] + 1 }
    return(mean(predict(m, d1, type = "response") - predict(m, d0, type = "response")))
  }
  ref <- levels(base[[var]])[1]
  sapply(levels_to, function(l) {
    d0 <- base; d1 <- base
    d0[[var]] <- factor(ref, levels = levels(base[[var]])); d1[[var]] <- factor(l, levels = levels(base[[var]]))
    mean(predict(m, d1, type = "response") - predict(m, d0, type = "response"))
  })
}
Rm1 <- R[complete.cases(R[, all.vars(f1)]), ]
ame_sector <- ame(m1d, "sector", levels(R$sector)[-1], Rm1)
ame_cohort <- ame(m1d, "cohort", levels(R$cohort)[-1], Rm1)
T4 <- rbind(ctab(m1a, label = "(1) LPM sector+cohort"), ctab(m1b, label = "(2) LPM + controls"),
            ctab(m1c, label = "(3) LPM + dept FE"), ctab(m1d, label = "(4) Logit (log-odds)"))
write.csv(T4, "output/tables/table4_test1_outcome_models.csv", row.names = FALSE)
S4 <- rbind(data.frame(model = "(1)", n = nobs(m1a), r2 = summary(m1a)$r.squared),
            data.frame(model = "(2)", n = nobs(m1b), r2 = summary(m1b)$r.squared),
            data.frame(model = "(3)", n = nobs(m1c), r2 = summary(m1c)$r.squared),
            data.frame(model = "(4)", n = nobs(m1d), r2 = 1 - m1d$deviance / m1d$null.deviance))
write.csv(S4, "output/tables/table4_stats.csv", row.names = FALSE)
write.csv(data.frame(term = c(names(ame_sector), names(ame_cohort)), ame = c(ame_sector, ame_cohort)),
          "output/tables/table4_logit_ame.csv", row.names = FALSE)
K$t1_projects <- length(unique(R$project_id)); K$t1_clusters <- length(unique(Rm1$project_id))

# Robustness: hand-coded subsample (400 results) - same LPM with manual labels
Rv <- merge(R, val[, c("result_id", "manual_type")], by = "result_id")
Rv$outcome_manual <- as.integer(Rv$manual_type == "outcome")
m1v <- lm(outcome_manual ~ sector + cohort, data = Rv)
write.csv(ctab(m1v, label = "LPM, hand-coded subsample"), "output/tables/tableA1_manual_subsample.csv", row.names = FALSE)
K$manual_sub_n <- nrow(Rv)

# =====================================================================================
# Test 2. Measurement integrity: are reported figures measured or constructed?
# =====================================================================================
Rn <- R[R$double_counted == 0, ]
tot <- function(d) sum(pmax(d$achieved, 0), na.rm = TRUE)
T5 <- do.call(rbind, lapply(c(levels(R$sector), "all"), function(s) {
  d <- if (s == "all") Rn else Rn[Rn$sector == s, ]
  data.frame(sector = s, results = nrow(d), share_scaled = mean(d$scaled),
             share_zero_baseline = mean(d$zero_baseline), share_pct_unit = mean(d$pct_unit),
             achieved_total_m = tot(d) / 1e6, achieved_from_scaled = tot(d[d$scaled == 1, ]) / tot(d))
}))
write.csv(T5, "output/tables/table5_construction_by_sector.csv", row.names = FALSE)
K$share_scaled <- round(mean(Rn$scaled), 4)
K$achieved_from_scaled <- round(T5$achieved_from_scaled[T5$sector == "all"], 4)
K$zero_baseline <- round(mean(Rn$zero_baseline), 4)
K$double_counted_share <- round(mean(R$double_counted), 4)
K$pct_unit_scaled <- round(mean(Rn$scaled[Rn$pct_unit == 1]), 4)
K$gender_status <- as.list(table(G$pair_status))
K$informative_share <- round(mean(G$informative), 4)

# Model 2a: which female figures are fixed-share constructions? (pair level)
f2 <- fixed_share ~ sector + region + fcv + income + ida + instrument + log_commit + cohort
m2a <- lm(f2, data = G)
m2b <- glm(f2, data = G, family = binomial)
# Model 2b: which results are rescaled? (result level, non-double-counted)
f3 <- scaled ~ sector + pct_unit + ind_type + region + fcv + income + ida + instrument + log_commit + cohort
m2c <- lm(f3, data = Rn)
T6 <- rbind(ctab(m2a, label = "(1) Fixed-share female figure, LPM"),
            ctab(m2b, label = "(2) Fixed-share female figure, logit"),
            ctab(m2c, label = "(3) Rescaled result, LPM"))
write.csv(T6, "output/tables/table6_test2_models.csv", row.names = FALSE)
write.csv(data.frame(model = c("(1)", "(2)", "(3)"), n = c(nobs(m2a), nobs(m2b), nobs(m2c)),
                     r2 = c(summary(m2a)$r.squared, 1 - m2b$deviance / m2b$null.deviance, summary(m2c)$r.squared)),
          "output/tables/table6_stats.csv", row.names = FALSE)
K$fixed_share_by_sector <- as.list(tapply(G$fixed_share, G$sector, mean))

# =====================================================================================
# Test 3. Progress judgement: does "behind" measure performance or time?
# =====================================================================================
D <- R[R$judgeable == 1 & R$ind_type != "unclassifiable", ]
D$ind_type <- droplevels(D$ind_type)
D$age_bin <- cut(D$years_since_approval, c(-Inf, 3, 5, 7, Inf), labels = c("<3 yrs", "3-5 yrs", "5-7 yrs", "7+ yrs"))
D$elapsed2 <- D$elapsed^2
K$t3_n <- nrow(D); K$t3_projects <- length(unique(D$project_id)); K$behind_rate <- round(mean(D$behind), 4)
K$behind_by_age <- as.list(round(tapply(D$behind, D$age_bin, mean), 4))
K$behind_by_type <- as.list(round(tapply(D$behind, D$ind_type, mean), 4))
K$median_progress_by_type <- as.list(round(tapply(D$progress_frac, D$ind_type, median), 4))

# Model 3a: fractional logit of progress (Papke-Wooldridge), clustered by project
f4 <- progress_frac ~ elapsed + elapsed2 + ind_type + scaled + sector + region + fcv + income + instrument + log_commit
m3a <- glm(f4, data = D, family = quasibinomial(link = "logit"))
# Model 3b: LPM of "behind" - timing only, then add design, then FE
m3b <- lm(behind ~ age_bin, data = D)
m3c <- lm(behind ~ age_bin + ind_type + scaled + sector, data = D)
m3d <- lm(behind ~ age_bin + ind_type + scaled + sector + region + fcv + income + instrument + log_commit, data = D)
m3e <- lm(behind ~ age_bin + ind_type + scaled + sector + region + fcv + income + instrument + log_commit + dept, data = D)
T7 <- rbind(ctab(m3a, label = "(1) Fractional logit: progress"), ctab(m3b, label = "(2) LPM behind: timing only"),
            ctab(m3c, label = "(3) LPM behind: + design"), ctab(m3d, label = "(4) LPM behind: + controls"),
            ctab(m3e, label = "(5) LPM behind: + dept FE"))
write.csv(T7, "output/tables/table7_test3_models.csv", row.names = FALSE)
S7 <- data.frame(model = c("(1)", "(2)", "(3)", "(4)", "(5)"),
                 n = c(nobs(m3a), nobs(m3b), nobs(m3c), nobs(m3d), nobs(m3e)),
                 r2 = c(NA, summary(m3b)$r.squared, summary(m3c)$r.squared, summary(m3d)$r.squared, summary(m3e)$r.squared))
write.csv(S7, "output/tables/table7_stats.csv", row.names = FALSE)
K$r2_timing <- round(summary(m3b)$r.squared, 4); K$r2_full <- round(summary(m3e)$r.squared, 4)
# share of explained variance attributable to timing
K$r2_timing_share <- round(summary(m3b)$r.squared / summary(m3e)$r.squared, 3)

# Average marginal effect of elapsed on predicted progress, and predicted curve by type
grid <- expand.grid(elapsed = seq(0.2, 1, by = 0.05), ind_type = levels(D$ind_type))
pred_curve <- do.call(rbind, lapply(seq_len(nrow(grid)), function(i) {
  d <- D; d$elapsed <- grid$elapsed[i]; d$elapsed2 <- d$elapsed^2
  d$ind_type <- factor(grid$ind_type[i], levels = levels(D$ind_type))
  data.frame(elapsed = grid$elapsed[i], ind_type = grid$ind_type[i], progress = mean(predict(m3a, d, type = "response")))
}))
write.csv(pred_curve, "output/tables/fig3_predicted_curve.csv", row.names = FALSE)
K$pred_progress_at_half <- as.list(setNames(round(pred_curve$progress[abs(pred_curve$elapsed - 0.5) < 1e-9], 3),
                                            levels(D$ind_type)))

# Robustness for Test 3: thresholds, logit, active only, drop rescaled, country clusters
rob <- list(
  "Threshold 0 pp" = lm(behind_t0 ~ age_bin + ind_type + scaled + sector + region + fcv + income + instrument + log_commit + dept, data = D),
  "Threshold 20 pp" = lm(behind_t20 ~ age_bin + ind_type + scaled + sector + region + fcv + income + instrument + log_commit + dept, data = D),
  "Active projects only" = lm(behind ~ age_bin + ind_type + scaled + sector + region + fcv + income + instrument + log_commit + dept, data = D[D$active == 1, ]),
  "Excluding rescaled results" = lm(behind ~ age_bin + ind_type + sector + region + fcv + income + instrument + log_commit + dept, data = D[D$scaled == 0, ])
)
T8 <- do.call(rbind, lapply(names(rob), function(n) ctab(rob[[n]], keep = "age_bin|ind_type", label = n)))
T8 <- rbind(T8, ctab(m3e, cluster = ~country, keep = "age_bin|ind_type", label = "Clustered by country"))
mlog <- glm(behind ~ age_bin + ind_type + scaled + sector + region + fcv + income + instrument + log_commit, data = D, family = binomial)
T8 <- rbind(T8, transform(ctab(mlog, keep = "age_bin|ind_type", label = "Logit (log-odds)")))
write.csv(T8, "output/tables/table8_robustness.csv", row.names = FALSE)
K$rob_n <- sapply(rob, nobs)

# =====================================================================================
# Figures (static, for print). Palette: reference categorical slots, validated.
# =====================================================================================
ink <- "#0b0b0b"; ink2 <- "#52514e"; grid_c <- "#e6e5e1"
pal <- c(reach = "#2a78d6", output = "#eb6834", outcome = "#1baf7a", unclassifiable = "#b9b8b2")
theme_paper <- theme_minimal(base_size = 10) +
  theme(text = element_text(colour = ink), axis.text = element_text(colour = ink2),
        panel.grid.major = element_line(colour = grid_c, linewidth = 0.3), panel.grid.minor = element_blank(),
        legend.position = "top", legend.justification = "left", legend.title = element_blank(),
        plot.title.position = "plot", plot.caption = element_text(colour = ink2, hjust = 0, size = 8))
sector_lab <- c(health = "Health, nutrition\n& population", wash = "Water, sanitation\n& hygiene",
                gender_equality = "Gender equality\nactions", economic_opportunity = "Economic\nopportunity",
                financial_services = "Financial\nservices")

# Figure 1: what the Scorecard counts, by results area
f1d <- as.data.frame(prop.table(table(R$sector, R$ind_type), 1)); names(f1d) <- c("sector", "type", "share")
f1d$type <- factor(f1d$type, levels = rev(c("reach", "output", "outcome", "unclassifiable")))
f1d$sector <- factor(f1d$sector, levels = rev(levels(R$sector)))
g1 <- ggplot(f1d, aes(x = share, y = sector, fill = type)) +
  geom_col(width = 0.62, colour = "white", linewidth = 0.6) +
  scale_fill_manual(values = pal, breaks = c("reach", "output", "outcome", "unclassifiable"),
                    labels = c("Reach (people/firms served)", "Output (training, works, loans)", "Outcome (welfare change)", "Unclassifiable")) +
  scale_x_continuous(labels = scales::percent, expand = c(0, 0)) + scale_y_discrete(labels = sector_lab) +
  labs(x = "Share of project indicators feeding the Scorecard", y = NULL) + theme_paper +
  theme(plot.margin = margin(5, 14, 5, 5)) +
  guides(fill = guide_legend(nrow = 2))
ggsave("output/figures/fig1_indicator_types.png", g1, width = 6.5, height = 3.4, dpi = 300, bg = "white")

# Figure 2: constructed figures - fixed-share female figures and rescaled results by area
f2d <- rbind(
  data.frame(sector = names(K$fixed_share_by_sector), share = unlist(K$fixed_share_by_sector), what = "Female figure = total x fixed share"),
  data.frame(sector = T5$sector[T5$sector != "all"], share = T5$achieved_from_scaled[T5$sector != "all"], what = "Achieved total from rescaled indicators"))
f2d$sector <- factor(f2d$sector, levels = rev(levels(R$sector)))
g2 <- ggplot(f2d, aes(x = share, y = sector)) +
  geom_col(width = 0.6, fill = "#2a78d6") +
  geom_text(aes(label = scales::percent(share, accuracy = 1)), hjust = -0.15, size = 3, colour = ink) +
  facet_wrap(~what, nrow = 1) + scale_y_discrete(labels = sector_lab) +
  scale_x_continuous(labels = scales::percent, limits = c(0, 1.05), breaks = c(0, 0.5, 1), expand = c(0, 0)) +
  labs(x = NULL, y = NULL) + theme_paper +
  theme(strip.text = element_text(face = "bold", hjust = 0), panel.spacing.x = unit(1.4, "lines"),
        plot.margin = margin(5, 14, 5, 5))
ggsave("output/figures/fig2_constructed.png", g2, width = 6.5, height = 3.2, dpi = 300, bg = "white")

# Figure 3: delivery curve vs the linear benchmark
D$elapsed_bin <- cut(D$elapsed, seq(0.2, 1, 0.1), include.lowest = TRUE)
bins <- aggregate(cbind(progress_frac, elapsed) ~ elapsed_bin + ind_type, data = D[D$ind_type %in% c("reach", "outcome"), ], FUN = mean)
bins$n <- aggregate(progress_frac ~ elapsed_bin + ind_type, data = D[D$ind_type %in% c("reach", "outcome"), ], FUN = length)$progress_frac
pc <- pred_curve[pred_curve$ind_type %in% c("reach", "outcome"), ]
g3 <- ggplot() +
  annotate("segment", x = 0.2, y = 0.2, xend = 1, yend = 1, linetype = "dashed", colour = ink2, linewidth = 0.5) +
  annotate("text", x = 0.86, y = 0.97, label = "Linear benchmark", colour = ink2, size = 3, angle = 0, hjust = 1) +
  geom_line(data = pc, aes(elapsed, progress, colour = ind_type), linewidth = 0.9) +
  geom_point(data = bins, aes(elapsed, progress_frac, colour = ind_type, size = n), alpha = 0.85, stroke = 0) +
  scale_colour_manual(values = pal[c("reach", "outcome")], labels = c("Reach indicators", "Outcome indicators")) +
  scale_size_area(max_size = 3.5, guide = "none") +
  scale_x_continuous(labels = scales::percent, limits = c(0.18, 1.02)) +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1.02)) +
  labs(x = "Share of implementation period elapsed", y = "Share of target achieved (capped at 100%)") + theme_paper
ggsave("output/figures/fig3_delivery_curve.png", g3, width = 6.5, height = 3.8, dpi = 300, bg = "white")

# Figure 4: "behind" rate by project age
f4d <- aggregate(behind ~ age_bin, data = D, FUN = mean); f4d$n <- as.vector(table(D$age_bin))
ci <- t(mapply(function(x, n) wilson(x, n), round(f4d$behind * f4d$n), f4d$n)); f4d$lo <- ci[, 1]; f4d$hi <- ci[, 2]
g4 <- ggplot(f4d, aes(x = age_bin, y = behind)) +
  geom_col(width = 0.55, fill = "#2a78d6") +
  geom_errorbar(aes(ymin = lo, ymax = hi), width = 0.12, colour = ink2, linewidth = 0.4) +
  geom_text(aes(y = hi, label = scales::percent(behind, accuracy = 1)), vjust = -0.6, size = 3.2, colour = ink) +
  scale_y_continuous(labels = scales::percent, limits = c(0, 1), expand = c(0, 0)) +
  labs(x = "Years since approval", y = "Share of results rated 'behind'") + theme_paper
ggsave("output/figures/fig4_behind_by_age.png", g4, width = 6.5, height = 3.2, dpi = 300, bg = "white")

write_json(K, "output/key_numbers.json", auto_unbox = TRUE, digits = 6, pretty = TRUE)
cat("Done. Tables in output/tables, figures in output/figures, key numbers in output/key_numbers.json\n")
