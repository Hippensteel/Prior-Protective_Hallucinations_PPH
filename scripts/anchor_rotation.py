#!/usr/bin/env python3
"""
PPH SelfCheckGPT Anchor Rotation
Tests every run as anchor to check result stability.
"""

import json
import sys
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from selfcheckgpt_test import load_stochastic_runs, extract_claims
from sentence_transformers import SentenceTransformer, util

DATA_DIR = str(REPO_DIR / "data" / "phase2a") + "/"
OUTPUT = str(REPO_DIR / "data" / "phase2a" / "selfcheckgpt_anchor_rotation.json")
THRESHOLD = 0.65

model = SentenceTransformer('all-MiniLM-L6-v2')
groups = load_stochastic_runs(DATA_DIR)

results = {}

for group_key, runs in sorted(groups.items()):
    n_runs = len(runs)
    if n_runs < 2:
        continue

    print(f"\n{'='*60}")
    print(f"Anchor rotation: {group_key} ({n_runs} runs)")
    print(f"{'='*60}")

    anchor_pass_rates = []

    for anchor_idx in range(n_runs):
        target = runs[anchor_idx]
        references = [r["response"] for r in runs if r["run_id"] != target["run_id"]]

        claims = extract_claims(target["response"])
        if not claims:
            anchor_pass_rates.append(0.0)
            continue

        claim_embeddings = model.encode(claims, convert_to_tensor=True)

        n_factual = 0
        for i, claim in enumerate(claims):
            support_scores = []
            for other_resp in references:
                other_sentences = extract_claims(other_resp)
                if not other_sentences:
                    continue
                other_emb = model.encode(other_sentences, convert_to_tensor=True)
                cosine = util.cos_sim(claim_embeddings[i:i+1], other_emb)
                support_scores.append(float(cosine.max()))

            avg = sum(support_scores) / len(support_scores) if support_scores else 0
            if avg > THRESHOLD:
                n_factual += 1

        pass_rate = n_factual / len(claims)
        anchor_pass_rates.append(pass_rate)
        print(f"  Anchor {anchor_idx+1:>2}: {n_factual}/{len(claims)} claims = {pass_rate:.0%}")

    arr = np.array(anchor_pass_rates)
    results[group_key] = {
        "model": runs[0]["model"],
        "scenario": runs[0]["scenario"],
        "n_anchors": n_runs,
        "threshold": THRESHOLD,
        "per_anchor_pass_rates": [round(x, 3) for x in anchor_pass_rates],
        "mean": round(float(arr.mean()), 3),
        "std": round(float(arr.std()), 3),
        "min": round(float(arr.min()), 3),
        "max": round(float(arr.max()), 3),
        "range": round(float(arr.max() - arr.min()), 3),
    }

with open(OUTPUT, "w") as f:
    json.dump(results, f, indent=2)

# Print summary
print(f"\n{'='*70}")
print("ANCHOR ROTATION SUMMARY (threshold=0.65, all 20 anchors)")
print(f"{'='*70}")
print(f"{'Group':<35} {'Mean':>6} {'Std':>6} {'Min':>6} {'Max':>6} {'Range':>6}")
print("-" * 70)

for gk, res in sorted(results.items()):
    print(f"{gk:<35} {res['mean']:>5.0%} {res['std']:>6.3f} {res['min']:>5.0%} {res['max']:>5.0%} {res['range']:>6.3f}")

# Overall
all_means = [r["mean"] for r in results.values()]
print(f"\n{'Overall mean of means:':<35} {np.mean(all_means):.0%}")
print(f"{'Overall std of means:':<35} {np.std(all_means):.3f}")

print(f"\nSaved: {OUTPUT}")
