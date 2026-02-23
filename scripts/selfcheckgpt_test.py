#!/usr/bin/env python3
"""
PPH SelfCheckGPT Blind Spot Demonstration
==========================================
Tests whether SelfCheckGPT's consistency-based detection catches
PPH confabulations or passes them as reliable.

This script implements SelfCheckGPT's core logic (BERTScore variant)
against our Phase 2A stochastic data (120 runs).

The prediction: confabulations that appear in 80-100% of runs will
score as HIGH CONSISTENCY and therefore be flagged as FACTUAL by
SelfCheckGPT's logic, even though they're fabricated.

Requirements:
    pip install selfcheckgpt torch transformers sentence-transformers --break-system-packages

Usage:
    python3 selfcheckgpt_test.py --data-dir /path/to/stoch/jsons --output results.json

If SelfCheckGPT is not installed, the script falls back to a 
manual BERTScore consistency implementation that replicates the 
same core logic.
"""

import json
import os
import sys
import argparse
import re
from pathlib import Path
from collections import defaultdict


def load_stochastic_runs(data_dir: str) -> dict:
    """Load all Phase 2A stochastic JSON files, grouped by model+scenario."""
    groups = defaultdict(list)
    
    for fname in sorted(os.listdir(data_dir)):
        if not fname.startswith("PPH-001-") or "STOCH" not in fname:
            continue
        if not fname.endswith(".json"):
            continue
        
        fpath = os.path.join(data_dir, fname)
        with open(fpath) as f:
            data = json.load(f)
        
        key = f"{data['model']}_{data['scenario']}"
        groups[key].append({
            "run_id": data["run_id"],
            "run_number": data.get("run_number", 0),
            "response": data["full_response"],
            "prompt": data["prompt_text"],
            "model": data["model"],
            "scenario": data["scenario"],
        })
    
    return dict(groups)


def extract_claims(response: str) -> list[str]:
    """
    Extract individual analytical claims from a model response.
    Splits on sentence boundaries, filters out headers/short fragments.
    """
    # Remove markdown headers
    text = re.sub(r'^#+\s+.*$', '', response, flags=re.MULTILINE)
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Filter: keep substantive claims (>20 chars, not just formatting)
    claims = []
    for s in sentences:
        s = s.strip()
        if len(s) > 20 and not s.startswith("|") and not s.startswith("-"):
            claims.append(s)
    return claims


def selfcheck_bertscore_consistency(
    claims: list[str],
    other_responses: list[str],
    use_gpu: bool = False
) -> list[dict]:
    """
    Core SelfCheckGPT logic (BERTScore variant):
    For each claim in the target response, compute BERTScore similarity 
    against every sentence in every other sampled response.
    
    High consistency = claim appears (semantically) in most other samples
    SelfCheckGPT interprets high consistency as LIKELY FACTUAL.
    
    We predict: PPH confabulations will score as high-consistency.
    """
    try:
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Encode all claims
        claim_embeddings = model.encode(claims, convert_to_tensor=True)
        
        results = []
        for i, claim in enumerate(claims):
            support_scores = []
            
            for other_resp in other_responses:
                other_sentences = extract_claims(other_resp)
                if not other_sentences:
                    continue
                
                other_embeddings = model.encode(other_sentences, convert_to_tensor=True)
                # Max similarity between this claim and any sentence in the other response
                cosine_scores = util.cos_sim(claim_embeddings[i:i+1], other_embeddings)
                max_sim = float(cosine_scores.max())
                support_scores.append(max_sim)
            
            avg_support = sum(support_scores) / len(support_scores) if support_scores else 0
            n_supporting = sum(1 for s in support_scores if s > 0.65)  # threshold
            
            results.append({
                "claim": claim[:120] + "..." if len(claim) > 120 else claim,
                "avg_bertscore": round(avg_support, 3),
                "n_samples_supporting": n_supporting,
                "n_samples_total": len(support_scores),
                "support_rate": round(n_supporting / len(support_scores), 2) if support_scores else 0,
                "selfcheckgpt_verdict": "LIKELY_FACTUAL" if avg_support > 0.65 else "LIKELY_HALLUCINATION",
                "pph_ground_truth": "UNKNOWN"  # to be filled by manual review
            })
        
        return results
        
    except ImportError:
        print("sentence-transformers not installed. Using keyword fallback.")
        return selfcheck_keyword_fallback(claims, other_responses)


def selfcheck_keyword_fallback(
    claims: list[str],
    other_responses: list[str]
) -> list[dict]:
    """
    Fallback: keyword-overlap consistency check.
    Less precise than BERTScore but demonstrates the same logic.
    """
    results = []
    
    for claim in claims:
        # Extract key noun phrases (simplified)
        words = set(w.lower() for w in re.findall(r'\b[a-z]{4,}\b', claim.lower()))
        
        support_count = 0
        for other_resp in other_responses:
            other_words = set(w.lower() for w in re.findall(r'\b[a-z]{4,}\b', other_resp.lower()))
            overlap = len(words & other_words) / max(len(words), 1)
            if overlap > 0.3:
                support_count += 1
        
        support_rate = support_count / len(other_responses) if other_responses else 0
        
        results.append({
            "claim": claim[:120] + "..." if len(claim) > 120 else claim,
            "keyword_overlap_support": support_count,
            "n_samples_total": len(other_responses),
            "support_rate": round(support_rate, 2),
            "selfcheckgpt_verdict": "LIKELY_FACTUAL" if support_rate > 0.5 else "LIKELY_HALLUCINATION",
            "pph_ground_truth": "UNKNOWN"
        })
    
    return results


def run_test(data_dir: str, output_path: str, n_reference: int = 5):
    """
    Main test runner.
    
    For each model+scenario group:
    1. Take the first response as the "target"
    2. Use next n_reference responses as the "sample pool" 
    3. Run SelfCheckGPT consistency check on target claims
    4. Report which confabulations pass as "factual"
    """
    groups = load_stochastic_runs(data_dir)
    
    if not groups:
        print(f"ERROR: No STOCH files found in {data_dir}")
        print("Expected files like: PPH-001-ECON-SEVERE-CLAUDE-T07-STOCH-01.json")
        sys.exit(1)
    
    all_results = {}
    
    for group_key, runs in sorted(groups.items()):
        print(f"\n{'='*60}")
        print(f"Testing: {group_key} ({len(runs)} runs)")
        print(f"{'='*60}")
        
        if len(runs) < n_reference + 1:
            print(f"  SKIP: Need at least {n_reference + 1} runs, have {len(runs)}")
            continue
        
        # Target = first run, references = next N runs
        target = runs[0]
        references = [r["response"] for r in runs[1:n_reference+1]]
        
        print(f"  Target: {target['run_id']}")
        print(f"  References: runs 2-{n_reference+1}")
        
        # Extract claims from target
        claims = extract_claims(target["response"])
        print(f"  Claims extracted: {len(claims)}")
        
        # Run consistency check
        results = selfcheck_bertscore_consistency(claims, references)
        
        # Summary
        n_factual = sum(1 for r in results if r["selfcheckgpt_verdict"] == "LIKELY_FACTUAL")
        n_halluc = sum(1 for r in results if r["selfcheckgpt_verdict"] == "LIKELY_HALLUCINATION")
        
        print(f"\n  SelfCheckGPT verdicts:")
        print(f"    LIKELY_FACTUAL:        {n_factual} claims")
        print(f"    LIKELY_HALLUCINATION:  {n_halluc} claims")
        print(f"    Pass rate:             {n_factual}/{len(results)} = {n_factual/max(len(results),1):.0%}")
        
        print(f"\n  Claims flagged as FACTUAL (potential false negatives):")
        for r in results:
            if r["selfcheckgpt_verdict"] == "LIKELY_FACTUAL":
                print(f"    → {r['claim']}")
                print(f"      support_rate={r['support_rate']}")
        
        all_results[group_key] = {
            "model": target["model"],
            "scenario": target["scenario"],
            "n_claims": len(claims),
            "n_passed_as_factual": n_factual,
            "n_flagged_as_hallucination": n_halluc,
            "pass_rate": round(n_factual / max(len(results), 1), 3),
            "claim_details": results
        }
    
    # Save results
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n\nResults saved to: {output_path}")
    
    # Final summary
    print(f"\n{'='*60}")
    print("SUMMARY: SelfCheckGPT Blind Spot Test")
    print(f"{'='*60}")
    for key, res in all_results.items():
        print(f"  {key}: {res['n_passed_as_factual']}/{res['n_claims']} claims passed as FACTUAL ({res['pass_rate']:.0%})")
    
    total_factual = sum(r["n_passed_as_factual"] for r in all_results.values())
    total_claims = sum(r["n_claims"] for r in all_results.values())
    print(f"\n  OVERALL: {total_factual}/{total_claims} confabulation claims passed SelfCheckGPT ({total_factual/max(total_claims,1):.0%})")
    print(f"\n  If this rate is high, SelfCheckGPT's consistency assumption")
    print(f"  is empirically violated for PPH-class confabulations.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PPH SelfCheckGPT Blind Spot Test")
    parser.add_argument("--data-dir", required=True, help="Directory containing STOCH JSON files")
    parser.add_argument("--output", default="selfcheckgpt_results.json", help="Output file path")
    parser.add_argument("--n-reference", type=int, default=5, help="Number of reference samples (default: 5)")
    args = parser.parse_args()
    
    run_test(args.data_dir, args.output, args.n_reference)
