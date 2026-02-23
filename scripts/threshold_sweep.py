#!/usr/bin/env python3
"""
PPH SelfCheckGPT Threshold Sweep
Runs n=19 BERTScore consistency at multiple thresholds.
"""

import json
import sys
sys.path.insert(0, "/Users/hippensteel/Vaults/Mainframe/Research/Hypothesis Engine/PPH-001/PPH Understanding The Machine")

from selfcheckgpt_test import load_stochastic_runs, extract_claims
from sentence_transformers import SentenceTransformer, util

DATA_DIR = "/Users/hippensteel/Vaults/Mainframe/Research/Hypothesis Engine/PPH-001/raw-phase2a/"
OUTPUT = DATA_DIR + "selfcheckgpt_threshold_sweep.json"
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
N_REF = 19

model = SentenceTransformer('all-MiniLM-L6-v2')
groups = load_stochastic_runs(DATA_DIR)

# Pre-compute all BERTScores once, then apply thresholds
group_scores = {}

for group_key, runs in sorted(groups.items()):
    if len(runs) < N_REF + 1:
        continue

    target = runs[0]
    references = [r["response"] for r in runs[1:N_REF+1]]
    claims = extract_claims(target["response"])

    print(f"Computing BERTScores: {group_key} ({len(claims)} claims x {len(references)} refs)")

    claim_embeddings = model.encode(claims, convert_to_tensor=True)

    claim_scores = []  # per-claim: list of max-sim scores across references
    for i, claim in enumerate(claims):
        support_scores = []
        for other_resp in references:
            other_sentences = extract_claims(other_resp)
            if not other_sentences:
                continue
            other_emb = model.encode(other_sentences, convert_to_tensor=True)
            cosine = util.cos_sim(claim_embeddings[i:i+1], other_emb)
            support_scores.append(float(cosine.max()))
        claim_scores.append(support_scores)

    group_scores[group_key] = {
        "claims": claims,
        "scores": claim_scores,
        "model": target["model"],
        "scenario": target["scenario"],
    }

# Apply each threshold
results = {}
for thresh in THRESHOLDS:
    thresh_key = f"{thresh:.2f}"
    results[thresh_key] = {"threshold": thresh, "groups": {}}

    total_factual = 0
    total_claims = 0

    for group_key, data in sorted(group_scores.items()):
        n_claims = len(data["claims"])
        n_factual = 0

        for scores in data["scores"]:
            avg = sum(scores) / len(scores) if scores else 0
            if avg > thresh:
                n_factual += 1

        pass_rate = round(n_factual / max(n_claims, 1), 3)
        results[thresh_key]["groups"][group_key] = {
            "n_factual": n_factual,
            "n_claims": n_claims,
            "pass_rate": pass_rate,
        }
        total_factual += n_factual
        total_claims += n_claims

    results[thresh_key]["overall"] = {
        "n_factual": total_factual,
        "n_claims": total_claims,
        "pass_rate": round(total_factual / max(total_claims, 1), 3),
    }

with open(OUTPUT, "w") as f:
    json.dump(results, f, indent=2)

# Print summary table
print(f"\n{'='*80}")
print("THRESHOLD SWEEP SUMMARY (n=19 references, BERTScore)")
print(f"{'='*80}")

header = f"{'Threshold':>10}"
group_keys = sorted(group_scores.keys())
for gk in group_keys:
    short = gk.replace("_", " / ")[:20]
    header += f"  {short:>20}"
header += f"  {'OVERALL':>10}"
print(header)
print("-" * len(header))

for thresh in THRESHOLDS:
    tk = f"{thresh:.2f}"
    row = f"{thresh:>10.2f}"
    for gk in group_keys:
        g = results[tk]["groups"][gk]
        row += f"  {g['n_factual']}/{g['n_claims']:>2} ({g['pass_rate']:.0%})".rjust(22)
    o = results[tk]["overall"]
    row += f"  {o['n_factual']}/{o['n_claims']} ({o['pass_rate']:.0%})".rjust(12)
    print(row)

print(f"\nSaved: {OUTPUT}")
