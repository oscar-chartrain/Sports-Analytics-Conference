# Verification log: claims in the full paper checked against code, data and sources

Written 2026-11-11 after the first complete draft. Every quantitative claim in
`paper/full_paper.md` was either recomputed from the committed data and code in
this repository, matched against a script output, or (for facts outside the
data) checked against a primary source. This log records what was checked, how,
and what was corrected. Nothing in it is a new analysis.

## Recomputed or re-run (all matched unless noted)

| Claim | How checked | Result |
|---|---|---|
| Primary entropy-clutch correlations (Table 2), all four cells | Recomputed from `results/{atp,wta}` CSVs | Exact match |
| Five-variant null, both tours and roles | Recomputed from clutch CSVs | Matches; WTA serve p = 0.017 at p = 0.70 (nominal), none survives the 10-comparison Bonferroni threshold (0.005) |
| Spearman rank checks | Recomputed | Match (WTA serve rho = -0.174, p = 0.203) |
| Influence-point removal (WTA serve, return; ATP) | Recomputed with Cook's distance | Match (WTA serve r = -0.181, p = 0.199; WTA return r = +0.242, p = 0.084) |
| Pooled test, interaction, Cochran's Q, pooled TOST | Re-ran `pooled_regression.py` | Match |
| Power / MDES | Re-ran `power_and_robustness.py` | Match (WTA 60.7% for a medium effect) |
| TOST bounds and all eight corrected bounds | Re-ran `disattenuated_equivalence_bounds.py` | Match, ATP cross-check passes |
| Shrinkage reliabilities | Re-ran `shrinkage_reliability.py` | Match (0.594, 0.371, 0.624, 0.132) |
| Opponent-adjusted return clutch (0.231 to 0.182; 0.055 to -0.106) | Re-ran `opponent_adjusted_return_clutch.py` on raw data | Match |
| Continuous-slope reliabilities | Read from the shrinkage script's reference table | Three of four cells lower, ATP return marginally higher (0.231 to 0.256); wording corrected |
| Era and surface covariate check | Re-ran `confound_check_era_surface.py` | Match (WTA serve p 0.056 to 0.082) |
| Four secondary predictors, 16 comparisons | Re-ran `secondary_predictors_regression.py` | 0 of 16 survive; lowest nominal p = 0.013 now stated |
| Entropy under pressure | Recomputed from `entropy_pressure_escalation.csv` | Match |
| Sign flips across p | Recomputed | 13 and 19 are endpoint (p = 0.60 vs 0.70) counts; wording corrected |
| ATP clutch-file provenance gap | Frozen vs reconstructed CSV | Max 0.0051 across variants (tiered), 0.002 to 0.003 at p = 0.65; WTA exact |
| All results tables (1, 3 to 6, A1 to A3) | Automated string match against the CSVs in `results/applications/` | One transcription error found (WTA LR return, -0.093 should be -0.092), fixed |
| Docx fidelity | 260 table cells, 10 tables and 3 figures compared with the markdown | No mismatches |
| Raw data identity | Git blob hashes vs upstream commit tree | All 8 files byte-identical (`DATA_MANIFEST.csv`) |

## Checked against sources

| Claim | Source | Result |
|---|---|---|
| BLR definition: average of serve LR and return LR, above 1 is clutch; reported per match | Tennis Abstract, "Roger Federer wasn't clutch, but he was almost clutch enough" (tennisabstract.com/blog/?p=3666) | Confirmed, and now cited |
| Stats Perform at SSAC 2022 | Stats Perform press release and the conference's research-paper listing | Confirmed as a finalist paper (Seidl and Lucey), "Live Counter-Factual Analysis in Women's Tennis Using Automatic Key-Moment Detection", using leverage, clutch and momentum metrics; wording changed from "presented" and the reference completed. The press release also names a third author (Marko); the conference listing names two |
| Klaassen and Magnus (2001) JASA 96(454) 500-509; (2003) EJOR 148(2) 257-267 | Bibliographic records | Confirmed |
| Barnett and Clarke (2005) IMA J. Manag. Math. 16(2) 113-120 | Bibliographic records | Confirmed |
| Newton and Keller (2005) Stud. Appl. Math. 114(3) 241-269 | Bibliographic records | Confirmed; title punctuation corrected |
| Efron and Morris (1975) JASA 70(350) 311-319 | Bibliographic records | Confirmed |
| Morris (1977), pp. 131-140 in Ladany and Machol (Eds.), Optimal Strategies in Sports | Citing papers only; the chapter was not retrieved | Page range added from citing sources; moderate confidence |

## Corrections made as a result

1. Rank-interval width for the named players: "20 to 30" corrected to "23 to 31".
2. Sign-flip claim reworded to "differ in sign between p = 0.60 and p = 0.70".
3. Abstract and conclusion no longer say true return-clutch spread is "not detectable" (the ATP variance-method interval excludes zero); now "small or not reliably detectable".
4. Section 5.1 now states the Bonferroni family (10 per tour), WTA serve's nominal p range, and the lowest nominal p among secondary predictors.
5. Continuous-slope wording made exact.
6. WTA LR return confidence-interval cell corrected (-0.092).
7. Stats Perform sentence, reference list (Seidl and Lucey, Sackmann BLR article, Morris pages, Newton and Keller title) corrected.

## Not independently re-derived

- Bug disclosures (parsing inversion, tiebreak flag, tie cluster, head-to-head) rest on the existing `docs/` write-ups and the standing parity guard; they were not re-created.
- Morris (1977) pages rest on citing papers.
- The disattenuated bounds at random-split reliabilities treat reliabilities as fixed (stated in the paper).

## Addendum 2026-11-16: mock-jury revisions

- Table 3 intervals: `src/robustness/matches_needed_ci.py` passes the 95% limits of each reliability (Fisher interval, original split; 2.5th to 97.5th percentile, random splits) through the Spearman-Brown formula; output `results/applications/matches_needed_ci.csv`. Point values differ from the paper's by under 1% where the paper used rounded reliabilities (WTA return 2,583 exact vs 2,566 from rounded 0.055; the paper keeps the earlier figure).
- Section 6.4 match-win translation: `src/robustness/win_prob_translation.py` (first-order, summed top-quartile leverage per match: ATP 2.36 serve and 2.24 return; WTA 1.95 and 1.97).
- New references checked by web search: Cramer (1977), Baseball Research Journal (SABR site; volume and pages not retrieved); Cohen-Zada, Krumer, Rosenboim and Shapir (2017), J. Econ. Psychol. 61, 176-190 (EconPapers record); De Paola and Scoppa (2015), IZA DP 9315. The description of the later baseball literature rests on secondary summaries and is worded cautiously.
- Wording changes: "independently replicated" replaced by "replicated on a second tour"; pre-registrations described as self-registered; range-restriction caveat added.
- Table 5 (break-point reliability) moved to Appendix A as Table A5; former Table 6 is now Table 5.
- Restructure for length and readability (2026-11-16): main text now 9 pages (13 total with references and appendices). Main tables reduced to Tables 1 to 3, where Table 3 consolidates reliability, matches needed, true SD, noise and match-win equivalent. Appendix A now holds A1 (reliability CIs), A2 (corrected equivalence bounds), A3 (pooled test and power), A4 (break-point reliability), A5 (full matches-needed table) and A6 (true-spread estimators). The former Table 4 (named-player ranks) and Table A3 (rank-interval summary) are in the repository as `results/applications/a3_bootstrap_players.csv` and `a3_bootstrap_summary.csv`; the named-player ranks are quoted in Section 6.2. Figures widened to 6.3 in (5.4 in for Figure 2). Every number in the rewritten Sections 4 to 6 was carried over from the previous draft's tables; the new match-win column of Table 3 is one true SD times the summed top-quartile leverage in `results/applications/win_prob_translation.csv` (5.1, 2.7, 3.7 and 2.6 pp, rounded to "about 5, 3, 4" and not shown for WTA return, whose true SD is not distinguishable from zero).

## Addendum 2026-11-16: reference check
- Cohen-Zada, Krumer, Rosenboim and Shapir (2017), J. Econ. Psychol. 61, 176-190, doi 10.1016/j.joep.2017.04.005: authors, title, volume and pages confirmed (EconPapers).
- De Paola and Scoppa: the earlier entry had the wrong title. Correct title is "Gender differences in reaction to psychological pressure: Evidence from tennis players" (IZA DP 9315, 2015; published in Eur. J. Work and Organizational Psychology 26(3), 444-456, 2017, per EconPapers). The paper now cites the published version.
- Cramer (1977), Baseball Research Journal: author, title and year confirmed on the SABR archive (dated 1977-02-01), which shows no volume or page numbers; the entry therefore gives none.
- Morris (1977), pp. 131-140 in Ladany and Machol (Eds.), Optimal Strategies in Sports, North-Holland: the page range and publisher are now confirmed in the reference list of a second, independent paper (arXiv 2601.15327); the chapter itself was still not retrieved.

## Addendum 2026-11-16 (later): all-shot analyses, cluster bootstrap and calibration
- All-shot analyses (`src/robustness/all_shots_analyses.py`, plan `all_shots_preregistration.md`): the script aborts unless it reproduces the paper's serve and return reliabilities on the original split within 0.001 (ATP 0.5720 and 0.2313, WTA 0.5784 and 0.0547, all within 0.0005) and hitter parity is at least 0.85 (ATP 0.954, WTA 0.966). 1,000 random splits per tour, seed 20261116. No outcome meets the pre-registered criterion. Table A7 and A8 in the paper are generated from the output CSVs by the assembly script, not typed. The Table 2 all-shot rows were checked string-by-string against `allshots_entropy_tests.csv`; one rounding error (WTA R2 reliability 0.505 shown as 0.51, correct 0.50) was found and fixed.
- Match-level cluster bootstrap (`src/robustness/cluster_bootstrap_ranks.py`, plan `cluster_bootstrap_preregistration.md`): unit weights reproduce every pipeline score; median 95% rank widths changed by -5.3% to +2.5% against the player-level bootstrap, under the pre-registered 10% threshold, so the paper uses the cluster intervals (Alcaraz return rank 32 [14, 64]; 21 ATP serve intervals and 8 return intervals exclude the pool mean). Bias tolerance not re-checked for this version (stated in Section 8).
- ATP frozen versus regenerated clutch table (`atp_frozen_vs_regenerated_tests.py`): max |delta r| 0.0048 over the variants present in both, smallest p 0.660 on the regenerated table.
- Match-win range (`win_prob_translation.py`, now runnable from a clean clone through `applications_analyses.load_tour`): top-quartile leverage per match ATP 2.36 serve and 2.24 return, bottom-quartile 0.24 and 0.24 (WTA about 1.96/1.97 and 0.19/0.21). The clean-clone failure of the earlier version (it read an untracked cache) was found by a smoke test and fixed.
- Pooled leverage ratio validity (computed on the exact pools, not saved as a script): r with overall point-win rate -0.22 ATP and -0.47 WTA; with serve point-win rate -0.28 and -0.26.
- Entropy versus style markers (committed features): |r| at most 0.17 with net-play rate, drop-shot rate, serve direction and return depth on both tours.
- Pre-registration dating: the earliest preserved commit is 2026-07-07; the public history was squashed on 2026-09-23; the November plans were committed with their outputs. The paper now says so (`preregistration_timeline.md`). Figure colors: the ATP blue was changed from #1f6f8b to #1b78a3 after the palette validator flagged the old value as failing the chroma floor; all four figures were regenerated.

## Addendum 2026-11-16 (latest): multilevel estimate, rally extension, threshold framing
- Multilevel model and match-clustered two-stage estimator (`multilevel_clutch_variance.py`, plan `multilevel_clutch_variance_preregistration.md`): both lie within 25% of the earlier variance-method estimates for ATP serve (2.02 and 2.11 against 2.15) and ATP return (1.10 and 1.09 against 1.22), so the pre-registered robustness rule is met; implied reliability 0.56, 0.25, 0.42, 0.27 (ATP serve, ATP return, WTA serve, WTA return), none at 0.70; likelihood-ratio p at most 0.002 in every cell, a test that ignores clustering. The match-within-player variance component model did not finish in over 10 minutes and is not reported.
- Rally extension (`rally_extension.py`, plan `rally_extension_preregistration.md`): validation reproduced the original-split reliabilities of R1, R2, R3, serve and return to four decimals on both tours. Two deviations are recorded in the plan: the random-split shrinkage check was added after a 3-split test run showed original-split shrunk values above 0.70 (the output of a code test was seen), and the first full run produced undefined shrunk reliabilities where a half had zero estimated true variance, so those splits are scored 0 and the run was repeated. The fixed-threshold cluster bootstrap gives serve and return rank widths within 6% of the re-estimated-threshold widths. Shrinkage does not meet the 95% rule for any rally outcome (closest: ATP winners 79%, WTA unforced errors 55%). The match-win columns in an earlier copy of `rally_extension_spread.csv` were mis-scaled by a factor of 100; the script and CSV were corrected (ATP rally 0.52 to 5.57 points, WTA 0.31 to 3.38).
- Threshold framing: Section 3 and a new Discussion paragraph state that 0.70 is a group-level minimum and individuals are held to 0.90; Nunnally and Bernstein (1994) added, with only the 0.90 individual-decision claim attributed to it. Not verified against the book itself (secondary sources only; the 0.70 attribution is disputed).

## Addendum 2026-11-16 (final pass): presentation points
- Section 6.2 BLR example: Federer and Djokovic BLR 0.976 (score intervals 0.966 to 0.988 and 0.963 to 0.988, pool mean 1.006), ranks 81 [62, 86] and 83 [63, 86], from `a3c_cluster_bootstrap_players.csv`.
- Section 5.2 now defines the equivalence bound in plain language; Section 7 states the practical reading of the entropy null (bound 0.30 on ATP serve is a standardized effect, stated as at most 0.3 SD of true clutch per SD of entropy).
- Table 2 drops the observed-bound column (all observed bounds are in Table A2, which gains the all-shot rows from `allshots_entropy_tests.csv`); Table 3 drops the true-SD intervals (in Tables A6 and A9) and marks intervals reaching zero.

## Addendum 2026-11-16 (trim to 12 pages)
- Appendix A tables moved to `paper/supplementary_tables.md` and renumbered S1 to S9 (old A1 to A9); earlier entries in this log use the old A labels. The paper keeps no appendix tables; Appendices B and C were merged into one short appendix.
- Text tightened in the introduction, Sections 3, 4.2, 4.4, 5.1, 6.1 to 6.3, 7, 8 and 9; the closing paragraph and the "people who use these numbers" paragraph were removed, and Figure 3 was narrowed. No number was changed except one consistency fix: the ATP return matches-needed interval in the text was 180 to unbounded against 201 to unbounded in Table 3 (original-split versus random-split source); both now read about 200.
- Page count from Word: 12 (11 through the references, the appendix on the last page).

## Addendum 2026-11-17 (slope estimator, chronological split)
- `src/robustness/slope_chronological.py` (plan in `docs/combined/slope_chronological_preregistration.md`, written before the run; the code was only syntax-checked first). Validation passed: quartile original-split reliabilities of S, Rt, R1, R2, R3 match `allshots_reliability.csv` on both tours.
- Results in `results/applications/slope_reliability.csv`, `slope_spread.csv`, `chronological_reliability.csv`; paper Section 4.3 and Tables S10 and S11. Neither the slope score nor the chronological split reaches 0.70 (slope random-split share at or above 0.70 at most 0.1%; highest chronological value ATP unforced-error clutch 0.66 [0.53, 0.76]).
- Disclosure: an earlier single-split check of a continuous slope already existed (`docs/atp/04_regression_results/split_half_reliability.md`); the new analysis adds random splits, SD scaling, rally points, clustered true spread and agreement with the quartile score. The 4.3 sentence now cites the new random-split figures.
- Page count from Word: 12.

## Addendum 2026-11-17 (match-nested variance model)
- `src/robustness/match_nested_variance.py` (plan `docs/combined/match_nested_preregistration.md`, written before the run; code syntax-checked only). Two documented deviations: (1) maximum likelihood replaced by REML after the WTA validation simulation failed (ATP results had been seen); (2) the WTA design failed the unchanged rule again (mean estimated match SD 1.05 pp at truth 0, limit 1.0; the other two recovery checks were within 15%), so the script reports no WTA fits and the paper reports ATP only. The first aborted ML run's log was not kept in the repo.
- Outputs `match_nested_variance.csv`, `match_nested_sensitivity.csv`, `match_nested_validation.csv`, `run_log_match_nested.txt`; paper Section 6.1, Discussion and Table S12.
- Result ATP: stable SD 2.0 (serve), 0.5 (return, p = 0.27), 1.2 (rally points); career reliability 0.46, 0.06, 0.30; matches needed about 250, 3,600, 500 against a median of 74. Consistent with Table S6; the return stable difference is no longer detectable once match-level variance is in the model.
- Trimmed back to 12 pages (Word) after the additions.

## Addendum 2026-11-18 (numbers consistency pass)
Checked the paper's text and Tables 1 to 3 and S5, S6, S9 to S12 against the CSVs in `results/applications/` (reliability, matches needed, true spread, multilevel, rally, slope, chronological, nested, rank intervals and named players, phase shares, break points, corrected bounds, win-probability translation). Everything matched except these, all fixed:
- Table 3 caption cited "Table A9" (now S9).
- WTA return corrected bound at the original-split reliability is 1.819, written 1.81 (now 1.82, paper and Table S2).
- "Clustering makes the noise 5% to 9% larger" was wrong: the ratio of clustered to binomial mean SE is 1.02 to 1.10 (now "2% to 10%").
- Rally shrinkage "below 0.62" (ATP error clutch is 0.6195, shown as 0.62) now "at or below 0.62"; leverage variants "above 0.64" (ATP error clutch 0.6418) now "reaches 0.65".
- Section 4.4 used serve clutch 0.54 and Table 1 0.53 (different random-split sets, seeds 20261116 and 20261103); stated in the text.
- The nested model's return figure (3,600 matches) against the split-half 550 is now explained in Section 6.1, and Section 8 records the nested model's deviations.
Not re-derived this pass (verified earlier and logged above): Table 2 correlations and p-values, Bonferroni thresholds, Spearman and influence re-tests, sign-flip counts, entropy-versus-style correlations, power, and the ATP clutch-file regeneration check.

## Addendum 2026-11-18 (confounder adjustment)
- `src/robustness/confound_adjusted_clutch.py` (plan `docs/combined/confound_adjustment_preregistration.md`, written before the run; only raw scores had been computed, to check the code reproduces the committed tables). Outputs `results/applications/confound_adjusted_{reliability,spread,chronological,entropy,coefficients,simulation}.csv` and `run_log_confound_adjusted.txt`; paper Section 4.3, Section 8 and Table S13.
- Validation, all passed before any result was used: raw scores equal the regenerated clutch tables to 1e-16 and the original-split reliabilities exactly; the fast routine equals `rally_extension.sums` to 4e-16 (raw, adjusted, within-match); leave-pair-out opponent strength equals brute force on 200 rows; zero covariates give the raw score exactly; the simulation checks (72 rows in `confound_adjusted_simulation.csv`) pass.
- Disclosure: a 5-split debugging run on WTA was seen before the final validation design was fixed. It exposed three flaws in the simulation design (unpaired test with shared noise; real covariates too weakly confounded to test a no-op; the induced R1 confound varied within a match, which the within-match estimator cannot remove by construction). The simulation was redesigned (paired, a built-in leverage-opponent confound added, R1 added) and the change is recorded in the plan. No estimator, covariate, threshold, split, seed or decision rule changed.
- Result: no adjusted score meets the criterion (largest random-split median 0.54, largest share at or above 0.70 1.1%, across all specifications); adjusted scores correlate 0.96 to 1.00 with the raw; the within-match estimator is less reliable (median at most 0.43); entropy-clutch correlations barely move (smallest p 0.070 against 0.056). Under a built-in confound the raw score is biased 9 to 19 points and A by 0.2 or less.
- Pairing checked: the second decimal of raw medians differs from Tables 1 and S10 because this run uses a new seed (20261119).
- Limits: linear, measured covariates only; opponent strength is a shrunk leave-pair-out rate (measured with error, so it may under-correct; the within-match estimator is the model-free counterpart); no within-match confounds; R2 and R3 not adjusted; the coefficients are fixed from the full sample (re-estimating them inside each half moves no reliability by more than 0.003).
- Page count from Word: 12 (text trimmed elsewhere to keep it: Section 6.2 rank paragraph, appendix, limitations wording; no number changed).

## Addendum 2026-11-18 (selection checks)
- `src/robustness/selection_checks.py` (plan `docs/combined/selection_checks_preregistration.md`, written before the run). Validation, all passed: the 40-match pool equals the paper's players; the extended point table leaves the paper's rows identical; leverage recomputed on 300 paper rows equals the cached value exactly; cutoff-40 medians are within 0.008 of the committed ones (different splits); blocked splits keep each tournament edition on one side and are balanced; the Grand Slam flag matches the confounder script's.
- Disclosure: a validation-only WTA run printed its cutoff-40 and 20-split blocked results as well as the validation lines; they were seen before the full run. No pool, estimator, threshold, seed or rule changed. The first full run was sequential; it was stopped after the ATP cutoff-40 pool (about an hour in) because it would have taken several hours, and relaunched as seven parallel processes (seeds depend on the task, not the process). The ATP cutoff-40 result of the stopped run (serve 0.532, return 0.239, rally 0.432) equals the parallel run's.
- Result: no pool meets the criterion (highest random-split median 0.68, ATP serve at 80 or more matches: 42 players, 42% of splits at or above 0.70); ATP serve rises 0.29, 0.44, 0.53, 0.63, 0.68 over floors 20 to 80 (in line with about 150 matches projected). Tournament-blocked medians differ from random-split medians by at most 0.03. Within Slam matches reliability is at most 0.37, within other matches at most 0.34; Slam minus other differences are within about one SE of zero; cross-stratum correlations 0.06 to 0.37, disattenuated values above 1 on ATP (uninterpretable: strata too noisy). All twelve charting-volume and Slam-share correlations are negative (-0.10 to -0.25) with p from 0.015, none below 0.0042.
- Outputs `selection_checks_{cutoff,blocked,strata,charting}.csv` and `run_log_selection_checks.txt` (seven process logs, paths scrubbed); paper Section 4.3, Discussion, Limitations and Table S14.
- Limits: only observed selection features; the 80-match pool is the most heavily charted players; no CIs on the disattenuated correlations.
- Page count from Word: 12 (page 12 is full; text trimmed in Sections 4.3, 4.4, 7, 8 and the appendix; the appendix no longer repeats the licence line or that derived outputs are committed, both stated in Section 3 and the README).

## Addendum 2026-11-19 (positive control and readability pass)
- `src/robustness/positive_control.py` (plan `docs/combined/positive_control_preregistration.md`, written before the run). Plants N(0, s) shifts on top-quartile points in the real design, redraws outcomes as Bernoulli around each player's role win rate, and applies the paper's split-half routine (40 draws x 25 random splits per cell, seed 20261121; ATP and WTA; S, Rt, R1; s = 0, 1, 2, 3, 4, 6 pp and the estimated spread).
- Validation, all passed: the real-data original-split reliabilities equal the committed values exactly (V3); null medians within 0.15 of zero in all six cells (V1; largest 0.14); simulated medians at the estimated spread within 0.15 of the observed ones in all six cells (V2; largest gap 0.09).
- Disclosure: the plan first said 4 draws x 50 splits; a validation-only WTA run (1 draw x 8 splits, null check not enforced in that mode) showed one cell's null median at +0.27 by chance and printed some grid results, so the sample sizes were raised before the full run (amendment recorded in the plan; no grid, threshold, seed rule or decision rule changed).
- Result: the criterion is met at 4 pp on ATP serve, return and rally points and WTA rally points, at 6 pp on WTA serve and return (WTA serve 85%, return 84% of splits at 4 pp). That is about 1.9 times the estimated ATP serve spread (2.15) and 3.3 times the return spread (1.22). Outputs `results/applications/positive_control.csv` (both tours) and `run_log_positive_control.txt`; paper Section 1, Section 4.1 and Table S15.
- Limits: binomial noise only (no match-level variance), so simulated reliability is an upper bound for a given spread; shifts are on the top quartile only; R2 and R3 not simulated.
- Paper edits in the same pass: Section 6.1 split into 'A direct estimate' and 'A three-level model'; Section 6.2 split in two; Figures 2 and 4 moved after the next paragraph to close white-space gaps; the charting-volume direction (all twelve correlations negative) is stated in Section 4.3. Text trimmed to hold 12 pages (Sections 1, 4.4, 6.1, 6.3, 7, appendix): the intro sentence about published tennis metrics (Related work says it), the Discussion sentence repeating Section 6.1's model comparison, rally match counts in the Data-needed paragraph and part of the model-based projection (Table S5). No number changed.
- Page count from Word: 12 (page 12 ends about 40 pt above the bottom margin).
