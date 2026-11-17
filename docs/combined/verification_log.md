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

