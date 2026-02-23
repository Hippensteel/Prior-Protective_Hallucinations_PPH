# SelfCheckGPT Blind Spot Test — PPH-001

**Date:** 2026-02-19
**Method:** BERTScore consistency (sentence-transformers, all-MiniLM-L6-v2)
**Data:** 120 stochastic runs (3 models x 2 scenarios x 20 runs)
**Script:** `PPH Understanding The Machine/selfcheckgpt_test.py`

---

## Overall Results

| Run | LIKELY_FACTUAL | Total Claims | Pass Rate |
|-----|---------------|-------------|-----------|
| n=5 references | 44 | 126 | **35%** |
| n=19 references | 46 | 126 | **37%** |

## Per-Group Breakdown

| Group | n=5 | n=19 |
|-------|-----|------|
| claude-opus-4.6 / economics | 4/15 (27%) | 5/15 (33%) |
| claude-opus-4.6 / physics | 3/9 (33%) | 3/9 (33%) |
| deepseek-r1 / economics | 9/22 (41%) | 9/22 (41%) |
| deepseek-r1 / physics | 6/26 (23%) | 6/26 (23%) |
| gemini-3-pro / economics | 14/25 (56%) | 15/25 (60%) |
| gemini-3-pro / physics | 8/29 (28%) | 8/29 (28%) |

## Interpretation

35-37% of PPH confabulation claims pass SelfCheckGPT as LIKELY_FACTUAL. Over a third of fabricated claims evade consistency-based detection.

The result is model-dependent. Gemini economics hits 56-60% (majority of confabulations evade detection). DeepSeek physics is only 23%. Models with more deterministic confabulation patterns fool consistency checks more reliably.

Increasing references from 5 to 19 barely changes the result (+2pp). The issue is not sample size. The confabulations are genuinely consistent across runs, confirming the core PPH thesis: these are structured and reproducible, not random hallucinations.

**Conclusion:** SelfCheckGPT's consistency assumption is empirically violated for PPH-class confabulations. The degree of violation varies by model, with Gemini showing the strongest blind spot.

---

## Follow-Up: Threshold Sweep (n=19 references)

How does the pass rate change as we tighten the BERTScore threshold?

| Threshold | Claude/Econ | Claude/Phys | DS-R1/Econ | DS-R1/Phys | Gemini/Econ | Gemini/Phys | **Overall** |
|-----------|-------------|-------------|------------|------------|-------------|-------------|-------------|
| 0.50 | 73% | 100% | 82% | 81% | 92% | 79% | **83%** |
| 0.55 | 60% | 100% | 73% | 58% | 88% | 62% | **71%** |
| 0.60 | 53% | 67% | 55% | 31% | 72% | 34% | **49%** |
| **0.65** | **33%** | **33%** | **41%** | **23%** | **60%** | **28%** | **36%** |
| 0.70 | 20% | 11% | 14% | 4% | 24% | 7% | **13%** |
| 0.75 | 13% | 11% | 4% | 0% | 8% | 3% | **6%** |
| 0.80 | 13% | 11% | 0% | 0% | 8% | 0% | **4%** |

At the standard threshold (0.65), 36% of confabulations evade detection. But the threshold is a dial, not a fix. Tightening it to 0.70 drops the false-negative rate to 13%, but at 0.60 it's 49%. The problem is continuous: there is no clean threshold that separates PPH confabulations from genuine consistency. SelfCheckGPT must trade false negatives (missed confabulations) against false positives (flagging real knowledge as hallucination).

**File:** `selfcheckgpt_threshold_sweep.json`

---

## Follow-Up: Anchor Rotation (threshold=0.65, all 20 anchors)

Does the result depend on which run we use as the target? Each of the 20 runs was tested as anchor with the other 19 as references.

| Group | Mean | Std | Min | Max | Range |
|-------|------|-----|-----|-----|-------|
| claude-opus-4.6 / economics | 43% | 0.128 | 19% | 67% | 0.476 |
| claude-opus-4.6 / physics | 29% | 0.105 | 8% | 50% | 0.423 |
| deepseek-r1 / economics | 42% | 0.093 | 22% | 59% | 0.364 |
| deepseek-r1 / physics | 24% | 0.084 | 9% | 40% | 0.312 |
| gemini-3-pro / economics | 58% | 0.112 | 29% | 83% | 0.542 |
| gemini-3-pro / physics | 23% | 0.108 | 6% | 43% | 0.366 |
| **Overall mean of means** | **36%** | 0.124 | | | |

The means are stable and match the single-anchor results (36% overall). But individual anchor positions vary substantially (std 0.08-0.13, ranges of 0.31-0.54). This variance comes from different runs producing different numbers of extractable claims, not from inconsistency in the confabulations themselves. The core finding is anchor-independent: roughly a third of PPH claims evade consistency detection regardless of which run is tested.

Gemini economics remains the strongest blind spot (mean 58%, peak 83%). At the worst anchor position, 83% of Gemini's fabricated economic claims pass as LIKELY_FACTUAL.

**File:** `selfcheckgpt_anchor_rotation.json`
