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
