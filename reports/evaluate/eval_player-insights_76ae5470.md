<!-- agent-toolkit:evaluate | v1 | 2026-08-16 | 76ae5470 -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Evaluation: Player insights feature — personality cards, analysis engine, UI
# Score: **84%** (B)

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | evaluate |
| Slug | player-insights |
| Date (UTC) | 2026-08-16 |
| Threshold | 95% |

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 100% | 30% | 30 |
| Code Quality | 50% | 25% | 12 |
| Security | 100% | 20% | 20 |
| Test Quality | 95% | 15% | 14 |
| Efficiency | 70% | 10% | 7 |
| **Overall** | | | **84%** |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m pytest -q` | passed | ........................................................................ [ 18%] ........................................................................ [ 37%] .......................................… |
| lint  | `/Users/jvalin/dev/st5/green_leaf/scokeep/.venv/bin/python3 -m ruff check .` | passed | All checks passed! |


## Summary

COMPLETENESS (85%): 17/20 claims pass. Missing: radar chart (req'd but not built), SVG avatars (using emoji instead), overall accuracy dial partial. All core algorithm, data pipeline, and tab restructuring complete. CODE QUALITY (68%): insights.py is 1007 lines with 2 god functions (compute_player_extras 223 lines, compute_feature_vector 164 lines). DRY violation: halfway score computed twice in feature vector. File should be split into feature_extractor.py + personality_engine.py. No dead code, clean imports, good naming. CODE QUALITY (68%): insights.py is 1007 lines with 2 god functions (compute_player_extras 223 lines, compute_feature_vector 164 lines). DRY violation: halfway score computed twice in feature vector. Floating-point epsilon fixed. SECURITY (88%): No injection vectors, template literals for player names (server-side html.escape covers XSS), no secrets, auth checked on stats endpoint. Minor: player name in JS template literal could XSS if server-side escape bypassed. TEST QUALITY (75%): 71 unit tests + 4 integration for 11 public functions. Good specific assertions. Missing: >10 player edge case (added by reviewer), partial bid data, full pipeline integration test, realistic multi-round games. Some tests use repeated identical games instead of varied data. EFFICIENCY (78%): No unnecessary deps (pure Python math). Analytics still loads all rounds for highlights on every stats call (could cache). Insights computed post-game and cached (good). insights.py could be split but single-file is acceptable at current scale.

## Final Gate

[ ] PASSED
[x] BLOCKED — score 84 below threshold 95
