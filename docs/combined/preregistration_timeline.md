# Pre-registration timeline and what can be verified

Every analysis plan in this project is a Markdown document in `docs/`. Each
states, in its own text, that it was written before the corresponding analysis
was run. None of them was deposited in an external registry, and the
repository's version control cannot independently confirm the stated ordering,
for these reasons:

- The earliest preserved commit is dated 2026-07-07 and already contains the
  full pipeline together with `step3_variable_preregistration.md`. Whatever
  history existed before that date was not preserved.
- The public history of the `master` branch was squashed on 2026-09-23. The
  earlier history (20 commits, 2026-07-07 to 2026-08-05) is kept on the branch
  `backup/pre-squash-2026-09-23` of the working repository; it is not part of
  the anonymized mirror.
- Several plans were later merged with their results into one document, and the
  November plans were committed together with their outputs (see below).

So the plans should be read as pre-specified analysis plans written by the
authors, with decision rules stated in advance, not as independently
time-stamped registrations.

| Plan | Date the document states | First commit that contains it |
|---|---|---|
| Primary entropy-clutch hypothesis (`docs/atp/03_leverage_clutch/step3_variable_preregistration.md`) | written before any regression was run | 2026-07-07 (first preserved commit) |
| WTA replication (`docs/wta/wta_replication_preregistration.md`) | before the WTA analysis | 2026-07-07 |
| Split-half reliability (`docs/atp/04_regression_results/split_half_reliability.md`) | before splitting any player's matches | 2026-07-07 |
| Pooled regression, power analysis, empirical-p variant | before each analysis | 2026-07-07 |
| Entropy under pressure | before the analysis | 2026-07-08 |
| Shrinkage reliability | before the analysis | 2026-07-13 |
| Era and surface, opponent adjustment, secondary predictors, corrected equivalence bounds | before each analysis | 2026-08-04 |
| Applications analyses (`docs/combined/applications_preregistration.md`) | 2026-11-03 | 2026-11-11 (committed with its outputs) |
| Extensions: random splits, break points, true spread | 2026-11-11 | 2026-11-11 (committed with its outputs) |
| Consistency fixes | 2026-11-11 | 2026-11-11 |
| All-shot clutch (`docs/combined/all_shots_preregistration.md`) | 2026-11-16 | after 2026-11-16 |
| Match-level cluster bootstrap (`docs/combined/cluster_bootstrap_preregistration.md`) | 2026-11-16 | after 2026-11-16 |
| Multilevel clutch variance (`docs/combined/multilevel_clutch_variance_preregistration.md`) | 2026-11-16 | after 2026-11-16 |
| Rally extension (`docs/combined/rally_extension_preregistration.md`) | 2026-11-16 | after 2026-11-16 |
| Match-nested variance model (`docs/combined/match_nested_preregistration.md`) | 2026-11-17 | after 2026-11-17 |
| Slope estimator and chronological split (`docs/combined/slope_chronological_preregistration.md`) | 2026-11-17 | after 2026-11-17 |
| Confounder adjustment (`docs/combined/confound_adjustment_preregistration.md`) | 2026-11-18 | after 2026-11-18 |
| Selection checks (`docs/combined/selection_checks_preregistration.md`) | 2026-11-18 | after 2026-11-18 |
| Positive control (`docs/combined/positive_control_preregistration.md`) | 2026-11-18 | after 2026-11-18 |
| Validity checks (`docs/combined/validity_checks_preregistration.md`) | 2026-11-19 | after 2026-11-19 |
| External criterion, decisive-set wins (`docs/combined/decider_validity_preregistration.md`) | 2026-11-19 | after 2026-11-19 |

The November plans were all written after the earlier results (the entropy
null and the reliability findings) were known, so they are pre-specified but
not blind.
